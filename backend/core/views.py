from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils import timezone
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
    CpvDictionary,
    ExpenseArticle,
    ExpenseArticleUser,
    Currency,
    TenderCriterion,
    ProcurementTender,
    ProcurementTenderPosition,
    TenderProposal,
    TenderProposalPosition,
    ProcurementTenderFile,
    SalesTender,
    SalesTenderPosition,
    SalesTenderProposal,
    SalesTenderProposalPosition,
    SalesTenderFile,
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
    ExistingCompanyStep2Serializer,
    CompanyCpvSerializer,
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
    ProcurementTenderSerializer,
    TenderProposalSerializer,
    TenderProposalPositionUpdateSerializer,
    ProcurementTenderFileSerializer,
    SalesTenderSerializer,
    SalesTenderProposalSerializer,
    SalesTenderFileSerializer,
)

User = get_user_model()


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
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
    """Step 2: Create new company and assign user as admin."""
    serializer = CompanyRegistrationStep2Serializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user_id = serializer.validated_data["user_id"]
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"user_id": "РљРѕСЂРёСЃС‚СѓРІР°С‡ РЅРµ Р·РЅР°Р№РґРµРЅРёР№."}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        company = Company.objects.create(
            edrpou=serializer.validated_data["edrpou"],
            name=serializer.validated_data["name"],
            goal_tenders=serializer.validated_data["goal_tenders"],
            goal_participation=serializer.validated_data["goal_participation"],
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
    """Step 2: Join existing company by code (Р„Р”Р РџРћРЈ). РЇРєС‰Рѕ С†Рµ РїРµСЂС€РёР№ РєРѕСЂРёСЃС‚СѓРІР°С‡ РєРѕРјРїР°РЅС–С— вЂ” РѕРЅРѕРІР»СЋС”РјРѕ РЅР°Р·РІСѓ С‚Р° РѕРґСЂР°Р·Сѓ СЃС…РІР°Р»СЋС”РјРѕ."""
    serializer = ExistingCompanyStep2Serializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user_id = serializer.validated_data["user_id"]
    edrpou = serializer.validated_data["edrpou"]
    new_name = (serializer.validated_data.get("name") or "").strip()

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"user_id": "РљРѕСЂРёСЃС‚СѓРІР°С‡ РЅРµ Р·РЅР°Р№РґРµРЅРёР№."}, status=status.HTTP_400_BAD_REQUEST)

    company = Company.objects.filter(edrpou=edrpou, status=Company.Status.ACTIVE).first()
    if not company:
        return Response({"edrpou": "РљРѕРјРїР°РЅС–СЋ Р· С‚Р°РєРёРј РєРѕРґРѕРј РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_400_BAD_REQUEST)

    if CompanyUser.objects.filter(user=user, company=company).exists():
        return Response(
            {"non_field_errors": "РљРѕСЂРёСЃС‚СѓРІР°С‡ РІР¶Рµ РјР°С” Р·РІ'СЏР·РѕРє Р· С†С–С”СЋ РєРѕРјРїР°РЅС–С”СЋ."}, status=status.HTTP_400_BAD_REQUEST
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

    return Response(CompanyUserSerializer(membership).data, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Р РµС”СЃС‚СЂР°С†С–СЏ - РљСЂРѕРє 3 (CPV-РєР°С‚РµРіРѕСЂС–С— РєРѕРјРїР°РЅС–С—)",
    description=(
        "Р—Р°РєСЂС–РїР»РµРЅРЅСЏ CPV-РєР°С‚РµРіРѕСЂС–Р№ Р·Р° РєРѕРјРїР°РЅС–С”СЋ РїС–Рґ С‡Р°СЃ СЂРµС”СЃС‚СЂР°С†С–С—.\n"
        "- РЇРєС‰Рѕ С†Рµ РїРµСЂС€РёР№ РїС–РґС‚РІРµСЂРґР¶РµРЅРёР№ РєРѕСЂРёСЃС‚СѓРІР°С‡ РєРѕРјРїР°РЅС–С— вЂ” СЃРїРёСЃРѕРє РєР°С‚РµРіРѕСЂС–Р№ РїРµСЂРµР·Р°РїРёСЃСѓС”С‚СЊСЃСЏ.\n"
        "- РЇРєС‰Рѕ РїС–РґС‚РІРµСЂРґР¶РµРЅРёС… РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ РІР¶Рµ Р±С–Р»СЊС€Рµ РѕРґРЅРѕРіРѕ вЂ” С–СЃРЅСѓСЋС‡С– РєР°С‚РµРіРѕСЂС–С— РЅРµ РІРёРґР°Р»СЏСЋС‚СЊСЃСЏ, "
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
    """
    Step 3: РџСЂРёРІ'СЏР·РєР° CPV-РєР°С‚РµРіРѕСЂС–Р№ РґРѕ РєРѕРјРїР°РЅС–С— РїС–Рґ С‡Р°СЃ СЂРµС”СЃС‚СЂР°С†С–С—.

    Р”Р»СЏ РїРµСЂС€РѕРіРѕ РїС–РґС‚РІРµСЂРґР¶РµРЅРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р° РєРѕРјРїР°РЅС–С— РґРѕР·РІРѕР»СЏС”РјРѕ Р·Р°РґР°С‚Рё РїРѕРІРЅРёР№ СЃРїРёСЃРѕРє.
    Р”Р»СЏ РЅР°СЃС‚СѓРїРЅРёС… РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ вЂ” Р»РёС€Рµ РґРѕРґР°С”РјРѕ РЅРѕРІС– РєР°С‚РµРіРѕСЂС–С—, РЅРµ РІРёРґР°Р»СЏСЋС‡Рё С–СЃРЅСѓСЋС‡С–.
    """
    user_id = request.data.get("user_id")
    company_id = request.data.get("company_id")
    cpv_ids = request.data.get("cpv_ids") or []

    if not user_id:
        return Response({"user_id": "РџРѕР»Рµ РѕР±РѕРІ'СЏР·РєРѕРІРµ."}, status=status.HTTP_400_BAD_REQUEST)
    if not company_id:
        return Response({"company_id": "РџРѕР»Рµ РѕР±РѕРІ'СЏР·РєРѕРІРµ."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"user_id": "РљРѕСЂРёСЃС‚СѓРІР°С‡ РЅРµ Р·РЅР°Р№РґРµРЅРёР№."}, status=status.HTTP_400_BAD_REQUEST)

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

    # Р’РёР·РЅР°С‡Р°С”РјРѕ, С‡Рё С†Рµ РїРµСЂС€РёР№ РїС–РґС‚РІРµСЂРґР¶РµРЅРёР№ РєРѕСЂРёСЃС‚СѓРІР°С‡ РєРѕРјРїР°РЅС–С—
    approved_members_qs = CompanyUser.objects.filter(
        company=company, status=CompanyUser.Status.APPROVED
    )
    approved_count = approved_members_qs.count()

    cpv_ids = [int(x) for x in cpv_ids if str(x).isdigit()]
    existing_ids = set(company.cpv_categories.values_list("id", flat=True))

    if approved_count <= 1:
        # РџРµСЂС€РёР№ РїС–РґС‚РІРµСЂРґР¶РµРЅРёР№ РєРѕСЂРёСЃС‚СѓРІР°С‡: РїРѕРІРЅР° Р·Р°РјС–РЅР° СЃРїРёСЃРєСѓ
        company.cpv_categories.set(cpv_ids)
    else:
        # РќР°СЃС‚СѓРїРЅС– РєРѕСЂРёСЃС‚СѓРІР°С‡С–: РЅРµ РґРѕР·РІРѕР»СЏС”РјРѕ РІРёРґР°Р»СЏС‚Рё РІР¶Рµ С–СЃРЅСѓСЋС‡С– РєР°С‚РµРіРѕСЂС–С—
        new_ids = set(cpv_ids)
        union_ids = sorted(existing_ids.union(new_ids))
        company.cpv_categories.set(union_ids)

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

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def members(self, request, pk=None):
        """РЎРїРёСЃРѕРє РєРѕСЂРёСЃС‚СѓРІР°С‡С–РІ (Р°РіРµРЅС‚С–РІ) РєРѕРјРїР°РЅС–С—."""
        company = self.get_object()
        memberships = CompanyUser.objects.filter(company=company).select_related(
            "user", "role"
        ).order_by("-created_at")
        serializer = CompanyUserSerializer(memberships, many=True)
        return Response(serializer.data)


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
    Р”РѕРґР°РІР°РЅРЅСЏ: Р°Р±Рѕ supplier_company_id, Р°Р±Рѕ edrpou (СЏРєС‰Рѕ РєРѕРјРїР°РЅС–СЏ С” вЂ” Р»РёС€Рµ Р·РІ'СЏР·РѕРє; СЏРєС‰Рѕ РЅРµРјР°С” вЂ” name РѕР±РѕРІ'СЏР·РєРѕРІР°, СЃС‚РІРѕСЂСЋС”С‚СЊСЃСЏ РєРѕРјРїР°РЅС–СЏ).
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
        РїС–РґС‚РІРµСЂРґР¶РµРЅРёР№ СЃС‚Р°С‚СѓСЃ. Р РѕР»С– РЅРµ РІСЂР°С…РѕРІСѓСЋС‚СЊСЃСЏ.
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
        response_serializer.instance = user
        return Response(response_serializer.data)
    serializer = MeSerializer(
        {"user": request.user, "memberships": request.user.memberships.all(), "permissions": []},
        context={"request": request},
    )
    serializer.instance = request.user
    return Response(serializer.data)


AVATAR_MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _is_allowed_avatar_content_type(content_type):
    if not content_type:
        return False
    ct = content_type.split(";")[0].strip().lower()
    return ct in ("image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp") or ct.startswith("image/")


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
        return Response({"detail": "Р РѕР·РјС–СЂ С„Р°Р№Р»Сѓ РЅРµ РїРѕРІРёРЅРµРЅ РїРµСЂРµРІРёС‰СѓРІР°С‚Рё 5 РњР‘."}, status=status.HTTP_400_BAD_REQUEST)
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
        """Filter by user's companies."""
        user = self.request.user
        if user.is_superuser:
            return Branch.objects.all()
        # Only show branches for companies where user is member
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        return Branch.objects.filter(company_id__in=user_companies).select_related("parent", "company")

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

        return queryset.select_related("parent", "branch")

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

    permission_classes = [permissions.IsAuthenticated]

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

        if parent_level_code:
            qs = CpvDictionary.objects.filter(cpv_parent_code=parent_level_code)
        else:
            qs = CpvDictionary.objects.filter(
                Q(cpv_parent_code__isnull=True) | Q(cpv_parent_code="") | Q(cpv_parent_code="0")
            )

        qs = qs.order_by("cpv_code")
        items = list(qs)
        level_codes = [item.cpv_level_code for item in items if item.cpv_level_code]

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
                "label": f"{item.cpv_code} - {item.name_ua}",
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
            CpvDictionary.objects.filter(companies_by_cpvs__isnull=False)
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
        """Filter by user's companies."""
        user = self.request.user
        if user.is_superuser:
            return ExpenseArticle.objects.all().select_related("parent", "company")
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        return ExpenseArticle.objects.filter(company_id__in=user_companies).select_related("parent", "company")

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
    Р”РѕРІС–РґРЅРёРє РѕРґРёРЅРёС†СЊ РІРёРјС–СЂСѓ вЂ” СЃРїС–Р»СЊРЅРёР№ РґР»СЏ РІСЃС–С… РєРѕРјРїР°РЅС–Р№.
    РЎРїРёСЃРѕРє РѕРґРёРЅРёС†СЊ (СЃРїС–Р»СЊРЅС– company=null + РѕРґРёРЅРёС†С– РєРѕРјРїР°РЅС–Р№ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°).
    РќР°РїРѕРІРЅРµРЅРЅСЏ вЂ” С‡РµСЂРµР· Р‘Р”; СЃС‚РІРѕСЂРµРЅРЅСЏ/СЂРµРґР°РіСѓРІР°РЅРЅСЏ С‡РµСЂРµР· API РІРёРјРєРЅРµРЅРѕ.
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

        if name:
            qs = qs.filter(name__icontains=name)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if cpv_id:
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
            return TenderCriterion.objects.all().select_related("company")
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        return TenderCriterion.objects.filter(
            company_id__in=user_companies
        ).select_related("company")


class ProcurementTenderViewSet(viewsets.ModelViewSet):
    """
    РўРµРЅРґРµСЂРё РЅР° Р·Р°РєСѓРїС–РІР»СЋ (company-scoped). РќРѕРјРµСЂ РїСЂРёСЃРІРѕСЋС”С‚СЊСЃСЏ РїСЂРё РїРµСЂС€РѕРјСѓ Р·Р±РµСЂРµР¶РµРЅРЅС–.
    Р”РѕСЃС‚СѓРї: Р±СѓРґСЊ-СЏРєРёР№ Р°РІС‚РѕСЂРёР·РѕРІР°РЅРёР№ РєРѕСЂРёСЃС‚СѓРІР°С‡ Р· РїС–РґС‚РІРµСЂРґР¶РµРЅРёРј С‡Р»РµРЅСЃС‚РІРѕРј Сѓ РєРѕРјРїР°РЅС–С—.
    РџСЂР°РІР° РґРѕСЃС‚СѓРїСѓ (tenders.create С‚РѕС‰Рѕ) РЅРµ РїРµСЂРµРІС–СЂСЏСЋС‚СЊСЃСЏ вЂ” РѕР±РјРµР¶РµРЅРЅСЏ Р·РЅСЏС‚Рѕ Р·Р° Р±Р°Р¶Р°РЅРЅСЏРј Р·Р°РјРѕРІРЅРёРєР°.
    """

    serializer_class = ProcurementTenderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return ProcurementTender.objects.all().select_related(
                "company", "category", "cpv_category", "expense_article",
                "branch", "department", "currency", "created_by", "parent",
            ).prefetch_related("positions__nomenclature__unit", "tender_criteria")
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        return ProcurementTender.objects.filter(
            company_id__in=user_companies
        ).select_related(
            "company", "category", "cpv_category", "expense_article",
            "branch", "department", "currency", "created_by", "parent",
        ).prefetch_related("positions__nomenclature__unit", "tender_criteria")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

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
            ).prefetch_related("positions__nomenclature__unit", "tender_criteria").first()
            if obj:
                return obj
            # Дозволяємо перегляд деталей тендера, доступного для участі, ще до підтвердження участі.
            obj = ProcurementTender.objects.filter(
                ~Q(company_id__in=user_company_ids),
                pk=pk,
                conduct_type__in=["rfx", "online_auction"],
                stage__in=["acceptance", "decision", "approval", "completed"],
            ).select_related(
                "company", "category", "cpv_category", "expense_article",
                "branch", "department", "currency", "created_by", "parent",
            ).prefetch_related("positions__nomenclature__unit", "tender_criteria").first()
            if obj:
                return obj
        raise Http404("РўРµРЅРґРµСЂ РЅРµ Р·РЅР°Р№РґРµРЅРѕ.")

    @extend_schema(
        parameters=[
            OpenApiParameter(name="tab", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="active | processing | completed"),
        ],
        responses=ProcurementTenderSerializer(many=True),
    )
    @action(detail=False, methods=["get"], url_path="for-participation")
    def for_participation(self, request):
        """РЎРїРёСЃРѕРє С‚РµРЅРґРµСЂС–РІ РґР»СЏ СѓС‡Р°СЃС‚С– (С–РЅС€РёС… РєРѕРјРїР°РЅС–Р№): РђРєС‚РёРІРЅС– / РћРїСЂР°С†СЊРѕРІСѓСЋС‚СЊСЃСЏ / Р—Р°РІРµСЂС€РµРЅС–."""
        user = request.user
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return Response([])
        tab = (request.query_params.get("tab") or "active").strip().lower()
        qs = (
            ProcurementTender.objects.filter(
                ~Q(company_id__in=user_company_ids),
                conduct_type__in=["rfx", "online_auction"],
                stage__in=["acceptance", "decision", "approval", "completed"],
            )
            .select_related(
                "company", "currency", "parent",
            )
            .prefetch_related("positions__nomenclature__unit", "tender_criteria")
            .order_by("-updated_at")
        )
        if tab == "active":
            qs = qs.filter(stage="acceptance")
        elif tab == "processing":
            qs = qs.filter(
                Q(stage="decision") | Q(stage="approval")
                | (Q(stage="preparation") & Q(tour_number__gt=1))
            )
        elif tab == "completed":
            qs = qs.filter(stage="completed")
        serializer = ProcurementTenderSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(responses=TenderProposalSerializer)
    @action(detail=True, methods=["post"], url_path="confirm-participation")
    def confirm_participation(self, request, pk=None):
        """РџС–РґС‚РІРµСЂРґРёС‚Рё СѓС‡Р°СЃС‚СЊ: СЃС‚РІРѕСЂСЋС” РїСЂРѕРїРѕР·РёС†С–СЋ С‚Р° РґРѕРґР°С” РєРѕРЅС‚СЂР°РіРµРЅС‚Р° РІ РґРѕРІС–РґРЅРёРє РѕСЂРіР°РЅС–Р·Р°С‚РѕСЂР°."""
        tender = ProcurementTender.objects.filter(pk=pk).select_related("company").first()
        if not tender:
            return Response({"detail": "РўРµРЅРґРµСЂ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
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
        proposal.submitted_at = timezone.now()
        proposal.save(update_fields=["submitted_at"])
        serializer = TenderProposalSerializer(proposal)
        return Response(serializer.data)

    @extend_schema(responses=TenderProposalSerializer)
    @action(detail=True, methods=["post"], url_path="withdraw-proposal")
    def withdraw_proposal(self, request, pk=None):
        """Р’С–РґРєР»РёРєР°С‚Рё РїСЂРѕРїРѕР·РёС†С–СЋ (РєРѕРјРїР°РЅС–СЏ РїРѕС‚РѕС‡РЅРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°)."""
        tender = ProcurementTender.objects.filter(pk=pk).first()
        if not tender:
            return Response({"detail": "РўРµРЅРґРµСЂ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
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
        proposal.save(update_fields=["submitted_at"])
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
                },
                "required": ["mode"],
            }
        },
    )
    @action(detail=True, methods=["post"], url_path="fix-decision")
    def fix_decision(self, request, pk=None):
        """
        Р—Р°С„С–РєСЃСѓРІР°С‚Рё СЂС–С€РµРЅРЅСЏ: winner вЂ” Р· РїРµСЂРµРјРѕР¶С†СЏРјРё РїРѕ РїРѕР·РёС†С–СЏС…, cancel вЂ” Р±РµР· РїРµСЂРµРјРѕР¶С†С–РІ,
        next_round вЂ” СЃС‚РІРѕСЂРёС‚Рё РЅР°СЃС‚СѓРїРЅРёР№ С‚СѓСЂ РЅР° РµС‚Р°РїС– РїС–РґРіРѕС‚РѕРІРєРё.
        """
        tender = self.get_object()
        mode = request.data.get("mode")
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
            return Response({"stage": "approval", "id": tender.id})
        if mode == "cancel":
            ProcurementTenderPosition.objects.filter(tender=tender).update(winner_proposal=None)
            tender.stage = "approval"
            tender.save(update_fields=["stage"])
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
            created_by=request.user,
        )
        new_tender.cpv_categories.set(parent.cpv_categories.all())
        new_tender.tender_criteria.set(parent.tender_criteria.all())
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
        qs = TenderProposal.objects.filter(tender=tender).select_related(
            "supplier_company"
        ).prefetch_related(
            "position_values__tender_position__nomenclature__unit",
        )
        serializer = TenderProposalSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(request=TenderProposalSerializer, responses=TenderProposalSerializer)
    @action(detail=True, methods=["post"], url_path="proposals/add")
    def proposal_add(self, request, pk=None):
        """Р”РѕРґР°С‚Рё РїСЂРѕРїРѕР·РёС†С–СЋ (РѕР±СЂР°С‚Рё РєРѕРЅС‚СЂР°РіРµРЅС‚Р°)."""
        tender = self.get_object()
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
        proposal = TenderProposal.objects.filter(
            tender=tender, id=proposal_id
        ).prefetch_related("position_values__tender_position").first()
        if not proposal:
            return Response({"detail": "РџСЂРѕРїРѕР·РёС†С–СЋ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        payload = TenderProposalPositionUpdateSerializer(data=request.data)
        if not payload.is_valid():
            return Response(payload.errors, status=status.HTTP_400_BAD_REQUEST)
        position_values_data = payload.validated_data.get("position_values") or []
        for item in position_values_data:
            tp_id = item.get("tender_position_id")
            if not tp_id:
                continue
            pos = ProcurementTenderPosition.objects.filter(
                tender=tender, id=tp_id
            ).first()
            if not pos:
                continue
            pv, _ = TenderProposalPosition.objects.get_or_create(
                proposal=proposal, tender_position=pos,
                defaults={"price": None, "criterion_values": {}},
            )
            if "price" in item:
                pv.price = item["price"]
            if "criterion_values" in item:
                pv.criterion_values = item["criterion_values"]
            pv.save()
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
        serializer = ProcurementTenderFileSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(request=OpenApiTypes.BINARY, responses=ProcurementTenderFileSerializer)
    @action(detail=True, methods=["post"], url_path="files/upload")
    def file_upload(self, request, pk=None):
        """РџСЂРёРєСЂС–РїРёС‚Рё С„Р°Р№Р» РґРѕ С‚РµРЅРґРµСЂР°."""
        tender = self.get_object()
        file_obj = request.FILES.get("file") or request.FILES.get("file_upload")
        if not file_obj:
            return Response(
                {"detail": "РќР°РґС–С€Р»С–С‚СЊ С„Р°Р№Р» Сѓ РїРѕР»С– file Р°Р±Рѕ file_upload."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
        obj = ProcurementTenderFile.objects.filter(tender=tender, id=file_id).first()
        if not obj:
            return Response({"detail": "Р¤Р°Р№Р» РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["patch"], url_path=r"files/(?P<file_id>\d+)")
    def file_patch(self, request, pk=None, file_id=None):
        """РћРЅРѕРІРёС‚Рё РІРёРґРёРјС–СЃС‚СЊ С„Р°Р№Р»Сѓ СѓС‡Р°СЃРЅРёРєР°Рј."""
        tender = self.get_object()
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

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return SalesTender.objects.all().select_related(
                "company", "category", "cpv_category", "expense_article",
                "branch", "department", "currency", "created_by", "parent",
            ).prefetch_related("positions__nomenclature__unit", "tender_criteria")
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        return SalesTender.objects.filter(
            company_id__in=user_companies
        ).select_related(
            "company", "category", "cpv_category", "expense_article",
            "branch", "department", "currency", "created_by", "parent",
        ).prefetch_related("positions__nomenclature__unit", "tender_criteria")

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
            ).prefetch_related("positions__nomenclature__unit", "tender_criteria").first()
            if obj:
                return obj
            # Дозволяємо перегляд деталей тендера, доступного для участі, ще до підтвердження участі.
            obj = SalesTender.objects.filter(
                ~Q(company_id__in=user_company_ids),
                pk=pk,
                conduct_type__in=["rfx", "online_auction"],
                stage__in=["acceptance", "decision", "approval", "completed"],
            ).select_related(
                "company", "category", "cpv_category", "expense_article",
                "branch", "department", "currency", "created_by", "parent",
            ).prefetch_related("positions__nomenclature__unit", "tender_criteria").first()
            if obj:
                return obj
        raise Http404("РўРµРЅРґРµСЂ РЅРµ Р·РЅР°Р№РґРµРЅРѕ.")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(
        parameters=[
            OpenApiParameter(name="tab", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description="active | processing | completed"),
        ],
        responses=SalesTenderSerializer(many=True),
    )
    @action(detail=False, methods=["get"], url_path="for-participation")
    def for_participation(self, request):
        """РЎРїРёСЃРѕРє С‚РµРЅРґРµСЂС–РІ РЅР° РїСЂРѕРґР°Р¶ РґР»СЏ СѓС‡Р°СЃС‚С– (С–РЅС€РёС… РєРѕРјРїР°РЅС–Р№): РђРєС‚РёРІРЅС– / РћРїСЂР°С†СЊРѕРІСѓСЋС‚СЊСЃСЏ / Р—Р°РІРµСЂС€РµРЅС–."""
        user = request.user
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return Response([])
        tab = (request.query_params.get("tab") or "active").strip().lower()
        qs = (
            SalesTender.objects.filter(
                ~Q(company_id__in=user_company_ids),
                conduct_type__in=["rfx", "online_auction"],
                stage__in=["acceptance", "decision", "approval", "completed"],
            )
            .select_related(
                "company", "currency", "parent",
            )
            .prefetch_related("positions__nomenclature__unit", "tender_criteria")
            .order_by("-updated_at")
        )
        if tab == "active":
            qs = qs.filter(stage="acceptance")
        elif tab == "processing":
            qs = qs.filter(
                Q(stage="decision") | Q(stage="approval")
                | (Q(stage="preparation") & Q(tour_number__gt=1))
            )
        elif tab == "completed":
            qs = qs.filter(stage="completed")
        serializer = SalesTenderSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(responses=SalesTenderProposalSerializer)
    @action(detail=True, methods=["post"], url_path="confirm-participation")
    def confirm_participation(self, request, pk=None):
        """РџС–РґС‚РІРµСЂРґРёС‚Рё СѓС‡Р°СЃС‚СЊ: СЃС‚РІРѕСЂСЋС” РїСЂРѕРїРѕР·РёС†С–СЋ С‚Р° РґРѕРґР°С” РєРѕРЅС‚СЂР°РіРµРЅС‚Р° РІ РґРѕРІС–РґРЅРёРє РѕСЂРіР°РЅС–Р·Р°С‚РѕСЂР°."""
        tender = SalesTender.objects.filter(pk=pk).select_related("company").first()
        if not tender:
            return Response({"detail": "РўРµРЅРґРµСЂ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
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
        proposal.submitted_at = timezone.now()
        proposal.save(update_fields=["submitted_at"])
        serializer = SalesTenderProposalSerializer(proposal)
        return Response(serializer.data)

    @extend_schema(responses=SalesTenderProposalSerializer)
    @action(detail=True, methods=["post"], url_path="withdraw-proposal")
    def withdraw_proposal(self, request, pk=None):
        """Р’С–РґРєР»РёРєР°С‚Рё РїСЂРѕРїРѕР·РёС†С–СЋ (РєРѕРјРїР°РЅС–СЏ РїРѕС‚РѕС‡РЅРѕРіРѕ РєРѕСЂРёСЃС‚СѓРІР°С‡Р°)."""
        tender = SalesTender.objects.filter(pk=pk).first()
        if not tender:
            return Response({"detail": "РўРµРЅРґРµСЂ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
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
        proposal.save(update_fields=["submitted_at"])
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
                },
                "required": ["mode"],
            }
        },
    )
    @action(detail=True, methods=["post"], url_path="fix-decision")
    def fix_decision(self, request, pk=None):
        """
        Р—Р°С„С–РєСЃСѓРІР°С‚Рё СЂС–С€РµРЅРЅСЏ: winner вЂ” Р· РїРµСЂРµРјРѕР¶С†СЏРјРё РїРѕ РїРѕР·РёС†С–СЏС…, cancel вЂ” Р±РµР· РїРµСЂРµРјРѕР¶С†С–РІ,
        next_round вЂ” СЃС‚РІРѕСЂРёС‚Рё РЅР°СЃС‚СѓРїРЅРёР№ С‚СѓСЂ РЅР° РµС‚Р°РїС– РїС–РґРіРѕС‚РѕРІРєРё.
        """
        tender = self.get_object()
        mode = request.data.get("mode")
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
            return Response({"stage": "approval", "id": tender.id})
        if mode == "cancel":
            SalesTenderPosition.objects.filter(tender=tender).update(winner_proposal=None)
            tender.stage = "approval"
            tender.save(update_fields=["stage"])
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
            created_by=request.user,
        )
        new_tender.cpv_categories.set(parent.cpv_categories.all())
        new_tender.tender_criteria.set(parent.tender_criteria.all())
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
        qs = SalesTenderProposal.objects.filter(tender=tender).select_related(
            "supplier_company"
        ).prefetch_related(
            "position_values__tender_position__nomenclature__unit",
        )
        serializer = SalesTenderProposalSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(request=SalesTenderProposalSerializer, responses=SalesTenderProposalSerializer)
    @action(detail=True, methods=["post"], url_path="proposals/add")
    def proposal_add(self, request, pk=None):
        """Р”РѕРґР°С‚Рё РїСЂРѕРїРѕР·РёС†С–СЋ (РѕР±СЂР°С‚Рё РєРѕРЅС‚СЂР°РіРµРЅС‚Р°)."""
        tender = self.get_object()
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
        proposal = SalesTenderProposal.objects.filter(
            tender=tender, id=proposal_id
        ).prefetch_related("position_values__tender_position").first()
        if not proposal:
            return Response({"detail": "РџСЂРѕРїРѕР·РёС†С–СЋ РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        payload = TenderProposalPositionUpdateSerializer(data=request.data)
        if not payload.is_valid():
            return Response(payload.errors, status=status.HTTP_400_BAD_REQUEST)
        position_values_data = payload.validated_data.get("position_values") or []
        for item in position_values_data:
            tp_id = item.get("tender_position_id")
            if not tp_id:
                continue
            pos = SalesTenderPosition.objects.filter(tender=tender, id=tp_id).first()
            if not pos:
                continue
            pv, _ = SalesTenderProposalPosition.objects.get_or_create(
                proposal=proposal, tender_position=pos,
                defaults={"price": None, "criterion_values": {}},
            )
            if "price" in item:
                pv.price = item["price"]
            if "criterion_values" in item:
                pv.criterion_values = item["criterion_values"]
            pv.save()
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
        serializer = SalesTenderFileSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(request=OpenApiTypes.BINARY, responses=SalesTenderFileSerializer)
    @action(detail=True, methods=["post"], url_path="files/upload")
    def file_upload(self, request, pk=None):
        """РџСЂРёРєСЂС–РїРёС‚Рё С„Р°Р№Р» РґРѕ С‚РµРЅРґРµСЂР° РЅР° РїСЂРѕРґР°Р¶."""
        tender = self.get_object()
        file_obj = request.FILES.get("file") or request.FILES.get("file_upload")
        if not file_obj:
            return Response(
                {"detail": "РќР°РґС–С€Р»С–С‚СЊ С„Р°Р№Р» Сѓ РїРѕР»С– file Р°Р±Рѕ file_upload."},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
        obj = SalesTenderFile.objects.filter(tender=tender, id=file_id).first()
        if not obj:
            return Response({"detail": "Р¤Р°Р№Р» РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["patch"], url_path=r"files/(?P<file_id>\d+)")
    def file_patch(self, request, pk=None, file_id=None):
        """РћРЅРѕРІРёС‚Рё РІРёРґРёРјС–СЃС‚СЊ С„Р°Р№Р»Сѓ СѓС‡Р°СЃРЅРёРєР°Рј."""
        tender = self.get_object()
        obj = SalesTenderFile.objects.filter(tender=tender, id=file_id).first()
        if not obj:
            return Response({"detail": "Р¤Р°Р№Р» РЅРµ Р·РЅР°Р№РґРµРЅРѕ."}, status=status.HTTP_404_NOT_FOUND)
        if "visible_to_participants" in request.data:
            obj.visible_to_participants = bool(request.data["visible_to_participants"])
            obj.save(update_fields=["visible_to_participants"])
        serializer = SalesTenderFileSerializer(obj, context={"request": request})
        return Response(serializer.data)
