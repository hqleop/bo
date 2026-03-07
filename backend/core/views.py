import base64
import hashlib
import json
import logging
import re
import time

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import (
    ValidationError as DRFValidationError,
    PermissionDenied,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q, Exists, OuterRef
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from .models import (
    Company,
    CompanySupplier,
    CompanyUser,
    Role,
    Permission,
    Notification,
    Branch,
    Department,
    BranchUser,
    DepartmentUser,
    Category,
    CategoryUser,
    CountryBusinessNumber,
    CpvDictionary,
    ExpenseArticle,
    ExpenseArticleUser,
    Currency,
    TenderCriterion,
    TenderAttribute,
    ApprovalModelRole,
    ApprovalModelRoleUser,
    ApprovalRangeMatrix,
    ApprovalModel,
    ApprovalModelStep,
    ProcurementTender,
    ProcurementTenderCriterion,
    ProcurementTenderPosition,
    TenderProposal,
    TenderProposalPosition,
    ProcurementTenderFile,
    SalesTender,
    SalesTenderCriterion,
    SalesTenderPosition,
    SalesTenderProposal,
    SalesTenderProposalPosition,
    SalesTenderFile,
    TenderApprovalJournal,
    TenderApprovalStageState,
    TenderApprovalStageStep,
    TenderApprovalStageStepUser,
    UnitOfMeasure,
    Nomenclature,
)
from .serializers import (
    UserSerializer,
    UserRegistrationStep1Serializer,
    CompanySerializer,
    CompanyListSerializer,
    CompanyCreateSerializer,
    CompanySupplierSerializer,
    CompanySupplierListSerializer,
    AddCompanySupplierSerializer,
    CompanyRegistrationStep2Serializer,
    CompanyRegistrationStep3Serializer,
    ExistingCompanyStep2Serializer,
    CompanyCpvSerializer,
    CountryBusinessNumberSerializer,
    RegistrationCompanyLookupSerializer,
    RegistrationCompanyLookupCompanySerializer,
    PermissionSerializer,
    RoleSerializer,
    CompanyUserSerializer,
    NotificationSerializer,
    MeSerializer,
    ProfileUpdateSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordChangeSerializer,
    BranchSerializer,
    DepartmentSerializer,
    BranchUserSerializer,
    DepartmentUserSerializer,
    CategorySerializer,
    CategoryUserSerializer,
    ExpenseArticleSerializer,
    ExpenseArticleUserSerializer,
    UnitOfMeasureSerializer,
    NomenclatureSerializer,
    CurrencySerializer,
    TenderCriterionSerializer,
    TenderAttributeSerializer,
    ApprovalModelRoleSerializer,
    ApprovalModelRoleUserSerializer,
    ApprovalRangeMatrixSerializer,
    ApprovalModelSerializer,
    ApprovalModelStepSerializer,
    ProcurementTenderSerializer,
    ProcurementTenderListSerializer,
    ProcurementParticipationTenderListSerializer,
    TenderProposalSerializer,
    TenderProposalStatusSerializer,
    TenderProposalPositionUpdateSerializer,
    ProcurementTenderFileSerializer,
    SalesTenderSerializer,
    SalesTenderListSerializer,
    SalesParticipationTenderListSerializer,
    SalesTenderProposalSerializer,
    SalesTenderProposalStatusSerializer,
    SalesTenderFileSerializer,
    TenderApprovalJournalSerializer,
)
from .realtime import publish_tender_event

User = get_user_model()
status_sync_logger = logging.getLogger("core.status_sync")
try:
    STATUS_SYNC_CACHE_TTL_SECONDS = max(
        0, int(getattr(settings, "STATUS_SYNC_CACHE_TTL_SECONDS", 2))
    )
except (TypeError, ValueError):
    STATUS_SYNC_CACHE_TTL_SECONDS = 2
try:
    STATUS_SYNC_THROTTLE_PER_MINUTE = max(
        0, int(getattr(settings, "STATUS_SYNC_THROTTLE_PER_MINUTE", 120))
    )
except (TypeError, ValueError):
    STATUS_SYNC_THROTTLE_PER_MINUTE = 120
STATUS_SYNC_LOG_METRICS = bool(getattr(settings, "STATUS_SYNC_LOG_METRICS", False))


def _resolve_request_company_id(request):
    """
    Resolve an approved company for the current user.
    If user has multiple approved companies, explicit company_id is required.
    """
    explicit_company_id = request.data.get("company_id") if hasattr(request, "data") else None
    if explicit_company_id is None:
        query_params = getattr(request, "query_params", None)
        if query_params is None:
            query_params = getattr(request, "GET", {})
        explicit_company_id = query_params.get("company_id")

    user_company_ids = list(
        CompanyUser.objects.filter(
            user=request.user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
    )
    if not user_company_ids:
        return None, Response(
            {"detail": "РќРµРјРѕР¶Р»РёРІРѕ РІРёР·РЅР°С‡РёС‚Рё РєРѕРјРїР°РЅС–СЋ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if explicit_company_id is not None:
        try:
            company_id = int(explicit_company_id)
        except (TypeError, ValueError):
            return None, Response(
                {"detail": "РќРµРєРѕСЂРµРєС‚РЅРёР№ company_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if company_id not in user_company_ids:
            return None, Response(
                {"detail": "РљРѕРјРїР°РЅС–СЏ РЅРµ РЅР°Р»РµР¶РёС‚СЊ РїРѕС‚РѕС‡РЅРѕРјСѓ РєРѕСЂРёСЃС‚СѓРІР°С‡Сѓ."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return company_id, None

    if len(user_company_ids) > 1:
        return None, Response(
            {"detail": "РћР±РµСЂС–С‚СЊ company_id РґР»СЏ РІРёРєРѕРЅР°РЅРЅСЏ РґС–С—."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return user_company_ids[0], None


def _parse_int_param(value, default=1, min_value=1):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, parsed)


def _parse_int_list_param(raw_values):
    if raw_values is None:
        return []
    if isinstance(raw_values, str):
        raw_values = [raw_values]
    out = []
    for raw in raw_values:
        for part in str(raw).split(","):
            part = part.strip()
            if not part:
                continue
            try:
                out.append(int(part))
            except (TypeError, ValueError):
                continue
    # preserve order, drop duplicates
    return list(dict.fromkeys(out))


def _is_truthy_query_param(raw_value):
    return str(raw_value or "").strip().lower() in {"1", "true", "yes", "on"}


def _expand_tree_ids_with_ancestors(model_cls, source_ids):
    pending = {int(item_id) for item_id in source_ids if item_id is not None}
    all_ids = set(pending)
    while pending:
        parent_ids = set(
            model_cls.objects.filter(id__in=pending)
            .exclude(parent_id__isnull=True)
            .values_list("parent_id", flat=True)
        )
        new_ids = parent_ids - all_ids
        if not new_ids:
            break
        all_ids.update(new_ids)
        pending = new_ids
    return all_ids


def _normalize_alnum_token(value):
    return re.sub(r"[^0-9a-zР°-СЏС–С—С”Т‘]", "", str(value or "").strip().casefold())


def _filter_participation_qs_by_tender_number(qs, tender_number, suffix):
    token = _normalize_alnum_token(tender_number)
    if not token:
        return qs

    if token.isdigit():
        try:
            return qs.filter(number=int(token))
        except (TypeError, ValueError):
            return qs.none()

    matched_ids = []
    for item in qs.values("id", "company_id", "number"):
        company_id = item.get("company_id")
        number = item.get("number")
        if not company_id or not number:
            continue
        display_token = _normalize_alnum_token(f"{number}-{company_id}-{suffix}")
        if display_token == token:
            matched_ids.append(item["id"])

    if not matched_ids:
        return qs.none()
    return qs.filter(id__in=matched_ids)


def _parse_iso_datetime_param(raw_value):
    value = str(raw_value or "").strip()
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _author_task_action_label(stage):
    if stage == "preparation":
        return "Виконати підготовку процедури"
    if stage == "decision":
        return "Прийняти рішення"
    if stage == "approval":
        return "Затвердити рішення"
    return "Опрацювати тендер"


def _approver_task_action_label(stage):
    if stage == TenderApprovalStageState.Stage.PREPARATION:
        return "Погодити підготовку процедури"
    if stage == TenderApprovalStageState.Stage.APPROVAL:
        return "Погодити рішення"
    return "Погодити тендер"


def _approval_stage_label(stage):
    return dict(TenderApprovalStageState.Stage.choices).get(stage, str(stage or ""))


def _count_active_approver_tasks(*, user, is_sales):
    filters = {
        "user": user,
        "status": TenderApprovalStageStepUser.Status.ACTIVE,
        "step__stage_state__stage__in": [
            TenderApprovalStageState.Stage.PREPARATION,
            TenderApprovalStageState.Stage.APPROVAL,
        ],
    }
    if is_sales:
        filters["step__stage_state__sales_tender__isnull"] = False
        return (
            TenderApprovalStageStepUser.objects.filter(**filters)
            .values(
                "step__stage_state__sales_tender_id",
                "step__stage_state__stage",
            )
            .distinct()
            .count()
        )
    filters["step__stage_state__procurement_tender__isnull"] = False
    return (
        TenderApprovalStageStepUser.objects.filter(**filters)
        .values(
            "step__stage_state__procurement_tender_id",
            "step__stage_state__stage",
        )
        .distinct()
        .count()
    )


def _collect_active_approver_tasks(*, user, is_sales):
    filters = {
        "user": user,
        "status": TenderApprovalStageStepUser.Status.ACTIVE,
        "step__stage_state__stage__in": [
            TenderApprovalStageState.Stage.PREPARATION,
            TenderApprovalStageState.Stage.APPROVAL,
        ],
    }
    if is_sales:
        filters["step__stage_state__sales_tender__isnull"] = False
        qs = TenderApprovalStageStepUser.objects.filter(**filters).select_related(
            "step__stage_state",
            "step__stage_state__sales_tender",
            "step__stage_state__sales_tender__created_by",
        )
    else:
        filters["step__stage_state__procurement_tender__isnull"] = False
        qs = TenderApprovalStageStepUser.objects.filter(**filters).select_related(
            "step__stage_state",
            "step__stage_state__procurement_tender",
            "step__stage_state__procurement_tender__created_by",
        )

    tasks = []
    seen = set()
    for step_user in qs.order_by("-step__stage_state__updated_at", "-id"):
        stage_state = step_user.step.stage_state
        tender = stage_state.sales_tender if is_sales else stage_state.procurement_tender
        if not tender:
            continue
        task_key = (int(tender.id), str(stage_state.stage or ""))
        if task_key in seen:
            continue
        seen.add(task_key)
        tasks.append(
            {
                "tender": tender,
                "stage": stage_state.stage,
                "task_action": _approver_task_action_label(stage_state.stage),
                "task_created_at": stage_state.updated_at or step_user.created_at,
            }
        )
    return tasks


def _build_status_sync_cache_key(
    *,
    kind: str,
    tender_id: int,
    user_id: int,
    updated_since,
):
    raw = "|".join(
        [
            "status-sync-v1",
            str(kind),
            str(tender_id),
            str(user_id),
            str(updated_since.isoformat() if updated_since is not None else ""),
        ]
    )
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return f"status-sync:{kind}:{tender_id}:{user_id}:{digest}"


def _status_sync_log(event: str, **payload):
    if not STATUS_SYNC_LOG_METRICS:
        return
    details = " ".join(f"{k}={v}" for k, v in payload.items())
    status_sync_logger.info("status_sync event=%s %s", event, details)


def _status_sync_rate_limit_key(*, kind: str, tender_id: int, actor_key: str, minute_bucket: int):
    raw = f"status-sync-rate-v1|{kind}|{tender_id}|{actor_key}|{minute_bucket}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return f"status-sync-rate:{digest}"


def _enforce_status_sync_rate_limit(*, request, kind: str, tender_id: int):
    if STATUS_SYNC_THROTTLE_PER_MINUTE <= 0:
        return None, None

    actor_key = "anon"
    user_id = None
    if request.user and request.user.is_authenticated:
        user_id = int(request.user.id)
        actor_key = f"user:{user_id}"
    else:
        actor_key = f"ip:{str(request.META.get('REMOTE_ADDR') or 'unknown')}"
    now_ts = int(time.time())
    minute_bucket = now_ts // 60
    cache_key = _status_sync_rate_limit_key(
        kind=kind,
        tender_id=int(tender_id),
        actor_key=actor_key,
        minute_bucket=minute_bucket,
    )

    current = cache.get(cache_key)
    if current is None:
        cache.set(cache_key, 1, 65)
        current = 1
    else:
        try:
            current = cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, 1, 65)
            current = 1
    remaining = max(0, STATUS_SYNC_THROTTLE_PER_MINUTE - int(current))
    if int(current) <= STATUS_SYNC_THROTTLE_PER_MINUTE:
        return None, remaining

    retry_after = max(1, 60 - (now_ts % 60))
    response = Response(
        {"detail": "Too many status sync requests. Please retry shortly."},
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
    response["Retry-After"] = str(retry_after)
    response["X-Status-Sync-RateLimit-Limit"] = str(STATUS_SYNC_THROTTLE_PER_MINUTE)
    response["X-Status-Sync-RateLimit-Remaining"] = "0"
    _status_sync_log(
        "throttle",
        kind=kind,
        tender_id=int(tender_id),
        user_id=user_id,
        actor=actor_key,
        limit=STATUS_SYNC_THROTTLE_PER_MINUTE,
    )
    return response, 0


def _encode_cursor_token(updated_at, object_id: int):
    if updated_at is None:
        return None
    payload = {
        "u": updated_at.isoformat(),
        "id": int(object_id),
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor_token(raw_cursor):
    raw_value = str(raw_cursor or "").strip()
    if not raw_value:
        return None
    try:
        padded = raw_value + ("=" * ((4 - len(raw_value) % 4) % 4))
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        payload = json.loads(decoded)
        updated_at = _parse_iso_datetime_param(payload.get("u"))
        object_id = int(payload.get("id"))
        if updated_at is None or object_id <= 0:
            return None
        return updated_at, object_id
    except Exception:
        return None


def _paginate_by_updated_cursor(*, qs, cursor, page_size: int):
    cursor_payload = _decode_cursor_token(cursor)
    if cursor_payload is not None:
        cursor_updated_at, cursor_object_id = cursor_payload
        qs = qs.filter(
            Q(updated_at__lt=cursor_updated_at)
            | (Q(updated_at=cursor_updated_at) & Q(id__lt=cursor_object_id))
        )
    rows = list(qs.order_by("-updated_at", "-id")[: page_size + 1])
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = None
    if has_more and rows:
        last_item = rows[-1]
        next_cursor = _encode_cursor_token(
            getattr(last_item, "updated_at", None),
            int(getattr(last_item, "id", 0)),
        )
    return rows, next_cursor, has_more


def _create_tender_approval_journal_entry(
    *,
    action: str,
    actor,
    stage: str = "",
    comment: str = "",
    procurement_tender=None,
    sales_tender=None,
):
    if procurement_tender is None and sales_tender is None:
        return
    TenderApprovalJournal.objects.create(
        procurement_tender=procurement_tender,
        sales_tender=sales_tender,
        stage=stage or "",
        action=action,
        comment=comment or "",
        actor=actor,
    )


def _format_journal_datetime(value):
    if not value:
        return ""
    dt_value = value
    if timezone.is_naive(dt_value):
        dt_value = timezone.make_aware(dt_value, timezone.get_current_timezone())
    try:
        dt_value = timezone.localtime(dt_value)
    except Exception:
        pass
    return dt_value.strftime("%d.%m.%Y %H:%M")


def _format_acceptance_period_comment(*, tender):
    start_text = _format_journal_datetime(getattr(tender, "start_at", None))
    end_text = _format_journal_datetime(getattr(tender, "end_at", None))
    if start_text and end_text:
        return f"{start_text} - {end_text}"
    if start_text:
        return start_text
    if end_text:
        return end_text
    return ""


def _log_tender_update_journal(
    *,
    before_stage: str,
    tender,
    request_data,
    actor,
    is_sales: bool,
):
    after_stage = tender.stage or ""
    request_keys = set(getattr(request_data, "keys", lambda: [])())
    target = {"sales_tender": tender} if is_sales else {"procurement_tender": tender}

    if before_stage == "passport" and after_stage == "preparation":
        _create_tender_approval_journal_entry(
            action=TenderApprovalJournal.Action.SAVED,
            actor=actor,
            stage=after_stage,
            comment="Збереження паспорта тендера",
            **target,
        )
        return

    if before_stage == "preparation" and after_stage == "acceptance":
        _create_tender_approval_journal_entry(
            action=TenderApprovalJournal.Action.PUBLISHED,
            actor=actor,
            stage=after_stage,
            comment="Погодження та публікація тендера",
            **target,
        )
        return

    acceptance_timing_changed = (
        before_stage == "acceptance"
        and after_stage == "acceptance"
        and ("start_at" in request_keys or "end_at" in request_keys)
    )
    acceptance_resumed = before_stage == "decision" and after_stage == "acceptance"
    if acceptance_timing_changed or acceptance_resumed:
        _create_tender_approval_journal_entry(
            action=TenderApprovalJournal.Action.SAVED,
            actor=actor,
            stage=after_stage,
            comment=_format_acceptance_period_comment(tender=tender),
            **target,
        )
        return

    if (
        before_stage == "preparation"
        and after_stage == "preparation"
        and (
            "positions" in request_keys
            or "criterion_ids" in request_keys
            or "attribute_ids" in request_keys
        )
    ):
        _create_tender_approval_journal_entry(
            action=TenderApprovalJournal.Action.SAVED,
            actor=actor,
            stage=after_stage,
            comment="Збереження підготовки процедури",
            **target,
        )


def _format_user_display_name(user):
    if not user:
        return ""
    full_name = " ".join(
        part
        for part in [
            getattr(user, "last_name", ""),
            getattr(user, "first_name", ""),
            getattr(user, "middle_name", ""),
        ]
        if part
    ).strip()
    return full_name or getattr(user, "email", "") or str(user)


def _format_user_short_name(full_name):
    tokens = [token for token in str(full_name or "").split() if token]
    if not tokens:
        return ""
    if len(tokens) == 1:
        return tokens[0]
    last_name = tokens[0]
    initials = "".join(f"{token[0]}." for token in tokens[1:] if token)
    return f"{last_name} {initials}".strip()


def _stage_state_target_kwargs(*, tender, is_sales):
    return {"sales_tender": tender} if is_sales else {"procurement_tender": tender}


def _ensure_stage_state_snapshot(*, tender, is_sales, stage, rebuild=False):
    target = _stage_state_target_kwargs(tender=tender, is_sales=is_sales)
    stage_state, _ = TenderApprovalStageState.objects.get_or_create(
        stage=stage,
        defaults={
            **target,
            "status": TenderApprovalStageState.Status.WAITING_AUTHOR,
            "current_order": None,
        },
        **target,
    )

    approval_model = getattr(tender, "approval_model", None)
    if approval_model is None:
        if stage_state.steps.exists():
            stage_state.steps.all().delete()
        if (
            stage_state.status != TenderApprovalStageState.Status.WAITING_AUTHOR
            or stage_state.current_order is not None
        ):
            stage_state.status = TenderApprovalStageState.Status.WAITING_AUTHOR
            stage_state.current_order = None
            stage_state.save(update_fields=["status", "current_order", "updated_at"])
        return stage_state, False

    if not rebuild and stage_state.steps.exists():
        return stage_state, True

    stage_state.steps.all().delete()
    model_steps = (
        approval_model.steps.select_related("role")
        .prefetch_related("role__role_users__user")
        .order_by("order", "id")
    )
    step_order = 1
    for model_step in model_steps:
        role = getattr(model_step, "role", None)
        if not role:
            continue
        role_users = list(role.role_users.select_related("user").all())
        if not role_users:
            continue
        rule = (
            model_step.preparation_rule
            if stage == TenderApprovalStageState.Stage.PREPARATION
            else model_step.approval_rule
        )
        snapshot_step = TenderApprovalStageStep.objects.create(
            stage_state=stage_state,
            order=step_order,
            role=role,
            role_name=role.name or "",
            approval_rule=rule or ApprovalModelStep.DecisionRule.ONE_OF,
        )
        for membership in role_users:
            user = getattr(membership, "user", None)
            if not user:
                continue
            TenderApprovalStageStepUser.objects.create(
                step=snapshot_step,
                user=user,
                full_name=_format_user_display_name(user),
                status=TenderApprovalStageStepUser.Status.PENDING,
            )
        if snapshot_step.step_users.exists():
            step_order += 1
        else:
            snapshot_step.delete()

    has_approvers = stage_state.steps.exists()
    stage_state.status = TenderApprovalStageState.Status.WAITING_AUTHOR
    stage_state.current_order = None
    stage_state.save(update_fields=["status", "current_order", "updated_at"])
    return stage_state, has_approvers


def _start_stage_approval_cycle(stage_state, *, increment_cycle=False):
    if not stage_state:
        return False

    step_users_qs = TenderApprovalStageStepUser.objects.filter(
        step__stage_state=stage_state
    )
    step_users_qs.update(
        status=TenderApprovalStageStepUser.Status.PENDING,
        acted_at=None,
        comment="",
    )
    first_step = stage_state.steps.order_by("order", "id").first()
    if not first_step:
        update_fields = ["status", "current_order", "updated_at"]
        stage_state.status = TenderApprovalStageState.Status.APPROVED
        stage_state.current_order = None
        if increment_cycle:
            stage_state.cycle = (stage_state.cycle or 1) + 1
            update_fields.append("cycle")
        stage_state.save(update_fields=update_fields)
        return False

    first_step.step_users.update(status=TenderApprovalStageStepUser.Status.ACTIVE)
    update_fields = ["status", "current_order", "updated_at"]
    stage_state.status = TenderApprovalStageState.Status.IN_PROGRESS
    stage_state.current_order = first_step.order
    if increment_cycle:
        stage_state.cycle = (stage_state.cycle or 1) + 1
        update_fields.append("cycle")
    stage_state.save(update_fields=update_fields)
    return True


def _activate_next_stage_step(stage_state, current_step):
    next_step = (
        stage_state.steps.filter(order__gt=current_step.order)
        .order_by("order", "id")
        .first()
    )
    if not next_step:
        stage_state.status = TenderApprovalStageState.Status.APPROVED
        stage_state.current_order = None
        stage_state.save(update_fields=["status", "current_order", "updated_at"])
        return True

    next_step.step_users.update(status=TenderApprovalStageStepUser.Status.ACTIVE)
    stage_state.status = TenderApprovalStageState.Status.IN_PROGRESS
    stage_state.current_order = next_step.order
    stage_state.save(update_fields=["status", "current_order", "updated_at"])
    return False


def _approve_active_stage_user(stage_state, step_user, comment=""):
    now_dt = timezone.now()
    step = step_user.step
    step_user.status = TenderApprovalStageStepUser.Status.APPROVED
    step_user.acted_at = now_dt
    step_user.comment = comment or ""
    step_user.save(update_fields=["status", "acted_at", "comment"])

    rule = step.approval_rule or ApprovalModelStep.DecisionRule.ONE_OF
    if rule == ApprovalModelStep.DecisionRule.ONE_OF:
        step.step_users.exclude(id=step_user.id).filter(
            status__in=[
                TenderApprovalStageStepUser.Status.ACTIVE,
                TenderApprovalStageStepUser.Status.PENDING,
            ]
        ).update(status=TenderApprovalStageStepUser.Status.SKIPPED)
        return _activate_next_stage_step(stage_state, step)

    has_pending_or_active = step.step_users.exclude(
        status=TenderApprovalStageStepUser.Status.APPROVED
    ).exists()
    if has_pending_or_active:
        return False
    return _activate_next_stage_step(stage_state, step)


def _reject_active_stage_user(stage_state, step_user, comment=""):
    now_dt = timezone.now()
    step_user.status = TenderApprovalStageStepUser.Status.REJECTED
    step_user.acted_at = now_dt
    step_user.comment = comment or ""
    step_user.save(update_fields=["status", "acted_at", "comment"])
    TenderApprovalStageStepUser.objects.filter(
        step__stage_state=stage_state,
        status=TenderApprovalStageStepUser.Status.ACTIVE,
    ).exclude(id=step_user.id).update(status=TenderApprovalStageStepUser.Status.PENDING)
    stage_state.status = TenderApprovalStageState.Status.REJECTED
    stage_state.current_order = None
    stage_state.save(update_fields=["status", "current_order", "updated_at"])


def _user_is_tender_approver(*, user, tender, is_sales):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    target = _stage_state_target_kwargs(tender=tender, is_sales=is_sales)
    return TenderApprovalStageStepUser.objects.filter(
        user=user,
        step__stage_state__in=TenderApprovalStageState.objects.filter(**target),
    ).exists()


def _build_tender_approval_route_payload(*, tender, is_sales, user, stage):
    if stage not in {
        TenderApprovalStageState.Stage.PREPARATION,
        TenderApprovalStageState.Stage.APPROVAL,
    }:
        return {
            "stage": stage or "",
            "has_approvers": False,
            "status": "",
            "can_author_submit": False,
            "can_author_publish": False,
            "can_approver_action": False,
            "nodes": [],
        }

    stage_state, has_approvers = _ensure_stage_state_snapshot(
        tender=tender,
        is_sales=is_sales,
        stage=stage,
        rebuild=False,
    )
    if (
        has_approvers
        and stage == TenderApprovalStageState.Stage.APPROVAL
        and stage_state.status == TenderApprovalStageState.Status.WAITING_AUTHOR
    ):
        _start_stage_approval_cycle(stage_state, increment_cycle=False)
        stage_state.refresh_from_db()

    is_author = bool(
        getattr(user, "is_authenticated", False)
        and getattr(tender, "created_by_id", None)
        and int(tender.created_by_id) == int(user.id)
    )

    def map_status(step_user_status):
        if step_user_status == TenderApprovalStageStepUser.Status.ACTIVE:
            return "active"
        if step_user_status == TenderApprovalStageStepUser.Status.APPROVED:
            return "approved"
        return "waiting"

    nodes = []
    author_name = _format_user_display_name(getattr(tender, "created_by", None))
    author_short_name = _format_user_short_name(author_name)

    if not has_approvers:
        nodes.append(
            {
                "kind": "author",
                "label": "Автор тендера",
                "order": 1,
                "users": [
                    {
                        "id": getattr(tender, "created_by_id", None),
                        "full_name": author_name,
                        "short_name": author_short_name,
                        "status": "active" if is_author else "waiting",
                    }
                ],
            }
        )
        return {
            "stage": stage,
            "has_approvers": False,
            "status": stage_state.status or "",
            "can_author_submit": False,
            "can_author_publish": bool(
                stage == TenderApprovalStageState.Stage.PREPARATION and is_author
            ),
            "can_approver_action": False,
            "nodes": nodes,
        }

    current_step_user = TenderApprovalStageStepUser.objects.filter(
        user=user,
        step__stage_state=stage_state,
        status=TenderApprovalStageStepUser.Status.ACTIVE,
    ).first()

    if stage == TenderApprovalStageState.Stage.PREPARATION:
        if stage_state.status in {
            TenderApprovalStageState.Status.WAITING_AUTHOR,
            TenderApprovalStageState.Status.REJECTED,
        }:
            start_author_status = "active" if is_author else "waiting"
        else:
            start_author_status = "approved"
        end_author_status = (
            "active"
            if stage_state.status == TenderApprovalStageState.Status.APPROVED and is_author
            else "waiting"
        )
        nodes.append(
            {
                "kind": "author",
                "label": "Автор тендера",
                "order": 1,
                "users": [
                    {
                        "id": getattr(tender, "created_by_id", None),
                        "full_name": author_name,
                        "short_name": author_short_name,
                        "status": start_author_status,
                    }
                ],
            }
        )

    steps = stage_state.steps.order_by("order", "id").prefetch_related("step_users")
    for step in steps:
        users = []
        for step_user in step.step_users.all():
            users.append(
                {
                    "id": step_user.user_id,
                    "full_name": step_user.full_name,
                    "short_name": _format_user_short_name(step_user.full_name),
                    "status": map_status(step_user.status),
                }
            )
        nodes.append(
            {
                "kind": "role",
                "label": step.role_name or "Роль",
                "order": step.order,
                "approval_rule": step.approval_rule,
                "users": users,
            }
        )

    if stage == TenderApprovalStageState.Stage.PREPARATION:
        nodes.append(
            {
                "kind": "author",
                "label": "Автор тендера",
                "order": 9999,
                "users": [
                    {
                        "id": getattr(tender, "created_by_id", None),
                        "full_name": author_name,
                        "short_name": author_short_name,
                        "status": end_author_status,
                    }
                ],
            }
        )

    can_author_submit = bool(
        is_author
        and stage == TenderApprovalStageState.Stage.PREPARATION
        and stage_state.status
        in {
            TenderApprovalStageState.Status.WAITING_AUTHOR,
            TenderApprovalStageState.Status.REJECTED,
        }
    )
    can_author_publish = bool(
        is_author
        and stage == TenderApprovalStageState.Stage.PREPARATION
        and stage_state.status == TenderApprovalStageState.Status.APPROVED
    )
    can_approver_action = bool(current_step_user)

    return {
        "stage": stage,
        "has_approvers": True,
        "status": stage_state.status or "",
        "can_author_submit": can_author_submit,
        "can_author_publish": can_author_publish,
        "can_approver_action": can_approver_action,
        "nodes": nodes,
    }


def _can_transition_from_preparation(*, tender, is_sales, target_stage):
    if target_stage not in {"acceptance", "decision"}:
        return True
    stage_state, has_approvers = _ensure_stage_state_snapshot(
        tender=tender,
        is_sales=is_sales,
        stage=TenderApprovalStageState.Stage.PREPARATION,
        rebuild=False,
    )
    if not has_approvers:
        return True
    return stage_state.status == TenderApprovalStageState.Status.APPROVED


def _is_tender_author(*, user, tender):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    tender_author_id = getattr(tender, "created_by_id", None)
    if not tender_author_id:
        return False
    try:
        return int(tender_author_id) == int(user.id)
    except (TypeError, ValueError):
        return False


def _ensure_user_can_edit_tender(*, user, tender, is_sales):
    if _is_tender_author(user=user, tender=tender):
        stage = (getattr(tender, "stage", "") or "").strip()
        if stage == TenderApprovalStageState.Stage.PREPARATION:
            stage_state, has_approvers = _ensure_stage_state_snapshot(
                tender=tender,
                is_sales=is_sales,
                stage=TenderApprovalStageState.Stage.PREPARATION,
                rebuild=False,
            )
            if has_approvers and stage_state.status not in {
                TenderApprovalStageState.Status.WAITING_AUTHOR,
                TenderApprovalStageState.Status.REJECTED,
                TenderApprovalStageState.Status.APPROVED,
            }:
                raise PermissionDenied(
                    "Author can edit tender only with active task on preparation stage."
                )
        return
    if _user_is_tender_approver(user=user, tender=tender, is_sales=is_sales):
        raise PermissionDenied("Approver has read-only access to this tender.")


def _validate_preparation_readiness_before_publish(*, tender):
    has_positions = tender.positions.exists()
    has_price_params = bool(
        str(getattr(tender, "price_criterion_vat", "") or "").strip()
        and str(getattr(tender, "price_criterion_delivery", "") or "").strip()
    )
    if not has_positions:
        raise DRFValidationError(
            {"detail": "Додайте хоча б одну позицію тендера перед погодженням."}
        )
    if not has_price_params:
        raise DRFValidationError(
            {
                "detail": (
                    "Налаштуйте параметри цінового критерію "
                    "(ПДВ та Доставка) перед погодженням."
                )
            }
        )


def _submit_tender_preparation_for_approval(*, tender, is_sales, actor, comment=""):
    if (tender.stage or "") != TenderApprovalStageState.Stage.PREPARATION:
        raise DRFValidationError(
            {"detail": "Approval submit is available only on preparation stage."}
        )
    if not _is_tender_author(user=actor, tender=tender):
        raise PermissionDenied("Only tender author can submit for approval.")

    stage_state, has_approvers = _ensure_stage_state_snapshot(
        tender=tender,
        is_sales=is_sales,
        stage=TenderApprovalStageState.Stage.PREPARATION,
        rebuild=False,
    )
    if not has_approvers:
        raise DRFValidationError(
            {"detail": "No approvers configured for preparation stage."}
        )
    _validate_preparation_readiness_before_publish(tender=tender)
    if stage_state.status == TenderApprovalStageState.Status.IN_PROGRESS:
        raise DRFValidationError({"detail": "Approval route is already in progress."})

    increment_cycle = stage_state.status in {
        TenderApprovalStageState.Status.APPROVED,
        TenderApprovalStageState.Status.REJECTED,
    }
    _start_stage_approval_cycle(stage_state, increment_cycle=increment_cycle)
    target = _stage_state_target_kwargs(tender=tender, is_sales=is_sales)
    _create_tender_approval_journal_entry(
        action=TenderApprovalJournal.Action.SAVED,
        actor=actor,
        stage=tender.stage or "",
        comment=comment or "Збереження підготовки процедури",
        **target,
    )
    return stage_state


def _apply_tender_approval_action(*, tender, is_sales, actor, action_type, comment=""):
    if action_type not in {"approved", "rejected"}:
        raise DRFValidationError(
            {"detail": "action must be approved or rejected."}
        )
    if action_type == "rejected" and not comment:
        raise DRFValidationError({"detail": "Comment is required for rejection."})

    stage = (tender.stage or "").strip()
    if stage not in {
        TenderApprovalStageState.Stage.PREPARATION,
        TenderApprovalStageState.Stage.APPROVAL,
    }:
        raise DRFValidationError(
            {"detail": "Approval action is not available on current stage."}
        )

    target = _stage_state_target_kwargs(tender=tender, is_sales=is_sales)
    stage_state, has_approvers = _ensure_stage_state_snapshot(
        tender=tender,
        is_sales=is_sales,
        stage=stage,
        rebuild=False,
    )

    if has_approvers:
        active_step_user = TenderApprovalStageStepUser.objects.filter(
            step__stage_state=stage_state,
            user=actor,
            status=TenderApprovalStageStepUser.Status.ACTIVE,
        ).select_related("step").first()
        if not active_step_user:
            raise PermissionDenied("You do not have an active approval task.")

        if action_type == "approved":
            stage_finished = _approve_active_stage_user(
                stage_state, active_step_user, comment=comment
            )
            if (
                stage == TenderApprovalStageState.Stage.APPROVAL
                and stage_finished
                and tender.stage != "completed"
            ):
                tender.stage = "completed"
                tender.save(update_fields=["stage"])
        else:
            _reject_active_stage_user(stage_state, active_step_user, comment=comment)
            if stage == TenderApprovalStageState.Stage.APPROVAL and tender.stage != "decision":
                tender.stage = "decision"
                tender.save(update_fields=["stage"])

        _create_tender_approval_journal_entry(
            action=action_type,
            actor=actor,
            stage=stage,
            comment=comment,
            **target,
        )
        return

    # Legacy fallback: approval stage without approvers.
    if stage != TenderApprovalStageState.Stage.APPROVAL:
        raise DRFValidationError(
            {"detail": "No approvers configured for this stage."}
        )
    if not _is_tender_author(user=actor, tender=tender):
        raise PermissionDenied("Only tender author can approve or reject.")

    _create_tender_approval_journal_entry(
        action=action_type,
        actor=actor,
        stage=stage,
        comment=comment,
        **target,
    )
    if action_type == "approved":
        tender.stage = "completed"
    else:
        tender.stage = "decision"
    tender.save(update_fields=["stage"])


def _start_approval_stage_cycle_if_needed(*, tender, is_sales):
    stage_state, has_approvers = _ensure_stage_state_snapshot(
        tender=tender,
        is_sales=is_sales,
        stage=TenderApprovalStageState.Stage.APPROVAL,
        rebuild=False,
    )
    if not has_approvers:
        return False
    increment_cycle = (
        stage_state.status != TenderApprovalStageState.Status.WAITING_AUTHOR
        or stage_state.current_order is not None
    )
    _start_stage_approval_cycle(stage_state, increment_cycle=increment_cycle)
    return True


def _expand_cpv_ids_with_descendants(cpv_ids):
    if not cpv_ids:
        return []

    selected = list(
        CpvDictionary.objects.filter(id__in=cpv_ids).values("id", "cpv_level_code")
    )
    if not selected:
        return []

    result_ids = {item["id"] for item in selected}
    pending_level_codes = {
        item["cpv_level_code"] for item in selected if item.get("cpv_level_code")
    }
    processed = set()

    while pending_level_codes:
        level_codes = list(pending_level_codes - processed)
        if not level_codes:
            break
        processed.update(level_codes)
        children = list(
            CpvDictionary.objects.filter(cpv_parent_code__in=level_codes).values(
                "id", "cpv_level_code"
            )
        )
        if not children:
            continue
        for child in children:
            result_ids.add(child["id"])
            next_level_code = child.get("cpv_level_code")
            if next_level_code and next_level_code not in processed:
                pending_level_codes.add(next_level_code)

    return list(result_ids)


def _filter_participation_qs_by_tab(qs, tab):
    if tab == "active":
        return qs.filter(stage="acceptance")
    if tab == "processing":
        return qs.filter(
            Q(stage="decision")
            | Q(stage="approval")
            | (Q(stage="preparation") & Q(tour_number__gt=1))
        )
    if tab == "completed":
        return qs.filter(stage="completed")
    if tab == "journal":
        return qs
    return qs.none()


def _has_non_empty_criterion_value(value):
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


def _get_tender_criteria_rows(tender):
    criteria_items_manager = getattr(tender, "criteria_items", None)
    snapshots = list(criteria_items_manager.all()) if criteria_items_manager is not None else []
    if snapshots:
        return [
            {"id": c.id, "name": c.name, "application": c.application, "is_required": bool(c.is_required)}
            for c in snapshots
            if bool(c.is_required)
        ]
    return list(
        tender.tender_criteria.filter(is_required=True).values("id", "name", "application", "is_required")
    )


def _validate_required_criteria_before_submit(tender, proposal, proposal_position_model):
    required_criteria = _get_tender_criteria_rows(tender)
    if not required_criteria:
        return None

    position_values = list(
        proposal_position_model.objects.filter(proposal=proposal).select_related("tender_position")
    )

    def _criterion_value_from_dict(raw, criterion_id):
        if not isinstance(raw, dict):
            return None
        return raw.get(criterion_id, raw.get(str(criterion_id)))

    missing = []

    required_general = [c for c in required_criteria if c.get("application") == "general"]
    for criterion in required_general:
        is_filled = any(
            _has_non_empty_criterion_value(
                _criterion_value_from_dict(getattr(pv, "criterion_values", {}), criterion["id"])
            )
            for pv in position_values
        )
        if not is_filled:
            missing.append(f"{criterion['name']} (Р·Р°РіР°Р»СЊРЅРёР№)")

    required_individual = [c for c in required_criteria if c.get("application") == "individual"]
    if required_individual:
        for pv in position_values:
            if getattr(pv, "price", None) is None:
                continue
            for criterion in required_individual:
                value = _criterion_value_from_dict(
                    getattr(pv, "criterion_values", {}), criterion["id"]
                )
                if _has_non_empty_criterion_value(value):
                    continue
                pos_name = (
                    getattr(getattr(pv, "tender_position", None), "name", "")
                    or f"РїРѕР·РёС†С–СЏ #{getattr(pv, 'tender_position_id', '?')}"
                )
                missing.append(f"{criterion['name']} ({pos_name})")

    if not missing:
        return None

    return {
        "detail": "РќРµРјРѕР¶Р»РёРІРѕ РїРѕРґР°С‚Рё РїСЂРѕРїРѕР·РёС†С–СЋ. Р—Р°РїРѕРІРЅС–С‚СЊ РѕР±РѕРІ'СЏР·РєРѕРІС– РєСЂРёС‚РµСЂС–С—.",
        "missing_required_criteria": missing,
    }


def _build_cpv_tree_for_tenders_queryset(qs):
    cpv_ids = set(qs.values_list("cpv_category_id", flat=True))
    cpv_ids.discard(None)
    cpv_ids.update(
        qs.values_list("cpv_categories__id", flat=True)
    )
    cpv_ids.discard(None)

    if not cpv_ids:
        return []

    selected = list(
        CpvDictionary.objects.filter(id__in=cpv_ids).values(
            "id", "cpv_code", "name_ua", "cpv_level_code", "cpv_parent_code"
        )
    )
    if not selected:
        return []

    included_by_level = {}
    pending_parent_codes = set()
    for item in selected:
        level_code = item.get("cpv_level_code")
        if level_code:
            included_by_level[level_code] = item
        parent_code = (item.get("cpv_parent_code") or "").strip()
        if parent_code and parent_code != "0":
            pending_parent_codes.add(parent_code)

    processed_parent_codes = set()
    while pending_parent_codes:
        to_fetch = list(pending_parent_codes - processed_parent_codes)
        if not to_fetch:
            break
        processed_parent_codes.update(to_fetch)
        parents = list(
            CpvDictionary.objects.filter(cpv_level_code__in=to_fetch).values(
                "id", "cpv_code", "name_ua", "cpv_level_code", "cpv_parent_code"
            )
        )
        for parent in parents:
            level_code = parent.get("cpv_level_code")
            if level_code:
                included_by_level[level_code] = parent
            parent_code = (parent.get("cpv_parent_code") or "").strip()
            if parent_code and parent_code != "0":
                pending_parent_codes.add(parent_code)

    nodes_by_level = {}
    for item in included_by_level.values():
        level_code = item.get("cpv_level_code")
        if not level_code:
            continue
        nodes_by_level[level_code] = {
            "id": item["id"],
            "cpv_code": item.get("cpv_code") or "",
            "name_ua": item.get("name_ua") or "",
            "label": f"{item.get('cpv_code') or ''} - {item.get('name_ua') or ''}",
            "children": [],
        }

    roots = []
    for level_code, node in nodes_by_level.items():
        parent_code = (included_by_level[level_code].get("cpv_parent_code") or "").strip()
        parent = nodes_by_level.get(parent_code)
        if parent:
            parent["children"].append(node)
        else:
            roots.append(node)

    def sort_tree(items):
        items.sort(key=lambda x: x.get("cpv_code") or "")
        for item in items:
            if item["children"]:
                sort_tree(item["children"])

    sort_tree(roots)
    return roots


def _to_decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _format_decimal_for_error(value):
    if value is None:
        return ""
    normalized = value.normalize()
    text = format(normalized, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _validate_online_auction_position_price(
    *,
    tender,
    position,
    proposal_position_model,
    new_price,
    is_procurement: bool,
):
    if getattr(tender, "conduct_type", "") != "online_auction":
        return None

    start_price = _to_decimal(getattr(position, "start_price", None))
    min_step = _to_decimal(getattr(position, "min_bid_step", None))
    max_step = _to_decimal(getattr(position, "max_bid_step", None))
    new_price_dec = _to_decimal(new_price)

    if start_price is None or min_step is None or max_step is None:
        return "Р”Р»СЏ РїРѕР·РёС†С–С— РЅРµ РЅР°Р»Р°С€С‚РѕРІР°РЅРѕ СЃС‚Р°СЂС‚РѕРІСѓ С†С–РЅСѓ С‚Р° РєСЂРѕРєРё СЃС‚Р°РІРєРё."
    if start_price <= 0 or min_step <= 0 or max_step <= 0 or min_step > max_step:
        return "РќРµРІС–СЂРЅС– РїР°СЂР°РјРµС‚СЂРё СЃС‚Р°РІРєРё РїРѕР·РёС†С–С—: Р·РЅР°С‡РµРЅРЅСЏ РјР°СЋС‚СЊ Р±СѓС‚Рё > 0, Р° РјС–РЅС–РјР°Р»СЊРЅРёР№ РєСЂРѕРє РЅРµ Р±С–Р»СЊС€РёР№ Р·Р° РјР°РєСЃРёРјР°Р»СЊРЅРёР№."
    if new_price_dec is None:
        return "Р’РєР°Р¶С–С‚СЊ РєРѕСЂРµРєС‚РЅСѓ С†С–РЅРѕРІСѓ РїСЂРѕРїРѕР·РёС†С–СЋ."

    current_prices = [
        _to_decimal(v)
        for v in proposal_position_model.objects.filter(
            proposal__tender=tender,
            tender_position=position,
            price__isnull=False,
        ).values_list("price", flat=True)
    ]
    current_prices = [v for v in current_prices if v is not None]

    if current_prices:
        best_price = min(current_prices) if is_procurement else max(current_prices)
        first_point = best_price - min_step if is_procurement else best_price + min_step
        second_point = (
            first_point - max_step if is_procurement else first_point + max_step
        )
    else:
        first_point = start_price
        second_point = start_price - max_step if is_procurement else start_price + max_step

    range_min = min(first_point, second_point)
    range_max = max(first_point, second_point)
    if new_price_dec < range_min or new_price_dec > range_max:
        return (
            "Р¦С–РЅР° РїРѕР·Р° РґРѕРїСѓСЃС‚РёРјРёРј РґС–Р°РїР°Р·РѕРЅРѕРј "
            f"[{_format_decimal_for_error(first_point)}; {_format_decimal_for_error(second_point)}]."
        )
    return None


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT login endpoint.
    """

    @extend_schema(
        summary="Р’С…С–Рґ РІ СЃРёСЃС‚РµРјСѓ",
        description="РћС‚СЂРёРјР°С‚Рё JWT С‚РѕРєРµРЅРё (access + refresh) РґР»СЏ Р°РІС‚РµРЅС‚РёС„С–РєР°С†С–С—.",
        responses={200: {"description": "РўРѕРєРµРЅРё СѓСЃРїС–С€РЅРѕ РѕС‚СЂРёРјР°РЅРѕ"}, 401: {"description": "РќРµРІС–СЂРЅС– РѕР±Р»С–РєРѕРІС– РґР°РЅС–"}},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(
    summary="Р РµС”СЃС‚СЂР°С†С–СЏ - РљСЂРѕРє 1",
    description="РЎС‚РІРѕСЂРµРЅРЅСЏ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°. РЇРєС‰Рѕ email РІР¶Рµ С–СЃРЅСѓС”, РїРѕРІРµСЂС‚Р°С” РїРѕРјРёР»РєСѓ.",
    request=UserRegistrationStep1Serializer,
    responses={
        201: UserSerializer,
        400: OpenApiResponse(description="РџРѕРјРёР»РєР° РІР°Р»С–РґР°С†С–С—"),
    },
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def registration_step1(request):
    """Step 1: Create user."""
    serializer = UserRegistrationStep1Serializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        user.registration_step = 2
        user.save(update_fields=["registration_step"])
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Р”РѕРІС–РґРЅРёРє РєСЂР°С—РЅ СЂРµС”СЃС‚СЂР°С†С–С—",
    description="РЎРїРёСЃРѕРє Р·РЅР°С‡РµРЅСЊ number_name С‚Р° number_code Р· С‚Р°Р±Р»РёС†С– countrybusinessnumber.",
    responses={200: CountryBusinessNumberSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def registration_country_business_numbers(request):
    qs = CountryBusinessNumber.objects.all().order_by("number_name", "number_code")
    serializer = CountryBusinessNumberSerializer(qs, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="Р РµС”СЃС‚СЂР°С†С–СЏ - РїРµСЂРµРІС–СЂРєР° РєРѕРјРїР°РЅС–С— Р·Р° РєРѕРґРѕРј",
    description=(
        "РџРѕРІРµСЂС‚Р°С” С–РЅС„РѕСЂРјР°С†С–СЋ РїСЂРѕ РєРѕРјРїР°РЅС–СЋ Р·Р° РєРѕРґРѕРј (Р„Р”Р РџРћРЈ/Р†РџРќ/С–РЅС€РёР№ РєРѕРґ). "
        "РЇРєС‰Рѕ РєРѕРјРїР°РЅС–СЏ Р·РЅР°Р№РґРµРЅР° С– РјР°С” Р·Р°СЂРµС”СЃС‚СЂРѕРІР°РЅРёС… РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ, "
        "СЂРµС”СЃС‚СЂР°С†С–СЏ РјР°С” РІРёРєРѕРЅСѓРІР°С‚РёСЃСЊ СЏРє РїСЂРёС”РґРЅР°РЅРЅСЏ РґРѕ С–СЃРЅСѓСЋС‡РѕС— РєРѕРјРїР°РЅС–С—."
    ),
    parameters=[
        OpenApiParameter(
            name="edrpou",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description="РљРѕРґ РєРѕРјРїР°РЅС–С— РґР»СЏ РїРµСЂРµРІС–СЂРєРё.",
        )
    ],
    responses={200: RegistrationCompanyLookupSerializer},
)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def registration_company_lookup(request):
    code = (request.query_params.get("edrpou") or "").strip()
    if not code:
        return Response({"edrpou": "Р’РєР°Р¶С–С‚СЊ РєРѕРґ РєРѕРјРїР°РЅС–С—."}, status=status.HTTP_400_BAD_REQUEST)

    company = Company.objects.filter(edrpou=code, status=Company.Status.ACTIVE).first()
    if not company:
        return Response(
            {"exists": False, "has_registered_users": False, "company": None},
            status=status.HTTP_200_OK,
        )

    has_registered_users = company.memberships.filter(status=CompanyUser.Status.APPROVED).exists()
    payload = {
        "exists": True,
        "has_registered_users": has_registered_users,
        "company": RegistrationCompanyLookupCompanySerializer(
            company, context={"request": request}
        ).data,
    }
    return Response(payload, status=status.HTTP_200_OK)


@extend_schema(
    summary="Р РµС”СЃС‚СЂР°С†С–СЏ - РљСЂРѕРє 2 (РќРѕРІР° РєРѕРјРїР°РЅС–СЏ)",
    description="РЎС‚РІРѕСЂРµРЅРЅСЏ РЅРѕРІРѕС— РєРѕРјРїР°РЅС–С— С‚Р° РїСЂРёР·РЅР°С‡РµРЅРЅСЏ РєРѕСЂРёСЃС‚СѓРІР°С‡Р° Р°РґРјС–РЅС–СЃС‚СЂР°С‚РѕСЂРѕРј.",
    request=CompanyRegistrationStep2Serializer,
    responses={
        201: CompanySerializer,
        400: OpenApiResponse(description="РџРѕРјРёР»РєР° РІР°Р»С–РґР°С†С–С—"),
    },
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def registration_step2_new_company(request):
    """РљСЂРѕРє 2: СЃС‚РІРѕСЂРµРЅРЅСЏ РЅРѕРІРѕС— РєРѕРјРїР°РЅС–С— С‚Р° РїСЂРёР·РЅР°С‡РµРЅРЅСЏ РєРѕСЂРёСЃС‚СѓРІР°С‡Р° Р°РґРјС–РЅС–СЃС‚СЂР°С‚РѕСЂРѕРј."""
    serializer = CompanyRegistrationStep2Serializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    payload = serializer.validated_data
    user_id = payload["user_id"]
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"user_id": "РљРѕСЂРёСЃС‚СѓРІР°С‡Р° РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_400_BAD_REQUEST)

    company_name = payload.get("name")
    if payload["subject_type"] == Company.SubjectType.INDIVIDUAL:
        company_name = (
            " ".join(
                part for part in [user.last_name, user.first_name, user.middle_name] if part
            ).strip()
            or user.email
        )

    with transaction.atomic():
        company = Company.objects.create(
            edrpou=payload["edrpou"],
            name=company_name,
            subject_type=payload["subject_type"],
            registration_country=payload.get("registration_country", ""),
            company_address=payload["company_address"],
            identity_document=payload.get("identity_document"),
            agree_trade_rules=payload["agree_trade_rules"],
            agree_privacy_policy=payload["agree_privacy_policy"],
            goal_tenders=False,
            goal_participation=False,
        )

        # Create admin role for company
        admin_role, _ = Role.objects.get_or_create(
            company=company, name="РђРґРјС–РЅС–СЃС‚СЂР°С‚РѕСЂ", defaults={"is_system": True}
        )

        # Assign all permissions to admin role (for MVP)
        admin_role.permissions.set(Permission.objects.all())

        # Create membership with approved status
        CompanyUser.objects.create(
            user=user, company=company, role=admin_role, status=CompanyUser.Status.APPROVED
        )
        user.registration_step = 3
        user.save(update_fields=["registration_step"])

    return Response(CompanySerializer(company).data, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Р РµС”СЃС‚СЂР°С†С–СЏ - РљСЂРѕРє 2 (Р†СЃРЅСѓСЋС‡Р° РєРѕРјРїР°РЅС–СЏ)",
    description="Р—Р°РїРёС‚ РЅР° РїСЂРёС”РґРЅР°РЅРЅСЏ РґРѕ С–СЃРЅСѓСЋС‡РѕС— РєРѕРјРїР°РЅС–С—. РЎС‚РІРѕСЂСЋС” СЃРїРѕРІС–С‰РµРЅРЅСЏ Р°РґРјС–РЅС–СЃС‚СЂР°С‚РѕСЂСѓ РєРѕРјРїР°РЅС–С—.",
    request=ExistingCompanyStep2Serializer,
    responses={
        201: CompanyUserSerializer,
        400: OpenApiResponse(description="РџРѕРјРёР»РєР° РІР°Р»С–РґР°С†С–С—"),
    },
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def registration_step2_existing_company(request):
    """РљСЂРѕРє 2: РїСЂРёС”РґРЅР°РЅРЅСЏ РґРѕ С–СЃРЅСѓСЋС‡РѕС— РєРѕРјРїР°РЅС–С— Р·Р° РєРѕРґРѕРј Р„Р”Р РџРћРЈ."""
    serializer = ExistingCompanyStep2Serializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user_id = serializer.validated_data["user_id"]
    edrpou = serializer.validated_data["edrpou"]
    new_name = (serializer.validated_data.get("name") or "").strip()

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"user_id": "РљРѕСЂРёСЃС‚СѓРІР°С‡Р° РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_400_BAD_REQUEST)

    company = Company.objects.filter(edrpou=edrpou, status=Company.Status.ACTIVE).first()
    if not company:
        return Response({"edrpou": "РљРѕРјРїР°РЅС–СЋ Р· С‚Р°РєРёРј РєРѕРґРѕРј РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_400_BAD_REQUEST)

    if CompanyUser.objects.filter(user=user, company=company).exists():
        return Response(
            {"non_field_errors": "РљРѕСЂРёСЃС‚СѓРІР°С‡ РІР¶Рµ РјР°С” Р·РІ'СЏР·РѕРє С–Р· С†С–С”СЋ РєРѕРјРїР°РЅС–С”СЋ."}, status=status.HTTP_400_BAD_REQUEST
        )

    has_approved = CompanyUser.objects.filter(company=company, status=CompanyUser.Status.APPROVED).exists()

    with transaction.atomic():
        if new_name and not has_approved:
            company.name = new_name
            company.save(update_fields=["name", "updated_at"])

        default_role, _ = Role.objects.get_or_create(
            company=company, name="РљРѕСЂРёСЃС‚СѓРІР°С‡", defaults={"is_system": True}
        )
        admin_role, _ = Role.objects.get_or_create(
            company=company, name="РђРґРјС–РЅС–СЃС‚СЂР°С‚РѕСЂ", defaults={"is_system": True}
        )

        if not has_approved:
            membership = CompanyUser.objects.create(
                user=user, company=company, role=admin_role, status=CompanyUser.Status.APPROVED
            )
        else:
            membership = CompanyUser.objects.create(
                user=user, company=company, role=default_role, status=CompanyUser.Status.PENDING
            )
            admin_memberships = CompanyUser.objects.filter(
                company=company, status=CompanyUser.Status.APPROVED, role__name="РђРґРјС–РЅС–СЃС‚СЂР°С‚РѕСЂ"
            )
            for admin_membership in admin_memberships:
                Notification.objects.create(
                    user=admin_membership.user,
                    type=Notification.Type.MEMBERSHIP_REQUEST,
                    title=f"Р—Р°РїРёС‚ РЅР° РїСЂРёС”РґРЅР°РЅРЅСЏ РІС–Рґ {user.get_full_name() or user.email}",
                    body=f"РљРѕСЂРёСЃС‚СѓРІР°С‡ {user.get_full_name() or user.email} ({user.email}) С…РѕС‡Рµ РїСЂРёС”РґРЅР°С‚РёСЃСЏ РґРѕ РєРѕРјРїР°РЅС–С— {company.name}.",
                    meta={"membership_id": membership.id, "user_id": user.id, "company_id": company.id},
                )
        user.registration_step = 4 if has_approved else 3
        user.save(update_fields=["registration_step"])

    return Response(CompanyUserSerializer(membership).data, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Р РµС”СЃС‚СЂР°С†С–СЏ - РљСЂРѕРє 3 (CPV-РєР°С‚РµРіРѕСЂС–С— РєРѕРјРїР°РЅС–С—)",
    description=(
        "Р—Р°РєСЂС–РїР»РµРЅРЅСЏ CPV-РєР°С‚РµРіРѕСЂС–Р№ Р·Р° РєРѕРјРїР°РЅС–С”СЋ РїС–Рґ С‡Р°СЃ СЂРµС”СЃС‚СЂР°С†С–С—.\n"
        "- РЇРєС‰Рѕ С†Рµ РїРµСЂС€РёР№ РїС–РґС‚РІРµСЂРґР¶РµРЅРёР№ РєРѕСЂРёСЃС‚СѓРІР°С‡ РєРѕРјРїР°РЅС–С— - СЃРїРёСЃРѕРє РєР°С‚РµРіРѕСЂС–Р№ РїРµСЂРµР·Р°РїРёСЃСѓС”С‚СЊСЃСЏ.\n"
        "- РЇРєС‰Рѕ РїС–РґС‚РІРµСЂРґР¶РµРЅРёС… РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ РІР¶Рµ Р±С–Р»СЊС€Рµ РѕРґРЅРѕРіРѕ - С–СЃРЅСѓСЋС‡С– РєР°С‚РµРіРѕСЂС–С— РЅРµ РІРёРґР°Р»СЏСЋС‚СЊСЃСЏ, "
        "РґРѕРґР°СЋС‚СЊСЃСЏ Р»РёС€Рµ РЅРѕРІС– (РѕР±'С”РґРЅР°РЅРЅСЏ СЃРїРёСЃРєС–РІ)."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer"},
                "company_id": {"type": "integer"},
                "cpv_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "РњР°СЃРёРІ ID CPV-РєРѕРґС–РІ РґР»СЏ Р·Р°РєСЂС–РїР»РµРЅРЅСЏ Р·Р° РєРѕРјРїР°РЅС–С”СЋ",
                },
            },
            "required": ["user_id", "company_id"],
        }
    },
    responses={
        200: CompanyCpvSerializer,
        400: OpenApiResponse(description="РџРѕРјРёР»РєР° РІР°Р»С–РґР°С†С–С—"),
    },
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def registration_step3_company_cpvs(request):
    """РљСЂРѕРє 3: РЅР°РїСЂСЏРјРєРё РґС–СЏР»СЊРЅРѕСЃС‚С– С‚Р° CPV-РєР°С‚РµРіРѕСЂС–С—."""
    payload = CompanyRegistrationStep3Serializer(data=request.data)
    if not payload.is_valid():
        return Response(payload.errors, status=status.HTTP_400_BAD_REQUEST)

    user_id = payload.validated_data["user_id"]
    company_id = payload.validated_data["company_id"]
    cpv_ids = payload.validated_data.get("cpv_ids") or []

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"user_id": "РљРѕСЂРёСЃС‚СѓРІР°С‡Р° РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        company = Company.objects.get(id=company_id, status=Company.Status.ACTIVE)
    except Company.DoesNotExist:
        return Response({"company_id": "РљРѕРјРїР°РЅС–СЋ РЅРµ Р·РЅР°Р№РґРµРЅРѕ Р°Р±Рѕ РІРѕРЅР° РЅРµР°РєС‚РёРІРЅР°."}, status=status.HTTP_400_BAD_REQUEST)

    if not CompanyUser.objects.filter(
        user=user, company=company, status=CompanyUser.Status.APPROVED
    ).exists():
        return Response(
            {"non_field_errors": "РљРѕСЂРёСЃС‚СѓРІР°С‡ РЅРµ РјР°С” РїС–РґС‚РІРµСЂРґР¶РµРЅРѕРіРѕ Р·РІ'СЏР·РєСѓ Р· С†С–С”СЋ РєРѕРјРїР°РЅС–С”СЋ."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    approved_count = CompanyUser.objects.filter(
        company=company, status=CompanyUser.Status.APPROVED
    ).count()
    existing_ids = set(company.cpv_categories.values_list("id", flat=True))

    with transaction.atomic():
        company.goal_tenders = payload.validated_data["goal_tenders"]
        company.goal_participation = payload.validated_data["goal_participation"]
        company.agree_participation_visibility = payload.validated_data["agree_participation_visibility"]
        company.save(
            update_fields=[
                "goal_tenders",
                "goal_participation",
                "agree_participation_visibility",
                "updated_at",
            ]
        )

        if company.goal_participation:
            if approved_count <= 1:
                company.cpv_categories.set(cpv_ids)
            else:
                union_ids = sorted(existing_ids.union(set(cpv_ids)))
                company.cpv_categories.set(union_ids)
        else:
            company.cpv_categories.clear()

        user.registration_step = 4
        user.save(update_fields=["registration_step"])

    serializer = CompanyCpvSerializer(company)
    return Response(serializer.data, status=status.HTTP_200_OK)


class CompanyViewSet(viewsets.ModelViewSet):
    """
    Company list/retrieve (for step 2 selection). Create for adding counterparties.
    """

    queryset = Company.objects.filter(status=Company.Status.ACTIVE)
    serializer_class = CompanyListSerializer
    permission_classes = [permissions.AllowAny]
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = super().get_queryset()
        edrpou = self.request.query_params.get("edrpou")
        if edrpou is not None and str(edrpou).strip():
            return qs.filter(edrpou=edrpou.strip())
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return CompanyCreateSerializer
        return CompanyListSerializer

    def perform_create(self, serializer):
        serializer.save(
            goal_tenders=False,
            goal_participation=True,
            status=Company.Status.ACTIVE,
        )

    @extend_schema(
        summary="РЎРїРёСЃРѕРє Р°РєС‚РёРІРЅРёС… РєРѕРјРїР°РЅС–Р№",
        description="РћС‚СЂРёРјР°С‚Рё СЃРїРёСЃРѕРє Р°РєС‚РёРІРЅРёС… РєРѕРјРїР°РЅС–Р№ РґР»СЏ РІРёР±РѕСЂСѓ РїСЂРё СЂРµС”СЃС‚СЂР°С†С–С—.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Р”РµС‚Р°Р»С– РєРѕРјРїР°РЅС–С—",
        description="РћС‚СЂРёРјР°С‚Рё РґРµС‚Р°Р»СЊРЅСѓ С–РЅС„РѕСЂРјР°С†С–СЋ РїСЂРѕ РєРѕРјРїР°РЅС–СЋ.",
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="РЎС‚РІРѕСЂРёС‚Рё РєРѕРјРїР°РЅС–СЋ (РєРѕРЅС‚СЂР°РіРµРЅС‚Р°)",
        description="Р”РѕРґР°С‚Рё РєРѕРјРїР°РЅС–СЋ РІСЂСѓС‡РЅСѓ (РєРѕРґ С‚Р° РЅР°Р·РІР°). Р”Р»СЏ СЃРїРёСЃРєСѓ РєРѕРЅС‚СЂР°РіРµРЅС‚С–РІ.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def members(self, request, pk=None):
        """РЎРїРёСЃРѕРє РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ (Р°РіРµРЅС‚С–РІ) РєРѕРјРїР°РЅС–С—."""
        company = self.get_object()
        memberships = CompanyUser.objects.filter(
            company=company,
            status=CompanyUser.Status.APPROVED,
        ).select_related("user", "role").order_by("-created_at")
        serializer = CompanyUserSerializer(memberships, many=True)
        return Response(serializer.data)


@extend_schema(
    summary="CPV-РєР°С‚РµРіРѕСЂС–С— РїРѕС‚РѕС‡РЅРѕС— РєРѕРјРїР°РЅС–С—",
    description=(
        "РћС‚СЂРёРјР°С‚Рё Р°Р±Рѕ РѕРЅРѕРІРёС‚Рё СЃРїРёСЃРѕРє CPV-РєР°С‚РµРіРѕСЂС–Р№, Р·Р°РєСЂС–РїР»РµРЅРёС… Р·Р° РєРѕРјРїР°РЅС–С”СЋ РїРѕС‚РѕС‡РЅРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°.\n"
        "РљРѕРјРїР°РЅС–СЏ РІРёР·РЅР°С‡Р°С”С‚СЊСЃСЏ Р·Р° РїРµСЂС€РёРј РїС–РґС‚РІРµСЂРґР¶РµРЅРёРј С‡Р»РµРЅСЃС‚РІРѕРј РєРѕСЂРёСЃС‚СѓРІР°С‡Р°."
    ),
    responses={200: CompanyCpvSerializer},
)
@api_view(["GET", "PUT"])
@permission_classes([permissions.IsAuthenticated])
def company_current_cpvs(request):
    """
    GET: РџРѕРІРµСЂС‚Р°С” РєРѕРјРїР°РЅС–СЋ РїРѕС‚РѕС‡РЅРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р° С‚Р° С—С— CPV-РєР°С‚РµРіРѕСЂС–С—.
    PUT: РћРЅРѕРІР»СЋС” СЃРїРёСЃРѕРє CPV-РєР°С‚РµРіРѕСЂС–Р№ РєРѕРјРїР°РЅС–С— (РїРѕРІРЅР° Р·Р°РјС–РЅР° СЃРїРёСЃРєСѓ).
    """
    user = request.user
    membership = (
        CompanyUser.objects.filter(user=user, status=CompanyUser.Status.APPROVED)
        .select_related("company")
        .first()
    )
    if not membership or not membership.company:
        return Response(
            {"detail": "РљРѕСЂРёСЃС‚СѓРІР°С‡ РЅРµ РјР°С” РїС–РґС‚РІРµСЂРґР¶РµРЅРѕРіРѕ С‡Р»РµРЅСЃС‚РІР° РЅС– РІ РѕРґРЅС–Р№ РєРѕРјРїР°РЅС–С—."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    company = membership.company

    if request.method == "GET":
        serializer = CompanyCpvSerializer(company)
        return Response(serializer.data)

    serializer = CompanyCpvSerializer(company, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response(CompanyCpvSerializer(company).data)


def _user_owner_company_ids(request):
    """Company IDs for which the current user can manage counterparties (approved memberships)."""
    user = request.user
    if user.is_superuser:
        return Company.objects.filter(status=Company.Status.ACTIVE).values_list("id", flat=True)
    return (
        CompanyUser.objects.filter(
            user=user,
            status=CompanyUser.Status.APPROVED,
        )
        .values_list("company_id", flat=True)
        .distinct()
    )


class CompanySupplierViewSet(viewsets.ModelViewSet):
    """
    РЎРїРёСЃРѕРє РєРѕРЅС‚СЂР°РіРµРЅС‚С–РІ РєРѕРјРїР°РЅС–С—: РґРѕРґР°РЅС– РІСЂСѓС‡РЅСѓ С‚Р° (Р·РіРѕРґРѕРј) С‚С–, С…С‚Рѕ РїС–РґС‚РІРµСЂРґРёРІ СѓС‡Р°СЃС‚СЊ Сѓ С‚РµРЅРґРµСЂР°С….
    Р”РѕРґР°РІР°РЅРЅСЏ: Р°Р±Рѕ supplier_company_id, Р°Р±Рѕ edrpou (СЏРєС‰Рѕ РєРѕРјРїР°РЅС–СЏ С” - Р»РёС€Рµ Р·РІ'СЏР·РѕРє; СЏРєС‰Рѕ РЅРµРјР°С” - name РѕР±РѕРІ'СЏР·РєРѕРІР°, СЃС‚РІРѕСЂСЋС”С‚СЊСЃСЏ РєРѕРјРїР°РЅС–СЏ).
    """

    serializer_class = CompanySupplierSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        owner_ids = list(_user_owner_company_ids(self.request))
        qs = (
            CompanySupplier.objects.filter(owner_company_id__in=owner_ids)
            .select_related("supplier_company", "owner_company")
            .order_by("-created_at")
        )
        if self.action == "list":
            qs = qs.prefetch_related("supplier_company__cpv_categories")
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return AddCompanySupplierSerializer
        if self.action == "list":
            return CompanySupplierListSerializer
        return CompanySupplierSerializer

    def create(self, request, *args, **kwargs):
        owner_ids = list(_user_owner_company_ids(request))
        if not owner_ids:
            raise permissions.exceptions.PermissionDenied("РќРµРјР°С” РґРѕСЃС‚СѓРїСѓ РґРѕ Р¶РѕРґРЅРѕС— РєРѕРјРїР°РЅС–С—.")
        owner_id = owner_ids[0]

        serializer = AddCompanySupplierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        supplier_id = data.get("supplier_company_id")
        if supplier_id is not None:
            if supplier_id == owner_id:
                raise DRFValidationError({"supplier_company_id": "РќРµ РјРѕР¶РЅР° РґРѕРґР°С‚Рё РІР»Р°СЃРЅСѓ РєРѕРјРїР°РЅС–СЋ СЏРє РєРѕРЅС‚СЂР°РіРµРЅС‚Р°."})
            if not Company.objects.filter(id=supplier_id, status=Company.Status.ACTIVE).exists():
                raise DRFValidationError({"supplier_company_id": "РљРѕРјРїР°РЅС–СЋ РЅРµ Р·РЅР°Р№РґРµРЅРѕ Р°Р±Рѕ РІРѕРЅР° РЅРµР°РєС‚РёРІРЅР°."})
            if CompanySupplier.objects.filter(owner_company_id=owner_id, supplier_company_id=supplier_id).exists():
                raise DRFValidationError({"supplier_company_id": "Р¦СЏ РєРѕРјРїР°РЅС–СЏ РІР¶Рµ С” Сѓ СЃРїРёСЃРєСѓ РєРѕРЅС‚СЂР°РіРµРЅС‚С–РІ."})
            obj = CompanySupplier.objects.create(
                owner_company_id=owner_id,
                supplier_company_id=supplier_id,
                source=CompanySupplier.Source.MANUAL,
            )
            return Response(
                CompanySupplierSerializer(obj).data,
                status=status.HTTP_201_CREATED,
            )

        edrpou = data["edrpou"]
        name = data.get("name") or ""

        company = Company.objects.filter(edrpou=edrpou, status=Company.Status.ACTIVE).first()
        if company:
            if CompanySupplier.objects.filter(owner_company_id=owner_id, supplier_company_id=company.id).exists():
                raise DRFValidationError({"edrpou": "Р¦СЏ РєРѕРјРїР°РЅС–СЏ РІР¶Рµ С” Сѓ СЃРїРёСЃРєСѓ РєРѕРЅС‚СЂР°РіРµРЅС‚С–РІ."})
            if company.id == owner_id:
                raise DRFValidationError({"edrpou": "РќРµ РјРѕР¶РЅР° РґРѕРґР°С‚Рё РІР»Р°СЃРЅСѓ РєРѕРјРїР°РЅС–СЋ СЏРє РєРѕРЅС‚СЂР°РіРµРЅС‚Р°."})
            obj = CompanySupplier.objects.create(
                owner_company_id=owner_id,
                supplier_company_id=company.id,
                source=CompanySupplier.Source.MANUAL,
            )
            return Response(
                CompanySupplierSerializer(obj).data,
                status=status.HTTP_201_CREATED,
            )

        if not name:
            raise DRFValidationError({"name": "РљРѕРјРїР°РЅС–С— Р· С‚Р°РєРёРј РєРѕРґРѕРј РЅРµРјР°С”. Р’РІРµРґС–С‚СЊ РЅР°Р·РІСѓ РґР»СЏ СЃС‚РІРѕСЂРµРЅРЅСЏ РєРѕРЅС‚СЂР°РіРµРЅС‚Р° (РїРѕРїРµСЂРµРґРЅСЏ РЅР°Р·РІР°)."})
        with transaction.atomic():
            new_company = Company.objects.create(
                edrpou=edrpou,
                name=name,
                goal_tenders=False,
                goal_participation=True,
                status=Company.Status.ACTIVE,
            )
            obj = CompanySupplier.objects.create(
                owner_company_id=owner_id,
                supplier_company_id=new_company.id,
                source=CompanySupplier.Source.MANUAL,
            )
        return Response(
            CompanySupplierSerializer(obj).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(summary="Р”РѕРґР°С‚Рё РєРѕРЅС‚СЂР°РіРµРЅС‚Р°", request=AddCompanySupplierSerializer)
    def create(self, request, *args, **kwargs):
        owner_ids = list(_user_owner_company_ids(request))
        if not owner_ids:
            raise permissions.exceptions.PermissionDenied("РќРµРјР°С” РґРѕСЃС‚СѓРїСѓ РґРѕ Р¶РѕРґРЅРѕС— РєРѕРјРїР°РЅС–С—.")
        owner_id = owner_ids[0]

        serializer = AddCompanySupplierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        supplier_id = data.get("supplier_company_id")
        if supplier_id is not None:
            if supplier_id == owner_id:
                raise DRFValidationError({"supplier_company_id": "РќРµ РјРѕР¶РЅР° РґРѕРґР°С‚Рё РІР»Р°СЃРЅСѓ РєРѕРјРїР°РЅС–СЋ СЏРє РєРѕРЅС‚СЂР°РіРµРЅС‚Р°."})
            if not Company.objects.filter(id=supplier_id, status=Company.Status.ACTIVE).exists():
                raise DRFValidationError({"supplier_company_id": "РљРѕРјРїР°РЅС–СЋ РЅРµ Р·РЅР°Р№РґРµРЅРѕ Р°Р±Рѕ РІРѕРЅР° РЅРµР°РєС‚РёРІРЅР°."})
            if CompanySupplier.objects.filter(owner_company_id=owner_id, supplier_company_id=supplier_id).exists():
                raise DRFValidationError({"supplier_company_id": "Р¦СЏ РєРѕРјРїР°РЅС–СЏ РІР¶Рµ С” Сѓ СЃРїРёСЃРєСѓ РєРѕРЅС‚СЂР°РіРµРЅС‚С–РІ."})
            obj = CompanySupplier.objects.create(
                owner_company_id=owner_id,
                supplier_company_id=supplier_id,
                source=CompanySupplier.Source.MANUAL,
            )
            return Response(
                CompanySupplierSerializer(obj).data,
                status=status.HTTP_201_CREATED,
            )

        edrpou = data["edrpou"]
        name = data.get("name") or ""

        company = Company.objects.filter(edrpou=edrpou, status=Company.Status.ACTIVE).first()
        if company:
            if CompanySupplier.objects.filter(owner_company_id=owner_id, supplier_company_id=company.id).exists():
                raise DRFValidationError({"edrpou": "Р¦СЏ РєРѕРјРїР°РЅС–СЏ РІР¶Рµ С” Сѓ СЃРїРёСЃРєСѓ РєРѕРЅС‚СЂР°РіРµРЅС‚С–РІ."})
            if company.id == owner_id:
                raise DRFValidationError({"edrpou": "РќРµ РјРѕР¶РЅР° РґРѕРґР°С‚Рё РІР»Р°СЃРЅСѓ РєРѕРјРїР°РЅС–СЋ СЏРє РєРѕРЅС‚СЂР°РіРµРЅС‚Р°."})
            obj = CompanySupplier.objects.create(
                owner_company_id=owner_id,
                supplier_company_id=company.id,
                source=CompanySupplier.Source.MANUAL,
            )
            return Response(
                CompanySupplierSerializer(obj).data,
                status=status.HTTP_201_CREATED,
            )

        if not name:
            raise DRFValidationError({"name": "РљРѕРјРїР°РЅС–С— Р· С‚Р°РєРёРј РєРѕРґРѕРј РЅРµРјР°С”. Р’РІРµРґС–С‚СЊ РЅР°Р·РІСѓ РґР»СЏ СЃС‚РІРѕСЂРµРЅРЅСЏ РєРѕРЅС‚СЂР°РіРµРЅС‚Р° (РїРѕРїРµСЂРµРґРЅСЏ РЅР°Р·РІР°)."})
        with transaction.atomic():
            new_company = Company.objects.create(
                edrpou=edrpou,
                name=name,
                goal_tenders=False,
                goal_participation=True,
                status=Company.Status.ACTIVE,
            )
            obj = CompanySupplier.objects.create(
                owner_company_id=owner_id,
                supplier_company_id=new_company.id,
                source=CompanySupplier.Source.MANUAL,
            )
        return Response(
            CompanySupplierSerializer(obj).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(summary="РЎРїРёСЃРѕРє РєРѕРЅС‚СЂР°РіРµРЅС‚С–РІ", description="РљРѕРЅС‚СЂР°РіРµРЅС‚Рё: РґРѕРґР°РЅС– РІСЂСѓС‡РЅСѓ С‚Р° Р· СѓС‡Р°СЃС‚С– РІ С‚РµРЅРґРµСЂР°С….")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="РўРµРЅРґРµСЂРё РєРѕРЅС‚СЂР°РіРµРЅС‚Р°", description="РўРµРЅРґРµСЂРё РєРѕРјРїР°РЅС–С—-РІР»Р°СЃРЅРёРєР°, РґРµ РєРѕРЅС‚СЂР°РіРµРЅС‚ РїРѕРґР°РІ РїСЂРѕРїРѕР·РёС†С–СЋ С– РІР¶Рµ Р·Р°РІРµСЂС€РµРЅРѕ РµС‚Р°Рї РїСЂРёР№РѕРјСѓ РїСЂРѕРїРѕР·РёС†С–Р№.")
    @action(detail=True, methods=["get"], url_path="tenders")
    def tenders(self, request, pk=None):
        relation = self.get_object()
        owner_company_id = relation.owner_company_id
        supplier_company_id = relation.supplier_company_id
        finished_acceptance_stages = ["decision", "approval", "completed"]

        procurement_stage_labels = dict(ProcurementTender.Stage.choices)
        sales_stage_labels = dict(SalesTender.Stage.choices)

        procurement_rows = list(
            ProcurementTender.objects.filter(
                company_id=owner_company_id,
                stage__in=finished_acceptance_stages,
                proposals__supplier_company_id=supplier_company_id,
            )
            .distinct()
            .values("id", "number", "name", "tour_number", "stage", "updated_at")
        )
        sales_rows = list(
            SalesTender.objects.filter(
                company_id=owner_company_id,
                stage__in=finished_acceptance_stages,
                proposals__supplier_company_id=supplier_company_id,
            )
            .distinct()
            .values("id", "number", "name", "tour_number", "stage", "updated_at")
        )

        results = [
            {
                "id": row["id"],
                "number": row.get("number"),
                "name": row.get("name") or "",
                "tour_number": row.get("tour_number") or 1,
                "stage": row.get("stage") or "",
                "stage_label": procurement_stage_labels.get(
                    row.get("stage"), row.get("stage") or ""
                ),
                "type": "procurement",
                "updated_at": row.get("updated_at"),
            }
            for row in procurement_rows
        ] + [
            {
                "id": row["id"],
                "number": row.get("number"),
                "name": row.get("name") or "",
                "tour_number": row.get("tour_number") or 1,
                "stage": row.get("stage") or "",
                "stage_label": sales_stage_labels.get(
                    row.get("stage"), row.get("stage") or ""
                ),
                "type": "sales",
                "updated_at": row.get("updated_at"),
            }
            for row in sales_rows
        ]

        results.sort(key=lambda item: item.get("updated_at") or timezone.now(), reverse=True)
        for item in results:
            item.pop("updated_at", None)

        return Response(results)


class CompanyUserViewSet(viewsets.ModelViewSet):
    """
    CompanyUser membership management.

    Р’ СЂР°РјРєР°С… РїРѕС‚РѕС‡РЅРѕРіРѕ MVP РІСЃС– РїС–РґС‚РІРµСЂРґР¶РµРЅС– СѓС‡Р°СЃРЅРёРєРё РєРѕРјРїР°РЅС–С— РјР°СЋС‚СЊ РѕРґРЅР°РєРѕРІС– РїСЂР°РІР°
    РґРѕСЃС‚СѓРїСѓ РІ РјРµР¶Р°С… СЃРІРѕС—С… РєРѕРјРїР°РЅС–Р№ (Р±РµР· РїРѕРґС–Р»Сѓ РЅР° Р°РґРјС–РЅС–СЃС‚СЂР°С‚РѕСЂС–РІ С‚Р° РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ).
    """

    serializer_class = CompanyUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        РџРѕРІРµСЂС‚Р°С”РјРѕ РІСЃС– С‡Р»РµРЅСЃС‚РІР° РєРѕРјРїР°РЅС–Р№, РІ СЏРєРёС… РїРѕС‚РѕС‡РЅРёР№ РєРѕСЂРёСЃС‚СѓРІР°С‡ РјР°С”
        РїС–РґС‚РІРµСЂРґР¶РµРЅРёР№ СЃС‚Р°С‚СѓСЃ. Р В РѕР»С– РЅРµ РІСЂР°С…РѕРІСѓСЋС‚СЊСЃСЏ.
        """
        user = self.request.user
        if user.is_superuser:
            return CompanyUser.objects.all()

        user_companies = CompanyUser.objects.filter(
            user=user,
            status=CompanyUser.Status.APPROVED,
        ).values_list("company_id", flat=True)
        return CompanyUser.objects.filter(company_id__in=user_companies)

    @extend_schema(
        summary="РЎРїРёСЃРѕРє С‡Р»РµРЅС–РІ РєРѕРјРїР°РЅС–С—",
        description="РћС‚СЂРёРјР°С‚Рё СЃРїРёСЃРѕРє РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ РєРѕРјРїР°РЅС–Р№, РІ СЏРєРёС… РїРѕС‚РѕС‡РЅРёР№ РєРѕСЂРёСЃС‚СѓРІР°С‡ РјР°С” РїС–РґС‚РІРµСЂРґР¶РµРЅРµ С‡Р»РµРЅСЃС‚РІРѕ.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Р”РµС‚Р°Р»С– С‡Р»РµРЅСЃС‚РІР°",
        description="РћС‚СЂРёРјР°С‚Рё РґРµС‚Р°Р»СЊРЅСѓ С–РЅС„РѕСЂРјР°С†С–СЋ РїСЂРѕ С‡Р»РµРЅСЃС‚РІРѕ.",
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Р”РѕРґР°С‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡Р° РґРѕ РєРѕРјРїР°РЅС–С—",
        description="Р”РѕРґР°С‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡Р° РґРѕ РєРѕРјРїР°РЅС–С— РІСЂСѓС‡РЅСѓ (Р±СѓРґСЊ-СЏРєРёР№ РїС–РґС‚РІРµСЂРґР¶РµРЅРёР№ СѓС‡Р°СЃРЅРёРє РєРѕРјРїР°РЅС–С—).",
        request=CompanyUserSerializer,
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="РџС–РґС‚РІРµСЂРґРёС‚Рё С‡Р»РµРЅСЃС‚РІРѕ",
        description="РџС–РґС‚РІРµСЂРґРёС‚Рё Р·Р°РїРёС‚ РЅР° РїСЂРёС”РґРЅР°РЅРЅСЏ РґРѕ РєРѕРјРїР°РЅС–С—.",
        responses={200: CompanyUserSerializer, 400: OpenApiResponse(description="РџРѕРјРёР»РєР°")},
    )
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve membership request."""
        membership = self.get_object()
        if membership.status != CompanyUser.Status.PENDING:
            return Response({"error": "РњРѕР¶РЅР° РїС–РґС‚РІРµСЂРґРёС‚Рё С‚С–Р»СЊРєРё Р·Р°РїРёС‚Рё Р·С– СЃС‚Р°С‚СѓСЃРѕРј 'РћС‡С–РєСѓС”'."}, status=400)

        membership.status = CompanyUser.Status.APPROVED
        membership.save()

        # Notify user about approval
        Notification.objects.create(
            user=membership.user,
            type=Notification.Type.MEMBERSHIP_REQUEST,
            title=f"Р’Р°С€ Р·Р°РїРёС‚ РїС–РґС‚РІРµСЂРґР¶РµРЅРѕ",
            body=f"Р’Р°С€ Р·Р°РїРёС‚ РЅР° РїСЂРёС”РґРЅР°РЅРЅСЏ РґРѕ РєРѕРјРїР°РЅС–С— {membership.company.name} Р±СѓР»Рѕ РїС–РґС‚РІРµСЂРґР¶РµРЅРѕ.",
            meta={"membership_id": membership.id, "company_id": membership.company.id},
        )

        return Response(CompanyUserSerializer(membership).data)

    @extend_schema(
        summary="Р’С–РґС…РёР»РёС‚Рё С‡Р»РµРЅСЃС‚РІРѕ",
        description="Р’С–РґС…РёР»РёС‚Рё Р·Р°РїРёС‚ РЅР° РїСЂРёС”РґРЅР°РЅРЅСЏ РґРѕ РєРѕРјРїР°РЅС–С—.",
        responses={200: CompanyUserSerializer, 400: OpenApiResponse(description="РџРѕРјРёР»РєР°")},
    )
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject membership request."""
        membership = self.get_object()
        if membership.status != CompanyUser.Status.PENDING:
            return Response({"error": "РњРѕР¶РЅР° РІС–РґС…РёР»РёС‚Рё С‚С–Р»СЊРєРё Р·Р°РїРёС‚Рё Р·С– СЃС‚Р°С‚СѓСЃРѕРј 'РћС‡С–РєСѓС”'."}, status=400)

        membership.status = CompanyUser.Status.REJECTED
        membership.save()

        # Notify user about rejection
        Notification.objects.create(
            user=membership.user,
            type=Notification.Type.MEMBERSHIP_REQUEST,
            title=f"Р’Р°С€ Р·Р°РїРёС‚ РІС–РґС…РёР»РµРЅРѕ",
            body=f"Р’Р°С€ Р·Р°РїРёС‚ РЅР° РїСЂРёС”РґРЅР°РЅРЅСЏ РґРѕ РєРѕРјРїР°РЅС–С— {membership.company.name} Р±СѓР»Рѕ РІС–РґС…РёР»РµРЅРѕ.",
            meta={"membership_id": membership.id, "company_id": membership.company.id},
        )

        return Response(CompanyUserSerializer(membership).data)

    @extend_schema(
        summary="РЎС‚РІРѕСЂРёС‚Рё РЅРѕРІРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р° РєРѕРјРїР°РЅС–С—",
        description="РЎС‚РІРѕСЂРёС‚Рё РЅРѕРІРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р° (User) С– РѕРґСЂР°Р·Сѓ РґРѕРґР°С‚Рё Р№РѕРіРѕ РґРѕ РєРѕРјРїР°РЅС–С— Р·С– СЃС‚Р°С‚СѓСЃРѕРј 'РџС–РґС‚РІРµСЂРґР¶РµРЅРѕ' (Р±СѓРґСЊ-СЏРєРёР№ РїС–РґС‚РІРµСЂРґР¶РµРЅРёР№ СѓС‡Р°СЃРЅРёРє РєРѕРјРїР°РЅС–С—).",
        request=UserRegistrationStep1Serializer,
        responses={201: CompanyUserSerializer, 400: OpenApiResponse(description="РџРѕРјРёР»РєР° РІР°Р»С–РґР°С†С–С—")},
    )
    @action(detail=False, methods=["post"], url_path="create-user")
    def create_user(self, request):
        """
        РЎС‚РІРѕСЂРёС‚Рё РЅРѕРІРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р° С‚Р° РїСЂРёРІ'СЏР·Р°С‚Рё Р№РѕРіРѕ РґРѕ РїРµСЂС€РѕС— РєРѕРјРїР°РЅС–С—,
        РІ СЏРєС–Р№ РїРѕС‚РѕС‡РЅРёР№ РєРѕСЂРёСЃС‚СѓРІР°С‡ РјР°С” РїС–РґС‚РІРµСЂРґР¶РµРЅРµ С‡Р»РµРЅСЃС‚РІРѕ.
        """
        user = request.user

        # Р—РЅР°С…РѕРґРёРјРѕ РєРѕРјРїР°РЅС–С—, РґРµ РєРѕСЂРёСЃС‚СѓРІР°С‡ РјР°С” РїС–РґС‚РІРµСЂРґР¶РµРЅРµ С‡Р»РµРЅСЃС‚РІРѕ
        memberships = CompanyUser.objects.filter(
            user=user,
            status=CompanyUser.Status.APPROVED,
        )
        if not memberships.exists() and not user.is_superuser:
            return Response(
                {"error": "РљРѕСЂРёСЃС‚СѓРІР°С‡ РЅРµ РјР°С” РїС–РґС‚РІРµСЂРґР¶РµРЅРѕРіРѕ С‡Р»РµРЅСЃС‚РІР° РЅС– РІ РѕРґРЅС–Р№ РєРѕРјРїР°РЅС–С—."},
                status=status.HTTP_403_FORBIDDEN,
            )

        company = memberships.first().company if memberships.exists() else None

        # РЎС‚РІРѕСЂСЋС”РјРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р° С‡РµСЂРµР· С–СЃРЅСѓСЋС‡РёР№ СЃРµСЂС–Р°Р»С–Р·Р°С‚РѕСЂ СЂРµС”СЃС‚СЂР°С†С–С— (РєСЂРѕРє 1)
        serializer = UserRegistrationStep1Serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_user = serializer.save()

        # РћС‚СЂРёРјСѓС”РјРѕ / СЃС‚РІРѕСЂСЋС”РјРѕ СЂРѕР»СЊ "РљРѕСЂРёСЃС‚СѓРІР°С‡" РґР»СЏ РєРѕРјРїР°РЅС–С—
        default_role, _ = Role.objects.get_or_create(
            company=company, name="РљРѕСЂРёСЃС‚СѓРІР°С‡", defaults={"is_system": True}
        )

        membership = CompanyUser.objects.create(
            user=new_user,
            company=company,
            role=default_role,
            status=CompanyUser.Status.APPROVED,
        )

        return Response(CompanyUserSerializer(membership).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="РћРЅРѕРІРёС‚Рё РґР°РЅС– РєРѕСЂРёСЃС‚СѓРІР°С‡Р° РєРѕРјРїР°РЅС–С—",
        description="РђРґРјС–РЅС–СЃС‚СЂР°С‚РѕСЂ РјРѕР¶Рµ РІС–РґСЂРµРґР°РіСѓРІР°С‚Рё С–Рј'СЏ, РїСЂС–Р·РІРёС‰Рµ, email, С‚РµР»РµС„РѕРЅ С‚Р° РїР°СЂРѕР»СЊ РєРѕСЂРёСЃС‚СѓРІР°С‡Р° РєРѕРјРїР°РЅС–С—.",
        responses={200: CompanyUserSerializer, 400: OpenApiResponse(description="РџРѕРјРёР»РєР° РІР°Р»С–РґР°С†С–С—")},
    )
    @action(detail=True, methods=["patch"], url_path="update-user")
    def update_user(self, request, pk=None):
        membership = self.get_object()
        user = membership.user

        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        email = request.data.get("email")
        phone = request.data.get("phone")
        password = request.data.get("password")
        password_confirm = request.data.get("password_confirm")

        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if email is not None:
            # РџРµСЂРµРІС–СЂРєР° РЅР° СѓРЅС–РєР°Р»СЊРЅС–СЃС‚СЊ email
            if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                return Response({"email": ["РљРѕСЂРёСЃС‚СѓРІР°С‡ Р· С‚Р°РєРёРј email РІР¶Рµ С–СЃРЅСѓС”."]}, status=status.HTTP_400_BAD_REQUEST)
            user.email = email
        if phone is not None:
            user.phone = phone

        if password is not None and password != "":
            if password != password_confirm:
                return Response(
                    {"password_confirm": ["РџР°СЂРѕР»С– РЅРµ СЃРїС–РІРїР°РґР°СЋС‚СЊ."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                validate_password(password, user)
            except DjangoValidationError as e:
                return Response(
                    {"password": list(e.messages)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.set_password(password)

        user.save()
        return Response(CompanyUserSerializer(membership).data)

    @extend_schema(
        summary="Р”РµР°РєС‚РёРІСѓРІР°С‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡Р° РєРѕРјРїР°РЅС–С—",
        description="РђРґРјС–РЅС–СЃС‚СЂР°С‚РѕСЂ РјРѕР¶Рµ РІРёРјРєРЅСѓС‚Рё Р°РєС‚РёРІРЅС–СЃС‚СЊ РєРѕСЂРёСЃС‚СѓРІР°С‡Р° (is_active = False), РїС–СЃР»СЏ С‡РѕРіРѕ РІС–РЅ РЅРµ Р·РјРѕР¶Рµ РІС…РѕРґРёС‚Рё РІ СЃРёСЃС‚РµРјСѓ.",
        responses={200: CompanyUserSerializer},
    )
    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        membership = self.get_object()
        user = membership.user
        if not user.is_active:
            return Response({"detail": "РљРѕСЂРёСЃС‚СѓРІР°С‡ РІР¶Рµ РґРµР°РєС‚РёРІРѕРІР°РЅРёР№."}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(CompanyUserSerializer(membership).data)

    @extend_schema(
        summary="РђРєС‚РёРІСѓРІР°С‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡Р° РєРѕРјРїР°РЅС–С—",
        description="РђРґРјС–РЅС–СЃС‚СЂР°С‚РѕСЂ РјРѕР¶Рµ СѓРІС–РјРєРЅСѓС‚Рё Р°РєС‚РёРІРЅС–СЃС‚СЊ РєРѕСЂРёСЃС‚СѓРІР°С‡Р° (is_active = True), РїС–СЃР»СЏ С‡РѕРіРѕ РІС–РЅ Р·РјРѕР¶Рµ РІС…РѕРґРёС‚Рё РІ СЃРёСЃС‚РµРјСѓ.",
        responses={200: CompanyUserSerializer},
    )
    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        membership = self.get_object()
        user = membership.user
        if user.is_active:
            return Response({"detail": "РљРѕСЂРёСЃС‚СѓРІР°С‡ РІР¶Рµ Р°РєС‚РёРІРѕРІР°РЅРёР№."}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response(CompanyUserSerializer(membership).data)


class RoleViewSet(viewsets.ModelViewSet):
    """
    Role management (company-scoped).
    """

    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter by user's companies."""
        user = self.request.user
        if user.is_superuser:
            return Role.objects.all()
        # Only show roles for companies where user is admin
        admin_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED, role__name="РђРґРјС–РЅС–СЃС‚СЂР°С‚РѕСЂ"
        ).values_list("company_id", flat=True)
        return Role.objects.filter(company_id__in=admin_companies)

    @extend_schema(
        summary="РЎРїРёСЃРѕРє СЂРѕР»РµР№",
        description="РћС‚СЂРёРјР°С‚Рё СЃРїРёСЃРѕРє СЂРѕР»РµР№ РєРѕРјРїР°РЅС–С— (С‚С–Р»СЊРєРё РґР»СЏ Р°РґРјС–РЅС–СЃС‚СЂР°С‚РѕСЂС–РІ).",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="РЎС‚РІРѕСЂРёС‚Рё СЂРѕР»СЊ",
        description="РЎС‚РІРѕСЂРёС‚Рё РЅРѕРІСѓ СЂРѕР»СЊ РґР»СЏ РєРѕРјРїР°РЅС–С—.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="РћРЅРѕРІРёС‚Рё СЂРѕР»СЊ",
        description="РћРЅРѕРІРёС‚Рё СЂРѕР»СЊ С‚Р° С—С— РїСЂР°РІР° РґРѕСЃС‚СѓРїСѓ.",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Р’РёРґР°Р»РёС‚Рё СЂРѕР»СЊ",
        description="Р’РёРґР°Р»РёС‚Рё СЂРѕР»СЊ (СЃРёСЃС‚РµРјРЅС– СЂРѕР»С– РІРёРґР°Р»РёС‚Рё РЅРµРјРѕР¶Р»РёРІРѕ).",
    )
    def destroy(self, request, *args, **kwargs):
        role = self.get_object()
        if role.is_system:
            return Response({"error": "РЎРёСЃС‚РµРјРЅС– СЂРѕР»С– РЅРµ РјРѕР¶РЅР° РІРёРґР°Р»СЏС‚Рё."}, status=400)
        return super().destroy(request, *args, **kwargs)


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Permission catalog (read-only).
    """

    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="РЎРїРёСЃРѕРє РїСЂР°РІ РґРѕСЃС‚СѓРїСѓ",
        description="РћС‚СЂРёРјР°С‚Рё РєР°С‚Р°Р»РѕРі РґРѕСЃС‚СѓРїРЅРёС… РїСЂР°РІ РґРѕСЃС‚СѓРїСѓ РґР»СЏ РїСЂРёР·РЅР°С‡РµРЅРЅСЏ СЂРѕР»СЏРј.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    User notifications.
    """

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Show only current user's notifications."""
        return Notification.objects.filter(user=self.request.user).order_by("-created_at")

    @extend_schema(
        summary="РЎРїРёСЃРѕРє СЃРїРѕРІС–С‰РµРЅСЊ",
        description="РћС‚СЂРёРјР°С‚Рё СЃРїРёСЃРѕРє СЃРїРѕРІС–С‰РµРЅСЊ РїРѕС‚РѕС‡РЅРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="РџРѕР·РЅР°С‡РёС‚Рё СЏРє РїСЂРѕС‡РёС‚Р°РЅРµ",
        description="РџРѕР·РЅР°С‡РёС‚Рё СЃРїРѕРІС–С‰РµРЅРЅСЏ СЏРє РїСЂРѕС‡РёС‚Р°РЅРµ.",
        responses={200: NotificationSerializer},
    )
    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """Mark notification as read."""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response(NotificationSerializer(notification).data)

    @extend_schema(
        summary="РџРѕР·РЅР°С‡РёС‚Рё РІСЃС– СЏРє РїСЂРѕС‡РёС‚Р°РЅС–",
        description="РџРѕР·РЅР°С‡РёС‚Рё РІСЃС– СЃРїРѕРІС–С‰РµРЅРЅСЏ РєРѕСЂРёСЃС‚СѓРІР°С‡Р° СЏРє РїСЂРѕС‡РёС‚Р°РЅС–.",
        responses={200: {"description": "РљС–Р»СЊРєС–СЃС‚СЊ РѕРЅРѕРІР»РµРЅРёС… СЃРїРѕРІС–С‰РµРЅСЊ"}},
    )
    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"count": count})


@extend_schema(
    summary="РџРѕС‚РѕС‡РЅРёР№ РєРѕСЂРёСЃС‚СѓРІР°С‡",
    description="РћС‚СЂРёРјР°С‚Рё Р°Р±Рѕ РѕРЅРѕРІРёС‚Рё РїСЂРѕС„С–Р»СЊ РїРѕС‚РѕС‡РЅРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°.",
    responses={200: MeSerializer},
)
@api_view(["GET", "PATCH"])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    """GET: РїРѕС‚РѕС‡РЅРёР№ РєРѕСЂРёСЃС‚СѓРІР°С‡, С‡Р»РµРЅСЃС‚РІР°, РїСЂР°РІР°. PATCH: РѕРЅРѕРІР»РµРЅРЅСЏ РїСЂРѕС„С–Р»СЋ (first_name, last_name, middle_name, phone)."""
    if request.method == "PATCH":
        serializer = ProfileUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        for key, value in serializer.validated_data.items():
            setattr(user, key, value)
        user.save(update_fields=list(serializer.validated_data.keys()))
        response_serializer = MeSerializer(
            {"user": user, "memberships": user.memberships.all(), "permissions": []},
            context={"request": request},
        )
        return Response(response_serializer.data)
    serializer = MeSerializer(
        {"user": request.user, "memberships": request.user.memberships.all(), "permissions": []},
        context={"request": request},
    )
    return Response(serializer.data)


AVATAR_MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _is_allowed_avatar_content_type(content_type):
    if not content_type:
        return False
    ct = content_type.split(";")[0].strip().lower()
    return ct in ("image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp") or ct.startswith("image/")


TENDER_FILE_MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
ALLOWED_TENDER_FILE_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/csv",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/zip",
    "application/x-zip-compressed",
}
ALLOWED_TENDER_FILE_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".txt",
    ".csv",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".zip",
}


def _file_extension(filename):
    name = str(filename or "")
    if "." not in name:
        return ""
    return f".{name.rsplit('.', 1)[1].lower()}"


def _is_allowed_tender_file(file_obj):
    ct = (getattr(file_obj, "content_type", "") or "").split(";")[0].strip().lower()
    ext = _file_extension(getattr(file_obj, "name", ""))
    return ct in ALLOWED_TENDER_FILE_CONTENT_TYPES or ext in ALLOWED_TENDER_FILE_EXTENSIONS


def _validate_tender_file(file_obj):
    if getattr(file_obj, "size", 0) > TENDER_FILE_MAX_SIZE_BYTES:
        return "File size must not exceed 20 MB."
    if not _is_allowed_tender_file(file_obj):
        return "Allowed formats: PDF, DOC/DOCX, XLS/XLSX, TXT, CSV, JPG/PNG/WEBP, ZIP."
    return None


@extend_schema(
    summary="Р—Р°РІР°РЅС‚Р°Р¶РёС‚Рё Р°РІР°С‚Р°СЂ",
    description="Р—Р°РІР°РЅС‚Р°Р¶РёС‚Рё С„РѕС‚Рѕ РґР»СЏ Р°РІР°С‚Р°СЂР° РїРѕС‚РѕС‡РЅРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р° (JPEG, PNG, GIF, WebP; РјР°РєСЃ. 5 РњР‘).",
    request={"multipart/form-data": {"type": "object", "properties": {"avatar": {"type": "string", "format": "binary"}}}},
    responses={200: {"description": "URL РЅРѕРІРѕРіРѕ Р°РІР°С‚Р°СЂР°"}},
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def me_avatar_upload(request):
    """Upload avatar for current user."""
    file = request.FILES.get("avatar") or request.FILES.get("file")
    if not file:
        return Response({"detail": "Р¤Р°Р№Р» РЅРµ РЅР°РґС–СЃР»Р°РЅРѕ. Р’РёРєРѕСЂРёСЃС‚РѕРІСѓР№С‚Рµ РїРѕР»Рµ avatar Р°Р±Рѕ file."}, status=status.HTTP_400_BAD_REQUEST)
    if not _is_allowed_avatar_content_type(getattr(file, "content_type", "")):
        return Response(
            {"detail": "Р”РѕР·РІРѕР»РµРЅС– С„РѕСЂРјР°С‚Рё: JPEG, PNG, GIF, WebP."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if file.size > AVATAR_MAX_SIZE_BYTES:
        return Response({"detail": "Р В РѕР·РјС–СЂ С„Р°Р№Р»Сѓ РЅРµ РїРѕРІРёРЅРµРЅ РїРµСЂРµРІРёС‰СѓРІР°С‚Рё 5 РњР‘."}, status=status.HTTP_400_BAD_REQUEST)
    user = request.user
    if user.avatar:
        try:
            user.avatar.delete(save=False)
        except Exception:
            pass
    user.avatar = file
    user.save(update_fields=["avatar"])
    url = user.avatar.url
    if request.get_host():
        url = request.build_absolute_uri(url)
    return Response({"avatar": url})


@extend_schema(
    summary="Р—Р°РїРёС‚ РЅР° РІС–РґРЅРѕРІР»РµРЅРЅСЏ РїР°СЂРѕР»СЏ",
    description="РќР°РґС–СЃР»Р°С‚Рё Р·Р°РїРёС‚ РЅР° РІС–РґРЅРѕРІР»РµРЅРЅСЏ РїР°СЂРѕР»СЏ (email Р· РїРѕСЃРёР»Р°РЅРЅСЏРј).",
    request=PasswordResetRequestSerializer,
    responses={200: {"description": "РЇРєС‰Рѕ email С–СЃРЅСѓС”, РЅР°РґС–СЃР»Р°РЅРѕ Р»РёСЃС‚"}},
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def password_reset_request(request):
    """Request password reset. Returns generic response to avoid email enumeration."""
    serializer = PasswordResetRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data["email"]
    response_data = {"message": "РЇРєС‰Рѕ email С–СЃРЅСѓС”, РЅР°РґС–СЃР»Р°РЅРѕ Р»РёСЃС‚ Р· С–РЅСЃС‚СЂСѓРєС†С–СЏРјРё."}

    user = User.objects.filter(email=email).first()
    if user:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_token = f"{uid}:{token}"
        # MVP/dev convenience: frontend can complete flow without email transport.
        if settings.DEBUG:
            response_data["reset_token"] = reset_token
        # TODO: integrate real email sending transport.

    return Response(response_data, status=status.HTTP_200_OK)


@extend_schema(
    summary="РџС–РґС‚РІРµСЂРґР¶РµРЅРЅСЏ РІС–РґРЅРѕРІР»РµРЅРЅСЏ РїР°СЂРѕР»СЏ",
    description="РџС–РґС‚РІРµСЂРґРёС‚Рё РІС–РґРЅРѕРІР»РµРЅРЅСЏ РїР°СЂРѕР»СЏ Р·Р° С‚РѕРєРµРЅРѕРј.",
    request=PasswordResetConfirmSerializer,
    responses={200: {"description": "РџР°СЂРѕР»СЊ СѓСЃРїС–С€РЅРѕ Р·РјС–РЅРµРЅРѕ"}},
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def password_reset_confirm(request):
    """Confirm password reset using reset token from request step."""
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    token_payload = serializer.validated_data["token"]
    new_password = serializer.validated_data["new_password"]

    try:
        uidb64, token = token_payload.split(":", 1)
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=user_id)
    except (ValueError, TypeError, OverflowError, User.DoesNotExist):
        return Response(
            {"token": "РќРµРІС–СЂРЅРёР№ Р°Р±Рѕ РїСЂРѕСЃС‚СЂРѕС‡РµРЅРёР№ С‚РѕРєРµРЅ."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not default_token_generator.check_token(user, token):
        return Response(
            {"token": "РќРµРІС–СЂРЅРёР№ Р°Р±Рѕ РїСЂРѕСЃС‚СЂРѕС‡РµРЅРёР№ С‚РѕРєРµРЅ."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(new_password)
    user.save(update_fields=["password"])
    return Response({"message": "РџР°СЂРѕР»СЊ СѓСЃРїС–С€РЅРѕ Р·РјС–РЅРµРЅРѕ."}, status=status.HTTP_200_OK)


@extend_schema(
    summary="Р—РјС–РЅР° РїР°СЂРѕР»СЏ",
    description="Р—РјС–РЅРёС‚Рё РїР°СЂРѕР»СЊ РґР»СЏ Р°РІС‚РµРЅС‚РёС„С–РєРѕРІР°РЅРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°.",
    request=PasswordChangeSerializer,
    responses={200: {"description": "РџР°СЂРѕР»СЊ СѓСЃРїС–С€РЅРѕ Р·РјС–РЅРµРЅРѕ"}},
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def password_change(request):
    """Change password for authenticated user."""
    serializer = PasswordChangeSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({"old_password": "РќРµРІС–СЂРЅРёР№ РїРѕС‚РѕС‡РЅРёР№ РїР°СЂРѕР»СЊ."}, status=400)
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"message": "РџР°СЂРѕР»СЊ СѓСЃРїС–С€РЅРѕ Р·РјС–РЅРµРЅРѕ."})
    return Response(serializer.errors, status=400)


class BranchViewSet(viewsets.ModelViewSet):
    """
    Branch management (tree structure).
    """

    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter by user's companies and optionally by user's assignments."""
        user = self.request.user
        self._allowed_tree_ids = None
        if user.is_superuser:
            return Branch.objects.all()

        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        queryset = Branch.objects.filter(company_id__in=user_companies)

        if _is_truthy_query_param(self.request.query_params.get("assigned_only")):
            assigned_ids = set(queryset.filter(users__user=user).values_list("id", flat=True))
            if not assigned_ids:
                self._allowed_tree_ids = set()
                return queryset.none().select_related("parent", "company")
            allowed_ids = _expand_tree_ids_with_ancestors(Branch, assigned_ids)
            self._allowed_tree_ids = allowed_ids
            queryset = queryset.filter(id__in=allowed_ids).distinct()

        return queryset.select_related("parent", "company")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if getattr(self, "_allowed_tree_ids", None) is not None:
            context["allowed_ids"] = self._allowed_tree_ids
        return context

    @extend_schema(
        summary="РЎРїРёСЃРѕРє С„С–Р»С–Р°Р»С–РІ",
        description="РћС‚СЂРёРјР°С‚Рё РґРµСЂРµРІРѕ С„С–Р»С–Р°Р»С–РІ РєРѕРјРїР°РЅС–С— (С‚С–Р»СЊРєРё РєРѕСЂРµРЅРµРІС– РµР»РµРјРµРЅС‚Рё, РґС–С‚Рё РІРєР»Р°РґРµРЅРѕ).",
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(parent__isnull=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="РЎС‚РІРѕСЂРёС‚Рё С„С–Р»С–Р°Р»",
        description="РЎС‚РІРѕСЂРёС‚Рё РЅРѕРІРёР№ С„С–Р»С–Р°Р».",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="РћРЅРѕРІРёС‚Рё С„С–Р»С–Р°Р»",
        description="РћРЅРѕРІРёС‚Рё С–РЅС„РѕСЂРјР°С†С–СЋ РїСЂРѕ С„С–Р»С–Р°Р».",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Р’РёРґР°Р»РёС‚Рё С„С–Р»С–Р°Р»",
        description="Р’РёРґР°Р»РёС‚Рё С„С–Р»С–Р°Р» (С‚Р°РєРѕР¶ РІРёРґР°Р»СЏС‚СЊСЃСЏ РґРѕС‡С–СЂРЅС– С„С–Р»С–Р°Р»Рё С‚Р° РїС–РґСЂРѕР·РґС–Р»Рё).",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    Department management (tree structure, belongs to branch).
    """

    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        РџРѕРІРµСЂС‚Р°С” РїС–РґСЂРѕР·РґС–Р»Рё, РѕР±РјРµР¶РµРЅС– РєРѕРјРїР°РЅС–СЏРјРё РїРѕС‚РѕС‡РЅРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°.

        - Р”Р»СЏ superuser: РІСЃС– РїС–РґСЂРѕР·РґС–Р»Рё.
        - Р”Р»СЏ Р·РІРёС‡Р°Р№РЅРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°: Р»РёС€Рµ РїС–РґСЂРѕР·РґС–Р»Рё С„С–Р»С–Р°Р»С–РІ РєРѕРјРїР°РЅС–Р№,
          РґРµ РІ РЅСЊРѕРіРѕ С” РїС–РґС‚РІРµСЂРґР¶РµРЅРµ С‡Р»РµРЅСЃС‚РІРѕ.
        - Р”РѕРґР°С‚РєРѕРІРѕ РјРѕР¶РЅР° РѕР±РјРµР¶РёС‚Рё СЂРµР·СѓР»СЊС‚Р°С‚ РїР°СЂР°РјРµС‚СЂРѕРј branch_id.
        """
        user = self.request.user
        self._allowed_tree_ids = None
        if user.is_superuser:
            queryset = Department.objects.all()
        else:
            user_companies = CompanyUser.objects.filter(
                user=user,
                status=CompanyUser.Status.APPROVED,
            ).values_list("company_id", flat=True)
            queryset = Department.objects.filter(
                branch__company_id__in=user_companies
            )

            if _is_truthy_query_param(self.request.query_params.get("assigned_only")):
                assigned_ids = set(queryset.filter(users__user=user).values_list("id", flat=True))
                if not assigned_ids:
                    self._allowed_tree_ids = set()
                    queryset = queryset.none()
                else:
                    allowed_ids = _expand_tree_ids_with_ancestors(Department, assigned_ids)
                    self._allowed_tree_ids = allowed_ids
                    queryset = queryset.filter(id__in=allowed_ids).distinct()

        branch_id = self.request.query_params.get("branch_id")
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        return queryset.select_related("parent", "branch")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if getattr(self, "_allowed_tree_ids", None) is not None:
            context["allowed_ids"] = self._allowed_tree_ids
        return context

    @extend_schema(
        summary="РЎРїРёСЃРѕРє РїС–РґСЂРѕР·РґС–Р»С–РІ",
        description="РћС‚СЂРёРјР°С‚Рё РґРµСЂРµРІРѕ РїС–РґСЂРѕР·РґС–Р»С–РІ РґР»СЏ С„С–Р»С–Р°Р»Сѓ (РїРѕС‚СЂС–Р±РµРЅ РїР°СЂР°РјРµС‚СЂ branch_id).",
        parameters=[
            OpenApiParameter(name="branch_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True)
        ],
    )
    def list(self, request, *args, **kwargs):
        branch_id = request.query_params.get("branch_id")
        if not branch_id:
            return Response({"error": "РџР°СЂР°РјРµС‚СЂ branch_id РѕР±РѕРІ'СЏР·РєРѕРІРёР№"}, status=400)
        # get_queryset РІР¶Рµ РІС–РґС„С–Р»СЊС‚СЂСѓС” Р·Р° branch_id, С‚СѓС‚ Р»РёС€Рµ Р±РµСЂРµРјРѕ РєРѕСЂРµРЅС–
        queryset = self.get_queryset().filter(parent__isnull=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="РЎС‚РІРѕСЂРёС‚Рё РїС–РґСЂРѕР·РґС–Р»",
        description="РЎС‚РІРѕСЂРёС‚Рё РЅРѕРІРёР№ РїС–РґСЂРѕР·РґС–Р».",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="РћРЅРѕРІРёС‚Рё РїС–РґСЂРѕР·РґС–Р»",
        description="РћРЅРѕРІРёС‚Рё С–РЅС„РѕСЂРјР°С†С–СЋ РїСЂРѕ РїС–РґСЂРѕР·РґС–Р».",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Р’РёРґР°Р»РёС‚Рё РїС–РґСЂРѕР·РґС–Р»",
        description="Р’РёРґР°Р»РёС‚Рё РїС–РґСЂРѕР·РґС–Р» (С‚Р°РєРѕР¶ РІРёРґР°Р»СЏС‚СЊСЃСЏ РґРѕС‡С–СЂРЅС– РїС–РґСЂРѕР·РґС–Р»Рё).",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class BranchUserViewSet(viewsets.ModelViewSet):
    """
    BranchUser management (assign users to branches).
    """

    serializer_class = BranchUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter by user's companies and optionally by branch."""
        user = self.request.user
        if user.is_superuser:
            queryset = BranchUser.objects.all()
        else:
            # Only show BranchUser for branches in user's companies
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            queryset = BranchUser.objects.filter(branch__company_id__in=user_companies)
        
        # Filter by branch_id if provided (for list endpoint)
        branch_id = self.request.query_params.get("branch_id")
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        
        return queryset.select_related("user", "branch")

    @extend_schema(
        summary="РЎРїРёСЃРѕРє РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ С„С–Р»С–Р°Р»Сѓ",
        description="РћС‚СЂРёРјР°С‚Рё СЃРїРёСЃРѕРє РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ С„С–Р»С–Р°Р»Сѓ (РїРѕС‚СЂС–Р±РµРЅ РїР°СЂР°РјРµС‚СЂ branch_id).",
        parameters=[
            OpenApiParameter(name="branch_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True)
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Р”РѕРґР°С‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ РґРѕ С„С–Р»С–Р°Р»Сѓ",
        description="Р”РѕРґР°С‚Рё РѕРґРЅРѕРіРѕ Р°Р±Рѕ РєС–Р»СЊРєР° РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ РґРѕ С„С–Р»С–Р°Р»Сѓ (РјР°СЃРёРІ user_ids).",
    )
    def create(self, request, *args, **kwargs):
        branch_id = request.data.get("branch")
        user_ids = request.data.get("user_ids", [])
        if not isinstance(user_ids, list):
            return Response({"error": "user_ids РїРѕРІРёРЅРµРЅ Р±СѓС‚Рё РјР°СЃРёРІРѕРј"}, status=400)

        created = []
        for user_id in user_ids:
            serializer = self.get_serializer(data={"branch": branch_id, "user_id": user_id})
            if serializer.is_valid():
                instance, created_flag = BranchUser.objects.get_or_create(
                    branch_id=branch_id, user_id=user_id
                )
                if created_flag:
                    created.append(BranchUserSerializer(instance).data)
        return Response(created, status=201)

    @extend_schema(
        summary="Р’РёРґР°Р»РёС‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡Р° Р· С„С–Р»С–Р°Р»Сѓ",
        description="Р’РёРґР°Р»РёС‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡Р° Р· С„С–Р»С–Р°Р»Сѓ.",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class DepartmentUserViewSet(viewsets.ModelViewSet):
    """
    DepartmentUser management (assign users to departments).
    """

    serializer_class = DepartmentUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter by user's companies and optionally by department."""
        user = self.request.user
        if user.is_superuser:
            queryset = DepartmentUser.objects.all()
        else:
            # Only show DepartmentUser for departments in branches of user's companies
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            queryset = DepartmentUser.objects.filter(department__branch__company_id__in=user_companies)
        
        # Filter by department_id if provided (for list endpoint)
        department_id = self.request.query_params.get("department_id")
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        
        return queryset.select_related("user", "department")

    @extend_schema(
        summary="РЎРїРёСЃРѕРє РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ РїС–РґСЂРѕР·РґС–Р»Сѓ",
        description="РћС‚СЂРёРјР°С‚Рё СЃРїРёСЃРѕРє РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ РїС–РґСЂРѕР·РґС–Р»Сѓ (РїРѕС‚СЂС–Р±РµРЅ РїР°СЂР°РјРµС‚СЂ department_id).",
        parameters=[
            OpenApiParameter(name="department_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True)
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Р”РѕРґР°С‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ РґРѕ РїС–РґСЂРѕР·РґС–Р»Сѓ",
        description="Р”РѕРґР°С‚Рё РѕРґРЅРѕРіРѕ Р°Р±Рѕ РєС–Р»СЊРєР° РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ РґРѕ РїС–РґСЂРѕР·РґС–Р»Сѓ (РјР°СЃРёРІ user_ids).",
    )
    def create(self, request, *args, **kwargs):
        department_id = request.data.get("department")
        user_ids = request.data.get("user_ids", [])
        if not isinstance(user_ids, list):
            return Response({"error": "user_ids РїРѕРІРёРЅРµРЅ Р±СѓС‚Рё РјР°СЃРёРІРѕРј"}, status=400)

        created = []
        for user_id in user_ids:
            serializer = self.get_serializer(data={"department": department_id, "user_id": user_id})
            if serializer.is_valid():
                instance, created_flag = DepartmentUser.objects.get_or_create(
                    department_id=department_id, user_id=user_id
                )
                if created_flag:
                    created.append(DepartmentUserSerializer(instance).data)
        return Response(created, status=201)

    @extend_schema(
        summary="Р’РёРґР°Р»РёС‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡Р° Р· РїС–РґСЂРѕР·РґС–Р»Сѓ",
        description="Р’РёРґР°Р»РёС‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡Р° Р· РїС–РґСЂРѕР·РґС–Р»Сѓ.",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="РњР°СЃРѕРІРѕ РІРёРґР°Р»РёС‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ Р· РїС–РґСЂРѕР·РґС–Р»Сѓ",
        description="Р’РёРґР°Р»РёС‚Рё РѕРґРЅРѕРіРѕ Р°Р±Рѕ РєС–Р»СЊРєРѕС… РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ Р· РїС–РґСЂРѕР·РґС–Р»Сѓ (РјР°СЃРёРІ user_ids).",
    )
    @action(detail=False, methods=["post"], url_path="bulk-delete")
    def bulk_delete(self, request):
        department_id = request.data.get("department")
        user_ids = request.data.get("user_ids", [])
        if not department_id:
            return Response({"error": "РџР°СЂР°РјРµС‚СЂ department РѕР±РѕРІ'СЏР·РєРѕРІРёР№"}, status=400)
        if not isinstance(user_ids, list):
            return Response({"error": "user_ids РїРѕРІРёРЅРµРЅ Р±СѓС‚Рё РјР°СЃРёРІРѕРј"}, status=400)

        user = request.user
        if user.is_superuser:
            qs = DepartmentUser.objects.all()
        else:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            qs = DepartmentUser.objects.filter(
                department__branch__company_id__in=user_companies
            )

        qs.filter(department_id=department_id, user_id__in=user_ids).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Category management (company-scoped flat list).
    """

    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter by user's companies."""
        user = self.request.user
        if user.is_superuser:
            return Category.objects.all().select_related("parent", "company")
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        return Category.objects.filter(company_id__in=user_companies).select_related("parent", "company")

    @extend_schema(
        summary="РЎРїРёСЃРѕРє РєР°С‚РµРіРѕСЂС–Р№",
        description="РћС‚СЂРёРјР°С‚Рё РґРµСЂРµРІРѕ РєР°С‚РµРіРѕСЂС–Р№ РєРѕРјРїР°РЅС–С— (С‚С–Р»СЊРєРё РєРѕСЂРµРЅРµРІС– РµР»РµРјРµРЅС‚Рё, РґС–С‚Рё РІРєР»Р°РґРµРЅРѕ).",
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(parent__isnull=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="РЎС‚РІРѕСЂРёС‚Рё РєР°С‚РµРіРѕСЂС–СЋ",
        description="РЎС‚РІРѕСЂРёС‚Рё РЅРѕРІСѓ РєР°С‚РµРіРѕСЂС–СЋ.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="РћРЅРѕРІРёС‚Рё РєР°С‚РµРіРѕСЂС–СЋ",
        description="РћРЅРѕРІРёС‚Рё С–РЅС„РѕСЂРјР°С†С–СЋ РїСЂРѕ РєР°С‚РµРіРѕСЂС–СЋ.",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Р’РёРґР°Р»РёС‚Рё РєР°С‚РµРіРѕСЂС–СЋ",
        description="Р’РёРґР°Р»РёС‚Рё РєР°С‚РµРіРѕСЂС–СЋ.",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class CategoryUserViewSet(viewsets.ModelViewSet):
    """
    CategoryUser management (assign users to categories).
    """

    serializer_class = CategoryUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter by user's companies and optionally by category."""
        user = self.request.user
        if user.is_superuser:
            queryset = CategoryUser.objects.all()
        else:
            # Only show CategoryUser for categories in user's companies
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            queryset = CategoryUser.objects.filter(category__company_id__in=user_companies)
        
        # Filter by category_id if provided (for list endpoint)
        category_id = self.request.query_params.get("category_id")
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        return queryset.select_related("user", "category")

    @extend_schema(
        summary="РЎРїРёСЃРѕРє РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ РєР°С‚РµРіРѕСЂС–С—",
        description="РћС‚СЂРёРјР°С‚Рё СЃРїРёСЃРѕРє РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ РєР°С‚РµРіРѕСЂС–С— (РїРѕС‚СЂС–Р±РµРЅ РїР°СЂР°РјРµС‚СЂ category_id).",
        parameters=[
            OpenApiParameter(name="category_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True)
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Р”РѕРґР°С‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ РґРѕ РєР°С‚РµРіРѕСЂС–С—",
        description="Р”РѕРґР°С‚Рё РѕРґРЅРѕРіРѕ Р°Р±Рѕ РєС–Р»СЊРєР° РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ РґРѕ РєР°С‚РµРіРѕСЂС–С— (РјР°СЃРёРІ user_ids).",
    )
    def create(self, request, *args, **kwargs):
        category_id = request.data.get("category")
        user_ids = request.data.get("user_ids", [])
        if not isinstance(user_ids, list):
            return Response({"error": "user_ids РїРѕРІРёРЅРµРЅ Р±СѓС‚Рё РјР°СЃРёРІРѕРј"}, status=400)

        result = []
        for user_id in user_ids:
            serializer = self.get_serializer(data={"category": category_id, "user_id": user_id})
            if serializer.is_valid():
                instance, created_flag = CategoryUser.objects.get_or_create(
                    category_id=category_id, user_id=user_id
                )
                if created_flag:
                    result.append(CategoryUserSerializer(instance).data)
        return Response(result, status=201)

    @extend_schema(
        summary="Р’РёРґР°Р»РёС‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡Р° Р· РєР°С‚РµРіРѕСЂС–С—",
        description="Р’РёРґР°Р»РёС‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡Р° Р· РєР°С‚РµРіРѕСЂС–С—.",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class CpvDictionaryTreeView(APIView):
    """
    РџРѕРІРµСЂС‚Р°С” РґРµСЂРµРІРѕ CPV-РєРѕРґС–РІ РґР»СЏ РІРёР±РѕСЂСѓ Сѓ РґРѕРІС–РґРЅРёРєСѓ.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Р”РµСЂРµРІРѕ CPV-РєРѕРґС–РІ",
        description=(
            "РџРѕРІРµСЂС‚Р°С” РїРѕРІРЅРёР№ РїРµСЂРµР»С–Рє CPV-РєРѕРґС–РІ Сѓ РІРёРіР»СЏРґС– РґРµСЂРµРІР°. "
            "Р”РµСЂРµРІРѕРїРѕРґС–Р±РЅР° СЃС‚СЂСѓРєС‚СѓСЂР° Р±СѓРґСѓС”С‚СЊСЃСЏ Р·Р° РїРѕР»СЏРјРё cpv_parent_code / cpv_level_code. "
            "РљРѕР¶РµРЅ РµР»РµРјРµРЅС‚ РјС–СЃС‚РёС‚СЊ id, cpv_code, name_ua, name_en, cpv_parent_code, cpv_level_code С‚Р° children."
        ),
        responses={200: OpenApiResponse(description="РЎРїРёСЃРѕРє РєРѕСЂРµРЅРµРІРёС… CPV-РµР»РµРјРµРЅС‚С–РІ Р· РІРєР»Р°РґРµРЅРёРјРё РґС–С‚СЊРјРё")},
    )
    def get(self, request):
        # РћС‚СЂРёРјСѓС”РјРѕ СѓСЃС– Р·Р°РїРёСЃРё
        items = list(CpvDictionary.objects.all())

        # Р†РЅРґРµРєСЃ Р·Р° РІРЅСѓС‚СЂС–С€РЅС–Рј РєРѕРґРѕРј СЂС–РІРЅСЏ
        by_level_code = {i.cpv_level_code: i for i in items}

        # РџС–РґРіРѕС‚СѓС”РјРѕ СЃРїРёСЃРѕРє РєРѕСЂРµРЅС–РІ
        roots: list[CpvDictionary] = []

        # РўРёРјС‡Р°СЃРѕРІРѕ РґРѕРґР°С”РјРѕ Р°С‚СЂРёР±СѓС‚ _children РґРѕ РѕР±'С”РєС‚С–РІ
        for item in items:
            parent_code = (item.cpv_parent_code or "").strip()
            if not parent_code or parent_code == "0":
                roots.append(item)
            else:
                parent = by_level_code.get(parent_code)
                if parent is None:
                    # РЇРєС‰Рѕ Р±Р°С‚СЊРєРѕ РЅРµ Р·РЅР°Р№РґРµРЅРёР№, РІРІР°Р¶Р°С”РјРѕ РµР»РµРјРµРЅС‚ РєРѕСЂРµРЅРµРј
                    roots.append(item)
                else:
                    children = getattr(parent, "_children", [])
                    children.append(item)
                    parent._children = children

        def serialize_node(node: CpvDictionary) -> dict:
            children = [serialize_node(c) for c in getattr(node, "_children", [])]
            return {
                "id": node.id,
                "cpv_parent_code": node.cpv_parent_code,
                "cpv_level_code": node.cpv_level_code,
                "cpv_code": node.cpv_code,
                "name_ua": node.name_ua,
                "name_en": node.name_en,
                "label": f"{node.cpv_code} - {node.name_ua}",
                "children": children,
            }

        data = [serialize_node(root) for root in roots]
        return Response(data)


class CpvDictionaryChildrenView(APIView):
    """
    Р›С–РЅРёРІРµ Р·Р°РІР°РЅС‚Р°Р¶РµРЅРЅСЏ CPV-РІСѓР·Р»С–РІ: РєРѕСЂРµРЅС– Р°Р±Рѕ РґС–С‚Рё РєРѕРЅРєСЂРµС‚РЅРѕРіРѕ РІСѓР·Р»Р°.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="CPV РІСѓР·Р»Рё (Р»С–РЅРёРІРѕ)",
        description=(
            "РџРѕРІРµСЂС‚Р°С” CPV-РІСѓР·Р»Рё РґР»СЏ lazy-tree.\n"
            "- Р‘РµР· РїР°СЂР°РјРµС‚СЂР° `parent_level_code`: РїРѕРІРµСЂС‚Р°С” С‚С–Р»СЊРєРё РєРѕСЂРµРЅРµРІС– РІСѓР·Р»Рё.\n"
            "- Р— РїР°СЂР°РјРµС‚СЂРѕРј `parent_level_code`: РїРѕРІРµСЂС‚Р°С” Р»РёС€Рµ РїСЂСЏРјРёС… РґС–С‚РµР№ РґР»СЏ С†СЊРѕРіРѕ РІСѓР·Р»Р°."
        ),
        parameters=[
            OpenApiParameter(
                name="parent_level_code",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Р’РЅСѓС‚СЂС–С€РЅС–Р№ РєРѕРґ Р±Р°С‚СЊРєС–РІСЃСЊРєРѕРіРѕ РІСѓР·Р»Р° (cpv_level_code).",
            )
        ],
        responses={200: OpenApiResponse(description="РЎРїРёСЃРѕРє РІСѓР·Р»С–РІ")},
    )
    def get(self, request):
        parent_level_code = (request.query_params.get("parent_level_code") or "").strip()
        search = (request.query_params.get("search") or "").strip()

        if search:
            search_term = search.casefold()
            qs = CpvDictionary.objects.all()
            items = [
                item
                for item in qs.order_by("cpv_code")
                if search_term in str(getattr(item, "cpv_code", "") or "").casefold()
                or search_term in str(getattr(item, "name_ua", "") or "").casefold()
                or search_term in str(getattr(item, "name_en", "") or "").casefold()
            ]
        elif parent_level_code:
            qs = CpvDictionary.objects.filter(cpv_parent_code=parent_level_code)
            items = list(qs.order_by("cpv_code"))
        else:
            qs = CpvDictionary.objects.filter(
                Q(cpv_parent_code__isnull=True) | Q(cpv_parent_code="") | Q(cpv_parent_code="0")
            )
            items = list(qs.order_by("cpv_code"))
        level_codes = [item.cpv_level_code for item in items if item.cpv_level_code]

        ancestors_by_level_code = {}
        if search and items:
            pending_parent_codes = {
                (item.cpv_parent_code or "").strip()
                for item in items
                if (item.cpv_parent_code or "").strip()
            }
            while pending_parent_codes:
                parent_items = list(
                    CpvDictionary.objects.filter(cpv_level_code__in=pending_parent_codes)
                )
                pending_parent_codes = set()
                for parent in parent_items:
                    parent_level_code = (parent.cpv_level_code or "").strip()
                    if parent_level_code:
                        ancestors_by_level_code[parent_level_code] = parent
                    next_parent_code = (parent.cpv_parent_code or "").strip()
                    if next_parent_code and next_parent_code not in ancestors_by_level_code:
                        pending_parent_codes.add(next_parent_code)

        def _label(item):
            return f"{item.cpv_code} - {item.name_ua}"

        def _hierarchy_label(item):
            parts = [_label(item)]
            parent_code = (item.cpv_parent_code or "").strip()
            guard = 0
            while parent_code and guard < 30:
                parent = ancestors_by_level_code.get(parent_code)
                if not parent:
                    break
                parts.append(_label(parent))
                parent_code = (parent.cpv_parent_code or "").strip()
                guard += 1
            parts.reverse()
            return " / ".join(parts)

        def _hierarchy_path(item):
            path_items = [item]
            parent_code = (item.cpv_parent_code or "").strip()
            guard = 0
            while parent_code and guard < 30:
                parent = ancestors_by_level_code.get(parent_code)
                if not parent:
                    break
                path_items.append(parent)
                parent_code = (parent.cpv_parent_code or "").strip()
                guard += 1
            path_items.reverse()
            result = []
            for idx, node in enumerate(path_items):
                is_last = idx == len(path_items) - 1
                result.append(
                    {
                        "id": node.id,
                        "cpv_level_code": node.cpv_level_code,
                        "label": _label(node),
                        "has_children": (not is_last) or (node.cpv_level_code in child_parent_codes),
                    }
                )
            return result

        child_parent_codes = set()
        if level_codes:
            child_parent_codes = set(
                CpvDictionary.objects.filter(cpv_parent_code__in=level_codes).values_list("cpv_parent_code", flat=True)
            )

        data = [
            {
                "id": item.id,
                "cpv_parent_code": item.cpv_parent_code,
                "cpv_level_code": item.cpv_level_code,
                "cpv_code": item.cpv_code,
                "name_ua": item.name_ua,
                "name_en": item.name_en,
                "label": _label(item),
                "hierarchy_label": _hierarchy_label(item) if search else _label(item),
                "hierarchy_path": _hierarchy_path(item) if search else [],
                "has_children": item.cpv_level_code in child_parent_codes,
                "children": [],
            }
            for item in items
        ]
        return Response(data)


class CpvWithCompaniesView(APIView):
    """
    РЎРїРёСЃРѕРє CPV-РєР°С‚РµРіРѕСЂС–Р№, Р·Р° СЏРєРёРјРё С” Р·Р°СЂРµС”СЃС‚СЂРѕРІР°РЅС– РєРѕРјРїР°РЅС–С— РІ СЃРёСЃС‚РµРјС– (РЅРµ РІ СЂР°РјРєР°С… РѕРґРЅС–С”С— РєРѕРјРїР°РЅС–С—).
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="CPV Р· Р·Р°СЂРµС”СЃС‚СЂРѕРІР°РЅРёРјРё РєРѕРјРїР°РЅС–СЏРјРё",
        description="РџРѕРІРµСЂС‚Р°С” РїР»РѕСЃРєРёР№ СЃРїРёСЃРѕРє CPV (id, cpv_code, name_ua, label), Р·Р° СЏРєРёРјРё С…РѕС‡Р° Р± РѕРґРЅР° РєРѕРјРїР°РЅС–СЏ Р·Р°СЂРµС”СЃС‚СЂРѕРІР°РЅР° РІ СЃРёСЃС‚РµРјС–.",
        responses={200: OpenApiResponse(description="РЎРїРёСЃРѕРє CPV")},
    )
    def get(self, request):
        qs = (
            CpvDictionary.objects.filter(
                companies_by_cpvs__status=Company.Status.ACTIVE,
                companies_by_cpvs__goal_participation=True,
                companies_by_cpvs__agree_participation_visibility=True,
            )
            .distinct()
            .order_by("cpv_code")
        )
        data = [
            {
                "id": item.id,
                "cpv_code": item.cpv_code,
                "name_ua": getattr(item, "name_ua", "") or "",
                "label": f"{getattr(item, 'cpv_code', '')} - {getattr(item, 'name_ua', '')}",
            }
            for item in qs
        ]
        return Response(data)


class ExpenseArticleViewSet(viewsets.ModelViewSet):
    """
    ExpenseArticle management (tree, company-scoped).
    """

    serializer_class = ExpenseArticleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter by user's companies and optionally by user's assignments."""
        user = self.request.user
        self._allowed_tree_ids = None
        if user.is_superuser:
            return ExpenseArticle.objects.all().select_related("parent", "company")
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        queryset = ExpenseArticle.objects.filter(company_id__in=user_companies)

        if _is_truthy_query_param(self.request.query_params.get("assigned_only")):
            assigned_ids = set(queryset.filter(users__user=user).values_list("id", flat=True))
            if not assigned_ids:
                self._allowed_tree_ids = set()
                return queryset.none().select_related("parent", "company")
            allowed_ids = _expand_tree_ids_with_ancestors(ExpenseArticle, assigned_ids)
            self._allowed_tree_ids = allowed_ids
            queryset = queryset.filter(id__in=allowed_ids).distinct()

        return queryset.select_related("parent", "company")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if getattr(self, "_allowed_tree_ids", None) is not None:
            context["allowed_ids"] = self._allowed_tree_ids
        return context

    @extend_schema(
        summary="РЎРїРёСЃРѕРє СЃС‚Р°С‚РµР№ РІРёС‚СЂР°С‚",
        description="РћС‚СЂРёРјР°С‚Рё РґРµСЂРµРІРѕ СЃС‚Р°С‚РµР№ РІРёС‚СЂР°С‚ РєРѕРјРїР°РЅС–С— (С‚С–Р»СЊРєРё РєРѕСЂРµРЅРµРІС– РµР»РµРјРµРЅС‚Рё, РґС–С‚Рё РІРєР»Р°РґРµРЅРѕ).",
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(parent__isnull=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="РЎС‚РІРѕСЂРёС‚Рё СЃС‚Р°С‚С‚СЋ РІРёС‚СЂР°С‚",
        description="РЎС‚РІРѕСЂРёС‚Рё РЅРѕРІСѓ СЃС‚Р°С‚С‚СЋ РІРёС‚СЂР°С‚.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="РћРЅРѕРІРёС‚Рё СЃС‚Р°С‚С‚СЋ РІРёС‚СЂР°С‚",
        description="РћРЅРѕРІРёС‚Рё С–РЅС„РѕСЂРјР°С†С–СЋ РїСЂРѕ СЃС‚Р°С‚С‚СЋ РІРёС‚СЂР°С‚.",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Р’РёРґР°Р»РёС‚Рё СЃС‚Р°С‚С‚СЋ РІРёС‚СЂР°С‚",
        description="Р’РёРґР°Р»РёС‚Рё СЃС‚Р°С‚С‚СЋ РІРёС‚СЂР°С‚.",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class ExpenseArticleUserViewSet(viewsets.ModelViewSet):
    """
    ExpenseArticleUser management (assign users to expense articles).
    """

    serializer_class = ExpenseArticleUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter by user's companies and optionally by expense article."""
        user = self.request.user
        if user.is_superuser:
            queryset = ExpenseArticleUser.objects.all()
        else:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            queryset = ExpenseArticleUser.objects.filter(expense__company_id__in=user_companies)

        expense_id = self.request.query_params.get("expense_id")
        if expense_id:
            queryset = queryset.filter(expense_id=expense_id)

        return queryset.select_related("user", "expense")

    @extend_schema(
        summary="РЎРїРёСЃРѕРє РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ СЃС‚Р°С‚С‚С– РІРёС‚СЂР°С‚",
        description="РћС‚СЂРёРјР°С‚Рё СЃРїРёСЃРѕРє РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ СЃС‚Р°С‚С‚С– РІРёС‚СЂР°С‚ (РїРѕС‚СЂС–Р±РµРЅ РїР°СЂР°РјРµС‚СЂ expense_id).",
        parameters=[
            OpenApiParameter(name="expense_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True)
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Р”РѕРґР°С‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ РґРѕ СЃС‚Р°С‚С‚С– РІРёС‚СЂР°С‚",
        description="Р”РѕРґР°С‚Рё РѕРґРЅРѕРіРѕ Р°Р±Рѕ РєС–Р»СЊРєР° РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ РґРѕ СЃС‚Р°С‚С‚С– РІРёС‚СЂР°С‚ (РјР°СЃРёРІ user_ids).",
    )
    def create(self, request, *args, **kwargs):
        expense_id = request.data.get("expense")
        user_ids = request.data.get("user_ids", [])
        if not isinstance(user_ids, list):
            return Response({"error": "user_ids РїРѕРІРёРЅРµРЅ Р±СѓС‚Рё РјР°СЃРёРІРѕРј"}, status=400)

        result = []
        for user_id in user_ids:
            serializer = self.get_serializer(data={"expense": expense_id, "user_id": user_id})
            if serializer.is_valid():
                instance, created_flag = ExpenseArticleUser.objects.get_or_create(
                    expense_id=expense_id, user_id=user_id
                )
                if created_flag:
                    result.append(ExpenseArticleUserSerializer(instance).data)
        return Response(result, status=201)

    @extend_schema(
        summary="Р’РёРґР°Р»РёС‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡Р° Р·С– СЃС‚Р°С‚С‚С– РІРёС‚СЂР°С‚",
        description="Р’РёРґР°Р»РёС‚Рё РєРѕСЂРёСЃС‚СѓРІР°С‡Р° Р·С– СЃС‚Р°С‚С‚С– РІРёС‚СЂР°С‚.",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class UnitOfMeasureViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Р”РѕРІС–РґРЅРёРє РѕРґРёРЅРёС†СЊ РІРёРјС–СЂСѓ - СЃРїС–Р»СЊРЅРёР№ РґР»СЏ РІСЃС–С… РєРѕРјРїР°РЅС–Р№.
    РЎРїРёСЃРѕРє РѕРґРёРЅРёС†СЊ (СЃРїС–Р»СЊРЅС– company=null + РѕРґРёРЅРёС†С– РєРѕРјРїР°РЅС–Р№ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°).
    РќР°РїРѕРІРЅРµРЅРЅСЏ - С‡РµСЂРµР· Р‘Р”; СЃС‚РІРѕСЂРµРЅРЅСЏ/СЂРµРґР°РіСѓРІР°РЅРЅСЏ С‡РµСЂРµР· API РІРёРјРєРЅРµРЅРѕ.
    """

    serializer_class = UnitOfMeasureSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        """РЎРїС–Р»СЊРЅС– РѕРґРёРЅРёС†С– (company=null) + РѕРґРёРЅРёС†С– РєРѕРјРїР°РЅС–Р№ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°."""
        user = self.request.user
        if user.is_superuser:
            return UnitOfMeasure.objects.all().select_related("company").order_by("name_ua")
        user_companies = list(
            CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        return (
            UnitOfMeasure.objects.filter(
                Q(company__isnull=True) | Q(company_id__in=user_companies)
            )
            .select_related("company")
            .order_by("name_ua")
        )


class NomenclatureViewSet(viewsets.ModelViewSet):
    """
    РќРѕРјРµРЅРєР»Р°С‚СѓСЂР° (company-scoped).
    """

    serializer_class = NomenclatureSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Р¤С–Р»СЊС‚СЂСѓС” РЅРѕРјРµРЅРєР»Р°С‚СѓСЂСѓ Р·Р° РєРѕРјРїР°РЅС–СЏРјРё РєРѕСЂРёСЃС‚СѓРІР°С‡Р° С‚Р° РїР°СЂР°РјРµС‚СЂР°РјРё."""
        user = self.request.user
        if user.is_superuser:
            qs = Nomenclature.objects.all().select_related(
                "company", "unit", "category", "cpv_category"
            )
        else:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            qs = Nomenclature.objects.filter(
                company_id__in=user_companies
            ).select_related("company", "unit", "category", "cpv_category")

        # Р¤С–Р»СЊС‚СЂРё
        name = self.request.query_params.get("name")
        category_id = self.request.query_params.get("category_id")
        cpv_id = self.request.query_params.get("cpv_id")
        cpv_ids = _parse_int_list_param(self.request.query_params.getlist("cpv_ids"))

        if name:
            qs = qs.filter(name__icontains=name)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if cpv_ids:
            qs = qs.filter(
                Q(cpv_category_id__in=cpv_ids) | Q(cpv_categories__id__in=cpv_ids)
            ).distinct()
        elif cpv_id:
            qs = qs.filter(
                Q(cpv_category_id=cpv_id) | Q(cpv_categories__id=cpv_id)
            ).distinct()

        return qs

    @extend_schema(
        summary="РЎРїРёСЃРѕРє РЅРѕРјРµРЅРєР»Р°С‚СѓСЂРё",
        description="РћС‚СЂРёРјР°С‚Рё СЃРїРёСЃРѕРє РЅРѕРјРµРЅРєР»Р°С‚СѓСЂРё РєРѕРјРїР°РЅС–С— Р· РјРѕР¶Р»РёРІРёРјРё С„С–Р»СЊС‚СЂР°РјРё (name, category_id, cpv_id).",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="РЎС‚РІРѕСЂРёС‚Рё РЅРѕРјРµРЅРєР»Р°С‚СѓСЂСѓ",
        description="РЎС‚РІРѕСЂРёС‚Рё РЅРѕРІРёР№ РµР»РµРјРµРЅС‚ РЅРѕРјРµРЅРєР»Р°С‚СѓСЂРё.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="РћРЅРѕРІРёС‚Рё РЅРѕРјРµРЅРєР»Р°С‚СѓСЂСѓ",
        description="РћРЅРѕРІРёС‚Рё РґР°РЅС– РЅРѕРјРµРЅРєР»Р°С‚СѓСЂРё.",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Р’РёРґР°Р»РёС‚Рё РЅРѕРјРµРЅРєР»Р°С‚СѓСЂСѓ",
        description="Р’РёРґР°Р»РёС‚Рё РµР»РµРјРµРЅС‚ РЅРѕРјРµРЅРєР»Р°С‚СѓСЂРё.",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Р”РµР°РєС‚РёРІСѓРІР°С‚Рё РЅРѕРјРµРЅРєР»Р°С‚СѓСЂСѓ",
        description="РџРѕР·РЅР°С‡РёС‚Рё РЅРѕРјРµРЅРєР»Р°С‚СѓСЂСѓ СЏРє РЅРµР°РєС‚РёРІРЅСѓ (is_active = False).",
    )
    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        return Response(self.get_serializer(obj).data)

    @extend_schema(
        summary="РђРєС‚РёРІСѓРІР°С‚Рё РЅРѕРјРµРЅРєР»Р°С‚СѓСЂСѓ",
        description="РџРѕР·РЅР°С‡РёС‚Рё РЅРѕРјРµРЅРєР»Р°С‚СѓСЂСѓ СЏРє Р°РєС‚РёРІРЅСѓ (is_active = True).",
    )
    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        obj = self.get_object()
        obj.is_active = True
        obj.save(update_fields=["is_active"])
        return Response(self.get_serializer(obj).data)


class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Р”РѕРІС–РґРЅРёРє РІР°Р»СЋС‚ (СЃРёСЃС‚РµРјРЅРёР№, С‚С–Р»СЊРєРё С‡РёС‚Р°РЅРЅСЏ).
    """

    queryset = Currency.objects.all().order_by("code")
    serializer_class = CurrencySerializer
    permission_classes = [permissions.IsAuthenticated]


class TenderCriterionViewSet(viewsets.ModelViewSet):
    """
    Р”РѕРІС–РґРЅРёРє РєСЂРёС‚РµСЂС–С—РІ С‚РµРЅРґРµСЂС–РІ (company-scoped).
    """

    serializer_class = TenderCriterionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            qs = TenderCriterion.objects.all().select_related("company")
            tender_type = (self.request.query_params.get("tender_type") or "").strip()
            if tender_type in {"procurement", "sales"}:
                qs = qs.filter(tender_type=tender_type)
            return qs
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        qs = TenderCriterion.objects.filter(
            company_id__in=user_companies
        ).select_related("company")
        tender_type = (self.request.query_params.get("tender_type") or "").strip()
        if tender_type in {"procurement", "sales"}:
            qs = qs.filter(tender_type=tender_type)
        return qs

    def perform_create(self, serializer):
        tender_type = (self.request.query_params.get("tender_type") or "").strip()
        if tender_type in {"procurement", "sales"}:
            serializer.save(tender_type=tender_type)
            return
        serializer.save()


class TenderAttributeViewSet(viewsets.ModelViewSet):
    """
    Р”РѕРІС–РґРЅРёРє Р°С‚СЂРёР±СѓС‚С–РІ С‚РµРЅРґРµСЂС–РІ (company-scoped).
    """

    serializer_class = TenderAttributeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            qs = TenderAttribute.objects.all().select_related("company", "category")
            tender_type = (self.request.query_params.get("tender_type") or "").strip()
            if tender_type in {"procurement", "sales"}:
                qs = qs.filter(tender_type=tender_type)
            return qs
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        qs = TenderAttribute.objects.filter(
            company_id__in=user_companies
        ).select_related("company", "category")
        tender_type = (self.request.query_params.get("tender_type") or "").strip()
        if tender_type in {"procurement", "sales"}:
            qs = qs.filter(tender_type=tender_type)
        return qs

    def perform_create(self, serializer):
        tender_type = (self.request.query_params.get("tender_type") or "").strip()
        if tender_type in {"procurement", "sales"}:
            serializer.save(tender_type=tender_type)
            return
        serializer.save()


class ApprovalModelRoleViewSet(viewsets.ModelViewSet):
    serializer_class = ApprovalModelRoleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = ApprovalModelRole.objects.all().select_related("company")
        if not user.is_superuser:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            qs = qs.filter(company_id__in=user_companies)
        application = (self.request.query_params.get("application") or "").strip()
        if application in {"procurement", "sales"}:
            qs = qs.filter(application=application)
        return qs


class ApprovalModelRoleUserViewSet(viewsets.ModelViewSet):
    serializer_class = ApprovalModelRoleUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = ApprovalModelRoleUser.objects.all().select_related("role", "role__company", "user")
        if not user.is_superuser:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            qs = qs.filter(role__company_id__in=user_companies)
        role_id = self.request.query_params.get("role_id")
        if role_id:
            qs = qs.filter(role_id=role_id)
        return qs


class ApprovalRangeMatrixViewSet(viewsets.ModelViewSet):
    serializer_class = ApprovalRangeMatrixSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = ApprovalRangeMatrix.objects.all().select_related("company", "currency")
        if not user.is_superuser:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            qs = qs.filter(company_id__in=user_companies)
        return qs


class ApprovalModelViewSet(viewsets.ModelViewSet):
    serializer_class = ApprovalModelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = ApprovalModel.objects.all().select_related("company").prefetch_related(
            "categories", "ranges__currency", "steps__role", "steps__role__role_users__user"
        )
        if not user.is_superuser:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            qs = qs.filter(company_id__in=user_companies)

        application = (self.request.query_params.get("application") or "").strip()
        if application in {"procurement", "sales"}:
            qs = qs.filter(application=application)

        category_ids = _parse_int_list_param(self.request.query_params.getlist("category_ids"))
        if category_ids:
            qs = qs.filter(categories__id__in=category_ids).distinct()

        range_ids = _parse_int_list_param(self.request.query_params.getlist("range_ids"))
        if range_ids:
            qs = qs.filter(ranges__id__in=range_ids).distinct()
        return qs

    @action(detail=False, methods=["get"], url_path="available-for-tender")
    def available_for_tender(self, request):
        company_id, error_response = _resolve_request_company_id(request)
        if error_response:
            return error_response
        application = (request.query_params.get("application") or "").strip()
        if application not in {"procurement", "sales"}:
            return Response(
                {"detail": "application РјР°С” Р±СѓС‚Рё procurement Р°Р±Рѕ sales."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        category_id = request.query_params.get("category_id")
        budget_raw = request.query_params.get("estimated_budget")
        if category_id in (None, "") or budget_raw in (None, ""):
            return Response([])
        try:
            category_id_int = int(category_id)
            if category_id_int <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"detail": "Некоректне значення category_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            budget_val = Decimal(str(budget_raw))
        except (InvalidOperation, TypeError, ValueError):
            return Response(
                {"detail": "Некоректне значення estimated_budget."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = ApprovalModel.objects.filter(
            company_id=company_id, application=application, is_active=True
        ).prefetch_related("ranges__currency", "categories")
        qs = qs.filter(
            categories__id=category_id_int,
            ranges__budget_from__lte=budget_val,
            ranges__budget_to__gte=budget_val,
        ).distinct()
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class ApprovalModelStepViewSet(viewsets.ModelViewSet):
    serializer_class = ApprovalModelStepSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = ApprovalModelStep.objects.all().select_related("model", "model__company", "role")
        if not user.is_superuser:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            qs = qs.filter(model__company_id__in=user_companies)
        model_id = self.request.query_params.get("model_id")
        if model_id:
            qs = qs.filter(model_id=model_id)
        return qs


class ProcurementTenderViewSet(viewsets.ModelViewSet):
    """
    РўРµРЅРґРµСЂРё РЅР° Р·Р°РєСѓРїС–РІР»СЋ (company-scoped). РќРѕРјРµСЂ РїСЂРёСЃРІРѕСЋС”С‚СЊСЃСЏ РїСЂРё РїРµСЂС€РѕРјСѓ Р·Р±РµСЂРµР¶РµРЅРЅС–.
    Р”РѕСЃС‚СѓРї: Р±СѓРґСЊ-СЏРєРёР№ Р°РІС‚РѕСЂРёР·РѕРІР°РЅРёР№ РєРѕСЂРёСЃС‚СѓРІР°С‡ Р· РїС–РґС‚РІРµСЂРґР¶РµРЅРёРј С‡Р»РµРЅСЃС‚РІРѕРј Сѓ РєРѕРјРїР°РЅС–С—.
    РџСЂР°РІР° РґРѕСЃС‚СѓРїСѓ (tenders.create С‚РѕС‰Рѕ) РЅРµ РїРµСЂРµРІС–СЂСЏСЋС‚СЊСЃСЏ - РѕР±РјРµР¶РµРЅРЅСЏ Р·РЅСЏС‚Рѕ Р·Р° Р±Р°Р¶Р°РЅРЅСЏРј Р·Р°РјРѕРІРЅРёРєР°.
    """

    serializer_class = ProcurementTenderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("list", "active_tasks"):
            return ProcurementTenderListSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        user = self.request.user
        base_qs = ProcurementTender.objects.all()
        if self.action in ("list", "active_tasks"):
            base_qs = base_qs.select_related("created_by")
        else:
            base_qs = base_qs.select_related(
                "company", "category", "cpv_category", "expense_article",
                "branch", "department", "currency", "created_by", "parent",
            ).prefetch_related(
                "positions__nomenclature__unit",
                "tender_criteria",
                "criteria_items__reference_criterion",
            )
        if user.is_superuser:
            return base_qs
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        return base_qs.filter(company_id__in=user_companies)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        tender = serializer.instance
        _ensure_user_can_edit_tender(
            user=self.request.user,
            tender=tender,
            is_sales=False,
        )

        before_stage = getattr(tender, "stage", "") or ""
        target_stage = serializer.validated_data.get("stage", before_stage) or ""
        if (
            before_stage == ProcurementTender.Stage.PREPARATION
            and target_stage != ProcurementTender.Stage.PREPARATION
            and not _can_transition_from_preparation(
                tender=tender,
                is_sales=False,
                target_stage=target_stage,
            )
        ):
            raise DRFValidationError(
                {"stage": "Transition requires completed approval route."}
            )

        approval_model_changed = "approval_model" in serializer.validated_data
        serializer.save()
        if approval_model_changed:
            _ensure_stage_state_snapshot(
                tender=serializer.instance,
                is_sales=False,
                stage=TenderApprovalStageState.Stage.PREPARATION,
                rebuild=True,
            )
            _ensure_stage_state_snapshot(
                tender=serializer.instance,
                is_sales=False,
                stage=TenderApprovalStageState.Stage.APPROVAL,
                rebuild=True,
            )
        _log_tender_update_journal(
            before_stage=before_stage,
            tender=serializer.instance,
            request_data=self.request.data,
            actor=self.request.user,
            is_sales=False,
        )

    def get_object(self):
        """Р”РѕР·РІРѕР»РёС‚Рё РґРѕСЃС‚СѓРї РґРѕ С‚РµРЅРґРµСЂР° РѕСЂРіР°РЅС–Р·Р°С‚РѕСЂР° Р°Р±Рѕ РґРѕ С‚РµРЅРґРµСЂР°, РґРµ РєРѕРјРїР°РЅС–СЏ РєРѕСЂРёСЃС‚СѓРІР°С‡Р° РјР°С” РїСЂРѕРїРѕР·РёС†С–СЋ (СѓС‡Р°СЃРЅРёРє)."""
        queryset = self.filter_queryset(self.get_queryset())
        pk = self.kwargs.get("pk")
        obj = queryset.filter(pk=pk).first()
        if obj:
            return obj
        from django.http import Http404
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=self.request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if user_company_ids:
            obj = ProcurementTender.objects.filter(
                pk=pk,
                proposals__supplier_company_id__in=user_company_ids,
            ).select_related(
                "company", "category", "cpv_category", "expense_article",
                "branch", "department", "currency", "created_by", "parent",
            ).prefetch_related(
                "positions__nomenclature__unit",
                "tender_criteria",
                "criteria_items__reference_criterion",
            ).first()
            if obj:
                return obj
            # Р”РѕР·РІРѕР»СЏС”РјРѕ РїРµСЂРµРіР»СЏРґ РґРµС‚Р°Р»РµР№ С‚РµРЅРґРµСЂР°, РґРѕСЃС‚СѓРїРЅРѕРіРѕ РґР»СЏ СѓС‡Р°СЃС‚С–, С‰Рµ РґРѕ РїС–РґС‚РІРµСЂРґР¶РµРЅРЅСЏ СѓС‡Р°СЃС‚С–.
            obj = ProcurementTender.objects.filter(
                ~Q(company_id__in=user_company_ids),
                pk=pk,
                conduct_type__in=["rfx", "online_auction"],
                stage__in=["acceptance", "decision", "approval", "completed", "preparation"],
            ).select_related(
                "company", "category", "cpv_category", "expense_article",
                "branch", "department", "currency", "created_by", "parent",
            ).prefetch_related(
                "positions__nomenclature__unit",
                "tender_criteria",
                "criteria_items__reference_criterion",
            ).first()
            if obj:
                return obj
        approver_obj = ProcurementTender.objects.filter(
            pk=pk,
        ).select_related(
            "company", "category", "cpv_category", "expense_article",
            "branch", "department", "currency", "created_by", "parent",
        ).prefetch_related(
            "positions__nomenclature__unit",
            "tender_criteria",
            "criteria_items__reference_criterion",
        ).first()
        if approver_obj and _user_is_tender_approver(
            user=self.request.user,
            tender=approver_obj,
            is_sales=False,
        ):
            return approver_obj
        raise Http404("РўРµРЅРґРµСЂ РЅРµ Р·РЅР°Р№РґРµРЅРѕ.")

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="count_only",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Return only count of active tasks.",
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Max rows when count_only=false (default 200, max 1000).",
            ),
        ],
        responses=OpenApiTypes.OBJECT,
    )
    @action(detail=False, methods=["get"], url_path="active-tasks")
    def active_tasks(self, request):
        active_stages = ["preparation", "decision", "approval"]
        count_only = str(request.query_params.get("count_only", "")).strip().lower() in (
            "1",
            "true",
            "yes",
        )
        limit = _parse_int_param(request.query_params.get("limit"), default=200, min_value=1)
        limit = min(limit, 1000)

        owner_qs = self.get_queryset().filter(
            stage__in=active_stages,
            created_by=request.user,
        ).order_by("-created_at", "-id")

        owner_total = owner_qs.count()
        approver_total = _count_active_approver_tasks(user=request.user, is_sales=False)
        total = owner_total + approver_total
        if count_only:
            return Response({"count": total})

        owner_rows = list(self.get_serializer(owner_qs[:limit], many=True).data)
        for row in owner_rows:
            stage = str(row.get("stage") or "")
            row["task_kind"] = "author"
            row["task_action"] = _author_task_action_label(stage)
            row["task_created_at"] = row.get("updated_at") or row.get("created_at")

        approver_tasks = _collect_active_approver_tasks(
            user=request.user,
            is_sales=False,
        )[:limit]
        approver_tenders = [task["tender"] for task in approver_tasks]
        approver_rows = (
            list(self.get_serializer(approver_tenders, many=True).data)
            if approver_tenders
            else []
        )
        for row, task in zip(approver_rows, approver_tasks):
            stage = str(task.get("stage") or row.get("stage") or "")
            row["stage"] = stage
            row["stage_label"] = _approval_stage_label(stage) or row.get("stage_label", "")
            row["task_kind"] = "approver"
            row["task_action"] = task.get("task_action") or _approver_task_action_label(stage)
            task_created_at = task.get("task_created_at")
            row["task_created_at"] = (
                task_created_at.isoformat()
                if getattr(task_created_at, "isoformat", None)
                else row.get("updated_at") or row.get("created_at")
            )

        combined_rows = owner_rows + approver_rows
        combined_rows.sort(
            key=lambda row: str(
                row.get("task_created_at") or row.get("updated_at") or row.get("created_at") or ""
            ),
            reverse=True,
        )
        return Response(
            {
                "count": total,
                "limit": limit,
                "results": combined_rows[:limit],
            }
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(name="tab", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="active | processing | completed | journal"),
            OpenApiParameter(name="page", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="company_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="cpv_ids", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Comma-separated CPV ids"),
            OpenApiParameter(name="reception_started", type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY, description="Available only for tab=active"),
            OpenApiParameter(name="conduct_type", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="rfx | online_auction"),
            OpenApiParameter(name="tender_number", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Tender number exact match"),
            OpenApiParameter(name="submitted_only", type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY, description="Only tenders with submitted proposal by current company (for tab=journal: with at least one position proposal)"),
            OpenApiParameter(name="participation_result", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="participation | win"),
            OpenApiParameter(name="cursor_mode", type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY, description="Use cursor pagination"),
            OpenApiParameter(name="cursor", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Opaque cursor token from previous page"),
        ],
        responses=OpenApiTypes.OBJECT,
    )
    @action(detail=False, methods=["get"], url_path="for-participation")
    def for_participation(self, request):
        """Lightweight paginated list of procurement tenders for participation."""
        user = request.user
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return Response({
                "count": 0,
                "page": 1,
                "page_size": 20,
                "total_pages": 0,
                "next_cursor": None,
                "has_more": False,
                "companies": [],
                "cpv_tree": [],
                "results": [],
            })

        tab = (request.query_params.get("tab") or "active").strip().lower()
        page = _parse_int_param(request.query_params.get("page"), default=1, min_value=1)
        cursor_mode = str(request.query_params.get("cursor_mode", "")).strip().lower() in ("1", "true", "yes")
        cursor_token = (request.query_params.get("cursor") or "").strip()
        page_size = 20
        reception_started = str(request.query_params.get("reception_started", "")).strip().lower() in ("1", "true", "yes")
        conduct_type = (request.query_params.get("conduct_type") or "").strip().lower()
        tender_number = (request.query_params.get("tender_number") or "").strip()
        submitted_only = str(request.query_params.get("submitted_only", "")).strip().lower() in ("1", "true", "yes")
        participation_result = (request.query_params.get("participation_result") or "").strip().lower()
        company_id = _parse_int_param(request.query_params.get("company_id"), default=0, min_value=0)
        cpv_ids = _parse_int_list_param(request.query_params.getlist("cpv_ids"))
        expanded_cpv_ids = _expand_cpv_ids_with_descendants(cpv_ids)

        proposal_subquery = TenderProposal.objects.filter(
            tender_id=OuterRef("pk"),
            supplier_company_id__in=user_company_ids,
        )
        submitted_proposal_subquery = proposal_subquery.filter(submitted_at__isnull=False)
        position_proposal_subquery = proposal_subquery.filter(position_values__isnull=False)
        won_proposal_subquery = proposal_subquery.filter(won_positions__isnull=False)

        qs = (
            ProcurementTender.objects.filter(
                ~Q(company_id__in=user_company_ids),
                conduct_type__in=["rfx", "online_auction"],
                stage__in=["acceptance", "decision", "approval", "completed", "preparation"],
            )
            .select_related(
                "company",
            )
            .prefetch_related("cpv_categories")
            .annotate(
                current_user_has_proposal=Exists(proposal_subquery),
                current_user_has_submitted_proposal=Exists(submitted_proposal_subquery),
                current_user_has_position_proposal=Exists(position_proposal_subquery),
                current_user_has_win=Exists(won_proposal_subquery),
            )
        )
        qs = _filter_participation_qs_by_tab(qs, tab)
        participated_filter_field = (
            "current_user_has_position_proposal"
            if tab == "journal"
            else "current_user_has_submitted_proposal"
        )
        if tab == "active" and reception_started:
            qs = qs.filter(start_at__isnull=False, start_at__lte=timezone.now())
        if conduct_type in ("rfx", "online_auction"):
            qs = qs.filter(conduct_type=conduct_type)
        if submitted_only:
            qs = qs.filter(**{participated_filter_field: True})
        if participation_result == "win":
            qs = qs.filter(
                **{
                    participated_filter_field: True,
                    "current_user_has_win": True,
                }
            )
        elif participation_result == "participation":
            qs = qs.filter(
                **{
                    participated_filter_field: True,
                    "current_user_has_win": False,
                }
            )
        if company_id:
            qs = qs.filter(company_id=company_id)
        if tender_number:
            qs = _filter_participation_qs_by_tender_number(qs, tender_number, "p")

        cpv_tree = _build_cpv_tree_for_tenders_queryset(qs)

        if expanded_cpv_ids:
            qs = qs.filter(
                Q(cpv_category_id__in=expanded_cpv_ids)
                | Q(cpv_categories__id__in=expanded_cpv_ids)
            ).distinct()

        company_options_qs = qs.values(
            "company_id",
            "company__name",
            "company__edrpou",
        ).distinct().order_by("company__name", "company__edrpou")
        companies = [
            {
                "id": item["company_id"],
                "name": item["company__name"] or "",
                "edrpou": item["company__edrpou"] or "",
                "label": (
                    f"{item['company__name']} ({item['company__edrpou']})"
                    if item.get("company__edrpou")
                    else (item["company__name"] or "")
                ),
            }
            for item in company_options_qs
            if item.get("company_id")
        ]

        if cursor_mode:
            rows, next_cursor, has_more = _paginate_by_updated_cursor(
                qs=qs,
                cursor=cursor_token,
                page_size=page_size,
            )
            serializer = ProcurementParticipationTenderListSerializer(
                rows, many=True, context={"request": request}
            )
            return Response({
                "count": None,
                "page": page,
                "page_size": page_size,
                "total_pages": None,
                "next_cursor": next_cursor,
                "has_more": has_more,
                "companies": companies,
                "cpv_tree": cpv_tree,
                "results": serializer.data,
            })

        total = qs.count()
        total_pages = (total + page_size - 1) // page_size
        start = (page - 1) * page_size
        end = start + page_size
        paged_qs = qs.order_by("-updated_at")[start:end]

        serializer = ProcurementParticipationTenderListSerializer(
            paged_qs, many=True, context={"request": request}
        )
        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "next_cursor": None,
            "has_more": page < total_pages,
            "companies": companies,
            "cpv_tree": cpv_tree,
            "results": serializer.data,
        })

    @extend_schema(responses=TenderProposalSerializer)
    @action(detail=True, methods=["post"], url_path="confirm-participation")
    def confirm_participation(self, request, pk=None):
        """РџС–РґС‚РІРµСЂРґРёС‚Рё СѓС‡Р°СЃС‚СЊ: СЃС‚РІРѕСЂСЋС” РїСЂРѕРїРѕР·РёС†С–СЋ С‚Р° РґРѕРґР°С” РєРѕРЅС‚СЂР°РіРµРЅС‚Р° РІ РґРѕРІС–РґРЅРёРє РѕСЂРіР°РЅС–Р·Р°С‚РѕСЂР°."""
        tender = ProcurementTender.objects.filter(pk=pk).select_related("company").first()
        if not tender:
            return Response({"detail": "РўРµРЅРґРµСЂ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        if tender.stage not in ("acceptance", "preparation"):
            return Response(
                {"detail": "РЈС‡Р°СЃС‚СЊ РјРѕР¶РЅР° РїС–РґС‚РІРµСЂРґРёС‚Рё Р»РёС€Рµ РґР»СЏ С‚РµРЅРґРµСЂР° РЅР° РїСЂРёР№РѕРј РїСЂРѕРїРѕР·РёС†С–Р№ Р°Р±Рѕ РїС–РґРіРѕС‚РѕРІРєСѓ."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return Response(
                {"detail": "РќРµРјРѕР¶Р»РёРІРѕ РІРёР·РЅР°С‡РёС‚Рё РєРѕРјРїР°РЅС–СЋ СѓС‡Р°СЃРЅРёРєР°."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        supplier_company_id, error_response = _resolve_request_company_id(request)
        if error_response:
            return error_response
        if tender.company_id == supplier_company_id:
            return Response(
                {"detail": "РћСЂРіР°РЅС–Р·Р°С‚РѕСЂ РЅРµ РјРѕР¶Рµ РїС–РґС‚РІРµСЂРґРёС‚Рё СѓС‡Р°СЃС‚СЊ Сѓ РІР»Р°СЃРЅРѕРјСѓ С‚РµРЅРґРµСЂС–."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            proposal, created = TenderProposal.objects.get_or_create(
                tender=tender,
                supplier_company_id=supplier_company_id,
            )
            CompanySupplier.objects.get_or_create(
                owner_company_id=tender.company_id,
                supplier_company_id=supplier_company_id,
                defaults={"source": CompanySupplier.Source.PARTICIPATION},
            )
        serializer = TenderProposalSerializer(proposal)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @extend_schema(responses=TenderProposalSerializer)
    @action(detail=True, methods=["post"], url_path="submit-proposal")
    def submit_proposal(self, request, pk=None):
        """РџРѕРґР°С‚Рё РїСЂРѕРїРѕР·РёС†С–СЋ (С„С–РєСЃСѓС” РїРѕРґР°С‡Сѓ РґР»СЏ РєРѕРјРїР°РЅС–С— РїРѕС‚РѕС‡РЅРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°)."""
        tender = ProcurementTender.objects.filter(pk=pk).first()
        if not tender:
            return Response({"detail": "РўРµРЅРґРµСЂ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        if tender.stage != "acceptance":
            return Response(
                {"detail": "РџРѕРґР°С‚Рё РїСЂРѕРїРѕР·РёС†С–СЋ РјРѕР¶РЅР° Р»РёС€Рµ РїС–Рґ С‡Р°СЃ РµС‚Р°РїСѓ РїСЂРёР№РѕРјСѓ РїСЂРѕРїРѕР·РёС†С–Р№."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if tender.end_at and timezone.now() > tender.end_at:
            return Response(
                {"detail": "РўРµСЂРјС–РЅ РїСЂРёР№РѕРјСѓ РїСЂРѕРїРѕР·РёС†С–Р№ Р·Р°РІРµСЂС€РµРЅРѕ."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return Response(
                {"detail": "РќРµРјРѕР¶Р»РёРІРѕ РІРёР·РЅР°С‡РёС‚Рё РєРѕРјРїР°РЅС–СЋ."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        supplier_company_id, error_response = _resolve_request_company_id(request)
        if error_response:
            return error_response
        proposal = TenderProposal.objects.filter(
            tender=tender, supplier_company_id=supplier_company_id
        ).first()
        if not proposal:
            return Response(
                {"detail": "РџСЂРѕРїРѕР·РёС†С–СЋ РЅРµ Р·РЅР°Р№РґРµРЅРѕ. РЎРїРѕС‡Р°С‚РєСѓ РїС–РґС‚РІРµСЂРґС–С‚СЊ СѓС‡Р°СЃС‚СЊ."},
                status=status.HTTP_404_NOT_FOUND,
            )
        required_criteria_error = _validate_required_criteria_before_submit(
            tender=tender,
            proposal=proposal,
            proposal_position_model=TenderProposalPosition,
        )
        if required_criteria_error:
            return Response(required_criteria_error, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            proposal.submitted_at = timezone.now()
            proposal.status_updated_at = timezone.now()
            proposal.save(update_fields=["submitted_at", "status_updated_at"])
            CompanySupplier.objects.get_or_create(
                owner_company_id=tender.company_id,
                supplier_company_id=supplier_company_id,
                defaults={"source": CompanySupplier.Source.PARTICIPATION},
            )
        payload_for_ws = {
            "proposal_id": proposal.id,
            "submitted_at": proposal.submitted_at.isoformat() if proposal.submitted_at else None,
        }
        transaction.on_commit(
            lambda: publish_tender_event(
                "procurement",
                int(tender.id),
                "proposal.submitted_at.updated",
                payload_for_ws,
            )
        )
        serializer = TenderProposalSerializer(proposal)
        return Response(serializer.data)

    @extend_schema(responses=TenderProposalSerializer)
    @action(detail=True, methods=["post"], url_path="withdraw-proposal")
    def withdraw_proposal(self, request, pk=None):
        """Р’С–РґРєР»РёРєР°С‚Рё РїСЂРѕРїРѕР·РёС†С–СЋ (РєРѕРјРїР°РЅС–СЏ РїРѕС‚РѕС‡РЅРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°)."""
        tender = ProcurementTender.objects.filter(pk=pk).first()
        if not tender:
            return Response({"detail": "РўРµРЅРґРµСЂ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        if tender.stage != "acceptance":
            return Response(
                {"detail": "Р’С–РґРєР»РёРєР°С‚Рё РїСЂРѕРїРѕР·РёС†С–СЋ РјРѕР¶РЅР° Р»РёС€Рµ РїС–Рґ С‡Р°СЃ РµС‚Р°РїСѓ РїСЂРёР№РѕРјСѓ РїСЂРѕРїРѕР·РёС†С–Р№."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if tender.end_at and timezone.now() > tender.end_at:
            return Response(
                {"detail": "РўРµСЂРјС–РЅ РїСЂРёР№РѕРјСѓ РїСЂРѕРїРѕР·РёС†С–Р№ Р·Р°РІРµСЂС€РµРЅРѕ."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return Response(
                {"detail": "РќРµРјРѕР¶Р»РёРІРѕ РІРёР·РЅР°С‡РёС‚Рё РєРѕРјРїР°РЅС–СЋ."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        supplier_company_id, error_response = _resolve_request_company_id(request)
        if error_response:
            return error_response
        proposal = TenderProposal.objects.filter(
            tender=tender, supplier_company_id=supplier_company_id
        ).first()
        if not proposal:
            return Response(
                {"detail": "РџСЂРѕРїРѕР·РёС†С–СЋ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."},
                status=status.HTTP_404_NOT_FOUND,
            )
        proposal.submitted_at = None
        proposal.status_updated_at = timezone.now()
        proposal.save(update_fields=["submitted_at", "status_updated_at"])
        payload_for_ws = {
            "proposal_id": proposal.id,
            "submitted_at": None,
        }
        transaction.on_commit(
            lambda: publish_tender_event(
                "procurement",
                int(tender.id),
                "proposal.submitted_at.updated",
                payload_for_ws,
            )
        )
        serializer = TenderProposalSerializer(proposal)
        return Response(serializer.data)

    @extend_schema(responses=[{"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "tour_number": {"type": "integer"}}}}])
    @action(detail=True, methods=["get"], url_path="tours")
    def tours_list(self, request, pk=None):
        """РЈСЃС– С‚СѓСЂРё СЃС–РјРµР№СЃС‚РІР° (РІС–Рґ РєРѕСЂРµРЅСЏ + СѓСЃС– РЅР°СЃС‚СѓРїРЅС–) РґР»СЏ РІРёРїР°РґР°СЋС‡РѕРіРѕ СЃРїРёСЃРєСѓ."""
        tender = self.get_object()
        root = tender
        while root.parent_id:
            root = root.parent
        collected = [root]
        stack = list(root.next_tours.all())
        while stack:
            t = stack.pop()
            collected.append(t)
            stack.extend(t.next_tours.all())
        collected.sort(key=lambda t: t.tour_number)
        return Response([{"id": t.id, "tour_number": t.tour_number} for t in collected])

    @action(detail=True, methods=["get"], url_path="approval-journal")
    def approval_journal(self, request, pk=None):
        tender = self.get_object()
        qs = TenderApprovalJournal.objects.filter(
            procurement_tender=tender
        ).select_related("actor")
        serializer = TenderApprovalJournalSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="approval-route")
    def approval_route(self, request, pk=None):
        tender = self.get_object()
        payload = _build_tender_approval_route_payload(
            tender=tender,
            is_sales=False,
            user=request.user,
            stage=tender.stage or "",
        )
        return Response(payload)

    @action(detail=True, methods=["post"], url_path="approval-submit")
    def approval_submit(self, request, pk=None):
        tender = self.get_object()
        comment = (request.data.get("comment") or "").strip()
        try:
            _submit_tender_preparation_for_approval(
                tender=tender,
                is_sales=False,
                actor=request.user,
                comment=comment,
            )
        except DRFValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        payload = _build_tender_approval_route_payload(
            tender=tender,
            is_sales=False,
            user=request.user,
            stage=tender.stage or "",
        )
        return Response({"id": tender.id, "stage": tender.stage, "route": payload})

    @action(detail=True, methods=["post"], url_path="approval-action")
    def approval_action(self, request, pk=None):
        tender = self.get_object()
        action_type = (request.data.get("action") or "").strip().lower()
        comment = (request.data.get("comment") or "").strip()
        try:
            _apply_tender_approval_action(
                tender=tender,
                is_sales=False,
                actor=request.user,
                action_type=action_type,
                comment=comment,
            )
        except DRFValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        payload = _build_tender_approval_route_payload(
            tender=tender,
            is_sales=False,
            user=request.user,
            stage=tender.stage or "",
        )
        return Response({"id": tender.id, "stage": tender.stage, "route": payload})

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["winner", "cancel", "next_round"]},
                    "position_winners": {
                        "type": "array",
                        "items": {"type": "object", "properties": {"position_id": {"type": "integer"}, "proposal_id": {"type": "integer"}}},
                    },
                    "comment": {"type": "string"},
                },
                "required": ["mode"],
            }
        },
    )
    @action(detail=True, methods=["post"], url_path="fix-decision")
    def fix_decision(self, request, pk=None):
        """
        Р—Р°С„С–РєСЃСѓРІР°С‚Рё СЂС–С€РµРЅРЅСЏ: winner - Р· РїРµСЂРµРјРѕР¶С†СЏРјРё РїРѕ РїРѕР·РёС†С–СЏС…, cancel - Р±РµР· РїРµСЂРµРјРѕР¶С†С–РІ,
        next_round - СЃС‚РІРѕСЂРёС‚Рё РЅР°СЃС‚СѓРїРЅРёР№ С‚СѓСЂ РЅР° РµС‚Р°РїС– РїС–РґРіРѕС‚РѕРІРєРё.
        """
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        mode = request.data.get("mode")
        comment = str(request.data.get("comment") or "").strip()
        journal_comment = comment or "Передано на затвердження"
        if mode not in ("winner", "cancel", "next_round"):
            return Response(
                {"detail": "mode РјР°С” Р±СѓС‚Рё: winner, cancel Р°Р±Рѕ next_round."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if mode == "winner":
            position_winners = request.data.get("position_winners") or []
            # РЎРєРёРЅСѓС‚Рё РІСЃС– РїРµСЂРµРјРѕР¶С†С– РїРѕ С†СЊРѕРјСѓ С‚РµРЅРґРµСЂСѓ, РїРѕС‚С–Рј РІСЃС‚Р°РЅРѕРІРёС‚Рё С‚С–Р»СЊРєРё РїРµСЂРµРґР°РЅС–
            ProcurementTenderPosition.objects.filter(tender=tender).update(winner_proposal=None)
            for item in position_winners:
                pos_id = item.get("position_id")
                prop_id = item.get("proposal_id")
                if pos_id is not None and prop_id is not None:
                    pos = ProcurementTenderPosition.objects.filter(tender=tender, id=pos_id).first()
                    if pos and TenderProposal.objects.filter(tender=tender, id=prop_id).exists():
                        pos.winner_proposal_id = prop_id
                        pos.save()
            tender.stage = "approval"
            tender.save(update_fields=["stage"])
            _start_approval_stage_cycle_if_needed(tender=tender, is_sales=False)
            _create_tender_approval_journal_entry(
                procurement_tender=tender,
                stage=tender.stage or "",
                action=TenderApprovalJournal.Action.SAVED,
                comment=journal_comment,
                actor=request.user,
            )
            return Response({"stage": "approval", "id": tender.id})
        if mode == "cancel":
            ProcurementTenderPosition.objects.filter(tender=tender).update(winner_proposal=None)
            tender.stage = "approval"
            tender.save(update_fields=["stage"])
            _start_approval_stage_cycle_if_needed(tender=tender, is_sales=False)
            _create_tender_approval_journal_entry(
                procurement_tender=tender,
                stage=tender.stage or "",
                action=TenderApprovalJournal.Action.SAVED,
                comment=journal_comment,
                actor=request.user,
            )
            return Response({"stage": "approval", "id": tender.id})
        # next_round
        parent = tender
        new_tender = ProcurementTender.objects.create(
            company=parent.company,
            parent=parent,
            tour_number=(parent.tour_number or 1) + 1,
            name=parent.name,
            stage="preparation",
            category=parent.category,
            expense_article=parent.expense_article,
            estimated_budget=parent.estimated_budget,
            branch=parent.branch,
            department=parent.department,
            conduct_type=parent.conduct_type,
            publication_type=parent.publication_type,
            currency=parent.currency,
            general_terms=parent.general_terms or "",
            price_criterion_vat=parent.price_criterion_vat or "",
            price_criterion_delivery=parent.price_criterion_delivery or "",
            approval_model=parent.approval_model,
            created_by=request.user,
        )
        new_tender.cpv_categories.set(parent.cpv_categories.all())
        new_tender.tender_criteria.set(parent.tender_criteria.all())
        if parent.criteria_items.exists():
            for crit in parent.criteria_items.all():
                ProcurementTenderCriterion.objects.create(
                    tender=new_tender,
                    reference_criterion=crit.reference_criterion,
                    name=crit.name,
                    type=crit.type,
                    application=crit.application,
                    is_required=bool(crit.is_required),
                    options=crit.options or {},
                )
        else:
            for crit in parent.tender_criteria.all():
                ProcurementTenderCriterion.objects.create(
                    tender=new_tender,
                    reference_criterion=crit,
                    name=crit.name,
                    type=crit.type,
                    application=getattr(crit, "application", TenderCriterion.Application.INDIVIDUAL),
                    is_required=bool(getattr(crit, "is_required", False)),
                    options=getattr(crit, "options", {}) or {},
                )
        for pos in parent.positions.all():
            ProcurementTenderPosition.objects.create(
                tender=new_tender,
                nomenclature=pos.nomenclature,
                quantity=pos.quantity,
                description=pos.description or "",
            )
        return Response({"stage": "preparation", "id": new_tender.id}, status=status.HTTP_201_CREATED)

    @extend_schema(responses=TenderProposalSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="proposals")
    def proposals_list(self, request, pk=None):
        """РЎРїРёСЃРѕРє РїСЂРѕРїРѕР·РёС†С–Р№ РїРѕ С‚РµРЅРґРµСЂСѓ."""
        tender = self.get_object()
        view_mode = str(request.query_params.get("view") or "").strip().lower()
        updated_since = _parse_iso_datetime_param(
            request.query_params.get("updated_since")
        )
        proposal_ids_raw = request.query_params.getlist("ids")
        if not proposal_ids_raw:
            proposal_ids_raw = request.query_params.get("ids")
        proposal_ids = _parse_int_list_param(proposal_ids_raw)
        if view_mode == "status":
            throttled_response, rate_limit_remaining = _enforce_status_sync_rate_limit(
                request=request,
                kind="procurement",
                tender_id=int(tender.id),
            )
            if throttled_response is not None:
                return throttled_response
            use_delta_cache = updated_since is not None and not proposal_ids
            cache_key = None
            if use_delta_cache and request.user and request.user.is_authenticated:
                cache_key = _build_status_sync_cache_key(
                    kind="procurement",
                    tender_id=int(tender.id),
                    user_id=int(request.user.id),
                    updated_since=updated_since,
                )
                cached_data = cache.get(cache_key)
                if cached_data is not None:
                    response = Response(cached_data)
                    response["X-Status-Sync-Cache"] = "HIT"
                    if rate_limit_remaining is not None:
                        response["X-Status-Sync-RateLimit-Limit"] = str(
                            STATUS_SYNC_THROTTLE_PER_MINUTE
                        )
                        response["X-Status-Sync-RateLimit-Remaining"] = str(
                            rate_limit_remaining
                        )
                    _status_sync_log(
                        "cache_hit",
                        kind="procurement",
                        tender_id=int(tender.id),
                        user_id=int(request.user.id),
                        rows=len(cached_data),
                    )
                    return response
            qs = TenderProposal.objects.filter(tender=tender).select_related(
                "supplier_company"
            )
            if updated_since is not None:
                qs = qs.filter(status_updated_at__gt=updated_since)
            if proposal_ids:
                qs = qs.filter(id__in=proposal_ids)
            elif "ids" in request.query_params:
                return Response([])
            serializer = TenderProposalStatusSerializer(qs, many=True)
            data = list(serializer.data)
            if cache_key:
                cache.set(cache_key, data, STATUS_SYNC_CACHE_TTL_SECONDS)
                response = Response(data)
                response["X-Status-Sync-Cache"] = "MISS"
                if rate_limit_remaining is not None:
                    response["X-Status-Sync-RateLimit-Limit"] = str(
                        STATUS_SYNC_THROTTLE_PER_MINUTE
                    )
                    response["X-Status-Sync-RateLimit-Remaining"] = str(
                        rate_limit_remaining
                    )
                _status_sync_log(
                    "cache_miss",
                    kind="procurement",
                    tender_id=int(tender.id),
                    user_id=int(request.user.id) if request.user and request.user.is_authenticated else None,
                    rows=len(data),
                )
                return response
            response = Response(data)
            if rate_limit_remaining is not None:
                response["X-Status-Sync-RateLimit-Limit"] = str(
                    STATUS_SYNC_THROTTLE_PER_MINUTE
                )
                response["X-Status-Sync-RateLimit-Remaining"] = str(
                    rate_limit_remaining
                )
            _status_sync_log(
                "no_cache",
                kind="procurement",
                tender_id=int(tender.id),
                user_id=int(request.user.id) if request.user and request.user.is_authenticated else None,
                rows=len(data),
            )
            return response
        qs = TenderProposal.objects.filter(tender=tender).select_related(
            "supplier_company"
        ).prefetch_related(
            "position_values__tender_position__nomenclature__unit",
        )
        if proposal_ids:
            qs = qs.filter(id__in=proposal_ids)
        elif "ids" in request.query_params:
            return Response([])
        serializer = TenderProposalSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(request=TenderProposalSerializer, responses=TenderProposalSerializer)
    @action(detail=True, methods=["post"], url_path="proposals/add")
    def proposal_add(self, request, pk=None):
        """Р”РѕРґР°С‚Рё РїСЂРѕРїРѕР·РёС†С–СЋ (РѕР±СЂР°С‚Рё РєРѕРЅС‚СЂР°РіРµРЅС‚Р°)."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        supplier_company_id = request.data.get("supplier_company_id") or request.data.get("supplier_company")
        if not supplier_company_id:
            return Response(
                {"detail": "РџРѕС‚СЂС–Р±РЅРѕ РІРєР°Р·Р°С‚Рё supplier_company_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        proposal, created = TenderProposal.objects.get_or_create(
            tender=tender,
            supplier_company_id=supplier_company_id,
        )
        serializer = TenderProposalSerializer(proposal)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @extend_schema(request=TenderProposalPositionUpdateSerializer)
    @action(detail=True, methods=["post", "patch"], url_path=r"proposals/(?P<proposal_id>[^/.]+)/position-values")
    def proposal_position_values(self, request, pk=None, proposal_id=None):
        """РћРЅРѕРІРёС‚Рё Р·РЅР°С‡РµРЅРЅСЏ РїРѕ РїРѕР·РёС†С–СЏС… РїСЂРѕРїРѕР·РёС†С–С— (С†С–РЅР° + РєСЂРёС‚РµСЂС–С—)."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        proposal = TenderProposal.objects.filter(
            tender=tender, id=proposal_id
        ).prefetch_related("position_values__tender_position").first()
        if not proposal:
            return Response({"detail": "РџСЂРѕРїРѕР·РёС†С–СЋ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        payload = TenderProposalPositionUpdateSerializer(data=request.data)
        if not payload.is_valid():
            return Response(payload.errors, status=status.HTTP_400_BAD_REQUEST)
        position_values_data = payload.validated_data.get("position_values") or []
        changed_position_ids: set[int] = set()
        for item in position_values_data:
            tp_id = item.get("tender_position_id")
            if not tp_id:
                continue
            pos = ProcurementTenderPosition.objects.filter(
                tender=tender, id=tp_id
            ).first()
            if not pos:
                continue
            if "price" in item:
                price_validation_error = _validate_online_auction_position_price(
                    tender=tender,
                    position=pos,
                    proposal_position_model=TenderProposalPosition,
                    new_price=item.get("price"),
                    is_procurement=True,
                )
                if price_validation_error:
                    return Response(
                        {"detail": price_validation_error, "tender_position_id": tp_id},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            pv, _ = TenderProposalPosition.objects.get_or_create(
                proposal=proposal, tender_position=pos,
                defaults={"price": None, "criterion_values": {}},
            )
            if "price" in item:
                pv.price = item["price"]
            if "criterion_values" in item:
                pv.criterion_values = item["criterion_values"]
            pv.save()
            changed_position_ids.add(int(tp_id))
        if changed_position_ids:
            payload_for_ws = {
                "proposal_id": proposal.id,
                "position_ids": sorted(changed_position_ids),
            }
            transaction.on_commit(
                lambda: publish_tender_event(
                    "procurement",
                    int(tender.id),
                    "proposal.position_values.updated",
                    payload_for_ws,
                )
            )
        qs = TenderProposal.objects.filter(id=proposal.id).prefetch_related(
            "position_values__tender_position__nomenclature__unit",
        )
        serializer = TenderProposalSerializer(qs.first())
        return Response(serializer.data)

    @extend_schema(responses=TenderProposalSerializer(many=True))
    @action(detail=True, methods=["get"], url_path=r"proposals/(?P<proposal_id>[^/.]+)")
    def proposal_detail(self, request, pk=None, proposal_id=None):
        """Р”РµС‚Р°Р»С– РїСЂРѕРїРѕР·РёС†С–С— (Р· РїРѕР·РёС†С–СЏРјРё С‚Р° Р·РЅР°С‡РµРЅРЅСЏРјРё)."""
        tender = self.get_object()
        proposal = TenderProposal.objects.filter(
            tender=tender, id=proposal_id
        ).prefetch_related(
            "position_values__tender_position__nomenclature__unit",
        ).first()
        if not proposal:
            return Response({"detail": "РџСЂРѕРїРѕР·РёС†С–СЋ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TenderProposalSerializer(proposal)
        return Response(serializer.data)

    @extend_schema(responses=ProcurementTenderFileSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="files")
    def files_list(self, request, pk=None):
        """РЎРїРёСЃРѕРє РїСЂРёРєСЂС–РїР»РµРЅРёС… С„Р°Р№Р»С–РІ."""
        tender = self.get_object()
        qs = ProcurementTenderFile.objects.filter(tender=tender)
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        is_owner = tender.company_id in user_company_ids
        if not is_owner:
            qs = qs.filter(visible_to_participants=True)
        serializer = ProcurementTenderFileSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(request=OpenApiTypes.BINARY, responses=ProcurementTenderFileSerializer)
    @action(detail=True, methods=["post"], url_path="files/upload")
    def file_upload(self, request, pk=None):
        """РџСЂРёРєСЂС–РїРёС‚Рё С„Р°Р№Р» РґРѕ С‚РµРЅРґРµСЂР°."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        file_obj = request.FILES.get("file") or request.FILES.get("file_upload")
        if not file_obj:
            return Response(
                {"detail": "РќР°РґС–С€Р»С–С‚СЊ С„Р°Р№Р» Сѓ РїРѕР»С– file Р°Р±Рѕ file_upload."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        validation_error = _validate_tender_file(file_obj)
        if validation_error:
            return Response({"detail": validation_error}, status=status.HTTP_400_BAD_REQUEST)
        name = request.data.get("name", "") or file_obj.name
        visible = request.data.get("visible_to_participants", True)
        if isinstance(visible, str):
            visible = visible.lower() in ("true", "1", "yes")
        obj = ProcurementTenderFile.objects.create(
            tender=tender,
            file=file_obj,
            name=name[:255],
            uploaded_by=getattr(request, "user", None),
            visible_to_participants=bool(visible),
        )
        serializer = ProcurementTenderFileSerializer(
            obj, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"files/(?P<file_id>\d+)")
    def file_delete(self, request, pk=None, file_id=None):
        """Р’РёРґР°Р»РёС‚Рё РїСЂРёРєСЂС–РїР»РµРЅРёР№ С„Р°Р№Р»."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        obj = ProcurementTenderFile.objects.filter(tender=tender, id=file_id).first()
        if not obj:
            return Response({"detail": "Р¤Р°Р№Р» РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["patch"], url_path=r"files/(?P<file_id>\d+)")
    def file_patch(self, request, pk=None, file_id=None):
        """РћРЅРѕРІРёС‚Рё РІРёРґРёРјС–СЃС‚СЊ С„Р°Р№Р»Сѓ СѓС‡Р°СЃРЅРёРєР°Рј."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        obj = ProcurementTenderFile.objects.filter(tender=tender, id=file_id).first()
        if not obj:
            return Response({"detail": "Р¤Р°Р№Р» РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        if "visible_to_participants" in request.data:
            obj.visible_to_participants = bool(request.data["visible_to_participants"])
            obj.save(update_fields=["visible_to_participants"])
        serializer = ProcurementTenderFileSerializer(obj, context={"request": request})
        return Response(serializer.data)


class SalesTenderViewSet(viewsets.ModelViewSet):
    """
    РўРµРЅРґРµСЂРё РЅР° РїСЂРѕРґР°Р¶ (company-scoped). РўР° СЃР°РјР° РїСЂРѕС†РµРґСѓСЂР° С‰Рѕ Р№ Р·Р°РєСѓРїС–РІР»СЏ;
    РїРµСЂРµРјРѕР¶РµС†СЊ СЂРµРєРѕРјРµРЅРґСѓС”С‚СЊСЃСЏ Р·Р° РЅР°Р№Р±С–Р»СЊС€РѕСЋ С†С–РЅРѕСЋ.
    """

    serializer_class = SalesTenderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("list", "active_tasks"):
            return SalesTenderListSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        user = self.request.user
        base_qs = SalesTender.objects.all()
        if self.action in ("list", "active_tasks"):
            base_qs = base_qs.select_related("created_by")
        else:
            base_qs = base_qs.select_related(
                "company", "category", "cpv_category", "expense_article",
                "branch", "department", "currency", "created_by", "parent",
            ).prefetch_related(
                "positions__nomenclature__unit",
                "tender_criteria",
                "criteria_items__reference_criterion",
            )
        if user.is_superuser:
            return base_qs
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        return base_qs.filter(company_id__in=user_companies)

    def get_object(self):
        """Р”РѕР·РІРѕР»РёС‚Рё РґРѕСЃС‚СѓРї РґРѕ С‚РµРЅРґРµСЂР° РѕСЂРіР°РЅС–Р·Р°С‚РѕСЂР° Р°Р±Рѕ РґРѕ С‚РµРЅРґРµСЂР°, РґРµ РєРѕРјРїР°РЅС–СЏ РєРѕСЂРёСЃС‚СѓРІР°С‡Р° РјР°С” РїСЂРѕРїРѕР·РёС†С–СЋ (СѓС‡Р°СЃРЅРёРє)."""
        queryset = self.filter_queryset(self.get_queryset())
        pk = self.kwargs.get("pk")
        obj = queryset.filter(pk=pk).first()
        if obj:
            return obj
        from django.http import Http404
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=self.request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if user_company_ids:
            obj = SalesTender.objects.filter(
                pk=pk,
                proposals__supplier_company_id__in=user_company_ids,
            ).select_related(
                "company", "category", "cpv_category", "expense_article",
                "branch", "department", "currency", "created_by", "parent",
            ).prefetch_related(
                "positions__nomenclature__unit",
                "tender_criteria",
                "criteria_items__reference_criterion",
            ).first()
            if obj:
                return obj
            # Р”РѕР·РІРѕР»СЏС”РјРѕ РїРµСЂРµРіР»СЏРґ РґРµС‚Р°Р»РµР№ С‚РµРЅРґРµСЂР°, РґРѕСЃС‚СѓРїРЅРѕРіРѕ РґР»СЏ СѓС‡Р°СЃС‚С–, С‰Рµ РґРѕ РїС–РґС‚РІРµСЂРґР¶РµРЅРЅСЏ СѓС‡Р°СЃС‚С–.
            obj = SalesTender.objects.filter(
                ~Q(company_id__in=user_company_ids),
                pk=pk,
                conduct_type__in=["rfx", "online_auction"],
                stage__in=["acceptance", "decision", "approval", "completed", "preparation"],
            ).select_related(
                "company", "category", "cpv_category", "expense_article",
                "branch", "department", "currency", "created_by", "parent",
            ).prefetch_related(
                "positions__nomenclature__unit",
                "tender_criteria",
                "criteria_items__reference_criterion",
            ).first()
            if obj:
                return obj
        approver_obj = SalesTender.objects.filter(
            pk=pk,
        ).select_related(
            "company", "category", "cpv_category", "expense_article",
            "branch", "department", "currency", "created_by", "parent",
        ).prefetch_related(
            "positions__nomenclature__unit",
            "tender_criteria",
            "criteria_items__reference_criterion",
        ).first()
        if approver_obj and _user_is_tender_approver(
            user=self.request.user,
            tender=approver_obj,
            is_sales=True,
        ):
            return approver_obj
        raise Http404("РўРµРЅРґРµСЂ РЅРµ Р·РЅР°Р№РґРµРЅРѕ.")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        tender = serializer.instance
        _ensure_user_can_edit_tender(
            user=self.request.user,
            tender=tender,
            is_sales=True,
        )

        before_stage = getattr(tender, "stage", "") or ""
        target_stage = serializer.validated_data.get("stage", before_stage) or ""
        if (
            before_stage == SalesTender.Stage.PREPARATION
            and target_stage != SalesTender.Stage.PREPARATION
            and not _can_transition_from_preparation(
                tender=tender,
                is_sales=True,
                target_stage=target_stage,
            )
        ):
            raise DRFValidationError(
                {"stage": "Transition requires completed approval route."}
            )

        approval_model_changed = "approval_model" in serializer.validated_data
        serializer.save()
        if approval_model_changed:
            _ensure_stage_state_snapshot(
                tender=serializer.instance,
                is_sales=True,
                stage=TenderApprovalStageState.Stage.PREPARATION,
                rebuild=True,
            )
            _ensure_stage_state_snapshot(
                tender=serializer.instance,
                is_sales=True,
                stage=TenderApprovalStageState.Stage.APPROVAL,
                rebuild=True,
            )
        _log_tender_update_journal(
            before_stage=before_stage,
            tender=serializer.instance,
            request_data=self.request.data,
            actor=self.request.user,
            is_sales=True,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="count_only",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Return only count of active tasks.",
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Max rows when count_only=false (default 200, max 1000).",
            ),
        ],
        responses=OpenApiTypes.OBJECT,
    )
    @action(detail=False, methods=["get"], url_path="active-tasks")
    def active_tasks(self, request):
        active_stages = ["preparation", "decision", "approval"]
        count_only = str(request.query_params.get("count_only", "")).strip().lower() in (
            "1",
            "true",
            "yes",
        )
        limit = _parse_int_param(request.query_params.get("limit"), default=200, min_value=1)
        limit = min(limit, 1000)

        owner_qs = self.get_queryset().filter(
            stage__in=active_stages,
            created_by=request.user,
        ).order_by("-created_at", "-id")

        owner_total = owner_qs.count()
        approver_total = _count_active_approver_tasks(user=request.user, is_sales=True)
        total = owner_total + approver_total
        if count_only:
            return Response({"count": total})

        owner_rows = list(self.get_serializer(owner_qs[:limit], many=True).data)
        for row in owner_rows:
            stage = str(row.get("stage") or "")
            row["task_kind"] = "author"
            row["task_action"] = _author_task_action_label(stage)
            row["task_created_at"] = row.get("updated_at") or row.get("created_at")

        approver_tasks = _collect_active_approver_tasks(
            user=request.user,
            is_sales=True,
        )[:limit]
        approver_tenders = [task["tender"] for task in approver_tasks]
        approver_rows = (
            list(self.get_serializer(approver_tenders, many=True).data)
            if approver_tenders
            else []
        )
        for row, task in zip(approver_rows, approver_tasks):
            stage = str(task.get("stage") or row.get("stage") or "")
            row["stage"] = stage
            row["stage_label"] = _approval_stage_label(stage) or row.get("stage_label", "")
            row["task_kind"] = "approver"
            row["task_action"] = task.get("task_action") or _approver_task_action_label(stage)
            task_created_at = task.get("task_created_at")
            row["task_created_at"] = (
                task_created_at.isoformat()
                if getattr(task_created_at, "isoformat", None)
                else row.get("updated_at") or row.get("created_at")
            )

        combined_rows = owner_rows + approver_rows
        combined_rows.sort(
            key=lambda row: str(
                row.get("task_created_at") or row.get("updated_at") or row.get("created_at") or ""
            ),
            reverse=True,
        )
        return Response(
            {
                "count": total,
                "limit": limit,
                "results": combined_rows[:limit],
            }
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(name="tab", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="active | processing | completed | journal"),
            OpenApiParameter(name="page", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="company_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="cpv_ids", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Comma-separated CPV ids"),
            OpenApiParameter(name="reception_started", type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY, description="Available only for tab=active"),
            OpenApiParameter(name="conduct_type", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="rfx | online_auction"),
            OpenApiParameter(name="tender_number", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Tender number exact match"),
            OpenApiParameter(name="submitted_only", type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY, description="Only tenders with submitted proposal by current company (for tab=journal: with at least one position proposal)"),
            OpenApiParameter(name="participation_result", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="participation | win"),
            OpenApiParameter(name="cursor_mode", type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY, description="Use cursor pagination"),
            OpenApiParameter(name="cursor", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="Opaque cursor token from previous page"),
        ],
        responses=OpenApiTypes.OBJECT,
    )
    @action(detail=False, methods=["get"], url_path="for-participation")
    def for_participation(self, request):
        """Lightweight paginated list of sales tenders for participation."""
        user = request.user
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return Response({
                "count": 0,
                "page": 1,
                "page_size": 20,
                "total_pages": 0,
                "next_cursor": None,
                "has_more": False,
                "companies": [],
                "cpv_tree": [],
                "results": [],
            })

        tab = (request.query_params.get("tab") or "active").strip().lower()
        page = _parse_int_param(request.query_params.get("page"), default=1, min_value=1)
        cursor_mode = str(request.query_params.get("cursor_mode", "")).strip().lower() in ("1", "true", "yes")
        cursor_token = (request.query_params.get("cursor") or "").strip()
        page_size = 20
        reception_started = str(request.query_params.get("reception_started", "")).strip().lower() in ("1", "true", "yes")
        conduct_type = (request.query_params.get("conduct_type") or "").strip().lower()
        tender_number = (request.query_params.get("tender_number") or "").strip()
        submitted_only = str(request.query_params.get("submitted_only", "")).strip().lower() in ("1", "true", "yes")
        participation_result = (request.query_params.get("participation_result") or "").strip().lower()
        company_id = _parse_int_param(request.query_params.get("company_id"), default=0, min_value=0)
        cpv_ids = _parse_int_list_param(request.query_params.getlist("cpv_ids"))
        expanded_cpv_ids = _expand_cpv_ids_with_descendants(cpv_ids)

        proposal_subquery = SalesTenderProposal.objects.filter(
            tender_id=OuterRef("pk"),
            supplier_company_id__in=user_company_ids,
        )
        submitted_proposal_subquery = proposal_subquery.filter(submitted_at__isnull=False)
        position_proposal_subquery = proposal_subquery.filter(position_values__isnull=False)
        won_proposal_subquery = proposal_subquery.filter(won_positions__isnull=False)

        qs = (
            SalesTender.objects.filter(
                ~Q(company_id__in=user_company_ids),
                conduct_type__in=["rfx", "online_auction"],
                stage__in=["acceptance", "decision", "approval", "completed", "preparation"],
            )
            .select_related(
                "company",
            )
            .prefetch_related("cpv_categories")
            .annotate(
                current_user_has_proposal=Exists(proposal_subquery),
                current_user_has_submitted_proposal=Exists(submitted_proposal_subquery),
                current_user_has_position_proposal=Exists(position_proposal_subquery),
                current_user_has_win=Exists(won_proposal_subquery),
            )
        )
        qs = _filter_participation_qs_by_tab(qs, tab)
        participated_filter_field = (
            "current_user_has_position_proposal"
            if tab == "journal"
            else "current_user_has_submitted_proposal"
        )
        if tab == "active" and reception_started:
            qs = qs.filter(start_at__isnull=False, start_at__lte=timezone.now())
        if conduct_type in ("rfx", "online_auction"):
            qs = qs.filter(conduct_type=conduct_type)
        if submitted_only:
            qs = qs.filter(**{participated_filter_field: True})
        if participation_result == "win":
            qs = qs.filter(
                **{
                    participated_filter_field: True,
                    "current_user_has_win": True,
                }
            )
        elif participation_result == "participation":
            qs = qs.filter(
                **{
                    participated_filter_field: True,
                    "current_user_has_win": False,
                }
            )
        if company_id:
            qs = qs.filter(company_id=company_id)
        if tender_number:
            qs = _filter_participation_qs_by_tender_number(qs, tender_number, "s")

        cpv_tree = _build_cpv_tree_for_tenders_queryset(qs)

        if expanded_cpv_ids:
            qs = qs.filter(
                Q(cpv_category_id__in=expanded_cpv_ids)
                | Q(cpv_categories__id__in=expanded_cpv_ids)
            ).distinct()

        company_options_qs = qs.values(
            "company_id",
            "company__name",
            "company__edrpou",
        ).distinct().order_by("company__name", "company__edrpou")
        companies = [
            {
                "id": item["company_id"],
                "name": item["company__name"] or "",
                "edrpou": item["company__edrpou"] or "",
                "label": (
                    f"{item['company__name']} ({item['company__edrpou']})"
                    if item.get("company__edrpou")
                    else (item["company__name"] or "")
                ),
            }
            for item in company_options_qs
            if item.get("company_id")
        ]

        if cursor_mode:
            rows, next_cursor, has_more = _paginate_by_updated_cursor(
                qs=qs,
                cursor=cursor_token,
                page_size=page_size,
            )
            serializer = SalesParticipationTenderListSerializer(
                rows, many=True, context={"request": request}
            )
            return Response({
                "count": None,
                "page": page,
                "page_size": page_size,
                "total_pages": None,
                "next_cursor": next_cursor,
                "has_more": has_more,
                "companies": companies,
                "cpv_tree": cpv_tree,
                "results": serializer.data,
            })

        total = qs.count()
        total_pages = (total + page_size - 1) // page_size
        start = (page - 1) * page_size
        end = start + page_size
        paged_qs = qs.order_by("-updated_at")[start:end]

        serializer = SalesParticipationTenderListSerializer(
            paged_qs, many=True, context={"request": request}
        )
        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "next_cursor": None,
            "has_more": page < total_pages,
            "companies": companies,
            "cpv_tree": cpv_tree,
            "results": serializer.data,
        })

    @extend_schema(responses=SalesTenderProposalSerializer)
    @action(detail=True, methods=["post"], url_path="confirm-participation")
    def confirm_participation(self, request, pk=None):
        """РџС–РґС‚РІРµСЂРґРёС‚Рё СѓС‡Р°СЃС‚СЊ: СЃС‚РІРѕСЂСЋС” РїСЂРѕРїРѕР·РёС†С–СЋ С‚Р° РґРѕРґР°С” РєРѕРЅС‚СЂР°РіРµРЅС‚Р° РІ РґРѕРІС–РґРЅРёРє РѕСЂРіР°РЅС–Р·Р°С‚РѕСЂР°."""
        tender = SalesTender.objects.filter(pk=pk).select_related("company").first()
        if not tender:
            return Response({"detail": "РўРµРЅРґРµСЂ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        if tender.stage not in ("acceptance", "preparation"):
            return Response(
                {"detail": "РЈС‡Р°СЃС‚СЊ РјРѕР¶РЅР° РїС–РґС‚РІРµСЂРґРёС‚Рё Р»РёС€Рµ РґР»СЏ С‚РµРЅРґРµСЂР° РЅР° РїСЂРёР№РѕРј РїСЂРѕРїРѕР·РёС†С–Р№ Р°Р±Рѕ РїС–РґРіРѕС‚РѕРІРєСѓ."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return Response(
                {"detail": "РќРµРјРѕР¶Р»РёРІРѕ РІРёР·РЅР°С‡РёС‚Рё РєРѕРјРїР°РЅС–СЋ СѓС‡Р°СЃРЅРёРєР°."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        supplier_company_id, error_response = _resolve_request_company_id(request)
        if error_response:
            return error_response
        if tender.company_id == supplier_company_id:
            return Response(
                {"detail": "РћСЂРіР°РЅС–Р·Р°С‚РѕСЂ РЅРµ РјРѕР¶Рµ РїС–РґС‚РІРµСЂРґРёС‚Рё СѓС‡Р°СЃС‚СЊ Сѓ РІР»Р°СЃРЅРѕРјСѓ С‚РµРЅРґРµСЂС–."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            proposal, created = SalesTenderProposal.objects.get_or_create(
                tender=tender,
                supplier_company_id=supplier_company_id,
            )
            CompanySupplier.objects.get_or_create(
                owner_company_id=tender.company_id,
                supplier_company_id=supplier_company_id,
                defaults={"source": CompanySupplier.Source.PARTICIPATION},
            )
        serializer = SalesTenderProposalSerializer(proposal)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @extend_schema(responses=SalesTenderProposalSerializer)
    @action(detail=True, methods=["post"], url_path="submit-proposal")
    def submit_proposal(self, request, pk=None):
        """РџРѕРґР°С‚Рё РїСЂРѕРїРѕР·РёС†С–СЋ (С„С–РєСЃСѓС” РїРѕРґР°С‡Сѓ РґР»СЏ РєРѕРјРїР°РЅС–С— РїРѕС‚РѕС‡РЅРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°)."""
        tender = SalesTender.objects.filter(pk=pk).first()
        if not tender:
            return Response({"detail": "РўРµРЅРґРµСЂ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        if tender.stage != "acceptance":
            return Response(
                {"detail": "РџРѕРґР°С‚Рё РїСЂРѕРїРѕР·РёС†С–СЋ РјРѕР¶РЅР° Р»РёС€Рµ РїС–Рґ С‡Р°СЃ РµС‚Р°РїСѓ РїСЂРёР№РѕРјСѓ РїСЂРѕРїРѕР·РёС†С–Р№."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if tender.end_at and timezone.now() > tender.end_at:
            return Response(
                {"detail": "РўРµСЂРјС–РЅ РїСЂРёР№РѕРјСѓ РїСЂРѕРїРѕР·РёС†С–Р№ Р·Р°РІРµСЂС€РµРЅРѕ."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return Response(
                {"detail": "РќРµРјРѕР¶Р»РёРІРѕ РІРёР·РЅР°С‡РёС‚Рё РєРѕРјРїР°РЅС–СЋ."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        supplier_company_id, error_response = _resolve_request_company_id(request)
        if error_response:
            return error_response
        proposal = SalesTenderProposal.objects.filter(
            tender=tender, supplier_company_id=supplier_company_id
        ).first()
        if not proposal:
            return Response(
                {"detail": "РџСЂРѕРїРѕР·РёС†С–СЋ РЅРµ Р·РЅР°Р№РґРµРЅРѕ. РЎРїРѕС‡Р°С‚РєСѓ РїС–РґС‚РІРµСЂРґС–С‚СЊ СѓС‡Р°СЃС‚СЊ."},
                status=status.HTTP_404_NOT_FOUND,
            )
        required_criteria_error = _validate_required_criteria_before_submit(
            tender=tender,
            proposal=proposal,
            proposal_position_model=SalesTenderProposalPosition,
        )
        if required_criteria_error:
            return Response(required_criteria_error, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            proposal.submitted_at = timezone.now()
            proposal.status_updated_at = timezone.now()
            proposal.save(update_fields=["submitted_at", "status_updated_at"])
            CompanySupplier.objects.get_or_create(
                owner_company_id=tender.company_id,
                supplier_company_id=supplier_company_id,
                defaults={"source": CompanySupplier.Source.PARTICIPATION},
            )
        payload_for_ws = {
            "proposal_id": proposal.id,
            "submitted_at": proposal.submitted_at.isoformat() if proposal.submitted_at else None,
        }
        transaction.on_commit(
            lambda: publish_tender_event(
                "sales",
                int(tender.id),
                "proposal.submitted_at.updated",
                payload_for_ws,
            )
        )
        serializer = SalesTenderProposalSerializer(proposal)
        return Response(serializer.data)

    @extend_schema(responses=SalesTenderProposalSerializer)
    @action(detail=True, methods=["post"], url_path="withdraw-proposal")
    def withdraw_proposal(self, request, pk=None):
        """Р’С–РґРєР»РёРєР°С‚Рё РїСЂРѕРїРѕР·РёС†С–СЋ (РєРѕРјРїР°РЅС–СЏ РїРѕС‚РѕС‡РЅРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°)."""
        tender = SalesTender.objects.filter(pk=pk).first()
        if not tender:
            return Response({"detail": "РўРµРЅРґРµСЂ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        if tender.stage != "acceptance":
            return Response(
                {"detail": "Р’С–РґРєР»РёРєР°С‚Рё РїСЂРѕРїРѕР·РёС†С–СЋ РјРѕР¶РЅР° Р»РёС€Рµ РїС–Рґ С‡Р°СЃ РµС‚Р°РїСѓ РїСЂРёР№РѕРјСѓ РїСЂРѕРїРѕР·РёС†С–Р№."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if tender.end_at and timezone.now() > tender.end_at:
            return Response(
                {"detail": "РўРµСЂРјС–РЅ РїСЂРёР№РѕРјСѓ РїСЂРѕРїРѕР·РёС†С–Р№ Р·Р°РІРµСЂС€РµРЅРѕ."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return Response(
                {"detail": "РќРµРјРѕР¶Р»РёРІРѕ РІРёР·РЅР°С‡РёС‚Рё РєРѕРјРїР°РЅС–СЋ."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        supplier_company_id, error_response = _resolve_request_company_id(request)
        if error_response:
            return error_response
        proposal = SalesTenderProposal.objects.filter(
            tender=tender, supplier_company_id=supplier_company_id
        ).first()
        if not proposal:
            return Response(
                {"detail": "РџСЂРѕРїРѕР·РёС†С–СЋ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."},
                status=status.HTTP_404_NOT_FOUND,
            )
        proposal.submitted_at = None
        proposal.status_updated_at = timezone.now()
        proposal.save(update_fields=["submitted_at", "status_updated_at"])
        payload_for_ws = {
            "proposal_id": proposal.id,
            "submitted_at": None,
        }
        transaction.on_commit(
            lambda: publish_tender_event(
                "sales",
                int(tender.id),
                "proposal.submitted_at.updated",
                payload_for_ws,
            )
        )
        serializer = SalesTenderProposalSerializer(proposal)
        return Response(serializer.data)

    @extend_schema(responses=[{"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "tour_number": {"type": "integer"}}}}])
    @action(detail=True, methods=["get"], url_path="tours")
    def tours_list(self, request, pk=None):
        """РЈСЃС– С‚СѓСЂРё СЃС–РјРµР№СЃС‚РІР° (РІС–Рґ РєРѕСЂРµРЅСЏ + СѓСЃС– РЅР°СЃС‚СѓРїРЅС–) РґР»СЏ РІРёРїР°РґР°СЋС‡РѕРіРѕ СЃРїРёСЃРєСѓ."""
        tender = self.get_object()
        root = tender
        while root.parent_id:
            root = root.parent
        collected = [root]
        stack = list(root.next_tours.all())
        while stack:
            t = stack.pop()
            collected.append(t)
            stack.extend(t.next_tours.all())
        collected.sort(key=lambda t: t.tour_number)
        return Response([{"id": t.id, "tour_number": t.tour_number} for t in collected])

    @action(detail=True, methods=["get"], url_path="approval-journal")
    def approval_journal(self, request, pk=None):
        tender = self.get_object()
        qs = TenderApprovalJournal.objects.filter(
            sales_tender=tender
        ).select_related("actor")
        serializer = TenderApprovalJournalSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="approval-route")
    def approval_route(self, request, pk=None):
        tender = self.get_object()
        payload = _build_tender_approval_route_payload(
            tender=tender,
            is_sales=True,
            user=request.user,
            stage=tender.stage or "",
        )
        return Response(payload)

    @action(detail=True, methods=["post"], url_path="approval-submit")
    def approval_submit(self, request, pk=None):
        tender = self.get_object()
        comment = (request.data.get("comment") or "").strip()
        try:
            _submit_tender_preparation_for_approval(
                tender=tender,
                is_sales=True,
                actor=request.user,
                comment=comment,
            )
        except DRFValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        payload = _build_tender_approval_route_payload(
            tender=tender,
            is_sales=True,
            user=request.user,
            stage=tender.stage or "",
        )
        return Response({"id": tender.id, "stage": tender.stage, "route": payload})

    @action(detail=True, methods=["post"], url_path="approval-action")
    def approval_action(self, request, pk=None):
        tender = self.get_object()
        action_type = (request.data.get("action") or "").strip().lower()
        comment = (request.data.get("comment") or "").strip()
        try:
            _apply_tender_approval_action(
                tender=tender,
                is_sales=True,
                actor=request.user,
                action_type=action_type,
                comment=comment,
            )
        except DRFValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        payload = _build_tender_approval_route_payload(
            tender=tender,
            is_sales=True,
            user=request.user,
            stage=tender.stage or "",
        )
        return Response({"id": tender.id, "stage": tender.stage, "route": payload})

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["winner", "cancel", "next_round"]},
                    "position_winners": {
                        "type": "array",
                        "items": {"type": "object", "properties": {"position_id": {"type": "integer"}, "proposal_id": {"type": "integer"}}},
                    },
                    "comment": {"type": "string"},
                },
                "required": ["mode"],
            }
        },
    )
    @action(detail=True, methods=["post"], url_path="fix-decision")
    def fix_decision(self, request, pk=None):
        """
        Р—Р°С„С–РєСЃСѓРІР°С‚Рё СЂС–С€РµРЅРЅСЏ: winner - Р· РїРµСЂРµРјРѕР¶С†СЏРјРё РїРѕ РїРѕР·РёС†С–СЏС…, cancel - Р±РµР· РїРµСЂРµРјРѕР¶С†С–РІ,
        next_round - СЃС‚РІРѕСЂРёС‚Рё РЅР°СЃС‚СѓРїРЅРёР№ С‚СѓСЂ РЅР° РµС‚Р°РїС– РїС–РґРіРѕС‚РѕРІРєРё.
        """
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        mode = request.data.get("mode")
        comment = str(request.data.get("comment") or "").strip()
        journal_comment = comment or "Передано на затвердження"
        if mode not in ("winner", "cancel", "next_round"):
            return Response(
                {"detail": "mode РјР°С” Р±СѓС‚Рё: winner, cancel Р°Р±Рѕ next_round."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if mode == "winner":
            position_winners = request.data.get("position_winners") or []
            SalesTenderPosition.objects.filter(tender=tender).update(winner_proposal=None)
            for item in position_winners:
                pos_id = item.get("position_id")
                prop_id = item.get("proposal_id")
                if pos_id is not None and prop_id is not None:
                    pos = SalesTenderPosition.objects.filter(tender=tender, id=pos_id).first()
                    if pos and SalesTenderProposal.objects.filter(tender=tender, id=prop_id).exists():
                        pos.winner_proposal_id = prop_id
                        pos.save()
            tender.stage = "approval"
            tender.save(update_fields=["stage"])
            _start_approval_stage_cycle_if_needed(tender=tender, is_sales=True)
            _create_tender_approval_journal_entry(
                sales_tender=tender,
                stage=tender.stage or "",
                action=TenderApprovalJournal.Action.SAVED,
                comment=journal_comment,
                actor=request.user,
            )
            return Response({"stage": "approval", "id": tender.id})
        if mode == "cancel":
            SalesTenderPosition.objects.filter(tender=tender).update(winner_proposal=None)
            tender.stage = "approval"
            tender.save(update_fields=["stage"])
            _start_approval_stage_cycle_if_needed(tender=tender, is_sales=True)
            _create_tender_approval_journal_entry(
                sales_tender=tender,
                stage=tender.stage or "",
                action=TenderApprovalJournal.Action.SAVED,
                comment=journal_comment,
                actor=request.user,
            )
            return Response({"stage": "approval", "id": tender.id})
        # next_round
        parent = tender
        new_tender = SalesTender.objects.create(
            company=parent.company,
            parent=parent,
            tour_number=(parent.tour_number or 1) + 1,
            name=parent.name,
            stage="preparation",
            category=parent.category,
            expense_article=parent.expense_article,
            estimated_budget=parent.estimated_budget,
            branch=parent.branch,
            department=parent.department,
            conduct_type=parent.conduct_type,
            publication_type=parent.publication_type,
            currency=parent.currency,
            general_terms=parent.general_terms or "",
            price_criterion_vat=parent.price_criterion_vat or "",
            price_criterion_delivery=parent.price_criterion_delivery or "",
            approval_model=parent.approval_model,
            created_by=request.user,
        )
        new_tender.cpv_categories.set(parent.cpv_categories.all())
        new_tender.tender_criteria.set(parent.tender_criteria.all())
        if parent.criteria_items.exists():
            for crit in parent.criteria_items.all():
                SalesTenderCriterion.objects.create(
                    tender=new_tender,
                    reference_criterion=crit.reference_criterion,
                    name=crit.name,
                    type=crit.type,
                    application=crit.application,
                    is_required=bool(crit.is_required),
                    options=crit.options or {},
                )
        else:
            for crit in parent.tender_criteria.all():
                SalesTenderCriterion.objects.create(
                    tender=new_tender,
                    reference_criterion=crit,
                    name=crit.name,
                    type=crit.type,
                    application=getattr(crit, "application", TenderCriterion.Application.INDIVIDUAL),
                    is_required=bool(getattr(crit, "is_required", False)),
                    options=getattr(crit, "options", {}) or {},
                )
        for pos in parent.positions.all():
            SalesTenderPosition.objects.create(
                tender=new_tender,
                nomenclature=pos.nomenclature,
                quantity=pos.quantity,
                description=pos.description or "",
            )
        return Response({"stage": "preparation", "id": new_tender.id}, status=status.HTTP_201_CREATED)

    @extend_schema(responses=SalesTenderProposalSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="proposals")
    def proposals_list(self, request, pk=None):
        """РЎРїРёСЃРѕРє РїСЂРѕРїРѕР·РёС†С–Р№ РїРѕ С‚РµРЅРґРµСЂСѓ РЅР° РїСЂРѕРґР°Р¶."""
        tender = self.get_object()
        view_mode = str(request.query_params.get("view") or "").strip().lower()
        updated_since = _parse_iso_datetime_param(
            request.query_params.get("updated_since")
        )
        proposal_ids_raw = request.query_params.getlist("ids")
        if not proposal_ids_raw:
            proposal_ids_raw = request.query_params.get("ids")
        proposal_ids = _parse_int_list_param(proposal_ids_raw)
        if view_mode == "status":
            throttled_response, rate_limit_remaining = _enforce_status_sync_rate_limit(
                request=request,
                kind="sales",
                tender_id=int(tender.id),
            )
            if throttled_response is not None:
                return throttled_response
            use_delta_cache = updated_since is not None and not proposal_ids
            cache_key = None
            if use_delta_cache and request.user and request.user.is_authenticated:
                cache_key = _build_status_sync_cache_key(
                    kind="sales",
                    tender_id=int(tender.id),
                    user_id=int(request.user.id),
                    updated_since=updated_since,
                )
                cached_data = cache.get(cache_key)
                if cached_data is not None:
                    response = Response(cached_data)
                    response["X-Status-Sync-Cache"] = "HIT"
                    if rate_limit_remaining is not None:
                        response["X-Status-Sync-RateLimit-Limit"] = str(
                            STATUS_SYNC_THROTTLE_PER_MINUTE
                        )
                        response["X-Status-Sync-RateLimit-Remaining"] = str(
                            rate_limit_remaining
                        )
                    _status_sync_log(
                        "cache_hit",
                        kind="sales",
                        tender_id=int(tender.id),
                        user_id=int(request.user.id),
                        rows=len(cached_data),
                    )
                    return response
            qs = SalesTenderProposal.objects.filter(tender=tender).select_related(
                "supplier_company"
            )
            if updated_since is not None:
                qs = qs.filter(status_updated_at__gt=updated_since)
            if proposal_ids:
                qs = qs.filter(id__in=proposal_ids)
            elif "ids" in request.query_params:
                return Response([])
            serializer = SalesTenderProposalStatusSerializer(qs, many=True)
            data = list(serializer.data)
            if cache_key:
                cache.set(cache_key, data, STATUS_SYNC_CACHE_TTL_SECONDS)
                response = Response(data)
                response["X-Status-Sync-Cache"] = "MISS"
                if rate_limit_remaining is not None:
                    response["X-Status-Sync-RateLimit-Limit"] = str(
                        STATUS_SYNC_THROTTLE_PER_MINUTE
                    )
                    response["X-Status-Sync-RateLimit-Remaining"] = str(
                        rate_limit_remaining
                    )
                _status_sync_log(
                    "cache_miss",
                    kind="sales",
                    tender_id=int(tender.id),
                    user_id=int(request.user.id) if request.user and request.user.is_authenticated else None,
                    rows=len(data),
                )
                return response
            response = Response(data)
            if rate_limit_remaining is not None:
                response["X-Status-Sync-RateLimit-Limit"] = str(
                    STATUS_SYNC_THROTTLE_PER_MINUTE
                )
                response["X-Status-Sync-RateLimit-Remaining"] = str(
                    rate_limit_remaining
                )
            _status_sync_log(
                "no_cache",
                kind="sales",
                tender_id=int(tender.id),
                user_id=int(request.user.id) if request.user and request.user.is_authenticated else None,
                rows=len(data),
            )
            return response
        qs = SalesTenderProposal.objects.filter(tender=tender).select_related(
            "supplier_company"
        ).prefetch_related(
            "position_values__tender_position__nomenclature__unit",
        )
        if proposal_ids:
            qs = qs.filter(id__in=proposal_ids)
        elif "ids" in request.query_params:
            return Response([])
        serializer = SalesTenderProposalSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(request=SalesTenderProposalSerializer, responses=SalesTenderProposalSerializer)
    @action(detail=True, methods=["post"], url_path="proposals/add")
    def proposal_add(self, request, pk=None):
        """Р”РѕРґР°С‚Рё РїСЂРѕРїРѕР·РёС†С–СЋ (РѕР±СЂР°С‚Рё РєРѕРЅС‚СЂР°РіРµРЅС‚Р°)."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        supplier_company_id = request.data.get("supplier_company_id") or request.data.get("supplier_company")
        if not supplier_company_id:
            return Response(
                {"detail": "РџРѕС‚СЂС–Р±РЅРѕ РІРєР°Р·Р°С‚Рё supplier_company_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        proposal, created = SalesTenderProposal.objects.get_or_create(
            tender=tender,
            supplier_company_id=supplier_company_id,
        )
        serializer = SalesTenderProposalSerializer(proposal)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @extend_schema(request=TenderProposalPositionUpdateSerializer)
    @action(detail=True, methods=["post", "patch"], url_path=r"proposals/(?P<proposal_id>[^/.]+)/position-values")
    def proposal_position_values(self, request, pk=None, proposal_id=None):
        """РћРЅРѕРІРёС‚Рё Р·РЅР°С‡РµРЅРЅСЏ РїРѕ РїРѕР·РёС†С–СЏС… РїСЂРѕРїРѕР·РёС†С–С—."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        proposal = SalesTenderProposal.objects.filter(
            tender=tender, id=proposal_id
        ).prefetch_related("position_values__tender_position").first()
        if not proposal:
            return Response({"detail": "РџСЂРѕРїРѕР·РёС†С–СЋ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        payload = TenderProposalPositionUpdateSerializer(data=request.data)
        if not payload.is_valid():
            return Response(payload.errors, status=status.HTTP_400_BAD_REQUEST)
        position_values_data = payload.validated_data.get("position_values") or []
        changed_position_ids: set[int] = set()
        for item in position_values_data:
            tp_id = item.get("tender_position_id")
            if not tp_id:
                continue
            pos = SalesTenderPosition.objects.filter(tender=tender, id=tp_id).first()
            if not pos:
                continue
            if "price" in item:
                price_validation_error = _validate_online_auction_position_price(
                    tender=tender,
                    position=pos,
                    proposal_position_model=SalesTenderProposalPosition,
                    new_price=item.get("price"),
                    is_procurement=False,
                )
                if price_validation_error:
                    return Response(
                        {"detail": price_validation_error, "tender_position_id": tp_id},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            pv, _ = SalesTenderProposalPosition.objects.get_or_create(
                proposal=proposal, tender_position=pos,
                defaults={"price": None, "criterion_values": {}},
            )
            if "price" in item:
                pv.price = item["price"]
            if "criterion_values" in item:
                pv.criterion_values = item["criterion_values"]
            pv.save()
            changed_position_ids.add(int(tp_id))
        if changed_position_ids:
            payload_for_ws = {
                "proposal_id": proposal.id,
                "position_ids": sorted(changed_position_ids),
            }
            transaction.on_commit(
                lambda: publish_tender_event(
                    "sales",
                    int(tender.id),
                    "proposal.position_values.updated",
                    payload_for_ws,
                )
            )
        qs = SalesTenderProposal.objects.filter(id=proposal.id).prefetch_related(
            "position_values__tender_position__nomenclature__unit",
        )
        serializer = SalesTenderProposalSerializer(qs.first())
        return Response(serializer.data)

    @extend_schema(responses=SalesTenderProposalSerializer(many=True))
    @action(detail=True, methods=["get"], url_path=r"proposals/(?P<proposal_id>[^/.]+)")
    def proposal_detail(self, request, pk=None, proposal_id=None):
        """Р”РµС‚Р°Р»С– РїСЂРѕРїРѕР·РёС†С–С—."""
        tender = self.get_object()
        proposal = SalesTenderProposal.objects.filter(
            tender=tender, id=proposal_id
        ).prefetch_related(
            "position_values__tender_position__nomenclature__unit",
        ).first()
        if not proposal:
            return Response({"detail": "РџСЂРѕРїРѕР·РёС†С–СЋ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SalesTenderProposalSerializer(proposal)
        return Response(serializer.data)

    @extend_schema(responses=SalesTenderFileSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="files")
    def files_list(self, request, pk=None):
        """РЎРїРёСЃРѕРє РїСЂРёРєСЂС–РїР»РµРЅРёС… С„Р°Р№Р»С–РІ."""
        tender = self.get_object()
        qs = SalesTenderFile.objects.filter(tender=tender)
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        is_owner = tender.company_id in user_company_ids
        if not is_owner:
            qs = qs.filter(visible_to_participants=True)
        serializer = SalesTenderFileSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(request=OpenApiTypes.BINARY, responses=SalesTenderFileSerializer)
    @action(detail=True, methods=["post"], url_path="files/upload")
    def file_upload(self, request, pk=None):
        """РџСЂРёРєСЂС–РїРёС‚Рё С„Р°Р№Р» РґРѕ С‚РµРЅРґРµСЂР° РЅР° РїСЂРѕРґР°Р¶."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        file_obj = request.FILES.get("file") or request.FILES.get("file_upload")
        if not file_obj:
            return Response(
                {"detail": "РќР°РґС–С€Р»С–С‚СЊ С„Р°Р№Р» Сѓ РїРѕР»С– file Р°Р±Рѕ file_upload."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        validation_error = _validate_tender_file(file_obj)
        if validation_error:
            return Response({"detail": validation_error}, status=status.HTTP_400_BAD_REQUEST)
        name = request.data.get("name", "") or file_obj.name
        visible = request.data.get("visible_to_participants", True)
        if isinstance(visible, str):
            visible = visible.lower() in ("true", "1", "yes")
        obj = SalesTenderFile.objects.create(
            tender=tender,
            file=file_obj,
            name=name[:255],
            uploaded_by=getattr(request, "user", None),
            visible_to_participants=bool(visible),
        )
        serializer = SalesTenderFileSerializer(
            obj, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"files/(?P<file_id>\d+)")
    def file_delete(self, request, pk=None, file_id=None):
        """Р’РёРґР°Р»РёС‚Рё РїСЂРёРєСЂС–РїР»РµРЅРёР№ С„Р°Р№Р»."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        obj = SalesTenderFile.objects.filter(tender=tender, id=file_id).first()
        if not obj:
            return Response({"detail": "Р¤Р°Р№Р» РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["patch"], url_path=r"files/(?P<file_id>\d+)")
    def file_patch(self, request, pk=None, file_id=None):
        """РћРЅРѕРІРёС‚Рё РІРёРґРёРјС–СЃС‚СЊ С„Р°Р№Р»Сѓ СѓС‡Р°СЃРЅРёРєР°Рј."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        obj = SalesTenderFile.objects.filter(tender=tender, id=file_id).first()
        if not obj:
            return Response({"detail": "Р¤Р°Р№Р» РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        if "visible_to_participants" in request.data:
            obj.visible_to_participants = bool(request.data["visible_to_participants"])
            obj.save(update_fields=["visible_to_participants"])
        serializer = SalesTenderFileSerializer(obj, context={"request": request})
        return Response(serializer.data)
