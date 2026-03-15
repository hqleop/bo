import base64
import copy as pycopy
import hashlib
import io
import json
import logging
import os
import re
import textwrap
import time
from datetime import datetime
from html import unescape
from xml.sax.saxutils import escape as xml_escape

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
from django.db import transaction, IntegrityError
from django.db.models import (
    Q,
    Exists,
    OuterRef,
    Count,
    Avg,
    Subquery,
    DecimalField,
    ExpressionWrapper,
    F,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover
    REPORTLAB_AVAILABLE = False

from .models import (
    Company,
    CompanySupplier,
    CompanyUser,
    Role,
    Permission,
    Notification,
    TenderChatThread,
    TenderChatMessage,
    TenderBidHistory,
    TenderProposalChangeLog,
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
    Warehouse,
    TenderCriterion,
    TenderAttribute,
    TenderConditionTemplate,
    ApprovalModelRole,
    ApprovalModelRoleUser,
    ApprovalRangeMatrix,
    ApprovalModel,
    ApprovalModelStep,
    ProcurementTender,
    ProcurementTenderInvitation,
    ProcurementTenderCriterion,
    ProcurementTenderPosition,
    TenderProposal,
    TenderProposalPosition,
    ProcurementTenderFile,
    SalesTender,
    SalesTenderInvitation,
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
    TenderChatThreadSerializer,
    TenderChatMessageSerializer,
    TenderBidHistorySerializer,
    TenderProposalChangeLogSerializer,
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
    WarehouseSerializer,
    TenderCriterionSerializer,
    TenderAttributeSerializer,
    TenderConditionTemplateSerializer,
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
            {"detail": "Неможливо визначити компанію користувача."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if explicit_company_id is not None:
        try:
            company_id = int(explicit_company_id)
        except (TypeError, ValueError):
            return None, Response(
                {"detail": "Некоректний company_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if company_id not in user_company_ids:
            return None, Response(
                {"detail": "Компанія не належить поточному користувачу."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return company_id, None

    if len(user_company_ids) > 1:
        return None, Response(
            {"detail": "Оберіть company_id для виконання дії."},
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


def _extract_requested_ids(request):
    raw_ids = None
    data = getattr(request, "data", None)
    if data is None:
        return []
    if hasattr(data, "getlist"):
        raw_ids = data.getlist("ids")
        if not raw_ids:
            raw_ids = data.get("ids")
    elif isinstance(data, dict):
        raw_ids = data.get("ids")
    requested_ids = [item for item in _parse_int_list_param(raw_ids) if item > 0]
    return requested_ids


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


def _expand_tree_ids_with_descendants(model_cls, source_ids):
    pending = {int(item_id) for item_id in source_ids if item_id is not None}
    all_ids = set(pending)
    while pending:
        child_ids = set(
            model_cls.objects.filter(parent_id__in=pending).values_list("id", flat=True)
        )
        new_ids = child_ids - all_ids
        if not new_ids:
            break
        all_ids.update(new_ids)
        pending = new_ids
    return all_ids


def _copy_tree_user_assignments(
    *,
    source_obj,
    target_ids,
    assignment_model,
    relation_field,
):
    source_user_ids = list(
        assignment_model.objects.filter(
            **{f"{relation_field}_id": source_obj.id}
        ).values_list("user_id", flat=True)
    )
    normalized_target_ids = sorted(
        {
            int(target_id)
            for target_id in (target_ids or [])
            if target_id is not None and int(target_id) != int(source_obj.id)
        }
    )
    if not source_user_ids or not normalized_target_ids:
        return {
            "created_count": 0,
            "target_ids": normalized_target_ids,
            "source_user_ids": source_user_ids,
        }

    existing_pairs = set(
        assignment_model.objects.filter(
            **{
                f"{relation_field}_id__in": normalized_target_ids,
                "user_id__in": source_user_ids,
            }
        ).values_list(f"{relation_field}_id", "user_id")
    )

    to_create = []
    for target_id in normalized_target_ids:
        for user_id in source_user_ids:
            pair = (target_id, user_id)
            if pair in existing_pairs:
                continue
            to_create.append(assignment_model(**{f"{relation_field}_id": target_id, "user_id": user_id}))

    if to_create:
        assignment_model.objects.bulk_create(to_create, ignore_conflicts=True)

    return {
        "created_count": len(to_create),
        "target_ids": normalized_target_ids,
        "source_user_ids": source_user_ids,
    }


def _ensure_branch_users_for_department_assignments(*, department_ids, user_ids):
    normalized_department_ids = sorted(
        {
            int(department_id)
            for department_id in (department_ids or [])
            if department_id is not None and int(department_id) > 0
        }
    )
    normalized_user_ids = sorted(
        {
            int(user_id)
            for user_id in (user_ids or [])
            if user_id is not None and int(user_id) > 0
        }
    )
    if not normalized_department_ids or not normalized_user_ids:
        return {
            "created_count": 0,
            "branch_ids": [],
            "user_ids": normalized_user_ids,
        }

    department_branch_map = dict(
        Department.objects.filter(id__in=normalized_department_ids).values_list("id", "branch_id")
    )
    required_pairs = sorted(
        {
            (int(branch_id), int(user_id))
            for department_id in normalized_department_ids
            for user_id in normalized_user_ids
            for branch_id in [department_branch_map.get(department_id)]
            if branch_id
        }
    )
    if not required_pairs:
        return {
            "created_count": 0,
            "branch_ids": [],
            "user_ids": normalized_user_ids,
        }

    branch_ids = sorted({branch_id for branch_id, _ in required_pairs})
    existing_pairs = set(
        BranchUser.objects.filter(
            branch_id__in=branch_ids,
            user_id__in=normalized_user_ids,
        ).values_list("branch_id", "user_id")
    )
    to_create = [
        BranchUser(branch_id=branch_id, user_id=user_id)
        for branch_id, user_id in required_pairs
        if (branch_id, user_id) not in existing_pairs
    ]
    if to_create:
        BranchUser.objects.bulk_create(to_create, ignore_conflicts=True)

    return {
        "created_count": len(to_create),
        "branch_ids": branch_ids,
        "user_ids": normalized_user_ids,
    }


def _apply_is_active_filter(queryset, request):
    if not hasattr(queryset.model, "is_active"):
        return queryset
    if _is_truthy_query_param(request.query_params.get("inactive_only")):
        return queryset.filter(is_active=False)
    if _is_truthy_query_param(request.query_params.get("include_inactive")):
        return queryset
    return queryset.filter(is_active=True)


def _is_flat_tree_request(request):
    return _is_truthy_query_param(request.query_params.get("flat"))


def _build_reference_delete_response(obj, blockers):
    detail = (
        f"Елемент «{obj}» не можна видалити. "
        + "; ".join(blockers)
        + ". За потреби деактивуйте його."
    )
    return Response(
        {"detail": detail, "blockers": blockers},
        status=status.HTTP_400_BAD_REQUEST,
    )


class ReferenceActivityMixin:
    def _get_delete_blockers(self, obj):
        return []

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        obj = self.get_object()
        obj.is_active = True
        obj.save(update_fields=["is_active"])
        return Response(self.get_serializer(obj).data)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        blockers = self._get_delete_blockers(obj)
        if blockers:
            return _build_reference_delete_response(obj, blockers)
        return super().destroy(request, *args, **kwargs)


def _normalize_alnum_token(value):
    return re.sub(r"[^0-9a-zа-яіїєґ]", "", str(value or "").strip().casefold())


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


def _filter_owner_tenders_qs_by_search(qs, search_value):
    term = str(search_value or "").strip()
    if not term:
        return qs

    filters = Q(name__icontains=term)
    number_tokens = []
    for raw in re.findall(r"\d+", term):
        try:
            value = int(raw)
        except (TypeError, ValueError):
            continue
        if value > 0:
            number_tokens.append(value)
    if number_tokens:
        filters |= Q(number__in=list(dict.fromkeys(number_tokens)))
    return qs.filter(filters)


def _resolve_preparation_stage_deletable_ids(*, candidate_ids, is_sales):
    candidate_ids = [int(item) for item in candidate_ids if int(item or 0) > 0]
    if not candidate_ids:
        return set()
    state_kwargs = {
        "stage": TenderApprovalStageState.Stage.PREPARATION,
    }
    tender_key = "sales_tender_id" if is_sales else "procurement_tender_id"
    state_kwargs[f"{tender_key}__in"] = candidate_ids
    stage_states = (
        TenderApprovalStageState.objects.filter(**state_kwargs)
        .annotate(
            has_steps=Exists(
                TenderApprovalStageStep.objects.filter(stage_state_id=OuterRef("pk"))
            )
        )
        .values(tender_key, "status", "has_steps")
    )
    state_by_tender_id = {
        int(item[tender_key]): {
            "status": str(item.get("status") or ""),
            "has_steps": bool(item.get("has_steps")),
        }
        for item in stage_states
        if item.get(tender_key)
    }

    deletable_ids = set()
    for tender_id in candidate_ids:
        stage_state = state_by_tender_id.get(tender_id)
        if not stage_state:
            deletable_ids.add(tender_id)
            continue
        if not stage_state["has_steps"]:
            deletable_ids.add(tender_id)
            continue
        if stage_state["status"] == TenderApprovalStageState.Status.WAITING_AUTHOR:
            deletable_ids.add(tender_id)

    return deletable_ids


def _resolve_journal_deletable_ids(*, request, rows, is_sales):
    if not request or not getattr(request, "user", None):
        return set()
    user = request.user
    if not getattr(user, "is_authenticated", False):
        return set()

    candidate_ids = []
    for tender in rows:
        if int(getattr(tender, "tour_number", 0) or 0) != 1:
            continue
        if str(getattr(tender, "stage", "") or "") != TenderApprovalStageState.Stage.PREPARATION:
            continue
        if int(getattr(tender, "created_by_id", 0) or 0) != int(user.id):
            continue
        candidate_ids.append(int(getattr(tender, "id", 0) or 0))

    return _resolve_preparation_stage_deletable_ids(
        candidate_ids=candidate_ids,
        is_sales=is_sales,
    )


def _build_owner_tender_journal_response(
    request,
    *,
    qs,
    serializer_cls,
):
    page = _parse_int_param(request.query_params.get("page"), default=1, min_value=1)
    page_size = _parse_int_param(request.query_params.get("page_size"), default=20, min_value=1)
    page_size = min(page_size, 100)

    status_filter = (request.query_params.get("status") or "active").strip().lower()
    if status_filter not in {"active", "completed", "all"}:
        status_filter = "active"

    active_stages = [
        "preparation",
        "acceptance",
        "decision",
        "approval",
    ]
    all_stage_values = [choice[0] for choice in ProcurementTender.Stage.choices]

    if status_filter == "active":
        qs = qs.filter(stage__in=active_stages)
    elif status_filter == "completed":
        qs = qs.filter(stage="completed")
    else:
        qs = qs.filter(stage__in=all_stage_values)

    stage_filter = (request.query_params.get("stage") or "").strip().lower()
    if status_filter in {"active", "all"} and stage_filter:
        allowed_stages = set(active_stages if status_filter == "active" else all_stage_values)
        if stage_filter in allowed_stages:
            qs = qs.filter(stage=stage_filter)

    search_value = (request.query_params.get("search") or "").strip()
    if search_value:
        qs = _filter_owner_tenders_qs_by_search(qs, search_value)

    author_id = _parse_int_param(
        request.query_params.get("author_id"),
        default=0,
        min_value=0,
    )
    if author_id:
        qs = qs.filter(created_by_id=author_id)

    branch_ids = [item for item in _parse_int_list_param(request.query_params.getlist("branch_ids")) if item > 0]
    if branch_ids:
        qs = qs.filter(branch_id__in=branch_ids)

    department_ids = [item for item in _parse_int_list_param(request.query_params.getlist("department_ids")) if item > 0]
    if department_ids:
        qs = qs.filter(department_id__in=department_ids)

    expense_ids = [item for item in _parse_int_list_param(request.query_params.getlist("expense_ids")) if item > 0]
    if expense_ids:
        qs = qs.filter(expense_article_id__in=expense_ids)

    conduct_type = (request.query_params.get("conduct_type") or "").strip().lower()
    if conduct_type in {"registration", "rfx", "online_auction"}:
        qs = qs.filter(conduct_type=conduct_type)

    total = qs.count()
    total_pages = (total + page_size - 1) // page_size

    # Journal metrics are computed in SQL to avoid per-row ORM queries in serializers.
    amount_output_field = DecimalField(max_digits=24, decimal_places=4)
    line_total_expr = ExpressionWrapper(
        Coalesce(F("positions__quantity"), Value(Decimal("0")))
        * Coalesce(F("positions__proposal_values__price"), Value(Decimal("0"))),
        output_field=amount_output_field,
    )
    is_sales_journal = qs.model is SalesTender
    position_model = SalesTenderPosition if is_sales_journal else ProcurementTenderPosition
    proposal_position_model = (
        SalesTenderProposalPosition if is_sales_journal else TenderProposalPosition
    )
    submitted_position_prices_exists = proposal_position_model.objects.filter(
        tender_position__tender_id=OuterRef("pk"),
        proposal__submitted_at__isnull=False,
        price__isnull=False,
    )
    avg_price_subquery = (
        proposal_position_model.objects.filter(
            tender_position_id=OuterRef("pk"),
            proposal__submitted_at__isnull=False,
            price__isnull=False,
        )
        .values("tender_position_id")
        .annotate(avg_price=Avg("price"))
        .values("avg_price")[:1]
    )
    market_total_subquery = (
        position_model.objects.filter(tender_id=OuterRef("pk"))
        .annotate(
            avg_price=Subquery(avg_price_subquery, output_field=amount_output_field),
            line_total=ExpressionWrapper(
                Coalesce(F("quantity"), Value(Decimal("0")))
                * Coalesce(F("avg_price"), Value(Decimal("0"))),
                output_field=amount_output_field,
            )
        )
        .values("tender_id")
        .annotate(
            total=Coalesce(
                Sum("line_total", output_field=amount_output_field),
                Value(Decimal("0")),
                output_field=amount_output_field,
            )
        )
        .values("total")[:1]
    )
    qs = qs.annotate(
        winners_count=Count(
            "positions",
            filter=Q(positions__winner_proposal__isnull=False),
            distinct=True,
        ),
        total_amount=Coalesce(
            Sum(
                line_total_expr,
                filter=Q(
                    positions__winner_proposal_id=F(
                        "positions__proposal_values__proposal_id"
                    )
                ),
                output_field=amount_output_field,
            ),
            Value(Decimal("0")),
            output_field=amount_output_field,
        ),
        market_total_amount=Coalesce(
            Subquery(market_total_subquery, output_field=amount_output_field),
            Value(Decimal("0")),
            output_field=amount_output_field,
        ),
        has_submitted_position_prices=Exists(submitted_position_prices_exists),
        has_next_tour=Exists(qs.model.objects.filter(parent_id=OuterRef("pk"))),
    )
    qs = qs.order_by("-updated_at", "-id")

    start = (page - 1) * page_size
    end = start + page_size
    rows = list(qs[start:end])
    journal_deletable_ids = _resolve_journal_deletable_ids(
        request=request,
        rows=rows,
        is_sales=qs.model is SalesTender,
    )
    serializer = serializer_cls(
        rows,
        many=True,
        context={
            "request": request,
            "journal_deletable_ids": journal_deletable_ids,
        },
    )
    return Response(
        {
            "count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_more": page < total_pages,
            "results": serializer.data,
        }
    )


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


_UA_TO_LATIN_MAP = {
    "А": "A",
    "Б": "B",
    "В": "V",
    "Г": "H",
    "Ґ": "G",
    "Д": "D",
    "Е": "E",
    "Є": "Ye",
    "Ж": "Zh",
    "З": "Z",
    "Р": "Y",
    "І": "I",
    "Ї": "Yi",
    "Й": "Y",
    "К": "K",
    "Л": "L",
    "М": "M",
    "Н": "N",
    "О": "O",
    "П": "P",
    "Р": "R",
    "РЎ": "S",
    "Рў": "T",
    "РЈ": "U",
    "Р¤": "F",
    "РҐ": "Kh",
    "Ц": "Ts",
    "Ч": "Ch",
    "РЁ": "Sh",
    "Щ": "Shch",
    "Ь": "",
    "Ю": "Yu",
    "РЇ": "Ya",
    "а": "a",
    "б": "b",
    "РІ": "v",
    "Рі": "h",
    "ґ": "g",
    "Рґ": "d",
    "е": "e",
    "є": "ye",
    "ж": "zh",
    "з": "z",
    "Рё": "y",
    "і": "i",
    "ї": "yi",
    "Р№": "y",
    "Рє": "k",
    "л": "l",
    "Рј": "m",
    "РЅ": "n",
    "Рѕ": "o",
    "Рї": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "Сѓ": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "С€": "sh",
    "щ": "shch",
    "ь": "",
    "ю": "yu",
    "я": "ya",
    "’": "'",
    "Кј": "'",
    "“": '"',
    "”": '"',
}


def _latinize_for_pdf(value):
    text = str(value or "")
    chars = []
    for ch in text:
        mapped = _UA_TO_LATIN_MAP.get(ch)
        if mapped is not None:
            chars.append(mapped)
            continue
        if ord(ch) < 128:
            chars.append(ch)
        else:
            chars.append("?")
    return "".join(chars)


def _format_protocol_datetime(value, fmt="%Y-%m-%d %H:%M:%S"):
    if value in (None, ""):
        return "-"
    if isinstance(value, datetime):
        dt_value = value
    else:
        dt_value = parse_datetime(str(value))
        if dt_value is None:
            return str(value)
    if timezone.is_naive(dt_value):
        dt_value = timezone.make_aware(dt_value, timezone.get_current_timezone())
    return timezone.localtime(dt_value).strftime(fmt)


def _format_protocol_number(value):
    if value in (None, ""):
        return "-"
    try:
        dec_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)
    normalized = format(dec_value.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def _pdf_escape_text(value):
    text = str(value or "")
    text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    text = text.replace("\r", " ").replace("\n", " ")
    return text


def _build_simple_pdf(lines):
    prepared_lines = []
    for raw_line in lines or []:
        line_text = _latinize_for_pdf(raw_line)
        line_parts = str(line_text).replace("\r", "\n").split("\n")
        for part in line_parts:
            collapsed = re.sub(r"\s+", " ", part).strip()
            if not collapsed:
                prepared_lines.append("")
                continue
            wrapped = textwrap.wrap(collapsed, width=96) or [collapsed]
            prepared_lines.extend(wrapped)
    if not prepared_lines:
        prepared_lines = ["-"]

    lines_per_page = 52
    page_chunks = [
        prepared_lines[i : i + lines_per_page]
        for i in range(0, len(prepared_lines), lines_per_page)
    ]

    page_ids = []
    content_ids = []
    next_obj_id = 3
    for _ in page_chunks:
        page_ids.append(next_obj_id)
        content_ids.append(next_obj_id + 1)
        next_obj_id += 2
    font_obj_id = next_obj_id

    objects = {}
    kids_refs = " ".join(f"{obj_id} 0 R" for obj_id in page_ids)
    objects[1] = "<< /Type /Catalog /Pages 2 0 R >>".encode("ascii")
    objects[2] = (
        f"<< /Type /Pages /Kids [{kids_refs}] /Count {len(page_ids)} >>".encode(
            "ascii"
        )
    )

    for page_obj_id, content_obj_id, chunk in zip(page_ids, content_ids, page_chunks):
        commands = ["BT", "/F1 10 Tf", "14 TL", "40 800 Td"]
        for line in chunk:
            commands.append(f"({_pdf_escape_text(line)}) Tj")
            commands.append("T*")
        commands.append("ET")
        stream = ("\n".join(commands) + "\n").encode("latin-1", "replace")
        objects[content_obj_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"endstream"
        )
        objects[page_obj_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 {font_obj_id} 0 R >> >> "
            f"/Contents {content_obj_id} 0 R >>".encode("ascii")
        )

    objects[font_obj_id] = (
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>".encode("ascii")
    )

    max_obj_id = font_obj_id
    pdf = bytearray()
    pdf.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (max_obj_id + 1)

    for obj_id in range(1, max_obj_id + 1):
        offsets[obj_id] = len(pdf)
        pdf.extend(f"{obj_id} 0 obj\n".encode("ascii"))
        pdf.extend(objects[obj_id])
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {max_obj_id + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for obj_id in range(1, max_obj_id + 1):
        pdf.extend(f"{offsets[obj_id]:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {max_obj_id + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("ascii")
    )
    return bytes(pdf)


def _collect_tour_chain_until_current(tender):
    """Collect procedure tours from first to current (inclusive)."""
    tender_model = tender.__class__
    company_id = getattr(tender, "company_id", None)
    number = getattr(tender, "number", None)
    current_tour_number = int(getattr(tender, "tour_number", 1) or 1)
    if not company_id or number is None:
        return [tender]
    qs = (
        tender_model.objects.filter(
            company_id=company_id,
            number=number,
            tour_number__lte=current_tour_number,
        )
        .only(
            "id",
            "tour_number",
            "conduct_type",
            "planned_start_at",
            "planned_end_at",
            "start_at",
            "end_at",
            "updated_at",
            "stage",
        )
        .order_by("tour_number", "id")
    )
    tours = list(qs)
    return tours or [tender]


def _resolve_tender_decision_mode(*, tender, positions):
    has_winners = any(getattr(pos, "winner_proposal_id", None) for pos in positions)
    if has_winners:
        return "winner"
    if tender.__class__.objects.filter(parent_id=tender.id).exists():
        return "next_round"
    stage = str(getattr(tender, "stage", "") or "")
    if stage in {"approval", "completed"}:
        return "cancel"
    return "pending"


_PROTOCOL_REPORTLAB_FONTS = None


def _format_protocol_display_number(value):
    if value in (None, ""):
        return "-"
    try:
        dec_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)
    normalized = format(dec_value.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    if not normalized:
        return "0"
    sign = ""
    if normalized.startswith("-"):
        sign = "-"
        normalized = normalized[1:]
    integer_part, dot, fraction_part = normalized.partition(".")
    try:
        integer_grouped = f"{int(integer_part):,}".replace(",", " ")
    except ValueError:
        integer_grouped = integer_part
    if dot and fraction_part:
        return f"{sign}{integer_grouped},{fraction_part}"
    return f"{sign}{integer_grouped}"


def _format_protocol_person(user):
    if user is None:
        return "-"
    parts = [
        getattr(user, "last_name", ""),
        getattr(user, "first_name", ""),
        getattr(user, "middle_name", ""),
    ]
    full_name = " ".join(part for part in parts if part).strip()
    if full_name:
        return full_name
    return getattr(user, "email", "") or "-"


def _protocol_text(value):
    text = str(value or "").strip()
    return text or "-"


def _protocol_decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _protocol_html_to_lines(value):
    raw = str(value or "").strip()
    if not raw:
        return []
    if BeautifulSoup is not None:
        soup = BeautifulSoup(raw, "html.parser")
        for br in soup.find_all("br"):
            br.replace_with("\n")
        lines = []
        for element in soup.find_all(
            ["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"]
        ):
            text = element.get_text(" ", strip=True)
            if not text:
                continue
            prefix = "• " if element.name == "li" else ""
            lines.append(f"{prefix}{text}")
        if lines:
            return lines
        text = soup.get_text("\n", strip=True)
    else:
        text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
        text = re.sub(r"</(p|div|li|h[1-6])>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = unescape(text)
    return [line.strip() for line in text.splitlines() if line.strip()]


def _protocol_criterion_options_display(options):
    if not options:
        return "-"
    if isinstance(options, dict):
        choices = (
            options.get("choices")
            or options.get("values")
            or options.get("text_choices")
            or options.get("numeric_choices")
        )
        if isinstance(choices, (list, tuple)):
            rendered = [str(item).strip() for item in choices if str(item).strip()]
            if rendered:
                return "; ".join(rendered)
        range_min = options.get("range_min")
        range_max = options.get("range_max")
        if range_min not in (None, "") or range_max not in (None, ""):
            return f"від {_protocol_text(range_min)} до {_protocol_text(range_max)}"
        flattened = []
        for key, value in options.items():
            if value in (None, "", [], {}, ()):
                continue
            if isinstance(value, (list, tuple)):
                value_text = ", ".join(
                    str(item).strip() for item in value if str(item).strip()
                )
            else:
                value_text = str(value).strip()
            if not value_text:
                continue
            flattened.append(f"{key}: {value_text}")
        if flattened:
            return "; ".join(flattened)
    if isinstance(options, (list, tuple)):
        rendered = [str(item).strip() for item in options if str(item).strip()]
        return "; ".join(rendered) or "-"
    return str(options).strip() or "-"


def _build_protocol_price_criterion_label(tender):
    vat_value = str(getattr(tender, "price_criterion_vat", "") or "").strip()
    vat_percent = getattr(tender, "price_criterion_vat_percent", None)
    delivery_value = str(getattr(tender, "price_criterion_delivery", "") or "").strip()
    vat_labels = {
        "with_vat": "з ПДВ",
        "without_vat": "без ПДВ",
    }
    delivery_labels = {
        "with_delivery": "з урахуванням доставки",
        "without_delivery": "без урахування доставки",
    }
    parts = []
    if vat_value:
        vat_label = vat_labels.get(vat_value, vat_value)
        if vat_value == "with_vat" and vat_percent not in (None, ""):
            vat_label = f"{vat_label} ({_format_protocol_display_number(vat_percent)}%)"
        parts.append(vat_label)
    if delivery_value:
        parts.append(delivery_labels.get(delivery_value, delivery_value))
    return "; ".join(parts) or "-"


def _build_tender_protocol_payload(*, tender, is_sales):
    position_model = SalesTenderPosition if is_sales else ProcurementTenderPosition
    proposal_model = SalesTenderProposal if is_sales else TenderProposal
    proposal_position_model = (
        SalesTenderProposalPosition if is_sales else TenderProposalPosition
    )
    invitation_model = SalesTenderInvitation if is_sales else ProcurementTenderInvitation

    positions = list(
        position_model.objects.filter(tender=tender)
        .select_related("winner_proposal__supplier_company", "nomenclature")
        .order_by("id")
    )
    proposals = list(
        proposal_model.objects.filter(tender=tender)
        .select_related("supplier_company")
        .order_by("supplier_company__name", "id")
    )
    proposal_prices = proposal_position_model.objects.filter(
        proposal__tender=tender,
        tender_position__tender=tender,
    ).values("proposal_id", "tender_position_id", "price")
    price_by_pair = {
        (int(row["proposal_id"]), int(row["tender_position_id"])): row.get("price")
        for row in proposal_prices
    }
    invitation_rows = list(
        invitation_model.objects.filter(tender=tender)
        .select_related("supplier_company")
        .order_by("created_at", "id")
    )

    journal_entries = list(
        (
            TenderApprovalJournal.objects.filter(sales_tender=tender)
            if is_sales
            else TenderApprovalJournal.objects.filter(procurement_tender=tender)
        )
        .select_related("actor")
        .order_by("created_at", "id")
    )
    decision_entry = next(
        (
            entry
            for entry in journal_entries
            if entry.action == TenderApprovalJournal.Action.SAVED
            and entry.stage == "approval"
        ),
        None,
    )
    if decision_entry is None and journal_entries:
        decision_entry = journal_entries[-1]

    criteria_items_manager = getattr(tender, "criteria_items", None)
    criteria_items = (
        list(criteria_items_manager.all()) if criteria_items_manager is not None else []
    )
    if not criteria_items:
        criteria_items = list(tender.tender_criteria.all())

    company_ids = {
        int(company_id)
        for company_id in (
            [getattr(item, "supplier_company_id", None) for item in proposals]
            + [getattr(item, "supplier_company_id", None) for item in invitation_rows]
        )
        if company_id
    }
    company_contacts = {}
    if company_ids:
        memberships = list(
            CompanyUser.objects.filter(
                company_id__in=company_ids,
                status=CompanyUser.Status.APPROVED,
            )
            .select_related("user", "role", "company")
            .order_by("company_id", "user__last_name", "user__first_name", "user__id")
        )
        for membership in memberships:
            user = getattr(membership, "user", None)
            if user is None:
                continue
            contact_parts = [_format_protocol_person(user)]
            if getattr(user, "email", ""):
                contact_parts.append(user.email)
            if getattr(user, "phone", ""):
                contact_parts.append(user.phone)
            company_contacts.setdefault(membership.company_id, []).append(
                " | ".join(part for part in contact_parts if part)
            )

    tours_payload = []
    for tour in _collect_tour_chain_until_current(tender):
        planned_start = _format_protocol_datetime(
            getattr(tour, "planned_start_at", None), "%d.%m.%Y %H:%M"
        )
        planned_end = _format_protocol_datetime(
            getattr(tour, "planned_end_at", None), "%d.%m.%Y %H:%M"
        )
        actual_start = _format_protocol_datetime(
            getattr(tour, "start_at", None), "%d.%m.%Y %H:%M"
        )
        actual_end = _format_protocol_datetime(
            getattr(tour, "end_at", None), "%d.%m.%Y %H:%M"
        )
        timing_changed = "-"
        if (
            planned_start != "-"
            and actual_start != "-"
            and planned_start != actual_start
        ) or (
            planned_end != "-"
            and actual_end != "-"
            and planned_end != actual_end
        ):
            timing_changed = _format_protocol_datetime(
                getattr(tour, "updated_at", None), "%d.%m.%Y %H:%M"
            )
        tours_payload.append(
            {
                "tour_number": getattr(tour, "tour_number", 1) or 1,
                "conduct_type_label": getattr(
                    tour,
                    "get_conduct_type_display",
                    lambda: getattr(tour, "conduct_type", "-"),
                )(),
                "planned_start_at": planned_start,
                "planned_end_at": planned_end,
                "start_at": actual_start if actual_start != "-" else planned_start,
                "end_at": actual_end if actual_end != "-" else planned_end,
                "timing_changed_at": timing_changed,
            }
        )

    criteria_type_labels = dict(TenderCriterion.Type.choices)
    criteria_application_labels = dict(TenderCriterion.Application.choices)
    criteria_payload = [
        {
            "name": getattr(item, "name", "") or "-",
            "type_label": criteria_type_labels.get(
                getattr(item, "type", ""), getattr(item, "type", "-")
            ),
            "value_display": _protocol_criterion_options_display(
                getattr(item, "options", {}) or {}
            ),
            "application_label": criteria_application_labels.get(
                getattr(item, "application", ""), getattr(item, "application", "-")
            ),
        }
        for item in criteria_items
    ]

    decision_mode = _resolve_tender_decision_mode(tender=tender, positions=positions)
    decision_labels = {
        "winner": "Переможця визначено",
        "cancel": "Завершено без переможця",
        "next_round": "Переведено в наступний тур",
        "pending": "Рішення не зафіксовано",
    }

    winners = []
    winners_total = Decimal("0")
    for position in positions:
        winner = getattr(position, "winner_proposal", None)
        if winner is None:
            continue
        raw_price = price_by_pair.get((int(winner.id), int(position.id)))
        price_dec = _protocol_decimal(raw_price)
        qty_dec = _protocol_decimal(getattr(position, "quantity", None))
        total_dec = (
            (price_dec * qty_dec)
            if price_dec is not None and qty_dec is not None
            else None
        )
        if total_dec is not None:
            winners_total += total_dec
        winners.append(
            {
                "supplier_name": getattr(
                    getattr(winner, "supplier_company", None), "name", "-"
                )
                or "-",
                "position_name": getattr(position, "name", "") or "-",
                "unit_name": getattr(position, "unit_name", "") or "-",
                "quantity": _format_protocol_display_number(
                    getattr(position, "quantity", None)
                ),
                "price": _format_protocol_display_number(raw_price),
                "total": _format_protocol_display_number(total_dec),
            }
        )

    estimated_budget_dec = _protocol_decimal(getattr(tender, "estimated_budget", None))
    effect_label = "Вигода" if is_sales else "Економія"
    effect_amount = "-"
    if estimated_budget_dec is not None:
        effect_value = (
            winners_total - estimated_budget_dec
            if is_sales
            else estimated_budget_dec - winners_total
        )
        effect_amount = _format_protocol_display_number(effect_value)

    invited_rows = invitation_rows or proposals
    invited_payload = []
    for item in invited_rows:
        supplier_company = getattr(item, "supplier_company", None)
        contacts = company_contacts.get(getattr(item, "supplier_company_id", None), [])
        invited_payload.append(
            {
                "company_name": getattr(supplier_company, "name", "-") or "-",
                "contacts": "\n".join(contacts) if contacts else "-",
                "invited_at": _format_protocol_datetime(
                    getattr(item, "created_at", None)
                    or getattr(item, "submitted_at", None),
                    "%d.%m.%Y %H:%M",
                ),
            }
        )

    journal_payload = [
        {
            "created_at": _format_protocol_datetime(
                getattr(entry, "created_at", None), "%d.%m.%Y %H:%M"
            ),
            "action_label": getattr(entry, "get_action_display", lambda: entry.action)(),
            "actor_name": _format_protocol_person(getattr(entry, "actor", None)),
            "comment": _protocol_text(getattr(entry, "comment", "")),
        }
        for entry in journal_entries
    ]

    company = getattr(tender, "company", None)
    return {
        "generated_at": _format_protocol_datetime(timezone.now(), "%d.%m.%Y %H:%M"),
        "company_name": getattr(company, "name", "-") or "-",
        "company_code": getattr(company, "edrpou", "-") or "-",
        "tender_kind_label": "Продаж" if is_sales else "Закупівля",
        "tender_number": str(
            getattr(tender, "number", "") or getattr(tender, "id", "-")
        ),
        "tender_name": getattr(tender, "name", "-") or "-",
        "decision_label": decision_labels.get(decision_mode, decision_mode),
        "decision_comment": _protocol_text(getattr(decision_entry, "comment", "")),
        "author_name": _format_protocol_person(getattr(tender, "created_by", None)),
        "budget_amount": _format_protocol_display_number(
            getattr(tender, "estimated_budget", None)
        ),
        "currency_code": getattr(getattr(tender, "currency", None), "code", "-") or "-",
        "expense_article_name": getattr(
            getattr(tender, "expense_article", None), "name", "-"
        )
        or "-",
        "branch_name": getattr(getattr(tender, "branch", None), "name", "-") or "-",
        "department_name": getattr(
            getattr(tender, "department", None), "name", "-"
        )
        or "-",
        "created_at": _format_protocol_datetime(
            getattr(tender, "created_at", None), "%d.%m.%Y %H:%M"
        ),
        "completed_at": _format_protocol_datetime(
            getattr(tender, "end_at", None) or getattr(tender, "updated_at", None),
            "%d.%m.%Y %H:%M",
        ),
        "decision_at": _format_protocol_datetime(
            getattr(decision_entry, "created_at", None)
            or getattr(tender, "updated_at", None),
            "%d.%m.%Y %H:%M",
        ),
        "conduct_type_label": getattr(
            tender,
            "get_conduct_type_display",
            lambda: getattr(tender, "conduct_type", "-"),
        )(),
        "publication_type_label": getattr(
            tender,
            "get_publication_type_display",
            lambda: getattr(tender, "publication_type", "-"),
        )(),
        "price_criterion_label": _build_protocol_price_criterion_label(tender),
        "winners_total": _format_protocol_display_number(winners_total),
        "effect_label": effect_label,
        "effect_amount": effect_amount,
        "general_terms_lines": _protocol_html_to_lines(
            getattr(tender, "general_terms", "")
        ),
        "tours": tours_payload,
        "winners": winners,
        "criteria": criteria_payload,
        "invited_participants": invited_payload,
        "approval_journal": journal_payload,
    }


def _get_protocol_reportlab_fonts():
    global _PROTOCOL_REPORTLAB_FONTS
    if _PROTOCOL_REPORTLAB_FONTS is not None:
        return _PROTOCOL_REPORTLAB_FONTS
    fonts = {"regular": "Helvetica", "bold": "Helvetica-Bold"}
    if not REPORTLAB_AVAILABLE:
        _PROTOCOL_REPORTLAB_FONTS = fonts
        return fonts
    font_pairs = [
        (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
        (
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ),
    ]
    for regular_path, bold_path in font_pairs:
        if not (os.path.exists(regular_path) and os.path.exists(bold_path)):
            continue
        try:
            pdfmetrics.registerFont(TTFont("ProtocolRegular", regular_path))
            pdfmetrics.registerFont(TTFont("ProtocolBold", bold_path))
            fonts = {"regular": "ProtocolRegular", "bold": "ProtocolBold"}
            break
        except Exception:
            continue
    _PROTOCOL_REPORTLAB_FONTS = fonts
    return fonts


def _protocol_pdf_paragraph(text, style):
    prepared = xml_escape(str(text or "-")).replace("\n", "<br/>")
    return Paragraph(prepared, style)


def _build_tender_protocol_pdf_content(payload):
    if not REPORTLAB_AVAILABLE:
        return None

    fonts = _get_protocol_reportlab_fonts()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f"Протокол тендера № {payload['tender_number']}",
    )

    sample_styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ProtocolTitle",
        parent=sample_styles["Title"],
        fontName=fonts["bold"],
        fontSize=15,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "ProtocolHeading",
        parent=sample_styles["Heading2"],
        fontName=fonts["bold"],
        fontSize=11,
        leading=14,
        textColor=colors.black,
        spaceBefore=0,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ProtocolBody",
        parent=sample_styles["Normal"],
        fontName=fonts["regular"],
        fontSize=9,
        leading=12,
        textColor=colors.black,
        spaceAfter=0,
    )
    body_bold_style = ParagraphStyle(
        "ProtocolBodyBold",
        parent=body_style,
        fontName=fonts["bold"],
    )
    body_right_style = ParagraphStyle(
        "ProtocolBodyRight",
        parent=body_style,
        alignment=TA_RIGHT,
    )
    body_center_bold_style = ParagraphStyle(
        "ProtocolBodyCenterBold",
        parent=body_bold_style,
        alignment=TA_CENTER,
    )

    def _display(value):
        prepared = str(value or "").strip()
        return prepared if prepared and prepared != "-" else "—"

    def build_plain_header():
        top_table = Table(
            [
                [
                    _protocol_pdf_paragraph(_display(payload["company_name"]), body_bold_style),
                    _protocol_pdf_paragraph(_display(payload["generated_at"]), body_right_style),
                ],
                [
                    _protocol_pdf_paragraph(_display(payload["company_code"]), body_style),
                    _protocol_pdf_paragraph("", body_style),
                ],
            ],
            colWidths=[110 * mm, 56 * mm],
            hAlign="LEFT",
        )
        top_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LINEBELOW", (0, 1), (0, 1), 0.8, colors.black),
                ]
            )
        )
        return top_table

    def build_detail_table(rows):
        prepared_rows = [
            [
                _protocol_pdf_paragraph(_display(row["label"]), body_bold_style),
                _protocol_pdf_paragraph(_display(row["value"]), body_style),
            ]
            for row in rows
        ]
        table = Table(prepared_rows, colWidths=[56 * mm, 110 * mm], hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
                    ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return table

    def build_schedule_table():
        rows = [
            [
                _protocol_pdf_paragraph("Створення тендера", body_bold_style),
                _protocol_pdf_paragraph(_display(payload["created_at"]), body_style),
            ]
        ]
        styles = [
            ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        current_row = 1
        for item in payload["tours"] or []:
            rows.append(
                [
                    _protocol_pdf_paragraph(
                        f"Тур {_display(item['tour_number'])} {_display(item['conduct_type_label'])}",
                        body_center_bold_style,
                    ),
                    _protocol_pdf_paragraph("", body_style),
                ]
            )
            styles.extend(
                [
                    ("SPAN", (0, current_row), (1, current_row)),
                    ("BACKGROUND", (0, current_row), (1, current_row), colors.HexColor("#f1f1f1")),
                ]
            )
            current_row += 1
            rows.append(
                [
                    _protocol_pdf_paragraph("Початок прийому пропозицій", body_bold_style),
                    _protocol_pdf_paragraph(_display(item["start_at"]), body_style),
                ]
            )
            current_row += 1
            if _display(item["timing_changed_at"]) != "—":
                rows.append(
                    [
                        _protocol_pdf_paragraph("Зміна часу проведення тендера", body_bold_style),
                        _protocol_pdf_paragraph(
                            _display(item["timing_changed_at"]), body_style
                        ),
                    ]
                )
                current_row += 1
            rows.append(
                [
                    _protocol_pdf_paragraph("Завершення прийому пропозицій", body_bold_style),
                    _protocol_pdf_paragraph(_display(item["end_at"]), body_style),
                ]
            )
            current_row += 1

        rows.append(
            [
                _protocol_pdf_paragraph("Завершення тендера", body_bold_style),
                _protocol_pdf_paragraph(_display(payload["completed_at"]), body_style),
            ]
        )
        table = Table(rows, colWidths=[56 * mm, 110 * mm], hAlign="LEFT")
        table.setStyle(TableStyle(styles))
        return table

    def build_grid_table(headers, rows, col_widths):
        prepared_rows = [
            [_protocol_pdf_paragraph(_display(header), body_bold_style) for header in headers]
        ]
        for row in rows or [["—"] * len(headers)]:
            prepared_rows.append(
                [_protocol_pdf_paragraph(_display(cell), body_style) for cell in row]
            )
        table = Table(
            prepared_rows,
            colWidths=col_widths,
            hAlign="LEFT",
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
                    ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f1f1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return table

    branch_department_parts = [
        _display(payload["branch_name"]),
        _display(payload["department_name"]),
    ]
    branch_department = " / ".join(
        item for item in branch_department_parts if item != "—"
    ) or "—"

    story = [
        build_plain_header(),
        Spacer(1, 12),
        _protocol_pdf_paragraph("Протокол проведення процедури", title_style),
        _protocol_pdf_paragraph(
            f"Тендер № {_display(payload['tender_number'])} {_display(payload['tender_name'])}",
            body_style,
        ),
        Spacer(1, 3),
        _protocol_pdf_paragraph(
            f"Рішення: {_display(payload['decision_label'])}", body_style
        ),
        _protocol_pdf_paragraph(
            f"Виконавець: {_display(payload['author_name'])}", body_style
        ),
        _protocol_pdf_paragraph(
            f"Бюджет: {_display(payload['budget_amount'])}    Валюта: {_display(payload['currency_code'])}",
            body_style,
        ),
        _protocol_pdf_paragraph(
            f"Стаття бюджету: {_display(payload['expense_article_name'])}",
            body_style,
        ),
        _protocol_pdf_paragraph(
            f"Філіал/Департамент: {branch_department}",
            body_style,
        ),
        _protocol_pdf_paragraph(
            f"Підрозділ: {_display(payload['department_name'])}",
            body_style,
        ),
        Spacer(1, 10),
        build_schedule_table(),
        PageBreak(),
        build_detail_table(
            [
                {"label": "Прийняте рішення", "value": payload["decision_label"]},
                {"label": "Дата рішення", "value": payload["decision_at"]},
                {
                    "label": "Параметри цінового критерію",
                    "value": payload["price_criterion_label"],
                },
            ]
        ),
        Spacer(1, 10),
        _protocol_pdf_paragraph("Переможці", heading_style),
        build_grid_table(
            [
                "Контрагент",
                "Позиція",
                "Одиниці виміру",
                "Кількість",
                "Ціна",
                "Вартість",
            ],
            [
                [
                    item["supplier_name"],
                    item["position_name"],
                    item["unit_name"],
                    item["quantity"],
                    item["price"],
                    item["total"],
                ]
                for item in payload["winners"]
            ],
            [34 * mm, 46 * mm, 24 * mm, 18 * mm, 20 * mm, 24 * mm],
        ),
        Spacer(1, 5),
        _protocol_pdf_paragraph(
            f"Разом: {_display(payload['winners_total'])}", body_bold_style
        ),
        _protocol_pdf_paragraph(
            f"{_display(payload['effect_label'])}: {_display(payload['effect_amount'])}",
            body_bold_style,
        ),
        Spacer(1, 10),
        _protocol_pdf_paragraph("Критерії тендера", heading_style),
        build_grid_table(
            ["Назва критерію", "Тип", "Значення", "Застосування"],
            [
                [
                    item["name"],
                    item["type_label"],
                    item["value_display"],
                    item["application_label"],
                ]
                for item in payload["criteria"]
            ],
            [46 * mm, 24 * mm, 58 * mm, 38 * mm],
        ),
        Spacer(1, 10),
        _protocol_pdf_paragraph("Запрошені учасники", heading_style),
        build_grid_table(
            ["Контрагенти", "Контактні особи / Агенти", "Дата запрошення"],
            [
                [
                    item["company_name"],
                    item["contacts"],
                    item["invited_at"],
                ]
                for item in payload["invited_participants"]
            ],
            [44 * mm, 84 * mm, 38 * mm],
        ),
        Spacer(1, 10),
        _protocol_pdf_paragraph("Опис умов та вимог", heading_style),
        Table(
            [[_protocol_pdf_paragraph(_display("\n".join(payload["general_terms_lines"] or ["—"])), body_style)]],
            colWidths=[166 * mm],
            hAlign="LEFT",
            style=TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        ),
        Spacer(1, 10),
        _protocol_pdf_paragraph("Журнал узгодження", heading_style),
        build_grid_table(
            ["Дата", "Дія", "Користувач", "Коментар"],
            [
                [
                    item["created_at"],
                    item["action_label"],
                    item["actor_name"],
                    item["comment"],
                ]
                for item in payload["approval_journal"]
            ],
            [28 * mm, 28 * mm, 42 * mm, 68 * mm],
        ),
    ]

    if _display(payload["decision_comment"]) != "—":
        story.extend(
            [
                Spacer(1, 10),
                _protocol_pdf_paragraph("Коментар до рішення", heading_style),
                Table(
                    [[_protocol_pdf_paragraph(_display(payload["decision_comment"]), body_style)]],
                    colWidths=[166 * mm],
                    hAlign="LEFT",
                    style=TableStyle(
                        [
                            ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ]
                    ),
                ),
            ]
        )

    doc.build(story)
    return buffer.getvalue()

def _build_tender_protocol_lines(*, tender, is_sales):
    position_model = SalesTenderPosition if is_sales else ProcurementTenderPosition
    proposal_model = SalesTenderProposal if is_sales else TenderProposal
    proposal_position_model = (
        SalesTenderProposalPosition if is_sales else TenderProposalPosition
    )

    positions = list(
        position_model.objects.filter(tender=tender)
        .select_related("winner_proposal__supplier_company", "nomenclature")
        .order_by("id")
    )
    proposals = list(
        proposal_model.objects.filter(tender=tender)
        .select_related("supplier_company")
        .order_by("supplier_company__name", "id")
    )
    proposal_prices = proposal_position_model.objects.filter(
        proposal__tender=tender,
        tender_position__tender=tender,
    ).values("proposal_id", "tender_position_id", "price")
    price_by_pair = {
        (int(row["proposal_id"]), int(row["tender_position_id"])): row.get("price")
        for row in proposal_prices
    }

    cpv_rows = list(tender.cpv_categories.all().values_list("cpv_code", "name_ua"))
    if not cpv_rows and getattr(tender, "cpv_category_id", None):
        cpv = getattr(tender, "cpv_category", None)
        if cpv is not None:
            cpv_rows = [(getattr(cpv, "cpv_code", ""), getattr(cpv, "name_ua", ""))]
    cpv_text = (
        "; ".join(f"{code} - {name}" for code, name in cpv_rows if code or name) or "-"
    )

    creator = getattr(tender, "created_by", None)
    creator_name_parts = [
        getattr(creator, "last_name", ""),
        getattr(creator, "first_name", ""),
        getattr(creator, "middle_name", ""),
    ]
    creator_name = " ".join(part for part in creator_name_parts if part).strip()
    if not creator_name:
        creator_name = getattr(creator, "email", "") or "-"

    decision_mode = _resolve_tender_decision_mode(tender=tender, positions=positions)
    decision_labels = {
        "winner": "Completed with winner",
        "cancel": "Completed without winner",
        "next_round": "Next round",
        "pending": "Not fixed",
    }

    journal_qs = (
        TenderApprovalJournal.objects.filter(sales_tender=tender)
        if is_sales
        else TenderApprovalJournal.objects.filter(procurement_tender=tender)
    )
    decision_entry = journal_qs.filter(
        action=TenderApprovalJournal.Action.SAVED,
        stage="approval",
    ).first()
    if decision_entry is None:
        decision_entry = journal_qs.first()

    lines = []
    lines.append(
        f"Tender protocol ({'Sales' if is_sales else 'Procurement'}) "
        f"ID={tender.id}, tour={getattr(tender, 'tour_number', 1)}"
    )
    lines.append(
        f"Number: {getattr(tender, 'number', '-')}, Name: {getattr(tender, 'name', '-')}"
    )
    lines.append(
        f"Company: {getattr(getattr(tender, 'company', None), 'name', '-')}, Stage: {getattr(tender, 'get_stage_display', lambda: getattr(tender, 'stage', '-'))()}"
    )
    lines.append(
        f"Conduct type: {getattr(tender, 'get_conduct_type_display', lambda: getattr(tender, 'conduct_type', '-'))()}, "
        f"Auction model: {getattr(tender, 'get_auction_model_display', lambda: getattr(tender, 'auction_model', '-'))()}"
    )
    lines.append(
        f"Publication type: {getattr(tender, 'get_publication_type_display', lambda: getattr(tender, 'publication_type', '-'))()}"
    )
    lines.append(
        f"Category: {getattr(getattr(tender, 'category', None), 'name', '-')}, CPV: {cpv_text}"
    )
    lines.append(
        f"Expense article: {getattr(getattr(tender, 'expense_article', None), 'name', '-')}"
    )
    lines.append(
        f"Branch: {getattr(getattr(tender, 'branch', None), 'name', '-')}, "
        f"Department: {getattr(getattr(tender, 'department', None), 'name', '-')}"
    )
    currency_code = getattr(getattr(tender, "currency", None), "code", "") or ""
    lines.append(
        f"Estimated budget: {_format_protocol_number(getattr(tender, 'estimated_budget', None))} {currency_code}".rstrip()
    )
    lines.append(f"Created by: {creator_name}")
    lines.append(f"Created at: {_format_protocol_datetime(getattr(tender, 'created_at', None))}")
    lines.append(f"Updated at: {_format_protocol_datetime(getattr(tender, 'updated_at', None))}")
    lines.append(f"Planned acceptance start: {_format_protocol_datetime(getattr(tender, 'planned_start_at', None))}")
    lines.append(f"Planned acceptance end: {_format_protocol_datetime(getattr(tender, 'planned_end_at', None))}")
    lines.append(f"Actual acceptance start: {_format_protocol_datetime(getattr(tender, 'start_at', None))}")
    lines.append(f"Actual acceptance end: {_format_protocol_datetime(getattr(tender, 'end_at', None))}")
    lines.append(
        f"General terms: {str(getattr(tender, 'general_terms', '') or '').strip() or '-'}"
    )
    lines.append("")

    tours = _collect_tour_chain_until_current(tender)
    lines.append("Acceptance schedule by tours:")
    for tour in tours:
        lines.append(
            f"- Tour {getattr(tour, 'tour_number', 1)} "
            f"(stage={getattr(tour, 'stage', '-')}) "
            f"start={_format_protocol_datetime(getattr(tour, 'start_at', None))}, "
            f"end={_format_protocol_datetime(getattr(tour, 'end_at', None))}"
        )
    lines.append("")

    lines.append(f"Decision: {decision_labels.get(decision_mode, decision_mode)}")
    if decision_entry is not None:
        lines.append(
            f"Decision journal time: {_format_protocol_datetime(getattr(decision_entry, 'created_at', None))}"
        )
        lines.append(
            f"Decision comment: {str(getattr(decision_entry, 'comment', '') or '').strip() or '-'}"
        )
    lines.append("")

    lines.append("Tender positions and winners:")
    grand_total = Decimal("0")
    for index, pos in enumerate(positions, start=1):
        winner = getattr(pos, "winner_proposal", None)
        winner_name = (
            getattr(getattr(winner, "supplier_company", None), "name", "-")
            if winner
            else "-"
        )
        winner_price_raw = (
            price_by_pair.get((int(winner.id), int(pos.id))) if winner else None
        )
        winner_price = _format_protocol_number(winner_price_raw)
        line_total = "-"
        if winner_price_raw not in (None, ""):
            try:
                qty = Decimal(str(getattr(pos, "quantity", 0) or 0))
                price = Decimal(str(winner_price_raw))
                total = qty * price
                grand_total += total
                line_total = _format_protocol_number(total)
            except (InvalidOperation, ValueError, TypeError):
                line_total = "-"
        lines.append(
            f"{index}. {getattr(pos, 'name', '-')}, qty={_format_protocol_number(getattr(pos, 'quantity', None))} {getattr(pos, 'unit_name', '') or ''}, "
            f"winner={winner_name}, winner_price={winner_price}, line_total={line_total}"
        )
    if not positions:
        lines.append("- No positions")
    lines.append(f"Tender total by selected winners: {_format_protocol_number(grand_total)}")
    lines.append("")

    lines.append("Invited counterparties:")
    for index, proposal in enumerate(proposals, start=1):
        supplier = getattr(proposal, "supplier_company", None)
        lines.append(
            f"{index}. {getattr(supplier, 'name', '-')}, "
            f"EDRPOU={getattr(supplier, 'edrpou', '-')}, "
            f"submitted_at={_format_protocol_datetime(getattr(proposal, 'submitted_at', None))}"
        )
    if not proposals:
        lines.append("- No invited counterparties")
    return lines


def _build_tender_protocol_pdf_response(*, tender, is_sales, download=False):
    payload = _build_tender_protocol_payload(tender=tender, is_sales=is_sales)
    pdf_content = _build_tender_protocol_pdf_content(payload)
    if not pdf_content:
        lines = _build_tender_protocol_lines(tender=tender, is_sales=is_sales)
        pdf_content = _build_simple_pdf(lines)
    prefix = "sales" if is_sales else "procurement"
    number_part = getattr(tender, "number", None) or getattr(tender, "id", "x")
    tour_part = getattr(tender, "tour_number", 1) or 1
    filename = f"tender-protocol-{prefix}-{number_part}-tour-{tour_part}.pdf"
    response = HttpResponse(pdf_content, content_type="application/pdf")
    disposition = "attachment" if str(download).lower() in {"1", "true", "yes"} else "inline"
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    return response


def _build_decision_market_reference_payload(*, tender, is_sales):
    """Return market references for current positions using first available tour prices."""
    position_model = SalesTenderPosition if is_sales else ProcurementTenderPosition
    proposal_position_model = (
        SalesTenderProposalPosition if is_sales else TenderProposalPosition
    )

    positions = list(
        position_model.objects.filter(tender=tender).values("id", "nomenclature_id")
    )
    if not positions:
        return {"mode_default": "first_tour", "position_market": []}

    nomenclature_ids = {
        int(row["nomenclature_id"])
        for row in positions
        if row.get("nomenclature_id") is not None
    }
    if not nomenclature_ids:
        return {"mode_default": "first_tour", "position_market": []}

    tours = _collect_tour_chain_until_current(tender)
    tour_ids = [int(t.id) for t in tours]
    tour_number_by_id = {int(t.id): int(getattr(t, "tour_number", 1) or 1) for t in tours}

    market_rows = list(
        proposal_position_model.objects.filter(
            proposal__tender_id__in=tour_ids,
            proposal__submitted_at__isnull=False,
            price__isnull=False,
            tender_position__nomenclature_id__in=nomenclature_ids,
        )
        .values("proposal__tender_id", "tender_position__nomenclature_id")
        .annotate(avg_price=Avg("price"))
    )
    market_rows.sort(
        key=lambda row: (
            tour_number_by_id.get(int(row["proposal__tender_id"]), 10**9),
            int(row["proposal__tender_id"]),
        )
    )

    first_market_by_nomenclature = {}
    first_market_source_by_nomenclature = {}
    for row in market_rows:
        nomenclature_id = int(row["tender_position__nomenclature_id"])
        if nomenclature_id in first_market_by_nomenclature:
            continue
        avg_price = row.get("avg_price")
        if avg_price is None:
            continue
        source_tour_id = int(row["proposal__tender_id"])
        first_market_by_nomenclature[nomenclature_id] = avg_price
        first_market_source_by_nomenclature[nomenclature_id] = {
            "source_tour_id": source_tour_id,
            "source_tour_number": tour_number_by_id.get(source_tour_id),
        }

    position_market = []
    for row in positions:
        position_id = int(row["id"])
        nomenclature_id = int(row["nomenclature_id"])
        source = first_market_source_by_nomenclature.get(nomenclature_id) or {}
        position_market.append(
            {
                "position_id": position_id,
                "nomenclature_id": nomenclature_id,
                "market_price": first_market_by_nomenclature.get(nomenclature_id),
                "source_tour_id": source.get("source_tour_id"),
                "source_tour_number": source.get("source_tour_number"),
            }
        )

    return {"mode_default": "first_tour", "position_market": position_market}


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


def _request_data_value(request_data, key):
    getter = getattr(request_data, "get", None)
    if callable(getter):
        return getter(key)
    if isinstance(request_data, dict):
        return request_data.get(key)
    return None


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
        timing_comment = str(_request_data_value(request_data, "timing_comment") or "").strip()
        _create_tender_approval_journal_entry(
            action=TenderApprovalJournal.Action.SAVED,
            actor=actor,
            stage=after_stage,
            comment=timing_comment or _format_acceptance_period_comment(tender=tender),
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
    if TenderApprovalStageStepUser.objects.filter(
        user=user,
        step__stage_state__in=TenderApprovalStageState.objects.filter(**target),
    ).exists():
        return True

    # Fallback: detect approver by current approval model roles even if
    # stage-state snapshot is not materialized yet.
    approval_model_id = getattr(tender, "approval_model_id", None)
    if not approval_model_id:
        return False
    return ApprovalModelStep.objects.filter(
        model_id=approval_model_id,
        role__role_users__user_id=user.id,
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


def _user_company_ids(user):
    if not user or not getattr(user, "is_authenticated", False):
        return []
    return list(
        CompanyUser.objects.filter(
            user=user,
            status=CompanyUser.Status.APPROVED,
        ).values_list("company_id", flat=True)
    )


def _user_represents_company(*, user, company_id):
    if not company_id:
        return False
    return int(company_id) in {int(item_id) for item_id in _user_company_ids(user)}


def _tender_kind(is_sales):
    return "sales" if is_sales else "procurement"


def _tender_detail_queryset(*, is_sales):
    tender_model = SalesTender if is_sales else ProcurementTender
    return tender_model.objects.select_related(
        "company", "category", "cpv_category", "expense_article",
        "branch", "department", "currency", "created_by", "parent",
    ).prefetch_related(
        "positions__nomenclature__unit",
        "tender_criteria",
        "criteria_items__reference_criterion",
    )


def _get_tender_for_owner_or_approver(*, user, tender_id, is_sales, base_queryset=None):
    queryset = base_queryset if base_queryset is not None else _tender_detail_queryset(is_sales=is_sales)
    tender = queryset.filter(pk=tender_id).first()
    if tender:
        if getattr(user, "is_superuser", False):
            return tender
        user_company_ids = {int(item_id) for item_id in _user_company_ids(user)}
        if int(tender.company_id) in user_company_ids:
            return tender
        if _user_is_tender_approver(
            user=user,
            tender=tender,
            is_sales=is_sales,
        ):
            return tender
    approver_tender = _tender_detail_queryset(is_sales=is_sales).filter(pk=tender_id).first()
    if approver_tender and _user_is_tender_approver(
        user=user,
        tender=approver_tender,
        is_sales=is_sales,
    ):
        return approver_tender
    return None


def _get_tender_invitation_model(*, is_sales):
    return SalesTenderInvitation if is_sales else ProcurementTenderInvitation


def _is_company_invited_to_tender(*, tender, supplier_company_id, is_sales):
    if not supplier_company_id:
        return False
    if getattr(tender, "publication_type", "") != "closed":
        return True
    invitation_model = _get_tender_invitation_model(is_sales=is_sales)
    return invitation_model.objects.filter(
        tender=tender,
        supplier_company_id=int(supplier_company_id),
    ).exists()


def _is_any_company_invited_to_tender(*, tender, supplier_company_ids, is_sales):
    normalized_ids = [int(item_id) for item_id in supplier_company_ids or [] if int(item_id) > 0]
    if not normalized_ids:
        return False
    if getattr(tender, "publication_type", "") != "closed":
        return True
    invitation_model = _get_tender_invitation_model(is_sales=is_sales)
    return invitation_model.objects.filter(
        tender=tender,
        supplier_company_id__in=normalized_ids,
    ).exists()


def _filter_participation_qs_by_publication_type(*, qs, user_company_ids):
    return qs.filter(
        Q(publication_type="open")
        | Q(invited_supplier_links__supplier_company_id__in=list(user_company_ids))
    ).distinct()


def _sync_tender_invited_suppliers(*, tender, supplier_company_ids, is_sales):
    invitation_model = _get_tender_invitation_model(is_sales=is_sales)
    normalized_ids = []
    seen = set()
    for item in supplier_company_ids or []:
        try:
            company_id = int(item)
        except (TypeError, ValueError):
            continue
        if company_id <= 0 or company_id in seen:
            continue
        seen.add(company_id)
        normalized_ids.append(company_id)

    existing_ids = set(
        invitation_model.objects.filter(tender=tender).values_list(
            "supplier_company_id", flat=True
        )
    )
    target_ids = set(normalized_ids)
    removed_ids = existing_ids - target_ids
    if removed_ids:
        invitation_model.objects.filter(
            tender=tender,
            supplier_company_id__in=list(removed_ids),
        ).delete()

    missing_ids = target_ids - existing_ids
    if not missing_ids:
        return

    invitation_model.objects.bulk_create(
        [
            invitation_model(tender=tender, supplier_company_id=company_id)
            for company_id in missing_ids
        ],
        ignore_conflicts=True,
    )


def _get_tender_for_owner_or_participant(*, user, tender_id, is_sales):
    tender = _tender_detail_queryset(is_sales=is_sales).filter(pk=tender_id).first()
    if not tender:
        return None
    user_company_ids = set(_user_company_ids(user))
    if not user_company_ids:
        return None
    if int(tender.company_id) in user_company_ids:
        return tender
    if _is_any_company_invited_to_tender(
        tender=tender,
        supplier_company_ids=user_company_ids,
        is_sales=is_sales,
    ):
        return tender
    proposal_model = _get_tender_proposal_model(is_sales=is_sales)
    has_proposal = proposal_model.objects.filter(
        tender_id=int(tender.id),
        supplier_company_id__in=user_company_ids,
    ).exists()
    return tender if has_proposal else None


def _filter_tender_proposals_for_user(*, qs, tender, user):
    user_company_ids = set(_user_company_ids(user))
    is_owner = int(tender.company_id) in user_company_ids
    if is_owner:
        return qs, True
    return qs.filter(supplier_company_id__in=user_company_ids), False


def _serialize_participation_representative_for_response(user):
    if not user:
        return {"full_name": "", "email": ""}
    return {
        "full_name": _format_user_display_name(user),
        "email": getattr(user, "email", "") or "",
    }


def _build_participation_locked_response(*, proposal):
    representative = getattr(proposal, "created_by", None)
    payload = {
        "detail": (
            "Представник вашої компанії вже підтвердив участь в тендері."
        ),
        "representative": _serialize_participation_representative_for_response(representative),
    }
    return Response(payload, status=status.HTTP_403_FORBIDDEN)


def _ensure_user_can_manage_company_proposal(*, proposal, user):
    representative_id = getattr(proposal, "created_by_id", None)
    if representative_id:
        try:
            if int(representative_id) != int(user.id):
                return _build_participation_locked_response(proposal=proposal)
        except (TypeError, ValueError):
            pass
        return None
    proposal.created_by = user
    proposal.save(update_fields=["created_by"])
    return None


def _tender_document_meta(*, tender, is_sales):
    kind = _tender_kind(is_sales)
    document_name = f"Тендер №{getattr(tender, 'number', None) or getattr(tender, 'id', '')}"
    route = (
        f"/cabinet/tenders/sales/{int(tender.id)}"
        if is_sales
        else f"/cabinet/tenders/{int(tender.id)}"
    )
    return {
        "tender_type": kind,
        "tender_id": int(tender.id),
        "document_name": document_name,
        "document_url": route,
    }


def _create_notification(*, user, notification_type, title, body="", meta=None):
    if not user:
        return None
    return Notification.objects.create(
        user=user,
        type=notification_type,
        title=title,
        body=body or "",
        meta=meta or {},
    )


def _notify_tender_author_stage_event(*, tender, is_sales, event_type, title, body=""):
    author = getattr(tender, "created_by", None)
    if not author:
        return
    meta = _tender_document_meta(tender=tender, is_sales=is_sales)
    meta["event"] = event_type
    _create_notification(
        user=author,
        notification_type=event_type,
        title=title,
        body=body,
        meta=meta,
    )


def _get_or_create_tender_chat_thread(*, tender, is_sales, supplier_company_id):
    return TenderChatThread.objects.get_or_create(
        tender_type=_tender_kind(is_sales),
        tender_id=int(tender.id),
        supplier_company_id=supplier_company_id,
        defaults={},
    )


def _get_tender_proposal_model(*, is_sales):
    return SalesTenderProposal if is_sales else TenderProposal


def _ensure_tender_chat_threads_for_submitted_participants(*, tender, is_sales):
    proposal_model = _get_tender_proposal_model(is_sales=is_sales)
    supplier_company_ids = list(
        proposal_model.objects.filter(
            tender=tender,
            submitted_at__isnull=False,
        )
        .exclude(supplier_company_id=tender.company_id)
        .values_list("supplier_company_id", flat=True)
        .distinct()
    )
    if not supplier_company_ids:
        return

    existing_company_ids = set(
        TenderChatThread.objects.filter(
            tender_type=_tender_kind(is_sales),
            tender_id=int(tender.id),
            supplier_company_id__in=supplier_company_ids,
        ).values_list("supplier_company_id", flat=True)
    )
    to_create = [
        TenderChatThread(
            tender_type=_tender_kind(is_sales),
            tender_id=int(tender.id),
            supplier_company_id=company_id,
        )
        for company_id in supplier_company_ids
        if int(company_id) not in existing_company_ids
    ]
    if to_create:
        TenderChatThread.objects.bulk_create(to_create, ignore_conflicts=True)


def _resolve_tender_chat_participant_company_ids(*, tender, is_sales, user_company_ids):
    user_company_ids = {int(item_id) for item_id in user_company_ids if int(item_id) != int(tender.company_id)}
    if not user_company_ids:
        return []

    proposal_model = _get_tender_proposal_model(is_sales=is_sales)
    proposal_company_ids = list(
        proposal_model.objects.filter(
            tender=tender,
            supplier_company_id__in=user_company_ids,
        )
        .values_list("supplier_company_id", flat=True)
        .distinct()
    )
    if proposal_company_ids:
        return [int(item_id) for item_id in proposal_company_ids]
    return sorted(user_company_ids)


def _annotate_tender_chat_threads_unread(*, qs, tender, is_owner):
    if is_owner:
        unread_filter = Q(messages__author_company_id=F("supplier_company_id")) & (
            Q(owner_last_read_at__isnull=True)
            | Q(messages__created_at__gt=F("owner_last_read_at"))
        )
    else:
        unread_filter = Q(messages__author_company_id=int(tender.company_id)) & (
            Q(supplier_last_read_at__isnull=True)
            | Q(messages__created_at__gt=F("supplier_last_read_at"))
        )
    return qs.annotate(unread_count=Count("messages", filter=unread_filter, distinct=True))


def _mark_tender_chat_thread_read(*, thread, is_owner):
    field_name = "owner_last_read_at" if is_owner else "supplier_last_read_at"
    setattr(thread, field_name, timezone.now())
    thread.save(update_fields=[field_name])


def _record_tender_bid_history(
    *,
    tender,
    is_sales,
    proposal,
    tender_position_id,
    price,
    actor,
):
    if getattr(tender, "conduct_type", "") != "online_auction":
        return
    TenderBidHistory.objects.create(
        tender_type=_tender_kind(is_sales),
        tender_id=int(tender.id),
        proposal_id=int(proposal.id),
        tender_position_id=int(tender_position_id),
        supplier_company_id=proposal.supplier_company_id,
        price=price,
        created_by=actor,
    )


def _record_tender_proposal_change_log(
    *,
    tender,
    is_sales,
    proposal,
    tender_position_id,
    original_price,
    original_criterion_values,
    current_price,
    current_criterion_values,
    actor,
):
    entry, created = TenderProposalChangeLog.objects.get_or_create(
        tender_type=_tender_kind(is_sales),
        proposal_id=int(proposal.id),
        tender_position_id=int(tender_position_id),
        defaults={
            "tender_id": int(tender.id),
            "supplier_company_id": proposal.supplier_company_id,
            "original_price": original_price,
            "original_criterion_values": original_criterion_values or {},
            "current_price": current_price,
            "current_criterion_values": current_criterion_values or {},
            "updated_by": actor,
        },
    )
    if created:
        return
    entry.tender_id = int(tender.id)
    entry.supplier_company_id = proposal.supplier_company_id
    entry.current_price = current_price
    entry.current_criterion_values = current_criterion_values or {}
    entry.updated_by = actor
    entry.save(
        update_fields=[
            "tender_id",
            "supplier_company",
            "current_price",
            "current_criterion_values",
            "updated_by",
            "updated_at",
        ]
    )


def _notify_tender_chat_message(*, tender, is_sales, thread, message, actor):
    meta = _tender_document_meta(tender=tender, is_sales=is_sales)
    meta.update(
        {
            "event": Notification.Type.CHAT_MESSAGE,
            "chat_thread_id": int(thread.id),
            "supplier_company_id": int(thread.supplier_company_id),
        }
    )
    title = "Нове повідомлення у чаті тендера"
    body = str(getattr(message, "body", "") or "").strip()
    if len(body) > 180:
        body = f"{body[:177]}..."

    recipients = []
    if _user_represents_company(user=actor, company_id=getattr(tender, "company_id", None)):
        recipients = list(
            CompanyUser.objects.filter(
                company_id=thread.supplier_company_id,
                status=CompanyUser.Status.APPROVED,
            )
            .select_related("user")
            .exclude(user_id=getattr(actor, "id", None))
        )
    else:
        author = getattr(tender, "created_by", None)
        if author and getattr(author, "id", None) != getattr(actor, "id", None):
            recipients = [type("Recipient", (), {"user": author})()]

    for membership in recipients:
        recipient_meta = _tender_document_meta(tender=tender, is_sales=is_sales)
        if _user_represents_company(user=membership.user, company_id=thread.supplier_company_id):
            recipient_meta["document_url"] = (
                f"/cabinet/tenders/sales/proposals/{int(tender.id)}"
                if is_sales
                else f"/cabinet/tenders/proposals/{int(tender.id)}"
            )
        recipient_meta.update(
            {
                "event": Notification.Type.CHAT_MESSAGE,
                "chat_thread_id": int(thread.id),
                "supplier_company_id": int(thread.supplier_company_id),
            }
        )
        _create_notification(
            user=membership.user,
            notification_type=Notification.Type.CHAT_MESSAGE,
            title=title,
            body=body,
            meta=recipient_meta,
        )


def _copy_sales_proposals_from_previous_tour(*, tender, actor):
    parent = getattr(tender, "parent", None)
    if not parent:
        return {"copied_companies": [], "copied_count": 0}

    parent_positions = list(parent.positions.order_by("id"))
    current_positions = list(tender.positions.order_by("id"))
    position_map = {}
    for parent_pos, current_pos in zip(parent_positions, current_positions):
        position_map[int(parent_pos.id)] = current_pos

    existing_company_ids = set(
        SalesTenderProposal.objects.filter(tender=tender).values_list("supplier_company_id", flat=True)
    )
    source_qs = (
        SalesTenderProposal.objects.filter(
            tender=parent,
            submitted_at__isnull=False,
        )
        .select_related("supplier_company")
        .prefetch_related("position_values")
        .order_by("id")
    )

    copied_company_ids = []
    for source_proposal in source_qs:
        if int(source_proposal.supplier_company_id) in existing_company_ids:
            continue
        target_proposal = SalesTenderProposal.objects.create(
            tender=tender,
            supplier_company_id=source_proposal.supplier_company_id,
            submitted_at=source_proposal.submitted_at,
            status_updated_at=timezone.now(),
        )
        new_values = []
        for source_value in source_proposal.position_values.all():
            target_position = position_map.get(int(source_value.tender_position_id))
            if not target_position:
                continue
            new_values.append(
                SalesTenderProposalPosition(
                    proposal=target_proposal,
                    tender_position=target_position,
                    price=source_value.price,
                    price_without_vat=source_value.price_without_vat,
                    criterion_values=source_value.criterion_values or {},
                )
            )
        if new_values:
            SalesTenderProposalPosition.objects.bulk_create(new_values)
        copied_company_ids.append(int(source_proposal.supplier_company_id))

    return {
        "copied_companies": copied_company_ids,
        "copied_count": len(copied_company_ids),
    }


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


def _can_user_delete_tender(*, user, tender, is_sales):
    if not _is_tender_author(user=user, tender=tender):
        return False
    stage = str(getattr(tender, "stage", "") or "").strip()
    if stage != TenderApprovalStageState.Stage.PREPARATION:
        return False
    if int(getattr(tender, "tour_number", 0) or 0) != 1:
        return False
    tender_id = int(getattr(tender, "id", 0) or 0)
    if tender_id <= 0:
        return False
    deletable_ids = _resolve_preparation_stage_deletable_ids(
        candidate_ids=[tender_id],
        is_sales=is_sales,
    )
    return tender_id in deletable_ids


def _ensure_user_can_delete_tender(*, user, tender, is_sales):
    if _can_user_delete_tender(user=user, tender=tender, is_sales=is_sales):
        return
    raise PermissionDenied(
        "Tender can be deleted only by author on round 1 in preparation stage "
        "before approval route starts."
    )


def _copy_tender_to_first_round(*, source_tender, actor, is_sales):
    tender_model = SalesTender if is_sales else ProcurementTender
    criteria_snapshot_model = SalesTenderCriterion if is_sales else ProcurementTenderCriterion
    position_model = SalesTenderPosition if is_sales else ProcurementTenderPosition

    with transaction.atomic():
        copied_tender = tender_model.objects.create(
            company=source_tender.company,
            parent=None,
            tour_number=1,
            name=source_tender.name,
            stage=TenderApprovalStageState.Stage.PREPARATION,
            category=source_tender.category,
            cpv_category=getattr(source_tender, "cpv_category", None),
            expense_article=source_tender.expense_article,
            estimated_budget=source_tender.estimated_budget,
            branch=source_tender.branch,
            department=source_tender.department,
            conduct_type=source_tender.conduct_type,
            auction_model=getattr(
                source_tender,
                "auction_model",
                tender_model.AuctionModel.CLASSIC_AUCTION,
            ),
            publication_type=source_tender.publication_type,
            currency=source_tender.currency,
            general_terms=source_tender.general_terms or "",
            invited_emails=getattr(source_tender, "invited_emails", []) or [],
            start_at=getattr(source_tender, "start_at", None),
            end_at=getattr(source_tender, "end_at", None),
            planned_start_at=getattr(source_tender, "planned_start_at", None),
            planned_end_at=getattr(source_tender, "planned_end_at", None),
            price_criterion_vat=source_tender.price_criterion_vat or "",
            price_criterion_vat_percent=source_tender.price_criterion_vat_percent,
            price_criterion_delivery=source_tender.price_criterion_delivery or "",
            approval_model=source_tender.approval_model,
            uses_position_warehouses=bool(
                getattr(source_tender, "uses_position_warehouses", False)
            ),
            created_by=actor,
        )
        copied_tender.cpv_categories.set(source_tender.cpv_categories.all())
        copied_tender.tender_criteria.set(source_tender.tender_criteria.all())
        copied_tender.tender_attributes.set(source_tender.tender_attributes.all())
        _sync_tender_invited_suppliers(
            tender=copied_tender,
            supplier_company_ids=list(
                source_tender.invited_supplier_links.values_list(
                    "supplier_company_id", flat=True
                )
            ),
            is_sales=is_sales,
        )

        criteria_to_create = []
        source_criteria_items = list(
            source_tender.criteria_items.select_related("reference_criterion").all()
        )
        if source_criteria_items:
            for criterion in source_criteria_items:
                options = criterion.options if isinstance(criterion.options, dict) else {}
                criteria_to_create.append(
                    criteria_snapshot_model(
                        tender=copied_tender,
                        reference_criterion=criterion.reference_criterion,
                        name=criterion.name,
                        type=criterion.type,
                        application=criterion.application,
                        is_required=bool(criterion.is_required),
                        options=pycopy.deepcopy(options),
                    )
                )
        else:
            for criterion in source_tender.tender_criteria.all():
                options = getattr(criterion, "options", {}) or {}
                if not isinstance(options, dict):
                    options = {}
                criteria_to_create.append(
                    criteria_snapshot_model(
                        tender=copied_tender,
                        reference_criterion=criterion,
                        name=criterion.name,
                        type=criterion.type,
                        application=getattr(
                            criterion,
                            "application",
                            TenderCriterion.Application.INDIVIDUAL,
                        ),
                        is_required=bool(getattr(criterion, "is_required", False)),
                        options=pycopy.deepcopy(options),
                    )
                )
        if criteria_to_create:
            criteria_snapshot_model.objects.bulk_create(criteria_to_create)

        source_positions = list(
            source_tender.positions.select_related("nomenclature", "warehouse").all()
        )
        positions_to_create = []
        for position in source_positions:
            attribute_values = (
                position.attribute_values
                if isinstance(position.attribute_values, dict)
                else {}
            )
            positions_to_create.append(
                position_model(
                    tender=copied_tender,
                    nomenclature=position.nomenclature,
                    name=position.name or "",
                    unit_name=position.unit_name or "",
                    quantity=position.quantity,
                    description=position.description or "",
                    warehouse=position.warehouse,
                    attribute_values=pycopy.deepcopy(attribute_values),
                    start_price=position.start_price,
                    min_bid_step=position.min_bid_step,
                    max_bid_step=position.max_bid_step,
                )
            )
        if positions_to_create:
            position_model.objects.bulk_create(positions_to_create)

        _ensure_stage_state_snapshot(
            tender=copied_tender,
            is_sales=is_sales,
            stage=TenderApprovalStageState.Stage.PREPARATION,
            rebuild=True,
        )
    return copied_tender


def _validate_preparation_readiness_before_publish(*, tender):
    has_positions = tender.positions.exists()
    uses_position_warehouses = bool(
        getattr(tender, "uses_position_warehouses", False)
    )
    vat_mode = str(getattr(tender, "price_criterion_vat", "") or "").strip()
    delivery_mode = str(getattr(tender, "price_criterion_delivery", "") or "").strip()
    vat_percent_raw = getattr(tender, "price_criterion_vat_percent", None)
    has_price_params = bool(vat_mode and delivery_mode)
    if has_price_params and vat_mode == "with_vat":
        try:
            vat_percent = Decimal(str(vat_percent_raw))
        except (InvalidOperation, TypeError, ValueError):
            vat_percent = None
        has_price_params = bool(
            vat_percent is not None and vat_percent > 0 and vat_percent <= 100
        )
    if not has_positions:
        raise DRFValidationError(
            {"detail": "Додайте хоча б одну позицію тендера перед погодженням."}
        )
    if uses_position_warehouses and tender.positions.filter(warehouse__isnull=True).exists():
        raise DRFValidationError(
            {
                "detail": (
                    "Оберіть склад для кожної позиції тендера, "
                    "оскільки використання складів увімкнене."
                )
            }
        )
    if not has_price_params:
        raise DRFValidationError(
            {
                "detail": (
                    "Налаштуйте параметри цінового критерію "
                    "(ПДВ, % ПДВ та Доставка) перед погодженням."
                )
            }
        )


def _to_decimal_or_none(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _calculate_price_without_vat(*, price, vat_mode, vat_percent):
    price_dec = _to_decimal_or_none(price)
    if price_dec is None:
        return None
    if vat_mode != "with_vat":
        return price_dec

    vat_percent_dec = _to_decimal_or_none(vat_percent)
    if vat_percent_dec is None or vat_percent_dec <= 0 or vat_percent_dec > 100:
        return None

    vat_rate = vat_percent_dec / Decimal("100")
    denominator = Decimal("1") + vat_rate
    if denominator <= 0:
        return None

    vat_part = (price_dec * vat_rate) / denominator
    return (price_dec - vat_part).quantize(Decimal("0.0001"))


def _recalculate_tender_position_values_without_vat(*, tender, is_sales):
    vat_mode = str(getattr(tender, "price_criterion_vat", "") or "").strip()
    vat_percent = getattr(tender, "price_criterion_vat_percent", None)

    proposal_position_model = (
        SalesTenderProposalPosition if is_sales else TenderProposalPosition
    )
    updates = []
    qs = proposal_position_model.objects.filter(proposal__tender=tender).only(
        "id", "price", "price_without_vat"
    )
    for row in qs.iterator(chunk_size=1000):
        computed = _calculate_price_without_vat(
            price=row.price,
            vat_mode=vat_mode,
            vat_percent=vat_percent,
        )
        if row.price_without_vat != computed:
            row.price_without_vat = computed
            updates.append(row)

    if updates:
        proposal_position_model.objects.bulk_update(
            updates,
            ["price_without_vat"],
            batch_size=1000,
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
                _notify_tender_author_stage_event(
                    tender=tender,
                    is_sales=is_sales,
                    event_type=Notification.Type.TENDER_COMPLETED,
                    title="Тендер завершено",
                    body='Тендер перейшов на етап "Завершено".',
                )
        else:
            _reject_active_stage_user(stage_state, active_step_user, comment=comment)
            if stage == TenderApprovalStageState.Stage.APPROVAL and tender.stage != "decision":
                tender.stage = "decision"
                tender.save(update_fields=["stage"])
                _recalculate_tender_position_values_without_vat(
                    tender=tender,
                    is_sales=is_sales,
                )

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
    if action_type == "approved":
        _notify_tender_author_stage_event(
            tender=tender,
            is_sales=is_sales,
            event_type=Notification.Type.TENDER_COMPLETED,
            title="Тендер завершено",
            body='Тендер перейшов на етап "Завершено".',
        )
    if action_type != "approved":
        _recalculate_tender_position_values_without_vat(
            tender=tender,
            is_sales=is_sales,
        )


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
            missing.append(f"{criterion['name']} (загальний)")

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
                    or f"позиція #{getattr(pv, 'tender_position_id', '?')}"
                )
                missing.append(f"{criterion['name']} ({pos_name})")

    if not missing:
        return None

    return {
        "detail": "Неможливо подати пропозицію. Заповніть обов'язкові критерії.",
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
        return "Для позиції не налаштовано стартову ціну та кроки ставки."
    if start_price <= 0 or min_step <= 0 or max_step <= 0 or min_step > max_step:
        return "Невірні параметри ставки позиції: значення мають бути > 0, а мінімальний крок не більший за максимальний."
    if new_price_dec is None:
        return "Вкажіть коректну цінову пропозицію."

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
            "Ціна поза допустимим діапазоном "
            f"[{_format_decimal_for_error(first_point)}; {_format_decimal_for_error(second_point)}]."
        )
    return None


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT login endpoint.
    """

    @extend_schema(
        summary="Вхід в систему",
        description="Отримати JWT токени (access + refresh) для автентифікації.",
        responses={200: {"description": "Токени успішно отримано"}, 401: {"description": "Невірні облікові дані"}},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(
    summary="Реєстрація - Крок 1",
    description="Створення користувача. Якщо email вже існує, повертає помилку.",
    request=UserRegistrationStep1Serializer,
    responses={
        201: UserSerializer,
        400: OpenApiResponse(description="Помилка валідації"),
    },
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def registration_step1(request):
    """Step 1: Create user."""
    duplicate_email_message = (
        "Користувач з таким email вже існує. У разі якщо ви не завершили реєстарцію, можете продовжити при вході."
    )
    serializer = UserRegistrationStep1Serializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = serializer.save()
    except IntegrityError:
        return Response({"email": [duplicate_email_message]}, status=status.HTTP_400_BAD_REQUEST)

    user.registration_step = 2
    user.save(update_fields=["registration_step"])
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Довідник країн реєстрації",
    description="Список значень number_name та number_code з таблиці countrybusinessnumber.",
    responses={200: CountryBusinessNumberSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def registration_country_business_numbers(request):
    qs = CountryBusinessNumber.objects.all().order_by("number_name", "number_code")
    serializer = CountryBusinessNumberSerializer(qs, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="Реєстрація - перевірка компанії за кодом",
    description=(
        "Повертає інформацію про компанію за кодом (ЄДРПОУ/ІПН/інший код). "
        "Якщо компанія знайдена і має зареєстрованих користувачів, "
        "реєстрація має виконуватись як приєднання до існуючої компанії."
    ),
    parameters=[
        OpenApiParameter(
            name="edrpou",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Код компанії для перевірки.",
        )
    ],
    responses={200: RegistrationCompanyLookupSerializer},
)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def registration_company_lookup(request):
    code = (request.query_params.get("edrpou") or "").strip()
    if not code:
        return Response({"edrpou": "Вкажіть код компанії."}, status=status.HTTP_400_BAD_REQUEST)

    company = (
        Company.objects.filter(edrpou=code, status=Company.Status.ACTIVE)
        .prefetch_related("cpv_categories")
        .first()
    )
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
    summary="Реєстрація - Крок 2 (Нова компанія)",
    description="Створення нової компанії та призначення користувача адміністратором.",
    request=CompanyRegistrationStep2Serializer,
    responses={
        201: CompanySerializer,
        400: OpenApiResponse(description="Помилка валідації"),
    },
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def registration_step2_new_company(request):
    """Крок 2: створення нової компанії та призначення користувача адміністратором."""
    serializer = CompanyRegistrationStep2Serializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    payload = serializer.validated_data
    user_id = payload["user_id"]
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"user_id": "Користувача не знайдено."}, status=status.HTTP_400_BAD_REQUEST)

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
            company=company, name="Адміністратор", defaults={"is_system": True}
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
    summary="Реєстрація - Крок 2 (Існуюча компанія)",
    description="Запит на приєднання до існуючої компанії. Створює сповіщення адміністратору компанії.",
    request=ExistingCompanyStep2Serializer,
    responses={
        201: CompanyUserSerializer,
        400: OpenApiResponse(description="Помилка валідації"),
    },
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def registration_step2_existing_company(request):
    """Крок 2: приєднання до існуючої компанії за кодом ЄДРПОУ."""
    serializer = ExistingCompanyStep2Serializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user_id = serializer.validated_data["user_id"]
    edrpou = serializer.validated_data["edrpou"]
    new_name = (serializer.validated_data.get("name") or "").strip()

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"user_id": "Користувача не знайдено."}, status=status.HTTP_400_BAD_REQUEST)

    company = Company.objects.filter(edrpou=edrpou, status=Company.Status.ACTIVE).first()
    if not company:
        return Response({"edrpou": "Компанію з таким кодом не знайдено."}, status=status.HTTP_400_BAD_REQUEST)

    if CompanyUser.objects.filter(user=user, company=company).exists():
        return Response(
            {"non_field_errors": "Користувач вже має зв'язок із цією компанією."}, status=status.HTTP_400_BAD_REQUEST
        )

    has_approved = CompanyUser.objects.filter(company=company, status=CompanyUser.Status.APPROVED).exists()

    with transaction.atomic():
        if new_name and not has_approved:
            company.name = new_name
            company.save(update_fields=["name", "updated_at"])

        default_role, _ = Role.objects.get_or_create(
            company=company, name="Користувач", defaults={"is_system": True}
        )
        admin_role, _ = Role.objects.get_or_create(
            company=company, name="Адміністратор", defaults={"is_system": True}
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
                company=company, status=CompanyUser.Status.APPROVED, role__name="Адміністратор"
            )
            for admin_membership in admin_memberships:
                Notification.objects.create(
                    user=admin_membership.user,
                    type=Notification.Type.MEMBERSHIP_REQUEST,
                    title=f"Запит на приєднання від {user.get_full_name() or user.email}",
                    body=f"Користувач {user.get_full_name() or user.email} ({user.email}) хоче приєднатися до компанії {company.name}.",
                    meta={"membership_id": membership.id, "user_id": user.id, "company_id": company.id},
                )
        user.registration_step = 3
        user.save(update_fields=["registration_step"])

    return Response(CompanyUserSerializer(membership).data, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Реєстрація - Крок 3 (CPV-категорії компанії)",
    description=(
        "Закріплення CPV-категорій за компанією під час реєстрації.\n"
        "- Якщо це перший підтверджений користувач компанії - список категорій перезаписується.\n"
        "- Якщо підтверджених користувачів вже більше одного - існуючі категорії не видаляються, "
        "додаються лише нові (об'єднання списків)."
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
                    "description": "Масив ID CPV-кодів для закріплення за компанією",
                },
            },
            "required": ["user_id", "company_id"],
        }
    },
    responses={
        200: CompanyCpvSerializer,
        400: OpenApiResponse(description="Помилка валідації"),
    },
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def registration_step3_company_cpvs(request):
    """Крок 3: напрямки діяльності та CPV-категорії."""
    try:
        user_id = int(request.data.get("user_id"))
    except (TypeError, ValueError):
        return Response({"user_id": "Вкажіть коректний ID користувача."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        company_id = int(request.data.get("company_id"))
    except (TypeError, ValueError):
        return Response({"company_id": "Вкажіть коректний ID компанії."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"user_id": "Користувача не знайдено."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        company = Company.objects.get(id=company_id, status=Company.Status.ACTIVE)
    except Company.DoesNotExist:
        return Response({"company_id": "Компанію не знайдено або вона неактивна."}, status=status.HTTP_400_BAD_REQUEST)

    membership = (
        CompanyUser.objects.filter(user=user, company=company)
        .only("id", "status")
        .order_by("-created_at")
        .first()
    )
    if not membership:
        return Response(
            {"non_field_errors": "Користувач не має підтвердженого зв'язку з цією компанією."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if membership.status != CompanyUser.Status.APPROVED:
        if user.registration_step != 4:
            user.registration_step = 4
            user.save(update_fields=["registration_step"])
        serializer = CompanyCpvSerializer(company)
        return Response(serializer.data, status=status.HTTP_200_OK)

    payload = CompanyRegistrationStep3Serializer(data=request.data)
    if not payload.is_valid():
        return Response(payload.errors, status=status.HTTP_400_BAD_REQUEST)

    cpv_ids = payload.validated_data.get("cpv_ids") or []
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
        summary="Список активних компаній",
        description="Отримати список активних компаній для вибору при реєстрації.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Деталі компанії",
        description="Отримати детальну інформацію про компанію.",
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Створити компанію (контрагента)",
        description="Додати компанію вручну (код та назва). Для списку контрагентів.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def members(self, request, pk=None):
        """Список користувачів (агентів) компанії."""
        company = self.get_object()
        memberships = CompanyUser.objects.filter(
            company=company,
            status=CompanyUser.Status.APPROVED,
        ).select_related("user", "role").order_by("-created_at")
        serializer = CompanyUserSerializer(memberships, many=True)
        return Response(serializer.data)


@extend_schema(
    summary="CPV-категорії поточної компанії",
    description=(
        "Отримати або оновити список CPV-категорій, закріплених за компанією поточного користувача.\n"
        "Компанія визначається за першим підтвердженим членством користувача."
    ),
    responses={200: CompanyCpvSerializer},
)
@api_view(["GET", "PUT"])
@permission_classes([permissions.IsAuthenticated])
def company_current_cpvs(request):
    """
    GET: Повертає компанію поточного користувача та її CPV-категорії.
    PUT: Оновлює список CPV-категорій компанії (повна заміна списку).
    """
    user = request.user
    membership = (
        CompanyUser.objects.filter(user=user, status=CompanyUser.Status.APPROVED)
        .select_related("company")
        .first()
    )
    if not membership or not membership.company:
        return Response(
            {"detail": "Користувач не має підтвердженого членства ні в одній компанії."},
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
    Список контрагентів компанії: додані вручну та (згодом) ті, хто підтвердив участь у тендерах.
    Додавання: або supplier_company_id, або edrpou (якщо компанія є - лише зв'язок; якщо немає - name обов'язкова, створюється компанія).
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
            raise permissions.exceptions.PermissionDenied("Немає доступу до жодної компанії.")
        owner_id = owner_ids[0]

        serializer = AddCompanySupplierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        supplier_id = data.get("supplier_company_id")
        if supplier_id is not None:
            if supplier_id == owner_id:
                raise DRFValidationError({"supplier_company_id": "Не можна додати власну компанію як контрагента."})
            if not Company.objects.filter(id=supplier_id, status=Company.Status.ACTIVE).exists():
                raise DRFValidationError({"supplier_company_id": "Компанію не знайдено або вона неактивна."})
            if CompanySupplier.objects.filter(owner_company_id=owner_id, supplier_company_id=supplier_id).exists():
                raise DRFValidationError({"supplier_company_id": "Ця компанія вже є у списку контрагентів."})
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
                raise DRFValidationError({"edrpou": "Ця компанія вже є у списку контрагентів."})
            if company.id == owner_id:
                raise DRFValidationError({"edrpou": "Не можна додати власну компанію як контрагента."})
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
            raise DRFValidationError({"name": "Компанії з таким кодом немає. Введіть назву для створення контрагента (попередня назва)."})
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

    @extend_schema(summary="Додати контрагента", request=AddCompanySupplierSerializer)
    def create(self, request, *args, **kwargs):
        owner_ids = list(_user_owner_company_ids(request))
        if not owner_ids:
            raise permissions.exceptions.PermissionDenied("Немає доступу до жодної компанії.")
        owner_id = owner_ids[0]

        serializer = AddCompanySupplierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        supplier_id = data.get("supplier_company_id")
        if supplier_id is not None:
            if supplier_id == owner_id:
                raise DRFValidationError({"supplier_company_id": "Не можна додати власну компанію як контрагента."})
            if not Company.objects.filter(id=supplier_id, status=Company.Status.ACTIVE).exists():
                raise DRFValidationError({"supplier_company_id": "Компанію не знайдено або вона неактивна."})
            if CompanySupplier.objects.filter(owner_company_id=owner_id, supplier_company_id=supplier_id).exists():
                raise DRFValidationError({"supplier_company_id": "Ця компанія вже є у списку контрагентів."})
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
                raise DRFValidationError({"edrpou": "Ця компанія вже є у списку контрагентів."})
            if company.id == owner_id:
                raise DRFValidationError({"edrpou": "Не можна додати власну компанію як контрагента."})
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
            raise DRFValidationError({"name": "Компанії з таким кодом немає. Введіть назву для створення контрагента (попередня назва)."})
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

    @extend_schema(summary="Список контрагентів", description="Контрагенти: додані вручну та з участі в тендерах.")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary="Тендери контрагента", description="Тендери компанії-власника, де контрагент подав пропозицію і вже завершено етап прийому пропозицій.")
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

    В рамках поточного MVP всі підтверджені учасники компанії мають однакові права
    доступу в межах своїх компаній (без поділу на адміністраторів та користувачів).
    """

    serializer_class = CompanyUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Повертаємо всі членства компаній, в яких поточний користувач має
        підтверджений статус. Ролі не враховуються.
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
        summary="Список членів компанії",
        description="Отримати список користувачів компаній, в яких поточний користувач має підтверджене членство.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Деталі членства",
        description="Отримати детальну інформацію про членство.",
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Додати користувача до компанії",
        description="Додати користувача до компанії вручну (будь-який підтверджений учасник компанії).",
        request=CompanyUserSerializer,
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Підтвердити членство",
        description="Підтвердити запит на приєднання до компанії.",
        responses={200: CompanyUserSerializer, 400: OpenApiResponse(description="Помилка")},
    )
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve membership request."""
        membership = self.get_object()
        if membership.status != CompanyUser.Status.PENDING:
            return Response({"error": "Можна підтвердити тільки запити зі статусом 'Очікує'."}, status=400)

        membership.status = CompanyUser.Status.APPROVED
        membership.save()

        # Notify user about approval
        Notification.objects.create(
            user=membership.user,
            type=Notification.Type.MEMBERSHIP_REQUEST,
            title=f"Ваш запит підтверджено",
            body=f"Ваш запит на приєднання до компанії {membership.company.name} було підтверджено.",
            meta={"membership_id": membership.id, "company_id": membership.company.id},
        )

        return Response(CompanyUserSerializer(membership).data)

    @extend_schema(
        summary="Відхилити членство",
        description="Відхилити запит на приєднання до компанії.",
        responses={200: CompanyUserSerializer, 400: OpenApiResponse(description="Помилка")},
    )
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject membership request."""
        membership = self.get_object()
        if membership.status != CompanyUser.Status.PENDING:
            return Response({"error": "Можна відхилити тільки запити зі статусом 'Очікує'."}, status=400)

        membership.status = CompanyUser.Status.REJECTED
        membership.save()

        # Notify user about rejection
        Notification.objects.create(
            user=membership.user,
            type=Notification.Type.MEMBERSHIP_REQUEST,
            title=f"Ваш запит відхилено",
            body=f"Ваш запит на приєднання до компанії {membership.company.name} було відхилено.",
            meta={"membership_id": membership.id, "company_id": membership.company.id},
        )

        return Response(CompanyUserSerializer(membership).data)

    @extend_schema(
        summary="Створити нового користувача компанії",
        description="Створити нового користувача (User) і одразу додати його до компанії зі статусом 'Підтверджено' (будь-який підтверджений учасник компанії).",
        request=UserRegistrationStep1Serializer,
        responses={201: CompanyUserSerializer, 400: OpenApiResponse(description="Помилка валідації")},
    )
    @action(detail=False, methods=["post"], url_path="create-user")
    def create_user(self, request):
        """
        Створити нового користувача та прив'язати його до першої компанії,
        в якій поточний користувач має підтверджене членство.
        """
        user = request.user

        # Знаходимо компанії, де користувач має підтверджене членство
        memberships = CompanyUser.objects.filter(
            user=user,
            status=CompanyUser.Status.APPROVED,
        )
        if not memberships.exists() and not user.is_superuser:
            return Response(
                {"error": "Користувач не має підтвердженого членства ні в одній компанії."},
                status=status.HTTP_403_FORBIDDEN,
            )

        company = memberships.first().company if memberships.exists() else None

        # Створюємо користувача через існуючий серіалізатор реєстрації (крок 1)
        serializer = UserRegistrationStep1Serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_user = serializer.save()

        # Отримуємо / створюємо роль "Користувач" для компанії
        default_role, _ = Role.objects.get_or_create(
            company=company, name="Користувач", defaults={"is_system": True}
        )

        membership = CompanyUser.objects.create(
            user=new_user,
            company=company,
            role=default_role,
            status=CompanyUser.Status.APPROVED,
        )

        return Response(CompanyUserSerializer(membership).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Оновити дані користувача компанії",
        description="Адміністратор може відредагувати ім'я, прізвище, email, телефон та пароль користувача компанії.",
        responses={200: CompanyUserSerializer, 400: OpenApiResponse(description="Помилка валідації")},
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
            # Перевірка на унікальність email
            if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                return Response({"email": ["Користувач з таким email вже існує."]}, status=status.HTTP_400_BAD_REQUEST)
            user.email = email
        if phone is not None:
            user.phone = phone

        if password is not None and password != "":
            if password != password_confirm:
                return Response(
                    {"password_confirm": ["Паролі не співпадають."]},
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
        summary="Деактивувати користувача компанії",
        description="Адміністратор може вимкнути активність користувача (is_active = False), після чого він не зможе входити в систему.",
        responses={200: CompanyUserSerializer},
    )
    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        membership = self.get_object()
        user = membership.user
        if not user.is_active:
            return Response({"detail": "Користувач вже деактивований."}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(CompanyUserSerializer(membership).data)

    @extend_schema(
        summary="Активувати користувача компанії",
        description="Адміністратор може увімкнути активність користувача (is_active = True), після чого він зможе входити в систему.",
        responses={200: CompanyUserSerializer},
    )
    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        membership = self.get_object()
        user = membership.user
        if user.is_active:
            return Response({"detail": "Користувач вже активований."}, status=status.HTTP_400_BAD_REQUEST)
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
            user=user, status=CompanyUser.Status.APPROVED, role__name="Адміністратор"
        ).values_list("company_id", flat=True)
        return Role.objects.filter(company_id__in=admin_companies)

    @extend_schema(
        summary="Список ролей",
        description="Отримати список ролей компанії (тільки для адміністраторів).",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Створити роль",
        description="Створити нову роль для компанії.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Оновити роль",
        description="Оновити роль та її права доступу.",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Видалити роль",
        description="Видалити роль (системні ролі видалити неможливо).",
    )
    def destroy(self, request, *args, **kwargs):
        role = self.get_object()
        if role.is_system:
            return Response({"error": "Системні ролі не можна видаляти."}, status=400)
        return super().destroy(request, *args, **kwargs)


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Permission catalog (read-only).
    """

    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Список прав доступу",
        description="Отримати каталог доступних прав доступу для призначення ролям.",
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
        summary="Список сповіщень",
        description="Отримати список сповіщень поточного користувача.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Позначити як прочитане",
        description="Позначити сповіщення як прочитане.",
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
        summary="Позначити всі як прочитані",
        description="Позначити всі сповіщення користувача як прочитані.",
        responses={200: {"description": "Кількість оновлених сповіщень"}},
    )
    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"count": count})

    @extend_schema(
        summary="Видалити сповіщення",
        description="Видалити одне сповіщення поточного користувача.",
        responses={204: None},
    )
    @action(detail=True, methods=["delete"], url_path="remove")
    def remove(self, request, pk=None):
        notification = self.get_object()
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary="Поточний користувач",
    description="Отримати або оновити профіль поточного користувача.",
    responses={200: MeSerializer},
)
@api_view(["GET", "PATCH"])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    """GET: поточний користувач, членства, права. PATCH: оновлення профілю (first_name, last_name, middle_name, phone)."""
    memberships_qs = (
        request.user.memberships.select_related("user", "company", "role")
        .prefetch_related("role__permissions")
        .all()
    )
    if request.method == "PATCH":
        serializer = ProfileUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        for key, value in serializer.validated_data.items():
            setattr(user, key, value)
        user.save(update_fields=list(serializer.validated_data.keys()))
        response_serializer = MeSerializer(
            {"user": user, "memberships": memberships_qs, "permissions": []},
            context={"request": request},
        )
        return Response(response_serializer.data)
    serializer = MeSerializer(
        {"user": request.user, "memberships": memberships_qs, "permissions": []},
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
    summary="Завантажити аватар",
    description="Завантажити фото для аватара поточного користувача (JPEG, PNG, GIF, WebP; макс. 5 МБ).",
    request={"multipart/form-data": {"type": "object", "properties": {"avatar": {"type": "string", "format": "binary"}}}},
    responses={200: {"description": "URL нового аватара"}},
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def me_avatar_upload(request):
    """Upload avatar for current user."""
    file = request.FILES.get("avatar") or request.FILES.get("file")
    if not file:
        return Response({"detail": "Файл не надіслано. Використовуйте поле avatar або file."}, status=status.HTTP_400_BAD_REQUEST)
    if not _is_allowed_avatar_content_type(getattr(file, "content_type", "")):
        return Response(
            {"detail": "Дозволені формати: JPEG, PNG, GIF, WebP."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if file.size > AVATAR_MAX_SIZE_BYTES:
        return Response({"detail": "Розмір файлу не повинен перевищувати 5 МБ."}, status=status.HTTP_400_BAD_REQUEST)
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
    summary="Запит на відновлення пароля",
    description="Надіслати запит на відновлення пароля (email з посиланням).",
    request=PasswordResetRequestSerializer,
    responses={200: {"description": "Якщо email існує, надіслано лист"}},
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def password_reset_request(request):
    """Request password reset. Returns generic response to avoid email enumeration."""
    serializer = PasswordResetRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data["email"]
    response_data = {"message": "Якщо email існує, надіслано лист з інструкціями."}

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
    summary="Підтвердження відновлення пароля",
    description="Підтвердити відновлення пароля за токеном.",
    request=PasswordResetConfirmSerializer,
    responses={200: {"description": "Пароль успішно змінено"}},
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
            {"token": "Невірний або прострочений токен."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not default_token_generator.check_token(user, token):
        return Response(
            {"token": "Невірний або прострочений токен."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(new_password)
    user.save(update_fields=["password"])
    return Response({"message": "Пароль успішно змінено."}, status=status.HTTP_200_OK)


@extend_schema(
    summary="Зміна пароля",
    description="Змінити пароль для автентифікованого користувача.",
    request=PasswordChangeSerializer,
    responses={200: {"description": "Пароль успішно змінено"}},
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def password_change(request):
    """Change password for authenticated user."""
    serializer = PasswordChangeSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({"old_password": "Невірний поточний пароль."}, status=400)
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"message": "Пароль успішно змінено."})
    return Response(serializer.errors, status=400)


class BranchViewSet(ReferenceActivityMixin, viewsets.ModelViewSet):
    """
    Branch management (tree structure).
    """

    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter by user's companies and optionally by user's assignments."""
        user = self.request.user
        self._allowed_tree_ids = None
        self._directly_assigned_ids = None
        if user.is_superuser:
            queryset = Branch.objects.all()
        else:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            queryset = Branch.objects.filter(company_id__in=user_companies)

        if _is_truthy_query_param(self.request.query_params.get("assigned_only")):
            assigned_ids = set(queryset.filter(users__user=user).values_list("id", flat=True))
            self._directly_assigned_ids = assigned_ids
            if not assigned_ids:
                self._allowed_tree_ids = set()
                return queryset.none().select_related("parent", "company")
            allowed_ids = _expand_tree_ids_with_ancestors(Branch, assigned_ids)
            self._allowed_tree_ids = allowed_ids
            queryset = queryset.filter(id__in=allowed_ids).distinct()

        queryset = _apply_is_active_filter(queryset, self.request)
        return queryset.select_related("parent", "company")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if getattr(self, "_allowed_tree_ids", None) is not None:
            context["allowed_ids"] = self._allowed_tree_ids
        if getattr(self, "_directly_assigned_ids", None) is not None:
            context["directly_assigned_ids"] = self._directly_assigned_ids
        return context

    @extend_schema(
        summary="Список філіалів",
        description="Отримати дерево філіалів компанії (тільки кореневі елементи, діти вкладено).",
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not _is_flat_tree_request(request):
            queryset = queryset.filter(parent__isnull=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Створити філіал",
        description="Створити новий філіал.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Оновити філіал",
        description="Оновити інформацію про філіал.",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Видалити філіал",
        description="Видалити філіал (також видаляться дочірні філіали та підрозділи).",
    )
    def _get_delete_blockers(self, obj):
        blockers = []
        if obj.children.exists():
            blockers.append("є дочірні філіали")
        if obj.departments.exists():
            blockers.append("є підрозділи, прив'язані до філіалу")
        if obj.procurement_tenders.exists() or obj.sales_tenders.exists():
            blockers.append("філіал використовується у тендерах")
        return blockers


class DepartmentViewSet(ReferenceActivityMixin, viewsets.ModelViewSet):
    """
    Department management (tree structure, belongs to branch).
    """

    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Повертає підрозділи, обмежені компаніями поточного користувача.

        - Для superuser: всі підрозділи.
        - Для звичайного користувача: лише підрозділи філіалів компаній,
          де в нього є підтверджене членство.
        - Додатково можна обмежити результат параметром branch_id.
        """
        user = self.request.user
        self._allowed_tree_ids = None
        self._directly_assigned_ids = None
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

        branch_id = self.request.query_params.get("branch_id")
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        if not user.is_superuser and _is_truthy_query_param(
            self.request.query_params.get("assigned_only")
        ):
            assigned_ids = set(queryset.filter(users__user=user).values_list("id", flat=True))
            self._directly_assigned_ids = assigned_ids
            if not assigned_ids:
                self._allowed_tree_ids = set()
                queryset = queryset.none()
            else:
                allowed_ids = _expand_tree_ids_with_ancestors(Department, assigned_ids)
                self._allowed_tree_ids = allowed_ids
                queryset = queryset.filter(id__in=allowed_ids).distinct()

        queryset = _apply_is_active_filter(queryset, self.request)
        return queryset.select_related("parent", "branch")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if getattr(self, "_allowed_tree_ids", None) is not None:
            context["allowed_ids"] = self._allowed_tree_ids
        if getattr(self, "_directly_assigned_ids", None) is not None:
            context["directly_assigned_ids"] = self._directly_assigned_ids
        return context

    @extend_schema(
        summary="Список підрозділів",
        description="Отримати дерево підрозділів для філіалу (потрібен параметр branch_id).",
        parameters=[
            OpenApiParameter(name="branch_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True)
        ],
    )
    def list(self, request, *args, **kwargs):
        branch_id = request.query_params.get("branch_id")
        if not branch_id and not _is_truthy_query_param(request.query_params.get("assigned_only")):
            return Response({"error": "Параметр branch_id обов'язковий"}, status=400)
        # get_queryset вже відфільтрує за branch_id, тут лише беремо корені
        queryset = self.get_queryset()
        if not _is_flat_tree_request(request):
            queryset = queryset.filter(parent__isnull=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Створити підрозділ",
        description="Створити новий підрозділ.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Оновити підрозділ",
        description="Оновити інформацію про підрозділ.",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Видалити підрозділ",
        description="Видалити підрозділ (також видаляться дочірні підрозділи).",
    )
    def _get_delete_blockers(self, obj):
        blockers = []
        if obj.children.exists():
            blockers.append("є дочірні підрозділи")
        if obj.procurement_tenders.exists() or obj.sales_tenders.exists():
            blockers.append("підрозділ використовується у тендерах")
        return blockers


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
        summary="Список користувачів філіалу",
        description="Отримати список користувачів філіалу (потрібен параметр branch_id).",
        parameters=[
            OpenApiParameter(name="branch_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True)
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Додати користувачів до філіалу",
        description="Додати одного або кілька користувачів до філіалу (масив user_ids).",
    )
    def create(self, request, *args, **kwargs):
        branch_id = request.data.get("branch")
        user_ids = request.data.get("user_ids", [])
        if not isinstance(user_ids, list):
            return Response({"error": "user_ids повинен бути масивом"}, status=400)

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
        summary="Скопіювати користувачів у батьківський філіал",
        description="Копіює користувачів поточного філіалу в його батьківський філіал без дублювання.",
    )
    @action(detail=False, methods=["post"], url_path="copy-parent")
    def copy_parent(self, request):
        branch_id = request.data.get("branch")
        if not branch_id:
            return Response({"error": "Параметр branch обов'язковий"}, status=400)

        user = request.user
        if user.is_superuser:
            source = Branch.objects.filter(id=branch_id).first()
        else:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            source = Branch.objects.filter(id=branch_id, company_id__in=user_companies).first()
        if source is None:
            return Response({"error": "Філіал не знайдено"}, status=404)

        result = _copy_tree_user_assignments(
            source_obj=source,
            target_ids=[source.parent_id] if source.parent_id else [],
            assignment_model=BranchUser,
            relation_field="branch",
        )
        return Response(result)

    @extend_schema(
        summary="Скопіювати користувачів у дочірні філіали",
        description="Копіює користувачів поточного філіалу в усі дочірні філіали без дублювання.",
    )
    @action(detail=False, methods=["post"], url_path="copy-descendants")
    def copy_descendants(self, request):
        branch_id = request.data.get("branch")
        if not branch_id:
            return Response({"error": "Параметр branch обов'язковий"}, status=400)

        user = request.user
        if user.is_superuser:
            source = Branch.objects.filter(id=branch_id).first()
        else:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            source = Branch.objects.filter(id=branch_id, company_id__in=user_companies).first()
        if source is None:
            return Response({"error": "Філіал не знайдено"}, status=404)

        target_ids = _expand_tree_ids_with_descendants(Branch, {source.id}) - {source.id}
        result = _copy_tree_user_assignments(
            source_obj=source,
            target_ids=target_ids,
            assignment_model=BranchUser,
            relation_field="branch",
        )
        return Response(result)

    @extend_schema(
        summary="Видалити користувача з філіалу",
        description="Видалити користувача з філіалу.",
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
        summary="Список користувачів підрозділу",
        description="Отримати список користувачів підрозділу (потрібен параметр department_id).",
        parameters=[
            OpenApiParameter(name="department_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True)
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Додати користувачів до підрозділу",
        description="Додати одного або кілька користувачів до підрозділу (масив user_ids).",
    )
    def create(self, request, *args, **kwargs):
        department_id = request.data.get("department")
        user_ids = request.data.get("user_ids", [])
        if not isinstance(user_ids, list):
            return Response({"error": "user_ids повинен бути масивом"}, status=400)

        created = []
        assigned_user_ids = []
        for user_id in user_ids:
            serializer = self.get_serializer(data={"department": department_id, "user_id": user_id})
            if serializer.is_valid():
                assigned_user_ids.append(int(user_id))
                instance, created_flag = DepartmentUser.objects.get_or_create(
                    department_id=department_id, user_id=user_id
                )
                if created_flag:
                    created.append(DepartmentUserSerializer(instance).data)
        _ensure_branch_users_for_department_assignments(
            department_ids=[department_id],
            user_ids=assigned_user_ids,
        )
        return Response(created, status=201)

    @extend_schema(
        summary="Скопіювати користувачів у батьківський підрозділ",
        description="Копіює користувачів поточного підрозділу в його батьківський підрозділ без дублювання.",
    )
    @action(detail=False, methods=["post"], url_path="copy-parent")
    def copy_parent(self, request):
        department_id = request.data.get("department")
        if not department_id:
            return Response({"error": "Параметр department обов'язковий"}, status=400)

        user = request.user
        if user.is_superuser:
            source = Department.objects.filter(id=department_id).first()
        else:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            source = Department.objects.filter(
                id=department_id, branch__company_id__in=user_companies
            ).first()
        if source is None:
            return Response({"error": "Підрозділ не знайдено"}, status=404)

        result = _copy_tree_user_assignments(
            source_obj=source,
            target_ids=[source.parent_id] if source.parent_id else [],
            assignment_model=DepartmentUser,
            relation_field="department",
        )
        _ensure_branch_users_for_department_assignments(
            department_ids=result.get("target_ids", []),
            user_ids=result.get("source_user_ids", []),
        )
        return Response(result)

    @extend_schema(
        summary="Скопіювати користувачів у дочірні підрозділи",
        description="Копіює користувачів поточного підрозділу в усі дочірні підрозділи без дублювання.",
    )
    @action(detail=False, methods=["post"], url_path="copy-descendants")
    def copy_descendants(self, request):
        department_id = request.data.get("department")
        if not department_id:
            return Response({"error": "Параметр department обов'язковий"}, status=400)

        user = request.user
        if user.is_superuser:
            source = Department.objects.filter(id=department_id).first()
        else:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            source = Department.objects.filter(
                id=department_id, branch__company_id__in=user_companies
            ).first()
        if source is None:
            return Response({"error": "Підрозділ не знайдено"}, status=404)

        target_ids = _expand_tree_ids_with_descendants(Department, {source.id}) - {source.id}
        result = _copy_tree_user_assignments(
            source_obj=source,
            target_ids=target_ids,
            assignment_model=DepartmentUser,
            relation_field="department",
        )
        _ensure_branch_users_for_department_assignments(
            department_ids=result.get("target_ids", []),
            user_ids=result.get("source_user_ids", []),
        )
        return Response(result)

    @extend_schema(
        summary="Видалити користувача з підрозділу",
        description="Видалити користувача з підрозділу.",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Масово видалити користувачів з підрозділу",
        description="Видалити одного або кількох користувачів з підрозділу (масив user_ids).",
    )
    @action(detail=False, methods=["post"], url_path="bulk-delete")
    def bulk_delete(self, request):
        department_id = request.data.get("department")
        user_ids = request.data.get("user_ids", [])
        if not department_id:
            return Response({"error": "Параметр department обов'язковий"}, status=400)
        if not isinstance(user_ids, list):
            return Response({"error": "user_ids повинен бути масивом"}, status=400)

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


class CategoryViewSet(ReferenceActivityMixin, viewsets.ModelViewSet):
    """
    Category management (company-scoped flat list).
    """

    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter by user's companies."""
        user = self.request.user
        self._allowed_tree_ids = None
        self._directly_assigned_ids = None
        if user.is_superuser:
            queryset = Category.objects.all()
        else:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            queryset = Category.objects.filter(company_id__in=user_companies)

        if _is_truthy_query_param(self.request.query_params.get("assigned_only")):
            assigned_ids = set(queryset.filter(users__user=user).values_list("id", flat=True))
            self._directly_assigned_ids = assigned_ids
            if not assigned_ids:
                self._allowed_tree_ids = set()
                return queryset.none().select_related("parent", "company")
            allowed_ids = _expand_tree_ids_with_ancestors(Category, assigned_ids)
            self._allowed_tree_ids = allowed_ids
            queryset = queryset.filter(id__in=allowed_ids).distinct()

        queryset = _apply_is_active_filter(queryset, self.request)
        return queryset.select_related("parent", "company")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if getattr(self, "_allowed_tree_ids", None) is not None:
            context["allowed_ids"] = self._allowed_tree_ids
        if getattr(self, "_directly_assigned_ids", None) is not None:
            context["directly_assigned_ids"] = self._directly_assigned_ids
        return context

    @extend_schema(
        summary="Список категорій",
        description="Отримати дерево категорій компанії (тільки кореневі елементи, діти вкладено).",
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not _is_flat_tree_request(request):
            queryset = queryset.filter(parent__isnull=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Створити категорію",
        description="Створити нову категорію.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Оновити категорію",
        description="Оновити інформацію про категорію.",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Видалити категорію",
        description="Видалити категорію.",
    )
    def _get_delete_blockers(self, obj):
        blockers = []
        if obj.children.exists():
            blockers.append("є дочірні категорії")
        if obj.procurement_tenders.exists() or obj.sales_tenders.exists():
            blockers.append("категорія використовується у тендерах")
        if obj.nomenclatures.exists():
            blockers.append("категорія використовується у номенклатурі")
        if obj.tender_attributes.exists():
            blockers.append("категорія використовується в атрибутах тендера")
        if obj.approval_models.exists():
            blockers.append("категорія використовується в моделях погодження")
        return blockers


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
        summary="Список користувачів категорії",
        description="Отримати список користувачів категорії (потрібен параметр category_id).",
        parameters=[
            OpenApiParameter(name="category_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True)
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Додати користувачів до категорії",
        description="Додати одного або кілька користувачів до категорії (масив user_ids).",
    )
    def create(self, request, *args, **kwargs):
        category_id = request.data.get("category")
        user_ids = request.data.get("user_ids", [])
        if not isinstance(user_ids, list):
            return Response({"error": "user_ids повинен бути масивом"}, status=400)

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
        summary="Скопіювати користувачів у батьківську категорію",
        description="Копіює користувачів поточної категорії в її батьківську категорію без дублювання.",
    )
    @action(detail=False, methods=["post"], url_path="copy-parent")
    def copy_parent(self, request):
        category_id = request.data.get("category")
        if not category_id:
            return Response({"error": "Параметр category обов'язковий"}, status=400)

        user = request.user
        if user.is_superuser:
            source = Category.objects.filter(id=category_id).first()
        else:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            source = Category.objects.filter(id=category_id, company_id__in=user_companies).first()
        if source is None:
            return Response({"error": "Категорію не знайдено"}, status=404)

        result = _copy_tree_user_assignments(
            source_obj=source,
            target_ids=[source.parent_id] if source.parent_id else [],
            assignment_model=CategoryUser,
            relation_field="category",
        )
        return Response(result)

    @extend_schema(
        summary="Скопіювати користувачів у дочірні категорії",
        description="Копіює користувачів поточної категорії в усі дочірні категорії без дублювання.",
    )
    @action(detail=False, methods=["post"], url_path="copy-descendants")
    def copy_descendants(self, request):
        category_id = request.data.get("category")
        if not category_id:
            return Response({"error": "Параметр category обов'язковий"}, status=400)

        user = request.user
        if user.is_superuser:
            source = Category.objects.filter(id=category_id).first()
        else:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            source = Category.objects.filter(id=category_id, company_id__in=user_companies).first()
        if source is None:
            return Response({"error": "Категорію не знайдено"}, status=404)

        target_ids = _expand_tree_ids_with_descendants(Category, {source.id}) - {source.id}
        result = _copy_tree_user_assignments(
            source_obj=source,
            target_ids=target_ids,
            assignment_model=CategoryUser,
            relation_field="category",
        )
        return Response(result)

    @extend_schema(
        summary="Видалити користувача з категорії",
        description="Видалити користувача з категорії.",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class CpvDictionaryTreeView(APIView):
    """
    Повертає дерево CPV-кодів для вибору у довіднику.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Дерево CPV-кодів",
        description=(
            "Повертає повний перелік CPV-кодів у вигляді дерева. "
            "Деревоподібна структура будується за полями cpv_parent_code / cpv_level_code. "
            "Кожен елемент містить id, cpv_code, name_ua, name_en, cpv_parent_code, cpv_level_code та children."
        ),
        responses={200: OpenApiResponse(description="Список кореневих CPV-елементів з вкладеними дітьми")},
    )
    def get(self, request):
        # Отримуємо усі записи
        items = list(CpvDictionary.objects.all())

        # Індекс за внутрішнім кодом рівня
        by_level_code = {i.cpv_level_code: i for i in items}

        # Підготуємо список коренів
        roots: list[CpvDictionary] = []

        # Тимчасово додаємо атрибут _children до об'єктів
        for item in items:
            parent_code = (item.cpv_parent_code or "").strip()
            if not parent_code or parent_code == "0":
                roots.append(item)
            else:
                parent = by_level_code.get(parent_code)
                if parent is None:
                    # Якщо батько не знайдений, вважаємо елемент коренем
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
    Ліниве завантаження CPV-вузлів: корені або діти конкретного вузла.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="CPV вузли (ліниво)",
        description=(
            "Повертає CPV-вузли для lazy-tree.\n"
            "- Без параметра `parent_level_code`: повертає тільки кореневі вузли.\n"
            "- З параметром `parent_level_code`: повертає лише прямих дітей для цього вузла."
        ),
        parameters=[
            OpenApiParameter(
                name="parent_level_code",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Внутрішній код батьківського вузла (cpv_level_code).",
            )
        ],
        responses={200: OpenApiResponse(description="Список вузлів")},
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
    Список CPV-категорій, за якими є зареєстровані компанії в системі (не в рамках однієї компанії).
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="CPV з зареєстрованими компаніями",
        description="Повертає плоский список CPV (id, cpv_code, name_ua, label), за якими хоча б одна компанія зареєстрована в системі.",
        responses={200: OpenApiResponse(description="Список CPV")},
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


class ExpenseArticleViewSet(ReferenceActivityMixin, viewsets.ModelViewSet):
    """
    ExpenseArticle management (tree, company-scoped).
    """

    serializer_class = ExpenseArticleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter by user's companies and optionally by user's assignments."""
        user = self.request.user
        self._allowed_tree_ids = None
        self._directly_assigned_ids = None
        if user.is_superuser:
            queryset = ExpenseArticle.objects.all()
        else:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            queryset = ExpenseArticle.objects.filter(company_id__in=user_companies)

        if _is_truthy_query_param(self.request.query_params.get("assigned_only")):
            assigned_ids = set(queryset.filter(users__user=user).values_list("id", flat=True))
            self._directly_assigned_ids = assigned_ids
            if not assigned_ids:
                self._allowed_tree_ids = set()
                return queryset.none().select_related("parent", "company")
            allowed_ids = _expand_tree_ids_with_ancestors(ExpenseArticle, assigned_ids)
            self._allowed_tree_ids = allowed_ids
            queryset = queryset.filter(id__in=allowed_ids).distinct()

        queryset = _apply_is_active_filter(queryset, self.request)
        return queryset.select_related("parent", "company")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if getattr(self, "_allowed_tree_ids", None) is not None:
            context["allowed_ids"] = self._allowed_tree_ids
        if getattr(self, "_directly_assigned_ids", None) is not None:
            context["directly_assigned_ids"] = self._directly_assigned_ids
        return context

    @extend_schema(
        summary="Список статей витрат",
        description="Отримати дерево статей витрат компанії (тільки кореневі елементи, діти вкладено).",
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not _is_flat_tree_request(request):
            queryset = queryset.filter(parent__isnull=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Створити статтю витрат",
        description="Створити нову статтю витрат.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Оновити статтю витрат",
        description="Оновити інформацію про статтю витрат.",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Видалити статтю витрат",
        description="Видалити статтю витрат.",
    )
    def _get_delete_blockers(self, obj):
        blockers = []
        if obj.children.exists():
            blockers.append("є дочірні статті бюджету")
        if obj.procurement_tenders.exists() or obj.sales_tenders.exists():
            blockers.append("стаття бюджету використовується у тендерах")
        return blockers


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
        summary="Список користувачів статті витрат",
        description="Отримати список користувачів статті витрат (потрібен параметр expense_id).",
        parameters=[
            OpenApiParameter(name="expense_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True)
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Додати користувачів до статті витрат",
        description="Додати одного або кілька користувачів до статті витрат (масив user_ids).",
    )
    def create(self, request, *args, **kwargs):
        expense_id = request.data.get("expense")
        user_ids = request.data.get("user_ids", [])
        if not isinstance(user_ids, list):
            return Response({"error": "user_ids повинен бути масивом"}, status=400)

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
        summary="Скопіювати користувачів у батьківську статтю бюджету",
        description="Копіює користувачів поточної статті бюджету в її батьківську статтю без дублювання.",
    )
    @action(detail=False, methods=["post"], url_path="copy-parent")
    def copy_parent(self, request):
        expense_id = request.data.get("expense")
        if not expense_id:
            return Response({"error": "Параметр expense обов'язковий"}, status=400)

        user = request.user
        if user.is_superuser:
            source = ExpenseArticle.objects.filter(id=expense_id).first()
        else:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            source = ExpenseArticle.objects.filter(
                id=expense_id, company_id__in=user_companies
            ).first()
        if source is None:
            return Response({"error": "Статтю бюджету не знайдено"}, status=404)

        result = _copy_tree_user_assignments(
            source_obj=source,
            target_ids=[source.parent_id] if source.parent_id else [],
            assignment_model=ExpenseArticleUser,
            relation_field="expense",
        )
        return Response(result)

    @extend_schema(
        summary="Скопіювати користувачів у дочірні статті бюджету",
        description="Копіює користувачів поточної статті бюджету в усі дочірні статті без дублювання.",
    )
    @action(detail=False, methods=["post"], url_path="copy-descendants")
    def copy_descendants(self, request):
        expense_id = request.data.get("expense")
        if not expense_id:
            return Response({"error": "Параметр expense обов'язковий"}, status=400)

        user = request.user
        if user.is_superuser:
            source = ExpenseArticle.objects.filter(id=expense_id).first()
        else:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            source = ExpenseArticle.objects.filter(
                id=expense_id, company_id__in=user_companies
            ).first()
        if source is None:
            return Response({"error": "Статтю бюджету не знайдено"}, status=404)

        target_ids = _expand_tree_ids_with_descendants(ExpenseArticle, {source.id}) - {
            source.id
        }
        result = _copy_tree_user_assignments(
            source_obj=source,
            target_ids=target_ids,
            assignment_model=ExpenseArticleUser,
            relation_field="expense",
        )
        return Response(result)

    @extend_schema(
        summary="Видалити користувача зі статті витрат",
        description="Видалити користувача зі статті витрат.",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class UnitOfMeasureViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Довідник одиниць виміру - спільний для всіх компаній.
    Список одиниць (спільні company=null + одиниці компаній користувача).
    Наповнення - через БД; створення/редагування через API вимкнено.
    """

    serializer_class = UnitOfMeasureSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        """Спільні одиниці (company=null) + одиниці компаній користувача."""
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


class NomenclatureViewSet(ReferenceActivityMixin, viewsets.ModelViewSet):
    """
    Номенклатура (company-scoped).
    """

    serializer_class = NomenclatureSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Фільтрує номенклатуру за компаніями користувача та параметрами."""
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

        # Фільтри
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

        return _apply_is_active_filter(qs, self.request)

    @extend_schema(
        summary="Список номенклатури",
        description="Отримати список номенклатури компанії з можливими фільтрами (name, category_id, cpv_id).",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Створити номенклатуру",
        description="Створити новий елемент номенклатури.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Оновити номенклатуру",
        description="Оновити дані номенклатури.",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Видалити номенклатуру",
        description="Видалити елемент номенклатури.",
    )
    def _get_delete_blockers(self, obj):
        blockers = []
        if obj.procurement_tender_positions.exists() or obj.sales_tender_positions.exists():
            blockers.append("номенклатура використовується у тендерних позиціях")
        return blockers

    @extend_schema(
        summary="Деактивувати номенклатуру",
        description="Позначити номенклатуру як неактивну (is_active = False).",
    )
    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        return Response(self.get_serializer(obj).data)

    @extend_schema(
        summary="Активувати номенклатуру",
        description="Позначити номенклатуру як активну (is_active = True).",
    )
    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        obj = self.get_object()
        obj.is_active = True
        obj.save(update_fields=["is_active"])
        return Response(self.get_serializer(obj).data)


class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Довідник валют (системний, тільки читання).
    """

    queryset = Currency.objects.all().order_by("code")
    serializer_class = CurrencySerializer
    permission_classes = [permissions.IsAuthenticated]


class TenderCriterionViewSet(ReferenceActivityMixin, viewsets.ModelViewSet):
    """
    Довідник критеріїв тендерів (company-scoped).
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
            return _apply_is_active_filter(qs, self.request)
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        qs = TenderCriterion.objects.filter(
            company_id__in=user_companies
        ).select_related("company")
        tender_type = (self.request.query_params.get("tender_type") or "").strip()
        if tender_type in {"procurement", "sales"}:
            qs = qs.filter(tender_type=tender_type)
        return _apply_is_active_filter(qs, self.request)

    def perform_create(self, serializer):
        tender_type = (self.request.query_params.get("tender_type") or "").strip()
        if tender_type in {"procurement", "sales"}:
            serializer.save(tender_type=tender_type)
            return
        serializer.save()

    def _get_delete_blockers(self, obj):
        blockers = []
        if (
            obj.procurement_tenders.exists()
            or obj.sales_tenders.exists()
            or obj.procurement_tender_snapshots.exists()
            or obj.sales_tender_snapshots.exists()
        ):
            blockers.append("критерій використовується у тендерах")
        return blockers


class TenderAttributeViewSet(ReferenceActivityMixin, viewsets.ModelViewSet):
    """
    Довідник атрибутів тендерів (company-scoped).
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
            return _apply_is_active_filter(qs, self.request)
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        qs = TenderAttribute.objects.filter(
            company_id__in=user_companies
        ).select_related("company", "category")
        tender_type = (self.request.query_params.get("tender_type") or "").strip()
        if tender_type in {"procurement", "sales"}:
            qs = qs.filter(tender_type=tender_type)
        return _apply_is_active_filter(qs, self.request)

    def perform_create(self, serializer):
        tender_type = (self.request.query_params.get("tender_type") or "").strip()
        if tender_type in {"procurement", "sales"}:
            serializer.save(tender_type=tender_type)
            return
        serializer.save()

    def _get_delete_blockers(self, obj):
        blockers = []
        if obj.procurement_tenders.exists() or obj.sales_tenders.exists():
            blockers.append("атрибут використовується у тендерах")
        return blockers


class WarehouseViewSet(ReferenceActivityMixin, viewsets.ModelViewSet):
    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            qs = Warehouse.objects.all().select_related("company", "linked_warehouse")
        else:
            user_companies = CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
            qs = Warehouse.objects.filter(company_id__in=user_companies).select_related(
                "company", "linked_warehouse"
            )
        warehouse_type = (self.request.query_params.get("warehouse_type") or "").strip()
        if warehouse_type in {
            Warehouse.WarehouseType.SHIPMENT,
            Warehouse.WarehouseType.DELIVERY,
        }:
            qs = qs.filter(warehouse_type=warehouse_type)
        return _apply_is_active_filter(qs, self.request)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        obj = self.get_object()
        linked_ids = {obj.pk}
        if obj.linked_warehouse_id:
            linked_ids.add(obj.linked_warehouse_id)
        Warehouse.objects.filter(pk__in=linked_ids).update(is_active=False)
        obj.refresh_from_db()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        obj = self.get_object()
        linked_ids = {obj.pk}
        if obj.linked_warehouse_id:
            linked_ids.add(obj.linked_warehouse_id)
        Warehouse.objects.filter(pk__in=linked_ids).update(is_active=True)
        obj.refresh_from_db()
        return Response(self.get_serializer(obj).data)

    def _get_delete_blockers(self, obj):
        blockers = []
        if (
            obj.procurement_tender_positions.exists()
            or obj.sales_tender_positions.exists()
        ):
            blockers.append("склад використовується у позиціях тендерів")
        return blockers


class TenderConditionTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = TenderConditionTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = TenderConditionTemplate.objects.all().select_related("company", "created_by")
        if user.is_superuser:
            return qs
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        return qs.filter(company_id__in=user_companies)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ApprovalModelRoleViewSet(ReferenceActivityMixin, viewsets.ModelViewSet):
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
        return _apply_is_active_filter(qs, self.request)

    def _get_delete_blockers(self, obj):
        blockers = []
        if obj.model_steps.exists():
            blockers.append("роль використовується в моделях погодження")
        return blockers


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


class ApprovalModelViewSet(ReferenceActivityMixin, viewsets.ModelViewSet):
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
        return _apply_is_active_filter(qs, self.request)

    @action(detail=False, methods=["get"], url_path="available-for-tender")
    def available_for_tender(self, request):
        company_id, error_response = _resolve_request_company_id(request)
        if error_response:
            return error_response
        application = (request.query_params.get("application") or "").strip()
        if application not in {"procurement", "sales"}:
            return Response(
                {"detail": "application має бути procurement або sales."},
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
            ranges__is_active=True,
        ).distinct()
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def _get_delete_blockers(self, obj):
        blockers = []
        if obj.procurement_tenders.exists() or obj.sales_tenders.exists():
            blockers.append("модель погодження використовується у тендерах")
        return blockers


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
    Тендери на закупівлю (company-scoped). Номер присвоюється при першому збереженні.
    Доступ: будь-який авторизований користувач з підтвердженим членством у компанії.
    Права доступу (tenders.create тощо) не перевіряються - обмеження знято за бажанням замовника.
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
            base_qs = base_qs.select_related(
                "created_by",
                "category",
                "cpv_category",
                "expense_article",
                "branch",
                "department",
            ).prefetch_related("cpv_categories")
        else:
            base_qs = base_qs.select_related(
                "company", "category", "cpv_category", "expense_article",
                "branch", "department", "currency", "created_by", "parent",
            ).prefetch_related(
                "positions__nomenclature__unit",
                "positions__warehouse",
                "tender_criteria",
                "criteria_items__reference_criterion",
            )
        if user.is_superuser:
            return base_qs
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        return base_qs.filter(company_id__in=user_companies)

    @extend_schema(
        parameters=[
            OpenApiParameter(name="page", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="page_size", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search by tender number or tender name.",
            ),
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="active | completed | all",
            ),
            OpenApiParameter(name="author_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter(
                name="branch_ids",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Comma-separated branch ids.",
            ),
            OpenApiParameter(
                name="department_ids",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Comma-separated department ids.",
            ),
            OpenApiParameter(
                name="expense_ids",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Comma-separated expense article ids.",
            ),
            OpenApiParameter(
                name="conduct_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="registration | rfx | online_auction",
            ),
            OpenApiParameter(
                name="stage",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="passport | preparation | acceptance | decision | approval | completed",
            ),
        ],
        responses=OpenApiTypes.OBJECT,
    )
    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        return _build_owner_tender_journal_response(
            request,
            qs=qs,
            serializer_cls=self.get_serializer_class(),
        )

    def destroy(self, request, *args, **kwargs):
        tender = self.get_object()
        _ensure_user_can_delete_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["post"], url_path="bulk-delete")
    def bulk_delete(self, request):
        requested_ids = _extract_requested_ids(request)
        if not requested_ids:
            return Response(
                {"detail": "Передайте непорожній масив ids."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = self.get_queryset().filter(id__in=requested_ids)
        existing_ids = set(qs.values_list("id", flat=True))
        candidate_ids = list(
            qs.filter(
                created_by_id=request.user.id,
                tour_number=1,
                stage=TenderApprovalStageState.Stage.PREPARATION,
            ).values_list("id", flat=True)
        )
        deletable_ids = _resolve_preparation_stage_deletable_ids(
            candidate_ids=candidate_ids,
            is_sales=False,
        )
        deleted_ids = list(
            ProcurementTender.objects.filter(id__in=deletable_ids).values_list("id", flat=True)
        )
        if deleted_ids:
            ProcurementTender.objects.filter(id__in=deleted_ids).delete()

        missing_ids = [item_id for item_id in requested_ids if item_id not in existing_ids]
        ineligible_ids = [
            item_id
            for item_id in requested_ids
            if item_id in existing_ids and item_id not in deletable_ids
        ]
        return Response(
            {
                "requested_ids": requested_ids,
                "deleted_ids": deleted_ids,
                "deleted_count": len(deleted_ids),
                "missing_ids": missing_ids,
                "ineligible_ids": ineligible_ids,
            }
        )

    @action(detail=False, methods=["post"], url_path="bulk-copy")
    def bulk_copy(self, request):
        requested_ids = _extract_requested_ids(request)
        if not requested_ids:
            return Response(
                {"detail": "Передайте непорожній масив ids."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        source_rows = list(
            self.get_queryset()
            .filter(id__in=requested_ids)
            .select_related(
                "company",
                "category",
                "cpv_category",
                "expense_article",
                "branch",
                "department",
                "currency",
                "approval_model",
            )
            .prefetch_related(
                "cpv_categories",
                "tender_criteria",
                "tender_attributes",
                "criteria_items__reference_criterion",
                "positions__nomenclature",
                "positions__warehouse",
            )
        )
        source_by_id = {int(item.id): item for item in source_rows}
        copied_rows = []
        copied_ids = []
        for source_id in requested_ids:
            source_tender = source_by_id.get(int(source_id))
            if not source_tender:
                continue
            copied_tender = _copy_tender_to_first_round(
                source_tender=source_tender,
                actor=request.user,
                is_sales=False,
            )
            copied_rows.append(
                {
                    "source_id": int(source_id),
                    "id": int(copied_tender.id),
                    "stage": copied_tender.stage,
                    "tour_number": copied_tender.tour_number,
                }
            )
            copied_ids.append(int(copied_tender.id))

        available_source_ids = set(source_by_id.keys())
        missing_ids = [item_id for item_id in requested_ids if item_id not in available_source_ids]
        return Response(
            {
                "requested_ids": requested_ids,
                "copied_ids": copied_ids,
                "copied_count": len(copied_ids),
                "copied": copied_rows,
                "missing_ids": missing_ids,
            },
            status=status.HTTP_201_CREATED,
        )

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
        acceptance_timing_changed = (
            before_stage == ProcurementTender.Stage.ACCEPTANCE
            and target_stage == ProcurementTender.Stage.ACCEPTANCE
            and any(field in self.request.data for field in ("start_at", "end_at"))
        )
        if acceptance_timing_changed:
            timing_comment = str(self.request.data.get("timing_comment") or "").strip()
            if not timing_comment:
                raise DRFValidationError(
                    {"timing_comment": "Comment is required when changing acceptance timing."}
                )

        approval_model_changed = "approval_model" in serializer.validated_data
        serializer.save()
        after_stage = getattr(serializer.instance, "stage", "") or ""
        if (
            before_stage != ProcurementTender.Stage.DECISION
            and after_stage == ProcurementTender.Stage.DECISION
        ):
            _recalculate_tender_position_values_without_vat(
                tender=serializer.instance,
                is_sales=False,
            )
            _notify_tender_author_stage_event(
                tender=serializer.instance,
                is_sales=False,
                event_type=Notification.Type.TENDER_TO_DECISION,
                title="Тендер перейшов на етап вибору рішення",
                body="Прийом пропозицій завершено, тендер очікує вибір рішення.",
            )
        if (
            before_stage != ProcurementTender.Stage.COMPLETED
            and after_stage == ProcurementTender.Stage.COMPLETED
        ):
            _notify_tender_author_stage_event(
                tender=serializer.instance,
                is_sales=False,
                event_type=Notification.Type.TENDER_COMPLETED,
                title="Тендер завершено",
                body='Тендер перейшов на етап "Завершено".',
            )
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
        """Access to tender detail is limited to tender owners and approvers."""
        queryset = self.filter_queryset(self.get_queryset())
        pk = self.kwargs.get("pk")
        obj = _get_tender_for_owner_or_approver(
            user=self.request.user,
            tender_id=pk,
            is_sales=False,
            base_queryset=queryset,
        )
        if obj:
            return obj
        from django.http import Http404
        raise Http404("Tender not found.")

    @action(detail=True, methods=["get"], url_path="participant-view")
    def participant_view(self, request, pk=None):
        tender = _get_tender_for_owner_or_participant(
            user=request.user,
            tender_id=pk,
            is_sales=False,
        )
        if not tender:
            return Response({"detail": "Tender not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProcurementTenderSerializer(tender, context={"request": request})
        return Response(serializer.data)

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
        qs = _filter_participation_qs_by_publication_type(
            qs=qs,
            user_company_ids=user_company_ids,
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
        """Підтвердити участь: створює пропозицію та додає контрагента в довідник організатора."""
        tender = ProcurementTender.objects.filter(pk=pk).select_related("company").first()
        if not tender:
            return Response({"detail": "Тендер не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        if tender.stage not in ("acceptance", "preparation"):
            return Response(
                {"detail": "Участь можна підтвердити лише для тендера на прийом пропозицій або підготовку."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return Response(
                {"detail": "Неможливо визначити компанію учасника."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        supplier_company_id, error_response = _resolve_request_company_id(request)
        if error_response:
            return error_response
        if not _is_company_invited_to_tender(
            tender=tender,
            supplier_company_id=supplier_company_id,
            is_sales=False,
        ):
            return Response(
                {"detail": "Your company is not invited to this tender."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if tender.company_id == supplier_company_id:
            return Response(
                {"detail": "Організатор не може підтвердити участь у власному тендері."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            proposal = (
                TenderProposal.objects.select_related("created_by")
                .filter(
                    tender=tender,
                    supplier_company_id=supplier_company_id,
                )
                .first()
            )
            created = False
            if proposal:
                locked_response = _ensure_user_can_manage_company_proposal(
                    proposal=proposal,
                    user=request.user,
                )
                if locked_response:
                    return locked_response
            else:
                proposal = TenderProposal.objects.create(
                    tender=tender,
                    supplier_company_id=supplier_company_id,
                    created_by=request.user,
                )
                created = True
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
        """Подати пропозицію (фіксує подачу для компанії поточного користувача)."""
        tender = ProcurementTender.objects.filter(pk=pk).first()
        if not tender:
            return Response({"detail": "Тендер не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        if tender.stage != "acceptance":
            return Response(
                {"detail": "Подати пропозицію можна лише під час етапу прийому пропозицій."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if tender.end_at and timezone.now() > tender.end_at:
            return Response(
                {"detail": "Термін прийому пропозицій завершено."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return Response(
                {"detail": "Неможливо визначити компанію."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        supplier_company_id, error_response = _resolve_request_company_id(request)
        if error_response:
            return error_response
        if not _is_company_invited_to_tender(
            tender=tender,
            supplier_company_id=supplier_company_id,
            is_sales=False,
        ):
            return Response(
                {"detail": "Your company is not invited to this tender."},
                status=status.HTTP_403_FORBIDDEN,
            )
        proposal = TenderProposal.objects.select_related("created_by").filter(
            tender=tender, supplier_company_id=supplier_company_id
        ).first()
        if not proposal:
            return Response(
                {"detail": "Пропозицію не знайдено. Спочатку підтвердіть участь."},
                status=status.HTTP_404_NOT_FOUND,
            )
        locked_response = _ensure_user_can_manage_company_proposal(
            proposal=proposal,
            user=request.user,
        )
        if locked_response:
            return locked_response
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
        """Відкликати пропозицію (компанія поточного користувача)."""
        tender = ProcurementTender.objects.filter(pk=pk).first()
        if not tender:
            return Response({"detail": "Тендер не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        if tender.stage != "acceptance":
            return Response(
                {"detail": "Відкликати пропозицію можна лише під час етапу прийому пропозицій."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if tender.end_at and timezone.now() > tender.end_at:
            return Response(
                {"detail": "Термін прийому пропозицій завершено."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return Response(
                {"detail": "Неможливо визначити компанію."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        supplier_company_id, error_response = _resolve_request_company_id(request)
        if error_response:
            return error_response
        if not _is_company_invited_to_tender(
            tender=tender,
            supplier_company_id=supplier_company_id,
            is_sales=False,
        ):
            return Response(
                {"detail": "Your company is not invited to this tender."},
                status=status.HTTP_403_FORBIDDEN,
            )
        proposal = TenderProposal.objects.select_related("created_by").filter(
            tender=tender, supplier_company_id=supplier_company_id
        ).first()
        if not proposal:
            return Response(
                {"detail": "Пропозицію не знайдено."},
                status=status.HTTP_404_NOT_FOUND,
            )
        locked_response = _ensure_user_can_manage_company_proposal(
            proposal=proposal,
            user=request.user,
        )
        if locked_response:
            return locked_response
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
        """Усі тури сімейства (від кореня + усі наступні) для випадаючого списку."""
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

    @extend_schema(
        responses=OpenApiTypes.OBJECT,
        summary="Tender protocol preview",
        description="Return structured tender protocol payload for modal preview.",
    )
    @action(detail=True, methods=["get"], url_path="protocol-preview")
    def protocol_preview(self, request, pk=None):
        tender = self.get_object()
        return Response(_build_tender_protocol_payload(tender=tender, is_sales=False))

    @extend_schema(
        responses={200: OpenApiTypes.BINARY},
        summary="Tender protocol PDF",
        description="Generate tender protocol in PDF format.",
    )
    @action(detail=True, methods=["get"], url_path="protocol-pdf")
    def protocol_pdf(self, request, pk=None):
        tender = self.get_object()
        return _build_tender_protocol_pdf_response(
            tender=tender,
            is_sales=False,
            download=request.query_params.get("download"),
        )

    @action(detail=True, methods=["get"], url_path="decision-market-reference")
    def decision_market_reference(self, request, pk=None):
        tender = self.get_object()
        payload = _build_decision_market_reference_payload(
            tender=tender,
            is_sales=False,
        )
        return Response(payload)

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

    @action(detail=True, methods=["get"], url_path="bid-history")
    def bid_history(self, request, pk=None):
        tender = self.get_object()
        position_id = _parse_int_param(request.query_params.get("tender_position_id"), min_value=1)
        if not position_id:
            return Response(
                {"detail": "Передайте tender_position_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = TenderBidHistory.objects.filter(
            tender_type="procurement",
            tender_id=int(tender.id),
            tender_position_id=position_id,
        ).select_related("supplier_company", "created_by")
        serializer = TenderBidHistorySerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="chat/threads")
    def chat_threads(self, request, pk=None):
        tender = _get_tender_for_owner_or_participant(
            user=request.user,
            tender_id=pk,
            is_sales=False,
        )
        if not tender:
            return Response({"detail": "Тендер не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        user_company_ids = set(_user_company_ids(request.user))
        is_owner = int(tender.company_id) in user_company_ids
        if is_owner:
            _ensure_tender_chat_threads_for_submitted_participants(
                tender=tender,
                is_sales=False,
            )
        qs = TenderChatThread.objects.filter(
            tender_type="procurement",
            tender_id=int(tender.id),
        ).select_related("supplier_company")
        if not is_owner:
            qs = qs.filter(supplier_company_id__in=user_company_ids).exclude(
                supplier_company_id=tender.company_id
            )
        qs = _annotate_tender_chat_threads_unread(
            qs=qs,
            tender=tender,
            is_owner=is_owner,
        )
        serializer = TenderChatThreadSerializer(
            qs.order_by("-last_message_at", "-updated_at"),
            many=True,
        )
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"], url_path="chat/messages")
    def chat_messages(self, request, pk=None):
        tender = _get_tender_for_owner_or_participant(
            user=request.user,
            tender_id=pk,
            is_sales=False,
        )
        if not tender:
            return Response({"detail": "Тендер не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        user_company_ids = set(_user_company_ids(request.user))
        is_owner = int(tender.company_id) in user_company_ids
        supplier_company_id_raw = (
            request.query_params.get("supplier_company_id")
            if request.method == "GET"
            else request.data.get("supplier_company_id")
        )
        supplier_company_id = None
        if is_owner:
            supplier_company_id = _parse_int_param(supplier_company_id_raw, min_value=1)
            if not supplier_company_id:
                return Response(
                    {"detail": "Передайте supplier_company_id."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            participant_company_ids = _resolve_tender_chat_participant_company_ids(
                tender=tender,
                is_sales=False,
                user_company_ids=user_company_ids,
            )
            if not participant_company_ids:
                return Response({"detail": "Компанію учасника не визначено."}, status=status.HTTP_403_FORBIDDEN)
            requested_company_id = _parse_int_param(supplier_company_id_raw, min_value=1)
            supplier_company_id = requested_company_id or participant_company_ids[0]
            if supplier_company_id not in participant_company_ids:
                return Response({"detail": "Немає доступу до цього чату."}, status=status.HTTP_403_FORBIDDEN)

        thread, _ = _get_or_create_tender_chat_thread(
            tender=tender,
            is_sales=False,
            supplier_company_id=supplier_company_id,
        )
        if request.method == "GET":
            qs = thread.messages.select_related("author_user", "author_company").all()
            _mark_tender_chat_thread_read(thread=thread, is_owner=is_owner)
            serializer = TenderChatMessageSerializer(qs, many=True)
            return Response(serializer.data)

        body = str(request.data.get("body") or "").strip()
        if not body:
            return Response({"detail": "Текст повідомлення обов'язковий."}, status=status.HTTP_400_BAD_REQUEST)
        if not is_owner:
            proposal = (
                TenderProposal.objects.select_related("created_by")
                .filter(
                    tender=tender,
                    supplier_company_id=supplier_company_id,
                )
                .first()
            )
            if proposal:
                locked_response = _ensure_user_can_manage_company_proposal(
                    proposal=proposal,
                    user=request.user,
                )
                if locked_response:
                    return locked_response
        if not is_owner:
            proposal = (
                SalesTenderProposal.objects.select_related("created_by")
                .filter(
                    tender=tender,
                    supplier_company_id=supplier_company_id,
                )
                .first()
            )
            if proposal:
                locked_response = _ensure_user_can_manage_company_proposal(
                    proposal=proposal,
                    user=request.user,
                )
                if locked_response:
                    return locked_response
        author_company_id = tender.company_id if is_owner else supplier_company_id
        with transaction.atomic():
            message = TenderChatMessage.objects.create(
                thread=thread,
                author_user=request.user,
                author_company_id=author_company_id,
                body=body,
            )
            thread.last_message_at = message.created_at
            thread.save(update_fields=["last_message_at", "updated_at"])
        _notify_tender_chat_message(
            tender=tender,
            is_sales=False,
            thread=thread,
            message=message,
            actor=request.user,
        )
        serializer = TenderChatMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="proposal-change-report")
    def proposal_change_report(self, request, pk=None):
        tender = self.get_object()
        _ensure_user_can_edit_tender(user=request.user, tender=tender, is_sales=False)
        position_names = {
            int(pos.id): getattr(pos, "name", "") or getattr(getattr(pos, "nomenclature", None), "name", "")
            for pos in tender.positions.all()
        }
        qs = TenderProposalChangeLog.objects.filter(
            tender_type="procurement",
            tender_id=int(tender.id),
        ).select_related("supplier_company", "updated_by")
        data = list(TenderProposalChangeLogSerializer(qs, many=True).data)
        for row in data:
            row["position_name"] = position_names.get(int(row.get("tender_position_id") or 0), "")
        return Response(data)

    @action(detail=True, methods=["post"], url_path="disqualify-proposals")
    def disqualify_proposals(self, request, pk=None):
        tender = self.get_object()
        _ensure_user_can_edit_tender(user=request.user, tender=tender, is_sales=False)
        items = request.data.get("items") or []
        if not isinstance(items, list):
            return Response({"detail": "items має бути масивом."}, status=status.HTTP_400_BAD_REQUEST)
        touched_ids = []
        with transaction.atomic():
            for item in items:
                proposal_id = _parse_int_param(item.get("proposal_id"), min_value=1)
                if not proposal_id:
                    continue
                proposal = TenderProposal.objects.filter(tender=tender, id=proposal_id).first()
                if not proposal:
                    continue
                should_disqualify = bool(item.get("disqualify"))
                comment = str(item.get("comment") or "").strip()
                if should_disqualify and not comment:
                    return Response(
                        {"detail": "Для дискваліфікації потрібно вказати коментар.", "proposal_id": proposal_id},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                proposal.disqualified_at = timezone.now() if should_disqualify else None
                proposal.disqualification_comment = comment if should_disqualify else ""
                proposal.disqualified_by = request.user if should_disqualify else None
                proposal.status_updated_at = timezone.now()
                proposal.save(
                    update_fields=[
                        "disqualified_at",
                        "disqualification_comment",
                        "disqualified_by",
                        "status_updated_at",
                    ]
                )
                touched_ids.append(int(proposal.id))
            if touched_ids:
                ProcurementTenderPosition.objects.filter(
                    tender=tender,
                    winner_proposal_id__in=touched_ids,
                ).update(winner_proposal=None)
        qs = TenderProposal.objects.filter(tender=tender).select_related("supplier_company", "disqualified_by").prefetch_related(
            "position_values__tender_position__nomenclature__unit"
        )
        return Response(TenderProposalSerializer(qs, many=True).data)

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
        Зафіксувати рішення: winner - з переможцями по позиціях, cancel - без переможців,
        next_round - створити наступний тур на етапі підготовки.
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
                {"detail": "mode має бути: winner, cancel або next_round."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if mode == "winner":
            position_winners = request.data.get("position_winners") or []
            # Скинути всі переможці по цьому тендеру, потім встановити тільки передані
            ProcurementTenderPosition.objects.filter(tender=tender).update(winner_proposal=None)
            for item in position_winners:
                pos_id = item.get("position_id")
                prop_id = item.get("proposal_id")
                if pos_id is not None and prop_id is not None:
                    pos = ProcurementTenderPosition.objects.filter(tender=tender, id=pos_id).first()
                    proposal = TenderProposal.objects.filter(tender=tender, id=prop_id).first()
                    if proposal and proposal.disqualified_at:
                        return Response(
                            {"detail": "Дискваліфіковану пропозицію не можна обрати переможцем.", "proposal_id": prop_id},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    if pos and proposal:
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
            auction_model=getattr(
                parent,
                "auction_model",
                ProcurementTender.AuctionModel.CLASSIC_AUCTION,
            ),
            publication_type=parent.publication_type,
            currency=parent.currency,
            general_terms=parent.general_terms or "",
            invited_emails=getattr(parent, "invited_emails", []) or [],
            planned_start_at=getattr(parent, "planned_start_at", None),
            planned_end_at=getattr(parent, "planned_end_at", None),
            price_criterion_vat=parent.price_criterion_vat or "",
            price_criterion_vat_percent=parent.price_criterion_vat_percent,
            price_criterion_delivery=parent.price_criterion_delivery or "",
            approval_model=parent.approval_model,
            uses_position_warehouses=bool(
                getattr(parent, "uses_position_warehouses", False)
            ),
            created_by=request.user,
        )
        new_tender.cpv_categories.set(parent.cpv_categories.all())
        new_tender.tender_criteria.set(parent.tender_criteria.all())
        _sync_tender_invited_suppliers(
            tender=new_tender,
            supplier_company_ids=list(
                parent.invited_supplier_links.values_list("supplier_company_id", flat=True)
            ),
            is_sales=False,
        )
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
                warehouse=pos.warehouse,
            )
        return Response({"stage": "preparation", "id": new_tender.id}, status=status.HTTP_201_CREATED)

    @extend_schema(responses=TenderProposalSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="proposals")
    def proposals_list(self, request, pk=None):
        """Список пропозицій по тендеру."""
        tender = _get_tender_for_owner_or_participant(
            user=request.user,
            tender_id=pk,
            is_sales=False,
        )
        if not tender:
            return Response({"detail": "Tender not found."}, status=status.HTTP_404_NOT_FOUND)
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
                "supplier_company", "disqualified_by"
            )
            if updated_since is not None:
                qs = qs.filter(status_updated_at__gt=updated_since)
            if proposal_ids:
                qs = qs.filter(id__in=proposal_ids)
            elif "ids" in request.query_params:
                return Response([])
            qs, _ = _filter_tender_proposals_for_user(qs=qs, tender=tender, user=request.user)
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
            "supplier_company", "disqualified_by"
        ).prefetch_related(
            "position_values__tender_position__nomenclature__unit",
        )
        if proposal_ids:
            qs = qs.filter(id__in=proposal_ids)
        elif "ids" in request.query_params:
            return Response([])
        qs, _ = _filter_tender_proposals_for_user(qs=qs, tender=tender, user=request.user)
        serializer = TenderProposalSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(request=TenderProposalSerializer, responses=TenderProposalSerializer)
    @action(detail=True, methods=["post"], url_path="proposals/add")
    def proposal_add(self, request, pk=None):
        """Додати пропозицію (обрати контрагента)."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        supplier_company_id = request.data.get("supplier_company_id") or request.data.get("supplier_company")
        if not supplier_company_id:
            return Response(
                {"detail": "Потрібно вказати supplier_company_id."},
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
        """Оновити значення по позиціях пропозиції (ціна + критерії)."""
        tender = _get_tender_for_owner_or_participant(
            user=request.user,
            tender_id=pk,
            is_sales=False,
        )
        if not tender:
            return Response({"detail": "Тендер не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        proposal_qs = TenderProposal.objects.filter(
            tender=tender,
            id=proposal_id,
        ).prefetch_related("position_values__tender_position")
        proposal_qs, actor_represents_owner = _filter_tender_proposals_for_user(
            qs=proposal_qs,
            tender=tender,
            user=request.user,
        )
        proposal = proposal_qs.first()
        if not proposal:
            return Response({"detail": "Пропозицію не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        if not actor_represents_owner:
            locked_response = _ensure_user_can_manage_company_proposal(
                proposal=proposal,
                user=request.user,
            )
            if locked_response:
                return locked_response
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
            previous_price = pv.price
            previous_criterion_values = pycopy.deepcopy(pv.criterion_values or {})
            has_changes = False
            if "price" in item:
                next_price = item["price"]
                if pv.price != next_price:
                    pv.price = next_price
                    has_changes = True
            if "criterion_values" in item:
                next_criterion_values = item["criterion_values"] or {}
                if (pv.criterion_values or {}) != next_criterion_values:
                    pv.criterion_values = next_criterion_values
                    has_changes = True
            if not has_changes:
                continue
            pv.save()
            changed_position_ids.add(int(tp_id))
            if "price" in item and previous_price != pv.price:
                _record_tender_bid_history(
                    tender=tender,
                    is_sales=False,
                    proposal=proposal,
                    tender_position_id=tp_id,
                    price=pv.price,
                    actor=request.user,
                )
            if actor_represents_owner and tender.stage == ProcurementTender.Stage.DECISION:
                _record_tender_proposal_change_log(
                    tender=tender,
                    is_sales=False,
                    proposal=proposal,
                    tender_position_id=tp_id,
                    original_price=previous_price,
                    original_criterion_values=previous_criterion_values,
                    current_price=pv.price,
                    current_criterion_values=pv.criterion_values or {},
                    actor=request.user,
                )
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
        """Деталі пропозиції (з позиціями та значеннями)."""
        tender = _get_tender_for_owner_or_participant(
            user=request.user,
            tender_id=pk,
            is_sales=False,
        )
        if not tender:
            return Response({"detail": "Тендер не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        proposal_qs = TenderProposal.objects.filter(
            tender=tender, id=proposal_id
        ).select_related("supplier_company", "disqualified_by").prefetch_related(
            "position_values__tender_position__nomenclature__unit",
        )
        proposal_qs, _ = _filter_tender_proposals_for_user(
            qs=proposal_qs,
            tender=tender,
            user=request.user,
        )
        proposal = proposal_qs.first()
        if not proposal:
            return Response({"detail": "Пропозицію не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TenderProposalSerializer(proposal)
        return Response(serializer.data)

    @extend_schema(responses=ProcurementTenderFileSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="files")
    def files_list(self, request, pk=None):
        """Список прикріплених файлів."""
        tender = _get_tender_for_owner_or_participant(
            user=request.user,
            tender_id=pk,
            is_sales=False,
        )
        if not tender:
            return Response({"detail": "Тендер не знайдено."}, status=status.HTTP_404_NOT_FOUND)
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
        """Прикріпити файл до тендера."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        file_obj = request.FILES.get("file") or request.FILES.get("file_upload")
        if not file_obj:
            return Response(
                {"detail": "Надішліть файл у полі file або file_upload."},
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
        """Видалити прикріплений файл."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        obj = ProcurementTenderFile.objects.filter(tender=tender, id=file_id).first()
        if not obj:
            return Response({"detail": "Файл не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["patch"], url_path=r"files/(?P<file_id>\d+)")
    def file_patch(self, request, pk=None, file_id=None):
        """Оновити видимість файлу учасникам."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=False,
        )
        obj = ProcurementTenderFile.objects.filter(tender=tender, id=file_id).first()
        if not obj:
            return Response({"detail": "Файл не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        if "visible_to_participants" in request.data:
            obj.visible_to_participants = bool(request.data["visible_to_participants"])
            obj.save(update_fields=["visible_to_participants"])
        serializer = ProcurementTenderFileSerializer(obj, context={"request": request})
        return Response(serializer.data)


class SalesTenderViewSet(viewsets.ModelViewSet):
    """
    Тендери на продаж (company-scoped). Та сама процедура, що й закупівля;
    переможець рекомендується за найбільшою ціною.
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
            base_qs = base_qs.select_related(
                "created_by",
                "category",
                "cpv_category",
                "expense_article",
                "branch",
                "department",
            ).prefetch_related("cpv_categories")
        else:
            base_qs = base_qs.select_related(
                "company", "category", "cpv_category", "expense_article",
                "branch", "department", "currency", "created_by", "parent",
            ).prefetch_related(
                "positions__nomenclature__unit",
                "positions__warehouse",
                "tender_criteria",
                "criteria_items__reference_criterion",
            )
        if user.is_superuser:
            return base_qs
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        return base_qs.filter(company_id__in=user_companies)

    @extend_schema(
        parameters=[
            OpenApiParameter(name="page", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="page_size", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search by tender number or tender name.",
            ),
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="active | completed | all",
            ),
            OpenApiParameter(name="author_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter(
                name="branch_ids",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Comma-separated branch ids.",
            ),
            OpenApiParameter(
                name="department_ids",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Comma-separated department ids.",
            ),
            OpenApiParameter(
                name="expense_ids",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Comma-separated expense article ids.",
            ),
            OpenApiParameter(
                name="conduct_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="registration | rfx | online_auction",
            ),
            OpenApiParameter(
                name="stage",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="passport | preparation | acceptance | decision | approval | completed",
            ),
        ],
        responses=OpenApiTypes.OBJECT,
    )
    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        return _build_owner_tender_journal_response(
            request,
            qs=qs,
            serializer_cls=self.get_serializer_class(),
        )

    def destroy(self, request, *args, **kwargs):
        tender = self.get_object()
        _ensure_user_can_delete_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["post"], url_path="bulk-delete")
    def bulk_delete(self, request):
        requested_ids = _extract_requested_ids(request)
        if not requested_ids:
            return Response(
                {"detail": "Передайте непорожній масив ids."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = self.get_queryset().filter(id__in=requested_ids)
        existing_ids = set(qs.values_list("id", flat=True))
        candidate_ids = list(
            qs.filter(
                created_by_id=request.user.id,
                tour_number=1,
                stage=TenderApprovalStageState.Stage.PREPARATION,
            ).values_list("id", flat=True)
        )
        deletable_ids = _resolve_preparation_stage_deletable_ids(
            candidate_ids=candidate_ids,
            is_sales=True,
        )
        deleted_ids = list(
            SalesTender.objects.filter(id__in=deletable_ids).values_list("id", flat=True)
        )
        if deleted_ids:
            SalesTender.objects.filter(id__in=deleted_ids).delete()

        missing_ids = [item_id for item_id in requested_ids if item_id not in existing_ids]
        ineligible_ids = [
            item_id
            for item_id in requested_ids
            if item_id in existing_ids and item_id not in deletable_ids
        ]
        return Response(
            {
                "requested_ids": requested_ids,
                "deleted_ids": deleted_ids,
                "deleted_count": len(deleted_ids),
                "missing_ids": missing_ids,
                "ineligible_ids": ineligible_ids,
            }
        )

    @action(detail=False, methods=["post"], url_path="bulk-copy")
    def bulk_copy(self, request):
        requested_ids = _extract_requested_ids(request)
        if not requested_ids:
            return Response(
                {"detail": "Передайте непорожній масив ids."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        source_rows = list(
            self.get_queryset()
            .filter(id__in=requested_ids)
            .select_related(
                "company",
                "category",
                "cpv_category",
                "expense_article",
                "branch",
                "department",
                "currency",
                "approval_model",
            )
            .prefetch_related(
                "cpv_categories",
                "tender_criteria",
                "tender_attributes",
                "criteria_items__reference_criterion",
                "positions__nomenclature",
                "positions__warehouse",
            )
        )
        source_by_id = {int(item.id): item for item in source_rows}
        copied_rows = []
        copied_ids = []
        for source_id in requested_ids:
            source_tender = source_by_id.get(int(source_id))
            if not source_tender:
                continue
            copied_tender = _copy_tender_to_first_round(
                source_tender=source_tender,
                actor=request.user,
                is_sales=True,
            )
            copied_rows.append(
                {
                    "source_id": int(source_id),
                    "id": int(copied_tender.id),
                    "stage": copied_tender.stage,
                    "tour_number": copied_tender.tour_number,
                }
            )
            copied_ids.append(int(copied_tender.id))

        available_source_ids = set(source_by_id.keys())
        missing_ids = [item_id for item_id in requested_ids if item_id not in available_source_ids]
        return Response(
            {
                "requested_ids": requested_ids,
                "copied_ids": copied_ids,
                "copied_count": len(copied_ids),
                "copied": copied_rows,
                "missing_ids": missing_ids,
            },
            status=status.HTTP_201_CREATED,
        )

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        pk = self.kwargs.get("pk")
        obj = _get_tender_for_owner_or_approver(
            user=self.request.user,
            tender_id=pk,
            is_sales=True,
            base_queryset=queryset,
        )
        if obj:
            return obj
        from django.http import Http404
        raise Http404("Tender not found.")

    @action(detail=True, methods=["get"], url_path="participant-view")
    def participant_view(self, request, pk=None):
        tender = _get_tender_for_owner_or_participant(
            user=request.user,
            tender_id=pk,
            is_sales=True,
        )
        if not tender:
            return Response({"detail": "Tender not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SalesTenderSerializer(tender, context={"request": request})
        return Response(serializer.data)

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
        acceptance_timing_changed = (
            before_stage == SalesTender.Stage.ACCEPTANCE
            and target_stage == SalesTender.Stage.ACCEPTANCE
            and any(field in self.request.data for field in ("start_at", "end_at"))
        )
        if acceptance_timing_changed:
            timing_comment = str(self.request.data.get("timing_comment") or "").strip()
            if not timing_comment:
                raise DRFValidationError(
                    {"timing_comment": "Comment is required when changing acceptance timing."}
                )

        approval_model_changed = "approval_model" in serializer.validated_data
        serializer.save()
        after_stage = getattr(serializer.instance, "stage", "") or ""
        if (
            before_stage != SalesTender.Stage.DECISION
            and after_stage == SalesTender.Stage.DECISION
        ):
            _recalculate_tender_position_values_without_vat(
                tender=serializer.instance,
                is_sales=True,
            )
            _notify_tender_author_stage_event(
                tender=serializer.instance,
                is_sales=True,
                event_type=Notification.Type.TENDER_TO_DECISION,
                title="Тендер перейшов на етап вибору рішення",
                body="Прийом пропозицій завершено, тендер очікує вибір рішення.",
            )
        if (
            before_stage != SalesTender.Stage.COMPLETED
            and after_stage == SalesTender.Stage.COMPLETED
        ):
            _notify_tender_author_stage_event(
                tender=serializer.instance,
                is_sales=True,
                event_type=Notification.Type.TENDER_COMPLETED,
                title="Тендер завершено",
                body='Тендер перейшов на етап "Завершено".',
            )
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
        qs = _filter_participation_qs_by_publication_type(
            qs=qs,
            user_company_ids=user_company_ids,
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
        """Підтвердити участь: створює пропозицію та додає контрагента в довідник організатора."""
        tender = SalesTender.objects.filter(pk=pk).select_related("company").first()
        if not tender:
            return Response({"detail": "Тендер не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        if tender.stage not in ("acceptance", "preparation"):
            return Response(
                {"detail": "Участь можна підтвердити лише для тендера на прийом пропозицій або підготовку."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return Response(
                {"detail": "Неможливо визначити компанію учасника."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        supplier_company_id, error_response = _resolve_request_company_id(request)
        if error_response:
            return error_response
        if not _is_company_invited_to_tender(
            tender=tender,
            supplier_company_id=supplier_company_id,
            is_sales=True,
        ):
            return Response(
                {"detail": "Your company is not invited to this tender."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if tender.company_id == supplier_company_id:
            return Response(
                {"detail": "Організатор не може підтвердити участь у власному тендері."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            proposal = (
                SalesTenderProposal.objects.select_related("created_by")
                .filter(
                    tender=tender,
                    supplier_company_id=supplier_company_id,
                )
                .first()
            )
            created = False
            if proposal:
                locked_response = _ensure_user_can_manage_company_proposal(
                    proposal=proposal,
                    user=request.user,
                )
                if locked_response:
                    return locked_response
            else:
                proposal = SalesTenderProposal.objects.create(
                    tender=tender,
                    supplier_company_id=supplier_company_id,
                    created_by=request.user,
                )
                created = True
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
        """Подати пропозицію (фіксує подачу для компанії поточного користувача)."""
        tender = SalesTender.objects.filter(pk=pk).first()
        if not tender:
            return Response({"detail": "Тендер не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        if tender.stage != "acceptance":
            return Response(
                {"detail": "Подати пропозицію можна лише під час етапу прийому пропозицій."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if tender.end_at and timezone.now() > tender.end_at:
            return Response(
                {"detail": "Термін прийому пропозицій завершено."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return Response(
                {"detail": "Неможливо визначити компанію."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        supplier_company_id, error_response = _resolve_request_company_id(request)
        if error_response:
            return error_response
        if not _is_company_invited_to_tender(
            tender=tender,
            supplier_company_id=supplier_company_id,
            is_sales=True,
        ):
            return Response(
                {"detail": "Your company is not invited to this tender."},
                status=status.HTTP_403_FORBIDDEN,
            )
        proposal = SalesTenderProposal.objects.select_related("created_by").filter(
            tender=tender, supplier_company_id=supplier_company_id
        ).first()
        if not proposal:
            return Response(
                {"detail": "Пропозицію не знайдено. Спочатку підтвердіть участь."},
                status=status.HTTP_404_NOT_FOUND,
            )
        locked_response = _ensure_user_can_manage_company_proposal(
            proposal=proposal,
            user=request.user,
        )
        if locked_response:
            return locked_response
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
        """Відкликати пропозицію (компанія поточного користувача)."""
        tender = SalesTender.objects.filter(pk=pk).first()
        if not tender:
            return Response({"detail": "Тендер не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        if tender.stage != "acceptance":
            return Response(
                {"detail": "Відкликати пропозицію можна лише під час етапу прийому пропозицій."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if tender.end_at and timezone.now() > tender.end_at:
            return Response(
                {"detail": "Термін прийому пропозицій завершено."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return Response(
                {"detail": "Неможливо визначити компанію."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        supplier_company_id, error_response = _resolve_request_company_id(request)
        if error_response:
            return error_response
        if not _is_company_invited_to_tender(
            tender=tender,
            supplier_company_id=supplier_company_id,
            is_sales=True,
        ):
            return Response(
                {"detail": "Your company is not invited to this tender."},
                status=status.HTTP_403_FORBIDDEN,
            )
        proposal = SalesTenderProposal.objects.select_related("created_by").filter(
            tender=tender, supplier_company_id=supplier_company_id
        ).first()
        if not proposal:
            return Response(
                {"detail": "Пропозицію не знайдено."},
                status=status.HTTP_404_NOT_FOUND,
            )
        locked_response = _ensure_user_can_manage_company_proposal(
            proposal=proposal,
            user=request.user,
        )
        if locked_response:
            return locked_response
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
        """Усі тури сімейства (від кореня + усі наступні) для випадаючого списку."""
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

    @extend_schema(
        responses=OpenApiTypes.OBJECT,
        summary="Tender protocol preview",
        description="Return structured tender protocol payload for modal preview.",
    )
    @action(detail=True, methods=["get"], url_path="protocol-preview")
    def protocol_preview(self, request, pk=None):
        tender = self.get_object()
        return Response(_build_tender_protocol_payload(tender=tender, is_sales=True))

    @extend_schema(
        responses={200: OpenApiTypes.BINARY},
        summary="Tender protocol PDF",
        description="Generate tender protocol in PDF format.",
    )
    @action(detail=True, methods=["get"], url_path="protocol-pdf")
    def protocol_pdf(self, request, pk=None):
        tender = self.get_object()
        return _build_tender_protocol_pdf_response(
            tender=tender,
            is_sales=True,
            download=request.query_params.get("download"),
        )

    @action(detail=True, methods=["get"], url_path="decision-market-reference")
    def decision_market_reference(self, request, pk=None):
        tender = self.get_object()
        payload = _build_decision_market_reference_payload(
            tender=tender,
            is_sales=True,
        )
        return Response(payload)

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

    @action(detail=True, methods=["get"], url_path="bid-history")
    def bid_history(self, request, pk=None):
        tender = self.get_object()
        position_id = _parse_int_param(request.query_params.get("tender_position_id"), min_value=1)
        if not position_id:
            return Response(
                {"detail": "Передайте tender_position_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = TenderBidHistory.objects.filter(
            tender_type="sales",
            tender_id=int(tender.id),
            tender_position_id=position_id,
        ).select_related("supplier_company", "created_by")
        serializer = TenderBidHistorySerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="chat/threads")
    def chat_threads(self, request, pk=None):
        tender = _get_tender_for_owner_or_participant(
            user=request.user,
            tender_id=pk,
            is_sales=True,
        )
        if not tender:
            return Response({"detail": "Тендер не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        user_company_ids = set(_user_company_ids(request.user))
        is_owner = int(tender.company_id) in user_company_ids
        if is_owner:
            _ensure_tender_chat_threads_for_submitted_participants(
                tender=tender,
                is_sales=True,
            )
        qs = TenderChatThread.objects.filter(
            tender_type="sales",
            tender_id=int(tender.id),
        ).select_related("supplier_company")
        if not is_owner:
            qs = qs.filter(supplier_company_id__in=user_company_ids).exclude(
                supplier_company_id=tender.company_id
            )
        qs = _annotate_tender_chat_threads_unread(
            qs=qs,
            tender=tender,
            is_owner=is_owner,
        )
        serializer = TenderChatThreadSerializer(
            qs.order_by("-last_message_at", "-updated_at"),
            many=True,
        )
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"], url_path="chat/messages")
    def chat_messages(self, request, pk=None):
        tender = _get_tender_for_owner_or_participant(
            user=request.user,
            tender_id=pk,
            is_sales=True,
        )
        if not tender:
            return Response({"detail": "Тендер не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        user_company_ids = set(_user_company_ids(request.user))
        is_owner = int(tender.company_id) in user_company_ids
        supplier_company_id_raw = (
            request.query_params.get("supplier_company_id")
            if request.method == "GET"
            else request.data.get("supplier_company_id")
        )
        supplier_company_id = None
        if is_owner:
            supplier_company_id = _parse_int_param(supplier_company_id_raw, min_value=1)
            if not supplier_company_id:
                return Response(
                    {"detail": "Передайте supplier_company_id."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            participant_company_ids = _resolve_tender_chat_participant_company_ids(
                tender=tender,
                is_sales=True,
                user_company_ids=user_company_ids,
            )
            if not participant_company_ids:
                return Response({"detail": "Компанію учасника не визначено."}, status=status.HTTP_403_FORBIDDEN)
            requested_company_id = _parse_int_param(supplier_company_id_raw, min_value=1)
            supplier_company_id = requested_company_id or participant_company_ids[0]
            if supplier_company_id not in participant_company_ids:
                return Response({"detail": "Немає доступу до цього чату."}, status=status.HTTP_403_FORBIDDEN)

        thread, _ = _get_or_create_tender_chat_thread(
            tender=tender,
            is_sales=True,
            supplier_company_id=supplier_company_id,
        )
        if request.method == "GET":
            qs = thread.messages.select_related("author_user", "author_company").all()
            _mark_tender_chat_thread_read(thread=thread, is_owner=is_owner)
            serializer = TenderChatMessageSerializer(qs, many=True)
            return Response(serializer.data)

        body = str(request.data.get("body") or "").strip()
        if not body:
            return Response({"detail": "Текст повідомлення обов'язковий."}, status=status.HTTP_400_BAD_REQUEST)
        author_company_id = tender.company_id if is_owner else supplier_company_id
        with transaction.atomic():
            message = TenderChatMessage.objects.create(
                thread=thread,
                author_user=request.user,
                author_company_id=author_company_id,
                body=body,
            )
            thread.last_message_at = message.created_at
            thread.save(update_fields=["last_message_at", "updated_at"])
        _notify_tender_chat_message(
            tender=tender,
            is_sales=True,
            thread=thread,
            message=message,
            actor=request.user,
        )
        serializer = TenderChatMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="proposal-change-report")
    def proposal_change_report(self, request, pk=None):
        tender = self.get_object()
        _ensure_user_can_edit_tender(user=request.user, tender=tender, is_sales=True)
        position_names = {
            int(pos.id): getattr(pos, "name", "") or getattr(getattr(pos, "nomenclature", None), "name", "")
            for pos in tender.positions.all()
        }
        qs = TenderProposalChangeLog.objects.filter(
            tender_type="sales",
            tender_id=int(tender.id),
        ).select_related("supplier_company", "updated_by")
        data = list(TenderProposalChangeLogSerializer(qs, many=True).data)
        for row in data:
            row["position_name"] = position_names.get(int(row.get("tender_position_id") or 0), "")
        return Response(data)

    @action(detail=True, methods=["post"], url_path="disqualify-proposals")
    def disqualify_proposals(self, request, pk=None):
        tender = self.get_object()
        _ensure_user_can_edit_tender(user=request.user, tender=tender, is_sales=True)
        items = request.data.get("items") or []
        if not isinstance(items, list):
            return Response({"detail": "items має бути масивом."}, status=status.HTTP_400_BAD_REQUEST)
        touched_ids = []
        with transaction.atomic():
            for item in items:
                proposal_id = _parse_int_param(item.get("proposal_id"), min_value=1)
                if not proposal_id:
                    continue
                proposal = SalesTenderProposal.objects.filter(tender=tender, id=proposal_id).first()
                if not proposal:
                    continue
                should_disqualify = bool(item.get("disqualify"))
                comment = str(item.get("comment") or "").strip()
                if should_disqualify and not comment:
                    return Response(
                        {"detail": "Для дискваліфікації потрібно вказати коментар.", "proposal_id": proposal_id},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                proposal.disqualified_at = timezone.now() if should_disqualify else None
                proposal.disqualification_comment = comment if should_disqualify else ""
                proposal.disqualified_by = request.user if should_disqualify else None
                proposal.status_updated_at = timezone.now()
                proposal.save(
                    update_fields=[
                        "disqualified_at",
                        "disqualification_comment",
                        "disqualified_by",
                        "status_updated_at",
                    ]
                )
                touched_ids.append(int(proposal.id))
            if touched_ids:
                SalesTenderPosition.objects.filter(
                    tender=tender,
                    winner_proposal_id__in=touched_ids,
                ).update(winner_proposal=None)
        qs = SalesTenderProposal.objects.filter(tender=tender).select_related("supplier_company", "disqualified_by").prefetch_related(
            "position_values__tender_position__nomenclature__unit"
        )
        return Response(SalesTenderProposalSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="carry-previous-tour-proposals")
    def carry_previous_tour_proposals(self, request, pk=None):
        tender = self.get_object()
        _ensure_user_can_edit_tender(user=request.user, tender=tender, is_sales=True)
        if int(getattr(tender, "tour_number", 1) or 1) <= 1 or not getattr(tender, "parent_id", None):
            return Response(
                {"detail": "На першому турі перенесення з попереднього туру недоступне."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = _copy_sales_proposals_from_previous_tour(tender=tender, actor=request.user)
        return Response(result)

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
        Зафіксувати рішення: winner - з переможцями по позиціях, cancel - без переможців,
        next_round - створити наступний тур на етапі підготовки.
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
                {"detail": "mode має бути: winner, cancel або next_round."},
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
                    proposal = SalesTenderProposal.objects.filter(tender=tender, id=prop_id).first()
                    if proposal and proposal.disqualified_at:
                        return Response(
                            {"detail": "Дискваліфіковану пропозицію не можна обрати переможцем.", "proposal_id": prop_id},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    if pos and proposal:
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
            auction_model=getattr(
                parent,
                "auction_model",
                SalesTender.AuctionModel.CLASSIC_AUCTION,
            ),
            publication_type=parent.publication_type,
            currency=parent.currency,
            general_terms=parent.general_terms or "",
            invited_emails=getattr(parent, "invited_emails", []) or [],
            planned_start_at=getattr(parent, "planned_start_at", None),
            planned_end_at=getattr(parent, "planned_end_at", None),
            price_criterion_vat=parent.price_criterion_vat or "",
            price_criterion_vat_percent=parent.price_criterion_vat_percent,
            price_criterion_delivery=parent.price_criterion_delivery or "",
            approval_model=parent.approval_model,
            uses_position_warehouses=bool(
                getattr(parent, "uses_position_warehouses", False)
            ),
            created_by=request.user,
        )
        new_tender.cpv_categories.set(parent.cpv_categories.all())
        new_tender.tender_criteria.set(parent.tender_criteria.all())
        _sync_tender_invited_suppliers(
            tender=new_tender,
            supplier_company_ids=list(
                parent.invited_supplier_links.values_list("supplier_company_id", flat=True)
            ),
            is_sales=True,
        )
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
                warehouse=pos.warehouse,
            )
        return Response({"stage": "preparation", "id": new_tender.id}, status=status.HTTP_201_CREATED)

    @extend_schema(responses=SalesTenderProposalSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="proposals")
    def proposals_list(self, request, pk=None):
        """Список пропозицій по тендеру на продаж."""
        tender = _get_tender_for_owner_or_participant(
            user=request.user,
            tender_id=pk,
            is_sales=True,
        )
        if not tender:
            return Response({"detail": "Tender not found."}, status=status.HTTP_404_NOT_FOUND)
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
                "supplier_company", "disqualified_by"
            )
            if updated_since is not None:
                qs = qs.filter(status_updated_at__gt=updated_since)
            if proposal_ids:
                qs = qs.filter(id__in=proposal_ids)
            elif "ids" in request.query_params:
                return Response([])
            qs, _ = _filter_tender_proposals_for_user(qs=qs, tender=tender, user=request.user)
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
            "supplier_company", "disqualified_by"
        ).prefetch_related(
            "position_values__tender_position__nomenclature__unit",
        )
        if proposal_ids:
            qs = qs.filter(id__in=proposal_ids)
        elif "ids" in request.query_params:
            return Response([])
        qs, _ = _filter_tender_proposals_for_user(qs=qs, tender=tender, user=request.user)
        serializer = SalesTenderProposalSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(request=SalesTenderProposalSerializer, responses=SalesTenderProposalSerializer)
    @action(detail=True, methods=["post"], url_path="proposals/add")
    def proposal_add(self, request, pk=None):
        """Додати пропозицію (обрати контрагента)."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        supplier_company_id = request.data.get("supplier_company_id") or request.data.get("supplier_company")
        if not supplier_company_id:
            return Response(
                {"detail": "Потрібно вказати supplier_company_id."},
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
        """Оновити значення по позиціях пропозиції."""
        tender = _get_tender_for_owner_or_participant(
            user=request.user,
            tender_id=pk,
            is_sales=True,
        )
        if not tender:
            return Response({"detail": "Тендер не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        proposal_qs = SalesTenderProposal.objects.filter(
            tender=tender,
            id=proposal_id,
        ).prefetch_related("position_values__tender_position")
        proposal_qs, actor_represents_owner = _filter_tender_proposals_for_user(
            qs=proposal_qs,
            tender=tender,
            user=request.user,
        )
        proposal = proposal_qs.first()
        if not proposal:
            return Response({"detail": "Пропозицію не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        if not actor_represents_owner:
            locked_response = _ensure_user_can_manage_company_proposal(
                proposal=proposal,
                user=request.user,
            )
            if locked_response:
                return locked_response
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
            previous_price = pv.price
            previous_criterion_values = pycopy.deepcopy(pv.criterion_values or {})
            has_changes = False
            if "price" in item:
                next_price = item["price"]
                if pv.price != next_price:
                    pv.price = next_price
                    has_changes = True
            if "criterion_values" in item:
                next_criterion_values = item["criterion_values"] or {}
                if (pv.criterion_values or {}) != next_criterion_values:
                    pv.criterion_values = next_criterion_values
                    has_changes = True
            if not has_changes:
                continue
            pv.save()
            changed_position_ids.add(int(tp_id))
            if "price" in item and previous_price != pv.price:
                _record_tender_bid_history(
                    tender=tender,
                    is_sales=True,
                    proposal=proposal,
                    tender_position_id=tp_id,
                    price=pv.price,
                    actor=request.user,
                )
            if actor_represents_owner and tender.stage == SalesTender.Stage.DECISION:
                _record_tender_proposal_change_log(
                    tender=tender,
                    is_sales=True,
                    proposal=proposal,
                    tender_position_id=tp_id,
                    original_price=previous_price,
                    original_criterion_values=previous_criterion_values,
                    current_price=pv.price,
                    current_criterion_values=pv.criterion_values or {},
                    actor=request.user,
                )
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
        """Деталі пропозиції."""
        tender = _get_tender_for_owner_or_participant(
            user=request.user,
            tender_id=pk,
            is_sales=True,
        )
        if not tender:
            return Response({"detail": "Тендер не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        proposal_qs = SalesTenderProposal.objects.filter(
            tender=tender, id=proposal_id
        ).select_related("supplier_company", "disqualified_by").prefetch_related(
            "position_values__tender_position__nomenclature__unit",
        )
        proposal_qs, _ = _filter_tender_proposals_for_user(
            qs=proposal_qs,
            tender=tender,
            user=request.user,
        )
        proposal = proposal_qs.first()
        if not proposal:
            return Response({"detail": "Пропозицію не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SalesTenderProposalSerializer(proposal)
        return Response(serializer.data)

    @extend_schema(responses=SalesTenderFileSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="files")
    def files_list(self, request, pk=None):
        """Список прикріплених файлів."""
        tender = _get_tender_for_owner_or_participant(
            user=request.user,
            tender_id=pk,
            is_sales=True,
        )
        if not tender:
            return Response({"detail": "Тендер не знайдено."}, status=status.HTTP_404_NOT_FOUND)
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
        """Прикріпити файл до тендера на продаж."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        file_obj = request.FILES.get("file") or request.FILES.get("file_upload")
        if not file_obj:
            return Response(
                {"detail": "Надішліть файл у полі file або file_upload."},
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
        """Видалити прикріплений файл."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        obj = SalesTenderFile.objects.filter(tender=tender, id=file_id).first()
        if not obj:
            return Response({"detail": "Файл не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["patch"], url_path=r"files/(?P<file_id>\d+)")
    def file_patch(self, request, pk=None, file_id=None):
        """Оновити видимість файлу учасникам."""
        tender = self.get_object()
        _ensure_user_can_edit_tender(
            user=request.user,
            tender=tender,
            is_sales=True,
        )
        obj = SalesTenderFile.objects.filter(tender=tender, id=file_id).first()
        if not obj:
            return Response({"detail": "Файл не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        if "visible_to_participants" in request.data:
            obj.visible_to_participants = bool(request.data["visible_to_participants"])
            obj.save(update_fields=["visible_to_participants"])
        serializer = SalesTenderFileSerializer(obj, context={"request": request})
        return Response(serializer.data)
