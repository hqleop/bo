from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from .models import (
    Company,
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
    SalesTender,
    UnitOfMeasure,
    Nomenclature,
)
from .serializers import (
    UserSerializer,
    UserRegistrationStep1Serializer,
    CompanySerializer,
    CompanyListSerializer,
    CompanyRegistrationStep2Serializer,
    ExistingCompanyStep2Serializer,
    PermissionSerializer,
    RoleSerializer,
    CompanyUserSerializer,
    NotificationSerializer,
    MeSerializer,
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
    SalesTenderSerializer,
)

User = get_user_model()


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
    serializer = UserRegistrationStep1Serializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
    """Step 2: Create new company and assign user as admin."""
    serializer = CompanyRegistrationStep2Serializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user_id = serializer.validated_data["user_id"]
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"user_id": "Користувач не знайдений."}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        company = Company.objects.create(
            edrpou=serializer.validated_data["edrpou"],
            name=serializer.validated_data["name"],
            goal_tenders=serializer.validated_data["goal_tenders"],
            goal_participation=serializer.validated_data["goal_participation"],
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
    """Step 2: Request to join existing company."""
    serializer = ExistingCompanyStep2Serializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user_id = serializer.validated_data["user_id"]
    company_id = serializer.validated_data["company_id"]

    try:
        user = User.objects.get(id=user_id)
        company = Company.objects.get(id=company_id, status=Company.Status.ACTIVE)
    except User.DoesNotExist:
        return Response({"user_id": "Користувач не знайдений."}, status=status.HTTP_400_BAD_REQUEST)
    except Company.DoesNotExist:
        return Response({"company_id": "Компанія не знайдена."}, status=status.HTTP_400_BAD_REQUEST)

    # Check if membership already exists
    if CompanyUser.objects.filter(user=user, company=company).exists():
        return Response(
            {"non_field_errors": "Користувач вже має зв'язок з цією компанією."}, status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():
        # Get default user role (or create if not exists)
        default_role, _ = Role.objects.get_or_create(
            company=company, name="Користувач", defaults={"is_system": True}
        )

        membership = CompanyUser.objects.create(
            user=user, company=company, role=default_role, status=CompanyUser.Status.PENDING
        )

        # Find company admins and send notifications
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

    return Response(CompanyUserSerializer(membership).data, status=status.HTTP_201_CREATED)


class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Company list/retrieve (for step 2 selection).
    """

    queryset = Company.objects.filter(status=Company.Status.ACTIVE)
    serializer_class = CompanyListSerializer
    permission_classes = [permissions.AllowAny]

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
    summary="Поточний користувач",
    description="Отримати інформацію про поточного користувача, його членства та права доступу.",
    responses={200: MeSerializer},
)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    """Get current user info with memberships and permissions (з ролей; у MVP не блокують доступ)."""
    serializer = MeSerializer({"user": request.user, "memberships": request.user.memberships.all(), "permissions": []})
    serializer.instance = request.user
    return Response(serializer.data)


@extend_schema(
    summary="Запит на відновлення пароля",
    description="Надіслати запит на відновлення пароля (email з посиланням).",
    request=PasswordResetRequestSerializer,
    responses={200: {"description": "Якщо email існує, надіслано лист"}},
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def password_reset_request(request):
    """Request password reset (MVP: just return success, no email sending yet)."""
    serializer = PasswordResetRequestSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data["email"]
        # In MVP, we don't send emails yet
        # TODO: Implement email sending with reset token
        return Response({"message": "Якщо email існує, надіслано лист з інструкціями."})
    return Response(serializer.errors, status=400)


@extend_schema(
    summary="Підтвердження відновлення пароля",
    description="Підтвердити відновлення пароля за токеном.",
    request=PasswordResetConfirmSerializer,
    responses={200: {"description": "Пароль успішно змінено"}},
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def password_reset_confirm(request):
    """Confirm password reset (MVP: placeholder)."""
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if serializer.is_valid():
        # TODO: Implement token validation and password reset
        return Response({"message": "Пароль успішно змінено."})
    return Response(serializer.errors, status=400)


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
        summary="Список філіалів",
        description="Отримати дерево філіалів компанії (тільки кореневі елементи, діти вкладено).",
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(parent__isnull=True)
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
        Повертає підрозділи, обмежені компаніями поточного користувача.

        - Для superuser: всі підрозділи.
        - Для звичайного користувача: лише підрозділи філіалів компаній,
          де в нього є підтверджене членство.
        - Додатково можна обмежити результат параметром branch_id.
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
        summary="Список підрозділів",
        description="Отримати дерево підрозділів для філіалу (потрібен параметр branch_id).",
        parameters=[
            OpenApiParameter(name="branch_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True)
        ],
    )
    def list(self, request, *args, **kwargs):
        branch_id = request.query_params.get("branch_id")
        if not branch_id:
            return Response({"error": "Параметр branch_id обов'язковий"}, status=400)
        # get_queryset вже відфільтрує за branch_id, тут лише беремо корені
        queryset = self.get_queryset().filter(parent__isnull=True)
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
        summary="Список категорій",
        description="Отримати дерево категорій компанії (тільки кореневі елементи, діти вкладено).",
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(parent__isnull=True)
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

    permission_classes = [permissions.IsAuthenticated]

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
        summary="Список статей витрат",
        description="Отримати дерево статей витрат компанії (тільки кореневі елементи, діти вкладено).",
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(parent__isnull=True)
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
        summary="Видалити користувача зі статті витрат",
        description="Видалити користувача зі статті витрат.",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class UnitOfMeasureViewSet(viewsets.ModelViewSet):
    """
    Довідник одиниць виміру (company-scoped).
    """

    serializer_class = UnitOfMeasureSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Повертає одиниці виміру компаній поточного користувача."""
        user = self.request.user
        if user.is_superuser:
            return UnitOfMeasure.objects.all().select_related("company")
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        return UnitOfMeasure.objects.filter(company_id__in=user_companies).select_related("company")


class NomenclatureViewSet(viewsets.ModelViewSet):
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

        if name:
            qs = qs.filter(name__icontains=name)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if cpv_id:
            qs = qs.filter(cpv_category_id=cpv_id)

        return qs

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
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

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


class TenderCriterionViewSet(viewsets.ModelViewSet):
    """
    Довідник критеріїв тендерів (company-scoped).
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
    Тендери на закупівлю (company-scoped). Номер присвоюється при першому збереженні.
    Доступ: будь-який авторизований користувач з підтвердженим членством у компанії.
    Права доступу (tenders.create тощо) не перевіряються — обмеження знято за бажанням замовника.
    """

    serializer_class = ProcurementTenderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return ProcurementTender.objects.all().select_related(
                "company", "category", "cpv_category", "expense_article",
                "branch", "department", "currency", "created_by", "parent",
            )
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        return ProcurementTender.objects.filter(
            company_id__in=user_companies
        ).select_related(
            "company", "category", "cpv_category", "expense_article",
            "branch", "department", "currency", "created_by", "parent",
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SalesTenderViewSet(viewsets.ModelViewSet):
    """
    Тендери на продаж (company-scoped).
    """

    serializer_class = SalesTenderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return SalesTender.objects.all().select_related(
                "company", "category", "cpv_category", "expense_article",
                "branch", "department", "currency", "created_by", "parent",
            )
        user_companies = CompanyUser.objects.filter(
            user=user, status=CompanyUser.Status.APPROVED
        ).values_list("company_id", flat=True)
        return SalesTender.objects.filter(
            company_id__in=user_companies
        ).select_related(
            "company", "category", "cpv_category", "expense_article",
            "branch", "department", "currency", "created_by", "parent",
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
