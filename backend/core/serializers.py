from rest_framework import serializers
import re
from decimal import Decimal, InvalidOperation
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
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
    ProcurementTenderPosition,
    TenderProposal,
    TenderProposalPosition,
    ProcurementTenderFile,
    SalesTender,
    SalesTenderPosition,
    SalesTenderProposal,
    SalesTenderProposalPosition,
    SalesTenderFile,
    TenderApprovalJournal,
    UnitOfMeasure,
    Nomenclature,
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """User serializer for read operations."""

    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "middle_name", "phone", "avatar", "is_active", "registration_step")
        read_only_fields = ("id", "email", "is_active")

    def get_avatar(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.avatar.url)
        return obj.avatar.url


class UserRegistrationStep1Serializer(serializers.Serializer):
    """Step 1: User registration."""

    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    middle_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=32, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_phone(self, value):
        """Очікуваний формат телефону: +380XXXXXXXXX (12 цифр, включно з кодом країни)."""
        if not value:
            raise serializers.ValidationError("Телефон обов'язковий.")
        raw = (value or "").strip()
        # Дозволяємо формати з пробілами/дефісами, але приводимо до цифр.
        digits = re.sub(r"\D", "", raw)
        if not digits.startswith("380") or len(digits) != 12:
            raise serializers.ValidationError("Телефон має бути у форматі +380XXXXXXXXX.")
        return f"+{digits}"

    def validate_email(self, value):
        email = (value or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Користувач з таким email вже існує.")
        return email

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class CompanyUserCreateSerializer(serializers.Serializer):
    """Create company member from Users page."""

    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    middle_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_phone(self, value):
        raw = (value or "").strip()
        if not raw:
            return ""
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 10 and digits.startswith("0"):
            digits = f"38{digits}"
        if not digits.startswith("380") or len(digits) != 12:
            raise serializers.ValidationError("Телефон має бути у форматі +380XXXXXXXXX.")
        return f"+{digits}"

    def validate_email(self, value):
        email = (value or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Користувач з таким email вже існує.")
        return email

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class CompanySerializer(serializers.ModelSerializer):
    """Company serializer."""

    registration_country = serializers.CharField(read_only=True)

    class Meta:
        model = Company
        fields = (
            "id",
            "edrpou",
            "name",
            "subject_type",
            "registration_country",
            "company_address",
            "identity_document",
            "goal_tenders",
            "goal_participation",
            "agree_trade_rules",
            "agree_privacy_policy",
            "agree_participation_visibility",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class CountryBusinessNumberSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    class Meta:
        model = CountryBusinessNumber
        fields = ("number_code", "country_code", "number_name", "label")

    def get_label(self, obj):
        return f"{obj.number_name} ({obj.number_code})"


class RegistrationCompanyLookupSerializer(serializers.Serializer):
    exists = serializers.BooleanField()
    has_registered_users = serializers.BooleanField()
    company = CompanySerializer(required=False, allow_null=True)


class CompanyCpvSerializer(serializers.ModelSerializer):
    """
    Серіалізатор для зв'язку компанії з CPV-категоріями (налаштування компанії).
    """

    cpv_categories = serializers.SerializerMethodField()
    cpv_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        required=False,
        source="cpv_categories",
        queryset=CpvDictionary.objects.all(),
        help_text="Масив ID CPV-кодів, закріплених за компанією",
    )

    class Meta:
        model = Company
        fields = ("id", "edrpou", "name", "cpv_categories", "cpv_ids")
        read_only_fields = ("id", "edrpou", "name", "cpv_categories")

    def get_cpv_categories(self, obj):
        qs = obj.cpv_categories.all()
        return [
            {
                "id": cpv.id,
                "cpv_code": cpv.cpv_code,
                "name_ua": cpv.name_ua,
                "label": f"{cpv.cpv_code} - {cpv.name_ua}",
            }
            for cpv in qs
        ]


class CompanyListSerializer(serializers.ModelSerializer):
    """Lightweight company serializer for listings."""

    class Meta:
        model = Company
        fields = ("id", "edrpou", "name", "status")


class CompanyWithCpvsSerializer(serializers.ModelSerializer):
    """Company with cpv_categories for filtering contractors by CPV."""

    cpv_categories = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = ("id", "edrpou", "name", "status", "cpv_categories")

    def get_cpv_categories(self, obj):
        qs = getattr(obj, "cpv_categories", None)
        if qs is None:
            return []
        if hasattr(qs, "all"):
            qs = qs.all()
        return [
            {"id": c.id, "cpv_code": getattr(c, "cpv_code", ""), "name_ua": getattr(c, "name_ua", ""), "label": f"{getattr(c, 'cpv_code', '')} - {getattr(c, 'name_ua', '')}"}
            for c in qs
        ]


class CompanyCreateSerializer(serializers.ModelSerializer):
    """Create company (e.g. counterparty) with code and name only."""

    class Meta:
        model = Company
        fields = ("edrpou", "name")

    def validate_edrpou(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Код компанії обов'язковий.")
        if Company.objects.filter(edrpou=value.strip()).exists():
            raise serializers.ValidationError("Компанія з таким кодом вже існує.")
        return value.strip()

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Назва компанії обов'язкова.")
        return value.strip()


class CompanySupplierSerializer(serializers.ModelSerializer):
    """Зв'язок компанія в†’ контрагент. Для списку контрагентів."""

    supplier_company = CompanyListSerializer(read_only=True)
    supplier_company_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = CompanySupplier
        fields = ("id", "owner_company", "supplier_company", "supplier_company_id", "source", "created_at")
        read_only_fields = ("id", "owner_company", "supplier_company", "source", "created_at")


class CompanySupplierListSerializer(serializers.ModelSerializer):
    """Список контрагентів з CPV категоріями для фільтрації."""

    supplier_company = CompanyWithCpvsSerializer(read_only=True)
    supplier_company_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = CompanySupplier
        fields = ("id", "owner_company", "supplier_company", "supplier_company_id", "source", "created_at")
        read_only_fields = ("id", "owner_company", "supplier_company", "source", "created_at")


class AddCompanySupplierSerializer(serializers.Serializer):
    """Додати контрагента: або supplier_company_id, або edrpou (+ name якщо компанії ще немає)."""

    supplier_company_id = serializers.IntegerField(required=False)
    edrpou = serializers.CharField(max_length=20, required=False, allow_blank=True)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        sid = attrs.get("supplier_company_id")
        edrpou = (attrs.get("edrpou") or "").strip()
        name = (attrs.get("name") or "").strip()
        if sid is not None:
            if edrpou:
                raise serializers.ValidationError({"edrpou": "Укажіть або ID компанії, або код (ЄДРПОУ), але не обидва."})
            return attrs
        if not edrpou:
            raise serializers.ValidationError({"edrpou": "Вкажіть код компанії (ЄДРПОУ) або ID існуючої компанії."})
        attrs["edrpou"] = edrpou
        attrs["name"] = name
        return attrs


class CompanyRegistrationStep2Serializer(serializers.Serializer):
    """Step 2: Company details and legal agreements."""

    SUBJECT_CHOICES = [
        Company.SubjectType.FOP_RESIDENT,
        Company.SubjectType.LEGAL_RESIDENT,
        Company.SubjectType.NON_RESIDENT,
        Company.SubjectType.INDIVIDUAL,
    ]

    user_id = serializers.IntegerField(required=True)
    subject_type = serializers.ChoiceField(choices=SUBJECT_CHOICES, required=True)
    edrpou = serializers.CharField(max_length=20, required=True)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    company_address = serializers.CharField(max_length=500, required=True)
    registration_country = serializers.CharField(max_length=50, required=False, allow_blank=True)
    identity_document = serializers.FileField(required=False, allow_null=True)
    agree_trade_rules = serializers.BooleanField(required=True)
    agree_privacy_policy = serializers.BooleanField(required=True)

    def validate_edrpou(self, value):
        code = (value or "").strip()
        if not code:
            raise serializers.ValidationError("Код компанії обов'язковий.")
        if Company.objects.filter(edrpou=code).exists():
            raise serializers.ValidationError("Компанія з таким кодом вже існує.")
        return code

    def validate(self, attrs):
        subject_type = attrs.get("subject_type")
        code = (attrs.get("edrpou") or "").strip()
        name = (attrs.get("name") or "").strip()
        address = (attrs.get("company_address") or "").strip()
        registration_country = (attrs.get("registration_country") or "").strip()
        identity_document = attrs.get("identity_document")

        if not attrs.get("agree_trade_rules"):
            raise serializers.ValidationError({"agree_trade_rules": "Потрібно погодитися з регламентом торгів."})
        if not attrs.get("agree_privacy_policy"):
            raise serializers.ValidationError({"agree_privacy_policy": "Потрібно погодитися з політикою конфіденційності."})
        if not address:
            raise serializers.ValidationError({"company_address": "Адреса обов'язкова."})

        if subject_type in (Company.SubjectType.FOP_RESIDENT, Company.SubjectType.INDIVIDUAL):
            if not re.fullmatch(r"\d{10}", code):
                raise serializers.ValidationError({"edrpou": "Код має містити 10 цифр."})
        elif subject_type == Company.SubjectType.LEGAL_RESIDENT:
            if not re.fullmatch(r"\d{8}", code):
                raise serializers.ValidationError({"edrpou": "Код ЄДРПОУ має містити 8 цифр."})
        elif subject_type == Company.SubjectType.NON_RESIDENT:
            if not registration_country:
                raise serializers.ValidationError({"registration_country": "Оберіть країну реєстрації."})
            if not CountryBusinessNumber.objects.filter(number_code=registration_country).exists():
                raise serializers.ValidationError({"registration_country": "Країну не знайдено."})
        else:
            raise serializers.ValidationError({"subject_type": "Некоректний тип суб'єкта."})

        if subject_type != Company.SubjectType.INDIVIDUAL and not name:
            raise serializers.ValidationError({"name": "Назва згідно уставних документів обов'язкова."})
        if subject_type == Company.SubjectType.INDIVIDUAL and not identity_document:
            raise serializers.ValidationError({"identity_document": "Завантажте документ, що підтверджує особу."})

        attrs["name"] = name
        attrs["company_address"] = address
        attrs["registration_country"] = registration_country
        return attrs


class CompanyRegistrationStep3Serializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    company_id = serializers.IntegerField(required=True)
    goal_tenders = serializers.BooleanField(required=True)
    goal_participation = serializers.BooleanField(required=True)
    agree_participation_visibility = serializers.BooleanField(required=True)
    cpv_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        goal_tenders = attrs.get("goal_tenders")
        goal_participation = attrs.get("goal_participation")
        agree_visibility = attrs.get("agree_participation_visibility")
        cpv_ids = attrs.get("cpv_ids") or []

        if not goal_tenders and not goal_participation:
            raise serializers.ValidationError("Оберіть хоча б один напрямок діяльності.")

        if goal_participation:
            if not agree_visibility:
                raise serializers.ValidationError(
                    {"agree_participation_visibility": "Потрібно підтвердити відображення реєстраційних даних."}
                )
            if not cpv_ids:
                raise serializers.ValidationError({"cpv_ids": "Оберіть хоча б одну CPV-категорію."})
        return attrs




class ExistingCompanyStep2Serializer(serializers.Serializer):
    """Крок 2: приєднання до існуючої компанії за кодом (ЄДРПОУ)."""

    user_id = serializers.IntegerField(required=True)
    edrpou = serializers.CharField(max_length=20, required=True)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_edrpou(self, value):
        code = (value or "").strip()
        if not code:
            raise serializers.ValidationError("Код компанії обов'язковий.")
        if not Company.objects.filter(edrpou=code, status=Company.Status.ACTIVE).exists():
            raise serializers.ValidationError("Компанію з таким кодом не знайдено.")
        return code


class PermissionSerializer(serializers.ModelSerializer):
    """Permission serializer."""

    class Meta:
        model = Permission
        fields = ("id", "code", "label")


class RoleSerializer(serializers.ModelSerializer):
    """Role serializer."""

    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), write_only=True, required=False, source="permissions"
    )

    class Meta:
        model = Role
        fields = ("id", "company", "name", "is_system", "permissions", "permission_ids")
        read_only_fields = ("id", "is_system")


class CompanyUserSerializer(serializers.ModelSerializer):
    """CompanyUser membership serializer."""

    user = UserSerializer(read_only=True)
    company = CompanyListSerializer(read_only=True)
    role = RoleSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)
    company_id = serializers.IntegerField(write_only=True, required=False)
    role_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = CompanyUser
        fields = (
            "id",
            "user",
            "user_id",
            "company",
            "company_id",
            "role",
            "role_id",
            "status",
            "invited_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "invited_by", "created_at", "updated_at")


class NotificationSerializer(serializers.ModelSerializer):
    """Notification serializer."""

    class Meta:
        model = Notification
        fields = ("id", "type", "title", "body", "is_read", "meta", "created_at")
        read_only_fields = ("id", "created_at")


class MeSerializer(serializers.Serializer):
    """Current user info with memberships and permissions."""

    user = UserSerializer(read_only=True)
    memberships = CompanyUserSerializer(many=True, read_only=True)
    permissions = serializers.SerializerMethodField()
    registration_step = serializers.SerializerMethodField()
    registration_company_id = serializers.SerializerMethodField()

    def get_permissions(self, obj):
        """Aggregate permissions from all approved memberships."""
        user = obj.get("user") if isinstance(obj, dict) else obj
        if not user:
            return []
        permissions = set()
        for membership in user.memberships.filter(status=CompanyUser.Status.APPROVED).select_related("role"):
            permissions.update(membership.role.permissions.values_list("code", flat=True))
        return list(permissions)

    def get_registration_step(self, obj):
        user = obj.get("user") if isinstance(obj, dict) else obj
        if not user:
            return 4
        return int(getattr(user, "registration_step", 4) or 4)

    def get_registration_company_id(self, obj):
        user = obj.get("user") if isinstance(obj, dict) else obj
        if not user:
            return None
        membership = user.memberships.order_by("-created_at").first()
        return membership.company_id if membership else None


class ProfileUpdateSerializer(serializers.Serializer):
    """Оновлення профілю поточного користувача (поля з кроку 1 реєстрації)."""

    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    middle_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    """Password reset request."""

    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Password reset confirmation."""

    token = serializers.CharField(required=True)
    new_password = serializers.CharField(write_only=True, required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """Change password for authenticated user."""

    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class BranchSerializer(serializers.ModelSerializer):
    """Branch serializer with tree structure."""

    children = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = ("id", "company", "parent", "name", "code", "children", "user_count", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def get_children(self, obj):
        """Get direct children branches."""
        children = obj.children.all()
        return BranchSerializer(children, many=True).data

    def get_user_count(self, obj):
        """Get count of users in branch."""
        return obj.users.count()


class DepartmentSerializer(serializers.ModelSerializer):
    """Department serializer with tree structure."""

    children = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ("id", "branch", "parent", "name", "children", "user_count", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def get_children(self, obj):
        """Get direct children departments."""
        children = obj.children.all()
        return DepartmentSerializer(children, many=True).data

    def get_user_count(self, obj):
        """Get count of users in department."""
        return obj.users.count()


class BranchUserSerializer(serializers.ModelSerializer):
    """BranchUser serializer."""

    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = BranchUser
        fields = ("id", "branch", "user", "user_id", "created_at")
        read_only_fields = ("id", "created_at")


class DepartmentUserSerializer(serializers.ModelSerializer):
    """DepartmentUser serializer."""

    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = DepartmentUser
        fields = ("id", "department", "user", "user_id", "created_at")
        read_only_fields = ("id", "created_at")


class CategorySerializer(serializers.ModelSerializer):
    """Category serializer with tree structure and CPV binding."""

    children = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()
    cpvs = serializers.SerializerMethodField()
    cpv_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        required=False,
        source="cpvs",
        queryset=CpvDictionary.objects.all(),
        help_text="Масив ID CPV-кодів, прив'язаних до категорії",
    )

    class Meta:
        model = Category
        fields = (
            "id",
            "company",
            "parent",
            "name",
            "code",
            "description",
            "children",
            "user_count",
            "cpvs",
            "cpv_ids",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_children(self, obj):
        """Get direct children categories."""
        children = obj.children.all()
        return CategorySerializer(children, many=True).data

    def get_user_count(self, obj):
        return obj.users.count()

    def get_cpvs(self, obj):
        """Return short CPV info for UI."""
        qs = obj.cpvs.all()
        return [
            {
                "id": cpv.id,
                "cpv_code": cpv.cpv_code,
                "name_ua": cpv.name_ua,
                "label": f"{cpv.cpv_code} - {cpv.name_ua}",
            }
            for cpv in qs
        ]


class CategoryUserSerializer(serializers.ModelSerializer):
    """CategoryUser serializer."""

    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = CategoryUser
        fields = ("id", "category", "user", "user_id", "created_at")
        read_only_fields = ("id", "created_at")


class ExpenseArticleSerializer(serializers.ModelSerializer):
    """ExpenseArticle serializer with tree structure."""

    children = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = ExpenseArticle
        fields = (
            "id",
            "company",
            "parent",
            "name",
            "code",
            "year_start",
            "year_end",
            "description",
            "children",
            "user_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_children(self, obj):
        children = obj.children.all()
        return ExpenseArticleSerializer(children, many=True).data

    def get_user_count(self, obj):
        return obj.users.count()


class ExpenseArticleUserSerializer(serializers.ModelSerializer):
    """ExpenseArticleUser serializer."""

    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ExpenseArticleUser
        fields = ("id", "expense", "user", "user_id", "created_at")
        read_only_fields = ("id", "created_at")


class UnitOfMeasureSerializer(serializers.ModelSerializer):
    """Серіалізатор довідника одиниць виміру."""

    class Meta:
        model = UnitOfMeasure
        fields = ("id", "company", "name_ua", "name_en", "short_name_ua", "short_name_en", "is_active")
        read_only_fields = ("id",)


class NomenclatureSerializer(serializers.ModelSerializer):
    """Серіалізатор номенклатури."""

    unit_name = serializers.CharField(source="unit.display_short_ua", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    cpv_label = serializers.SerializerMethodField()
    cpv_categories = serializers.SerializerMethodField()
    cpv_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=CpvDictionary.objects.all(), required=False, source="cpv_categories"
    )

    class Meta:
        model = Nomenclature
        fields = (
            "id",
            "company",
            "name",
            "unit",
            "unit_name",
            "code",
            "external_number",
            "description",
            "specification_file",
            "image_file",
            "category",
            "category_name",
            "cpv_category",
            "cpv_label",
            "cpv_categories",
            "cpv_ids",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "cpv_categories")

    def get_cpv_label(self, obj):
        qs = obj.cpv_categories.all()
        if qs.exists():
            cpv = qs.first()
            return f"{cpv.cpv_code} - {cpv.name_ua}"
        cpv = obj.cpv_category
        if not cpv:
            return ""
        return f"{cpv.cpv_code} - {cpv.name_ua}"

    def get_cpv_categories(self, obj):
        return [
            {"id": c.id, "cpv_code": c.cpv_code, "name_ua": c.name_ua, "label": f"{c.cpv_code} - {c.name_ua}"}
            for c in obj.cpv_categories.all()
        ]

    def validate(self, attrs):
        """Унікальність: пара назва + одиниця виміру в межах компанії."""
        company = attrs.get("company") or (self.instance.company if self.instance else None)
        unit = attrs.get("unit") or (self.instance.unit_id if self.instance else None)
        name = (attrs.get("name") or (self.instance.name if self.instance else "") or "").strip()
        if not company or not unit or not name:
            return attrs
        qs = Nomenclature.objects.filter(company=company, unit=unit).filter(name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            from rest_framework import serializers as drf
            raise drf.ValidationError(
                {"name": "Номенклатура з такою назвою та одиницею виміру вже існує в довіднику."}
            )
        return attrs


class CurrencySerializer(serializers.ModelSerializer):
    """Довідник валют (тільки читання для API)."""

    class Meta:
        model = Currency
        fields = ("id", "code", "code_iso", "name")


class TenderCriterionSerializer(serializers.ModelSerializer):
    """Серіалізатор критерію тендеру."""

    type_label = serializers.CharField(source="get_type_display", read_only=True)
    application_label = serializers.CharField(source="get_application_display", read_only=True)
    tender_type_label = serializers.CharField(source="get_tender_type_display", read_only=True)

    class Meta:
        model = TenderCriterion
        fields = (
            "id",
            "company",
            "name",
            "type",
            "type_label",
            "tender_type",
            "tender_type_label",
            "application",
            "application_label",
            "is_required",
            "options",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        """Унікальність: назва + тип критерія в межах компанії."""
        company = attrs.get("company") or (self.instance.company if self.instance else None)
        name = (attrs.get("name") or (self.instance.name if self.instance else "") or "").strip()
        ctype = attrs.get("type") or (self.instance.type if self.instance else None)
        tender_type = attrs.get("tender_type") or (self.instance.tender_type if self.instance else None)
        if not company or not name or not ctype or not tender_type:
            return attrs
        qs = TenderCriterion.objects.filter(
            company=company,
            name__iexact=name,
            type=ctype,
            tender_type=tender_type,
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            from rest_framework import serializers as drf
            raise drf.ValidationError(
                {"name": "Критерій з такою назвою та типом вже існує в довіднику."}
            )
        return attrs


class TenderAttributeSerializer(serializers.ModelSerializer):
    """Серіалізатор атрибута тендеру."""

    type_label = serializers.CharField(source="get_type_display", read_only=True)
    tender_type_label = serializers.CharField(source="get_tender_type_display", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = TenderAttribute
        fields = (
            "id",
            "company",
            "name",
            "type",
            "type_label",
            "tender_type",
            "tender_type_label",
            "category",
            "category_name",
            "is_required",
            "options",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        """Унікальність: назва + тип атрибута в межах компанії."""
        company = attrs.get("company") or (self.instance.company if self.instance else None)
        name = (attrs.get("name") or (self.instance.name if self.instance else "") or "").strip()
        atype = attrs.get("type") or (self.instance.type if self.instance else None)
        tender_type = attrs.get("tender_type") or (self.instance.tender_type if self.instance else None)
        if not company or not name or not atype or not tender_type:
            return attrs
        qs = TenderAttribute.objects.filter(
            company=company,
            name__iexact=name,
            type=atype,
            tender_type=tender_type,
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {"name": "Атрибут з такою назвою та типом вже існує в довіднику."}
            )
        return attrs


class ApprovalModelRoleUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalModelRoleUser
        fields = ("id", "role", "user", "full_name", "created_at")
        read_only_fields = ("id", "created_at", "full_name")

    def get_full_name(self, obj):
        if not obj.user:
            return ""
        name = obj.user.get_full_name() if hasattr(obj.user, "get_full_name") else ""
        return name or obj.user.email or str(obj.user)


class ApprovalModelRoleSerializer(serializers.ModelSerializer):
    application_label = serializers.CharField(source="get_application_display", read_only=True)
    users = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalModelRole
        fields = (
            "id",
            "company",
            "name",
            "application",
            "application_label",
            "users",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "application_label", "users")

    def get_users(self, obj):
        memberships = obj.role_users.select_related("user").all()
        return [
            {
                "id": item.user_id,
                "full_name": item.user.get_full_name() or item.user.email or str(item.user),
                "email": item.user.email,
            }
            for item in memberships
            if item.user_id
        ]


class ApprovalRangeMatrixSerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(source="currency.code", read_only=True)

    class Meta:
        model = ApprovalRangeMatrix
        fields = (
            "id",
            "company",
            "budget_from",
            "budget_to",
            "currency",
            "currency_code",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "currency_code")

    def validate(self, attrs):
        budget_from = attrs.get("budget_from", getattr(self.instance, "budget_from", None))
        budget_to = attrs.get("budget_to", getattr(self.instance, "budget_to", None))
        if budget_from is not None and budget_to is not None and budget_from > budget_to:
            raise serializers.ValidationError(
                {"budget_to": "Бюджет по має бути більшим або рівним бюджету з."}
            )
        return attrs


class ApprovalModelStepSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = ApprovalModelStep
        fields = (
            "id",
            "model",
            "role",
            "role_name",
            "order",
            "preparation_rule",
            "approval_rule",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "role_name")


class ApprovalModelNestedStepSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = ApprovalModelStep
        fields = (
            "id",
            "role",
            "role_name",
            "order",
            "preparation_rule",
            "approval_rule",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "role_name")


class ApprovalModelSerializer(serializers.ModelSerializer):
    application_label = serializers.CharField(source="get_application_display", read_only=True)
    steps = ApprovalModelNestedStepSerializer(many=True, required=False)
    categories_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all(), required=False, source="categories"
    )
    range_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=ApprovalRangeMatrix.objects.all(), required=False, source="ranges"
    )

    class Meta:
        model = ApprovalModel
        fields = (
            "id",
            "company",
            "name",
            "application",
            "application_label",
            "is_active",
            "categories",
            "categories_ids",
            "ranges",
            "range_ids",
            "steps",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "application_label", "categories", "ranges")

    def create(self, validated_data):
        steps_data = validated_data.pop("steps", [])
        categories = validated_data.pop("categories", None)
        ranges = validated_data.pop("ranges", None)
        instance = super().create(validated_data)
        if categories is not None:
            instance.categories.set(categories)
        if ranges is not None:
            instance.ranges.set(ranges)
        if steps_data:
            ApprovalModelStep.objects.bulk_create(
                [
                    ApprovalModelStep(
                        model=instance,
                        role=item["role"],
                        order=item.get("order") or idx + 1,
                        preparation_rule=item.get("preparation_rule") or ApprovalModelStep.DecisionRule.ONE_OF,
                        approval_rule=item.get("approval_rule") or ApprovalModelStep.DecisionRule.ONE_OF,
                    )
                    for idx, item in enumerate(steps_data)
                ]
            )
        return instance

    def update(self, instance, validated_data):
        steps_data = validated_data.pop("steps", None)
        categories = validated_data.pop("categories", None)
        ranges = validated_data.pop("ranges", None)
        instance = super().update(instance, validated_data)
        if categories is not None:
            instance.categories.set(categories)
        if ranges is not None:
            instance.ranges.set(ranges)
        if steps_data is not None:
            instance.steps.all().delete()
            ApprovalModelStep.objects.bulk_create(
                [
                    ApprovalModelStep(
                        model=instance,
                        role=item["role"],
                        order=item.get("order") or idx + 1,
                        preparation_rule=item.get("preparation_rule") or ApprovalModelStep.DecisionRule.ONE_OF,
                        approval_rule=item.get("approval_rule") or ApprovalModelStep.DecisionRule.ONE_OF,
                    )
                    for idx, item in enumerate(steps_data)
                ]
            )
        return instance


class TenderApprovalJournalSerializer(serializers.ModelSerializer):
    user_display = serializers.SerializerMethodField()
    action_label = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = TenderApprovalJournal
        fields = (
            "id",
            "procurement_tender",
            "sales_tender",
            "stage",
            "action",
            "action_label",
            "comment",
            "actor",
            "user_display",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "user_display", "action_label")

    def get_user_display(self, obj):
        if not obj.actor:
            return ""
        return obj.actor.get_full_name() or obj.actor.email or str(obj.actor)


class ProcurementTenderPositionSerializer(serializers.ModelSerializer):
    """Позиція тендера на закупівлю."""

    nomenclature_id = serializers.PrimaryKeyRelatedField(
        queryset=Nomenclature.objects.all(), source="nomenclature"
    )
    name = serializers.CharField(source="nomenclature.name", read_only=True)
    unit_name = serializers.CharField(source="nomenclature.unit.display_short_ua", read_only=True)
    winner_proposal_id = serializers.SerializerMethodField()
    winner_supplier_name = serializers.SerializerMethodField()
    winner_price = serializers.SerializerMethodField()
    winner_criterion_values = serializers.SerializerMethodField()

    class Meta:
        model = ProcurementTenderPosition
        fields = (
            "id", "tender", "nomenclature", "nomenclature_id", "name", "unit_name",
            "quantity", "description", "start_price", "min_bid_step", "max_bid_step",
            "attribute_values",
            "winner_proposal_id", "winner_supplier_name", "winner_price", "winner_criterion_values",
        )
        read_only_fields = ("id", "tender", "name", "unit_name", "winner_proposal_id", "winner_supplier_name", "winner_price", "winner_criterion_values")
        extra_kwargs = {"nomenclature": {"required": False}}

    def get_winner_proposal_id(self, obj):
        try:
            return getattr(obj, "winner_proposal_id", None)
        except Exception:
            return None

    def get_winner_supplier_name(self, obj):
        try:
            if not getattr(obj, "winner_proposal_id", None) or not getattr(obj, "winner_proposal", None):
                return None
            return getattr(obj.winner_proposal.supplier_company, "name", None)
        except Exception:
            return None

    def get_winner_price(self, obj):
        try:
            if not getattr(obj, "winner_proposal_id", None) or not getattr(obj, "winner_proposal", None):
                return None
            pv = TenderProposalPosition.objects.filter(
                proposal=obj.winner_proposal, tender_position=obj
            ).first()
            return str(pv.price) if pv and pv.price is not None else None
        except Exception:
            return None

    def get_winner_criterion_values(self, obj):
        try:
            if not getattr(obj, "winner_proposal_id", None) or not getattr(obj, "winner_proposal", None):
                return None
            pv = TenderProposalPosition.objects.filter(
                proposal=obj.winner_proposal, tender_position=obj
            ).first()
            return pv.criterion_values if pv and getattr(pv, "criterion_values", None) else {}
        except Exception:
            return {}


class ProcurementTenderSerializer(serializers.ModelSerializer):
    """Тендер на закупівлю (паспорт та етапи)."""

    number = serializers.SerializerMethodField()
    stage_label = serializers.CharField(source="get_stage_display", read_only=True)
    conduct_type_label = serializers.CharField(
        source="get_conduct_type_display", read_only=True
    )
    publication_type_label = serializers.CharField(
        source="get_publication_type_display", read_only=True
    )
    currency_code = serializers.CharField(source="currency.code", read_only=True)
    category_name = serializers.SerializerMethodField()
    cpv_label = serializers.SerializerMethodField()
    cpv_categories = serializers.SerializerMethodField()
    cpv_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=CpvDictionary.objects.all(), required=False, source="cpv_categories"
    )
    expense_article_name = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    created_by_display = serializers.SerializerMethodField()
    positions = ProcurementTenderPositionSerializer(many=True, required=False)
    approval_model_id = serializers.PrimaryKeyRelatedField(
        queryset=ApprovalModel.objects.none(),
        required=False,
        allow_null=True,
        source="approval_model",
    )

    def validate(self, attrs):
        """Категорія CPV обовʼязкова: хоча б одна CPV має бути обрана."""
        cpv_categories = attrs.get("cpv_categories")
        if cpv_categories is not None and len(cpv_categories) == 0:
            from rest_framework import serializers as drf
            raise drf.ValidationError(
                {"cpv_ids": "Оберіть хоча б одну категорію CPV."}
            )
        if not self.instance and (cpv_categories is None or len(cpv_categories) == 0):
            from rest_framework import serializers as drf
            raise drf.ValidationError(
                {"cpv_ids": "Оберіть хоча б одну категорію CPV."}
            )
        criterion_ids = attrs.get("tender_criteria")
        if criterion_ids is not None:
            wrong_ids = [
                c.id for c in criterion_ids if getattr(c, "tender_type", None) != "procurement"
            ]
            if wrong_ids:
                from rest_framework import serializers as drf
                raise drf.ValidationError(
                    {"criterion_ids": "Selected criteria do not belong to procurement dictionary."}
                )
        attribute_ids = attrs.get("tender_attributes")
        if attribute_ids is not None:
            wrong_ids = [
                a.id for a in attribute_ids if getattr(a, "tender_type", None) != "procurement"
            ]
            if wrong_ids:
                from rest_framework import serializers as drf
                raise drf.ValidationError(
                    {"attribute_ids": "Selected attributes do not belong to procurement dictionary."}
                )
        return attrs

    criterion_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=TenderCriterion.objects.none(), required=False, source="tender_criteria"
    )
    attribute_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=TenderAttribute.objects.none(), required=False, source="tender_attributes"
    )
    criteria = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()
    is_latest_tour = serializers.SerializerMethodField()
    current_user_has_proposal = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = TenderCriterion.objects.filter(tender_type="procurement")
        self.fields["criterion_ids"].queryset = qs
        if hasattr(self.fields["criterion_ids"], "child_relation"):
            self.fields["criterion_ids"].child_relation.queryset = qs
        attr_qs = TenderAttribute.objects.filter(tender_type="procurement")
        self.fields["attribute_ids"].queryset = attr_qs
        if hasattr(self.fields["attribute_ids"], "child_relation"):
            self.fields["attribute_ids"].child_relation.queryset = attr_qs
        self.fields["approval_model_id"].queryset = ApprovalModel.objects.filter(
            application=ApprovalModel.Application.PROCUREMENT
        )

    def _normalize_criterion_ids_payload(self, data):
        if not self.instance:
            return data

        raw_ids = []
        if hasattr(data, "getlist"):
            raw_ids = data.getlist("criterion_ids")
        elif isinstance(data, dict):
            raw_ids = data.get("criterion_ids") or []
        else:
            return data

        if raw_ids is None:
            return data
        if not isinstance(raw_ids, (list, tuple)):
            raw_ids = [raw_ids]

        parsed_ids = []
        for raw in raw_ids:
            try:
                parsed = int(raw)
            except (TypeError, ValueError):
                continue
            if parsed > 0:
                parsed_ids.append(parsed)
        if not parsed_ids:
            return data

        valid_ref_ids = set(
            TenderCriterion.objects.filter(
                id__in=parsed_ids, tender_type="procurement"
            ).values_list("id", flat=True)
        )
        missing_ids = [item_id for item_id in parsed_ids if item_id not in valid_ref_ids]
        if not missing_ids:
            return data

        replacement_by_snapshot_id = {
            snapshot_id: ref_id
            for snapshot_id, ref_id in self.instance.criteria_items.filter(
                id__in=missing_ids
            ).values_list("id", "reference_criterion_id")
            if ref_id
        }
        normalized_ids = [replacement_by_snapshot_id.get(item_id, item_id) for item_id in parsed_ids]
        if normalized_ids == parsed_ids:
            return data

        if hasattr(data, "copy"):
            mutable = data.copy()
            if hasattr(mutable, "setlist"):
                mutable.setlist("criterion_ids", [str(item_id) for item_id in normalized_ids])
            else:
                mutable["criterion_ids"] = normalized_ids
            return mutable

        normalized = dict(data)
        normalized["criterion_ids"] = normalized_ids
        return normalized

    def to_internal_value(self, data):
        return super().to_internal_value(self._normalize_criterion_ids_payload(data))

    class Meta:
        model = ProcurementTender
        fields = (
            "id",
            "company",
            "parent",
            "tour_number",
            "number",
            "name",
            "stage",
            "stage_label",
            "category",
            "category_name",
            "cpv_category",
            "cpv_label",
            "cpv_categories",
            "cpv_ids",
            "expense_article",
            "expense_article_name",
            "estimated_budget",
            "branch",
            "branch_name",
            "department",
            "department_name",
            "conduct_type",
            "conduct_type_label",
            "publication_type",
            "publication_type_label",
            "currency",
            "currency_code",
            "general_terms",
            "created_by",
            "created_by_display",
            "start_at",
            "end_at",
            "created_at",
            "updated_at",
            "price_criterion_vat",
            "price_criterion_delivery",
            "tender_criteria",
            "criterion_ids",
            "criteria",
            "attribute_ids",
            "attributes",
            "positions",
            "approval_model",
            "approval_model_id",
            "is_latest_tour",
            "current_user_has_proposal",
        )
        read_only_fields = (
            "id",
            "number",
            "created_by",
            "created_at",
            "updated_at",
            "stage_label",
            "conduct_type_label",
            "publication_type_label",
            "currency_code",
            "category_name",
            "cpv_label",
            "cpv_categories",
            "expense_article_name",
            "branch_name",
            "department_name",
            "created_by_display",
            "is_latest_tour",
            "current_user_has_proposal",
        )

    def get_is_latest_tour(self, obj):
        return not obj.next_tours.exists()

    def get_number(self, obj):
        return f"p-{obj.company_id}-{obj.id}" if obj.company_id and obj.id else ""

    def get_current_user_has_proposal(self, obj):
        request = self.context.get("request")
        if not request or not getattr(request, "user", None):
            return False
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return False
        return TenderProposal.objects.filter(
            tender=obj, supplier_company_id__in=user_company_ids
        ).exists()

    def get_category_name(self, obj):
        return obj.category.name if obj.category else ""

    def get_cpv_label(self, obj):
        qs = obj.cpv_categories.all()
        if qs.exists():
            cpv = qs.first()
            return f"{cpv.cpv_code} - {cpv.name_ua}"
        if not obj.cpv_category_id:
            return ""
        return f"{obj.cpv_category.cpv_code} - {obj.cpv_category.name_ua}"

    def get_cpv_categories(self, obj):
        return [
            {"id": c.id, "cpv_code": c.cpv_code, "name_ua": c.name_ua, "label": f"{c.cpv_code} - {c.name_ua}"}
            for c in obj.cpv_categories.all()
        ]

    def get_expense_article_name(self, obj):
        return obj.expense_article.name if obj.expense_article else ""

    def get_branch_name(self, obj):
        return obj.branch.name if obj.branch else ""

    def get_department_name(self, obj):
        return obj.department.name if obj.department else ""

    def get_created_by_display(self, obj):
        user = getattr(obj, "created_by", None)
        if not user:
            return ""
        full_name = " ".join(
            part for part in [user.last_name, user.first_name, user.middle_name] if part
        ).strip()
        return full_name or getattr(user, "email", "") or ""

    def get_criteria(self, obj):
        snapshots = list(obj.criteria_items.all())
        if snapshots:
            return [
                {
                    "id": c.id,
                    "reference_criterion_id": c.reference_criterion_id,
                    "name": c.name,
                    "type": c.type,
                    "application": getattr(c, "application", "individual"),
                    "application_label": c.get_application_display(),
                    "is_required": bool(getattr(c, "is_required", False)),
                }
                for c in snapshots
            ]
        return [
            {
                "id": c.id,
                "name": c.name,
                "type": c.type,
                "application": getattr(c, "application", "individual"),
                "application_label": getattr(c, "get_application_display", lambda: "Індивідуальний")(),
                "is_required": bool(getattr(c, "is_required", False)),
            }
            for c in obj.tender_criteria.all()
        ]

    def get_attributes(self, obj):
        return [
            {
                "id": a.id,
                "name": a.name,
                "type": a.type,
                "tender_type": a.tender_type,
                "is_required": bool(getattr(a, "is_required", False)),
                "options": getattr(a, "options", {}) or {},
            }
            for a in obj.tender_attributes.all()
        ]

    def _sync_criteria_items(self, instance, criteria):
        if criteria is None:
            return
        desired_ref_ids = set()
        existing_by_ref = {
            item.reference_criterion_id: item
            for item in instance.criteria_items.all()
            if item.reference_criterion_id
        }
        for criterion in criteria:
            ref_id = getattr(criterion, "id", None)
            if not ref_id:
                continue
            desired_ref_ids.add(ref_id)
            if ref_id in existing_by_ref:
                continue
            instance.criteria_items.create(
                reference_criterion=criterion,
                name=criterion.name,
                type=criterion.type,
                application=getattr(criterion, "application", TenderCriterion.Application.INDIVIDUAL),
                is_required=bool(getattr(criterion, "is_required", False)),
                options=getattr(criterion, "options", {}) or {},
            )
        if desired_ref_ids:
            instance.criteria_items.exclude(reference_criterion_id__in=desired_ref_ids).delete()
        else:
            instance.criteria_items.all().delete()

    @staticmethod
    def _validate_positions_no_duplicate_nomenclature(positions_data):
        if not positions_data:
            return
        from rest_framework import serializers as drf
        nom_id_key = lambda x: x if isinstance(x, int) else getattr(x, "id", None)
        seen = set()
        for item in positions_data:
            nom = item.get("nomenclature") or item.get("nomenclature_id")
            nom_id = nom_id_key(nom) if nom is not None else None
            if nom_id is not None:
                if nom_id in seen:
                    raise drf.ValidationError(
                        {"positions": "Одна й та сама номенклатура не може бути додана двічі до позицій тендера."}
                    )
                seen.add(nom_id)

    @staticmethod
    def _validate_online_auction_position_pricing(instance, positions_data):
        if not positions_data:
            return
        from rest_framework import serializers as drf

        is_online_auction = getattr(instance, "conduct_type", "") == "online_auction"
        required_msg = (
            "Для моделі «Класичні торги» заповніть стартову ціну, мінімальний та максимальний крок ставки по кожній позиції."
        )
        base_msg = "Перевірте параметри ставки по кожній позиції: значення мають бути > 0, а мінімальний крок не може перевищувати максимальний."

        for item in positions_data:
            start_price = item.get("start_price")
            min_bid_step = item.get("min_bid_step")
            max_bid_step = item.get("max_bid_step")

            if is_online_auction and (
                start_price in (None, "") or min_bid_step in (None, "") or max_bid_step in (None, "")
            ):
                raise drf.ValidationError({"positions": required_msg})

            provided = any(v not in (None, "") for v in (start_price, min_bid_step, max_bid_step))
            if not provided:
                continue

            if start_price in (None, "") or min_bid_step in (None, "") or max_bid_step in (None, ""):
                raise drf.ValidationError({"positions": base_msg})

            try:
                start_price_dec = Decimal(str(start_price))
                min_step_dec = Decimal(str(min_bid_step))
                max_step_dec = Decimal(str(max_bid_step))
            except (InvalidOperation, ValueError, TypeError):
                raise drf.ValidationError({"positions": base_msg})

            if start_price_dec <= 0 or min_step_dec <= 0 or max_step_dec <= 0:
                raise drf.ValidationError({"positions": base_msg})
            if min_step_dec > max_step_dec:
                raise drf.ValidationError({"positions": base_msg})

    def _update_positions(self, instance, positions_data):
        if positions_data is None:
            return
        self._validate_positions_no_duplicate_nomenclature(positions_data)
        self._validate_online_auction_position_pricing(instance, positions_data)
        nom_id_key = lambda x: x if isinstance(x, int) else getattr(x, "id", None)
        current = {p.nomenclature_id: p for p in instance.positions.all()}
        seen_ids = set()
        for item in positions_data:
            nom = item.get("nomenclature") or item.get("nomenclature_id")
            nom_id = nom_id_key(nom) if nom is not None else None
            if not nom_id:
                continue
            existing = current.get(nom_id)
            quantity = item.get("quantity", 1)
            description = item.get("description", "")
            start_price = item.get("start_price")
            min_bid_step = item.get("min_bid_step")
            max_bid_step = item.get("max_bid_step")
            attribute_values = item.get("attribute_values") or {}
            if not isinstance(attribute_values, dict):
                attribute_values = {}
            if existing:
                existing.quantity = quantity
                existing.description = description
                existing.start_price = (
                    start_price if start_price not in ("", None) else None
                )
                existing.min_bid_step = (
                    min_bid_step if min_bid_step not in ("", None) else None
                )
                existing.max_bid_step = (
                    max_bid_step if max_bid_step not in ("", None) else None
                )
                existing.attribute_values = attribute_values
                existing.save()
                seen_ids.add(existing.id)
            else:
                new_pos = instance.positions.create(
                    nomenclature_id=nom_id,
                    quantity=quantity,
                    description=description,
                    start_price=start_price if start_price not in ("", None) else None,
                    min_bid_step=min_bid_step if min_bid_step not in ("", None) else None,
                    max_bid_step=max_bid_step if max_bid_step not in ("", None) else None,
                    attribute_values=attribute_values,
                )
                seen_ids.add(new_pos.id)
        for pos in list(instance.positions.all()):
            if pos.id not in seen_ids:
                pos.delete()

    def update(self, instance, validated_data):
        positions_data = validated_data.pop("positions", None)
        criterion_ids = validated_data.pop("tender_criteria", None)
        attribute_ids = validated_data.pop("tender_attributes", None)
        if criterion_ids is not None:
            instance.tender_criteria.set(criterion_ids)
            self._sync_criteria_items(instance, criterion_ids)
        if attribute_ids is not None:
            instance.tender_attributes.set(attribute_ids)
        super().update(instance, validated_data)
        if positions_data is not None:
            self._update_positions(instance, positions_data)
        return instance


class ProcurementParticipationTenderListSerializer(serializers.ModelSerializer):
    """Lightweight procurement tender serializer for participation list."""

    number = serializers.SerializerMethodField()
    stage_label = serializers.CharField(source="get_stage_display", read_only=True)
    conduct_type_label = serializers.CharField(
        source="get_conduct_type_display", read_only=True
    )
    company = serializers.SerializerMethodField()
    cpv_categories = serializers.SerializerMethodField()
    current_user_has_proposal = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProcurementTender
        fields = (
            "id",
            "number",
            "tour_number",
            "name",
            "stage",
            "stage_label",
            "conduct_type",
            "conduct_type_label",
            "company",
            "cpv_categories",
            "start_at",
            "end_at",
            "created_at",
            "updated_at",
            "current_user_has_proposal",
        )

    def get_company(self, obj):
        company = getattr(obj, "company", None)
        if not company:
            return None
        return {
            "id": company.id,
            "name": company.name,
            "edrpou": company.edrpou,
            "label": f"{company.name} ({company.edrpou})" if company.edrpou else company.name,
        }

    def get_number(self, obj):
        return f"p-{obj.company_id}-{obj.id}" if obj.company_id and obj.id else ""

    def get_cpv_categories(self, obj):
        return [
            {
                "id": c.id,
                "cpv_code": c.cpv_code,
                "name_ua": c.name_ua,
                "label": f"{c.cpv_code} - {c.name_ua}",
            }
            for c in obj.cpv_categories.all()
        ]


class TenderProposalPositionSerializer(serializers.ModelSerializer):
    """Значення по позиції в пропозиції."""

    tender_position_id = serializers.PrimaryKeyRelatedField(
        queryset=ProcurementTenderPosition.objects.none(), source="tender_position"
    )
    position_name = serializers.CharField(source="tender_position.nomenclature.name", read_only=True)
    position_quantity = serializers.DecimalField(
        source="tender_position.quantity", max_digits=18, decimal_places=4, read_only=True
    )
    position_unit = serializers.CharField(
        source="tender_position.nomenclature.unit.display_short_ua", read_only=True
    )

    class Meta:
        model = TenderProposalPosition
        fields = (
            "id",
            "tender_position",
            "tender_position_id",
            "position_name",
            "position_quantity",
            "position_unit",
            "price",
            "criterion_values",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "context" in kwargs and "tender" in kwargs["context"]:
            self.fields["tender_position"].queryset = (
                ProcurementTenderPosition.objects.filter(tender=kwargs["context"]["tender"])
            )


class TenderProposalSerializer(serializers.ModelSerializer):
    """Пропозиція контрагента в тендері."""

    supplier_company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(), source="supplier_company"
    )
    supplier_name = serializers.CharField(source="supplier_company.name", read_only=True)
    position_values = TenderProposalPositionSerializer(many=True, read_only=True)

    class Meta:
        model = TenderProposal
        fields = (
            "id", "tender", "supplier_company", "supplier_company_id", "supplier_name",
            "position_values", "created_at", "submitted_at",
        )
        read_only_fields = ("id", "tender", "created_at", "submitted_at")


class TenderProposalPositionUpdateSerializer(serializers.Serializer):
    """Оновлення значень по позиціях пропозиції (bulk)."""

    position_values = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of { tender_position_id, price?, criterion_values? }",
    )


class ProcurementTenderFileSerializer(serializers.ModelSerializer):
    """Файл, прикріплений до тендера."""

    file_url = serializers.SerializerMethodField()
    uploaded_by_display = serializers.SerializerMethodField()

    class Meta:
        model = ProcurementTenderFile
        fields = (
            "id", "tender", "file", "file_url", "name", "uploaded_at",
            "uploaded_by", "uploaded_by_display", "visible_to_participants",
        )
        read_only_fields = ("id", "tender", "uploaded_at", "uploaded_by")

    def get_file_url(self, obj):
        request = self.context.get("request")
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else ""

    def get_uploaded_by_display(self, obj):
        if not obj.uploaded_by:
            return ""
        return obj.uploaded_by.get_full_name() or obj.uploaded_by.email or str(obj.uploaded_by)


class SalesTenderPositionSerializer(serializers.ModelSerializer):
    """Позиція тендера на продаж."""

    nomenclature_id = serializers.PrimaryKeyRelatedField(
        queryset=Nomenclature.objects.all(), source="nomenclature"
    )
    name = serializers.CharField(source="nomenclature.name", read_only=True)
    unit_name = serializers.CharField(source="nomenclature.unit.display_short_ua", read_only=True)
    winner_proposal_id = serializers.SerializerMethodField()
    winner_supplier_name = serializers.SerializerMethodField()
    winner_price = serializers.SerializerMethodField()
    winner_criterion_values = serializers.SerializerMethodField()

    class Meta:
        model = SalesTenderPosition
        fields = (
            "id", "tender", "nomenclature", "nomenclature_id", "name", "unit_name",
            "quantity", "description", "start_price", "min_bid_step", "max_bid_step",
            "attribute_values",
            "winner_proposal_id", "winner_supplier_name", "winner_price", "winner_criterion_values",
        )
        read_only_fields = ("id", "tender", "name", "unit_name", "winner_proposal_id", "winner_supplier_name", "winner_price", "winner_criterion_values")
        extra_kwargs = {"nomenclature": {"required": False}}

    def get_winner_proposal_id(self, obj):
        try:
            return getattr(obj, "winner_proposal_id", None)
        except Exception:
            return None

    def get_winner_supplier_name(self, obj):
        try:
            if not getattr(obj, "winner_proposal_id", None) or not getattr(obj, "winner_proposal", None):
                return None
            return getattr(obj.winner_proposal.supplier_company, "name", None)
        except Exception:
            return None

    def get_winner_price(self, obj):
        try:
            if not getattr(obj, "winner_proposal_id", None) or not getattr(obj, "winner_proposal", None):
                return None
            pv = SalesTenderProposalPosition.objects.filter(
                proposal=obj.winner_proposal, tender_position=obj
            ).first()
            return str(pv.price) if pv and pv.price is not None else None
        except Exception:
            return None

    def get_winner_criterion_values(self, obj):
        try:
            if not getattr(obj, "winner_proposal_id", None) or not getattr(obj, "winner_proposal", None):
                return None
            pv = SalesTenderProposalPosition.objects.filter(
                proposal=obj.winner_proposal, tender_position=obj
            ).first()
            return pv.criterion_values if pv and getattr(pv, "criterion_values", None) else {}
        except Exception:
            return {}


class SalesTenderSerializer(serializers.ModelSerializer):
    """Тендер на продаж (паспорт та етапи)."""

    number = serializers.SerializerMethodField()
    stage_label = serializers.CharField(source="get_stage_display", read_only=True)
    conduct_type_label = serializers.CharField(
        source="get_conduct_type_display", read_only=True
    )
    publication_type_label = serializers.CharField(
        source="get_publication_type_display", read_only=True
    )
    currency_code = serializers.CharField(source="currency.code", read_only=True)
    category_name = serializers.SerializerMethodField()
    cpv_label = serializers.SerializerMethodField()
    cpv_categories = serializers.SerializerMethodField()
    cpv_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=CpvDictionary.objects.all(), required=False, source="cpv_categories"
    )
    expense_article_name = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    created_by_display = serializers.SerializerMethodField()
    positions = SalesTenderPositionSerializer(many=True, required=False)
    approval_model_id = serializers.PrimaryKeyRelatedField(
        queryset=ApprovalModel.objects.none(),
        required=False,
        allow_null=True,
        source="approval_model",
    )
    criterion_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=TenderCriterion.objects.none(), required=False, source="tender_criteria"
    )
    attribute_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=TenderAttribute.objects.none(), required=False, source="tender_attributes"
    )
    criteria = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()
    is_latest_tour = serializers.SerializerMethodField()
    current_user_has_proposal = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = TenderCriterion.objects.filter(tender_type="sales")
        self.fields["criterion_ids"].queryset = qs
        if hasattr(self.fields["criterion_ids"], "child_relation"):
            self.fields["criterion_ids"].child_relation.queryset = qs
        attr_qs = TenderAttribute.objects.filter(tender_type="sales")
        self.fields["attribute_ids"].queryset = attr_qs
        if hasattr(self.fields["attribute_ids"], "child_relation"):
            self.fields["attribute_ids"].child_relation.queryset = attr_qs
        self.fields["approval_model_id"].queryset = ApprovalModel.objects.filter(
            application=ApprovalModel.Application.SALES
        )

    def _normalize_criterion_ids_payload(self, data):
        if not self.instance:
            return data

        raw_ids = []
        if hasattr(data, "getlist"):
            raw_ids = data.getlist("criterion_ids")
        elif isinstance(data, dict):
            raw_ids = data.get("criterion_ids") or []
        else:
            return data

        if raw_ids is None:
            return data
        if not isinstance(raw_ids, (list, tuple)):
            raw_ids = [raw_ids]

        parsed_ids = []
        for raw in raw_ids:
            try:
                parsed = int(raw)
            except (TypeError, ValueError):
                continue
            if parsed > 0:
                parsed_ids.append(parsed)
        if not parsed_ids:
            return data

        valid_ref_ids = set(
            TenderCriterion.objects.filter(
                id__in=parsed_ids, tender_type="sales"
            ).values_list("id", flat=True)
        )
        missing_ids = [item_id for item_id in parsed_ids if item_id not in valid_ref_ids]
        if not missing_ids:
            return data

        replacement_by_snapshot_id = {
            snapshot_id: ref_id
            for snapshot_id, ref_id in self.instance.criteria_items.filter(
                id__in=missing_ids
            ).values_list("id", "reference_criterion_id")
            if ref_id
        }
        normalized_ids = [replacement_by_snapshot_id.get(item_id, item_id) for item_id in parsed_ids]
        if normalized_ids == parsed_ids:
            return data

        if hasattr(data, "copy"):
            mutable = data.copy()
            if hasattr(mutable, "setlist"):
                mutable.setlist("criterion_ids", [str(item_id) for item_id in normalized_ids])
            else:
                mutable["criterion_ids"] = normalized_ids
            return mutable

        normalized = dict(data)
        normalized["criterion_ids"] = normalized_ids
        return normalized

    def to_internal_value(self, data):
        return super().to_internal_value(self._normalize_criterion_ids_payload(data))

    def validate(self, attrs):
        """Категорія CPV обовʼязкова: хоча б одна CPV має бути обрана."""
        cpv_categories = attrs.get("cpv_categories")
        if cpv_categories is not None and len(cpv_categories) == 0:
            from rest_framework import serializers as drf
            raise drf.ValidationError(
                {"cpv_ids": "Оберіть хоча б одну категорію CPV."}
            )
        if not self.instance and (cpv_categories is None or len(cpv_categories) == 0):
            from rest_framework import serializers as drf
            raise drf.ValidationError(
                {"cpv_ids": "Оберіть хоча б одну категорію CPV."}
            )
        criterion_ids = attrs.get("tender_criteria")
        if criterion_ids is not None:
            wrong_ids = [
                c.id for c in criterion_ids if getattr(c, "tender_type", None) != "sales"
            ]
            if wrong_ids:
                from rest_framework import serializers as drf
                raise drf.ValidationError(
                    {"criterion_ids": "Selected criteria do not belong to sales dictionary."}
                )
        attribute_ids = attrs.get("tender_attributes")
        if attribute_ids is not None:
            wrong_ids = [
                a.id for a in attribute_ids if getattr(a, "tender_type", None) != "sales"
            ]
            if wrong_ids:
                from rest_framework import serializers as drf
                raise drf.ValidationError(
                    {"attribute_ids": "Selected attributes do not belong to sales dictionary."}
                )
        return attrs

    class Meta:
        model = SalesTender
        fields = (
            "id",
            "company",
            "parent",
            "tour_number",
            "number",
            "name",
            "stage",
            "stage_label",
            "category",
            "category_name",
            "cpv_category",
            "cpv_label",
            "cpv_categories",
            "cpv_ids",
            "expense_article",
            "expense_article_name",
            "estimated_budget",
            "branch",
            "branch_name",
            "department",
            "department_name",
            "conduct_type",
            "conduct_type_label",
            "publication_type",
            "publication_type_label",
            "currency",
            "currency_code",
            "general_terms",
            "created_by",
            "created_by_display",
            "start_at",
            "end_at",
            "created_at",
            "updated_at",
            "price_criterion_vat",
            "price_criterion_delivery",
            "tender_criteria",
            "criterion_ids",
            "criteria",
            "attribute_ids",
            "attributes",
            "positions",
            "approval_model",
            "approval_model_id",
            "is_latest_tour",
            "current_user_has_proposal",
        )
        read_only_fields = (
            "id",
            "number",
            "created_by",
            "created_at",
            "updated_at",
            "stage_label",
            "conduct_type_label",
            "publication_type_label",
            "currency_code",
            "category_name",
            "cpv_label",
            "cpv_categories",
            "expense_article_name",
            "branch_name",
            "department_name",
            "created_by_display",
            "is_latest_tour",
            "current_user_has_proposal",
        )

    def get_is_latest_tour(self, obj):
        return not obj.next_tours.exists()

    def get_number(self, obj):
        return f"s-{obj.company_id}-{obj.id}" if obj.company_id and obj.id else ""

    def get_current_user_has_proposal(self, obj):
        request = self.context.get("request")
        if not request or not getattr(request, "user", None):
            return False
        user_company_ids = list(
            CompanyUser.objects.filter(
                user=request.user, status=CompanyUser.Status.APPROVED
            ).values_list("company_id", flat=True)
        )
        if not user_company_ids:
            return False
        return SalesTenderProposal.objects.filter(
            tender=obj, supplier_company_id__in=user_company_ids
        ).exists()

    def get_category_name(self, obj):
        return obj.category.name if obj.category else ""

    def get_cpv_label(self, obj):
        qs = obj.cpv_categories.all()
        if qs.exists():
            cpv = qs.first()
            return f"{cpv.cpv_code} - {cpv.name_ua}"
        if not obj.cpv_category_id:
            return ""
        return f"{obj.cpv_category.cpv_code} - {obj.cpv_category.name_ua}"

    def get_cpv_categories(self, obj):
        return [
            {"id": c.id, "cpv_code": c.cpv_code, "name_ua": c.name_ua, "label": f"{c.cpv_code} - {c.name_ua}"}
            for c in obj.cpv_categories.all()
        ]

    def get_expense_article_name(self, obj):
        return obj.expense_article.name if obj.expense_article else ""

    def get_branch_name(self, obj):
        return obj.branch.name if obj.branch else ""

    def get_department_name(self, obj):
        return obj.department.name if obj.department else ""

    def get_created_by_display(self, obj):
        user = getattr(obj, "created_by", None)
        if not user:
            return ""
        full_name = " ".join(
            part for part in [user.last_name, user.first_name, user.middle_name] if part
        ).strip()
        return full_name or getattr(user, "email", "") or ""

    def get_criteria(self, obj):
        snapshots = list(obj.criteria_items.all())
        if snapshots:
            return [
                {
                    "id": c.id,
                    "reference_criterion_id": c.reference_criterion_id,
                    "name": c.name,
                    "type": c.type,
                    "application": getattr(c, "application", "individual"),
                    "application_label": c.get_application_display(),
                    "is_required": bool(getattr(c, "is_required", False)),
                }
                for c in snapshots
            ]
        return [
            {
                "id": c.id,
                "name": c.name,
                "type": c.type,
                "application": getattr(c, "application", "individual"),
                "application_label": getattr(c, "get_application_display", lambda: "Індивідуальний")(),
                "is_required": bool(getattr(c, "is_required", False)),
            }
            for c in obj.tender_criteria.all()
        ]

    def get_attributes(self, obj):
        return [
            {
                "id": a.id,
                "name": a.name,
                "type": a.type,
                "tender_type": a.tender_type,
                "is_required": bool(getattr(a, "is_required", False)),
                "options": getattr(a, "options", {}) or {},
            }
            for a in obj.tender_attributes.all()
        ]

    def _sync_criteria_items(self, instance, criteria):
        if criteria is None:
            return
        desired_ref_ids = set()
        existing_by_ref = {
            item.reference_criterion_id: item
            for item in instance.criteria_items.all()
            if item.reference_criterion_id
        }
        for criterion in criteria:
            ref_id = getattr(criterion, "id", None)
            if not ref_id:
                continue
            desired_ref_ids.add(ref_id)
            if ref_id in existing_by_ref:
                continue
            instance.criteria_items.create(
                reference_criterion=criterion,
                name=criterion.name,
                type=criterion.type,
                application=getattr(criterion, "application", TenderCriterion.Application.INDIVIDUAL),
                is_required=bool(getattr(criterion, "is_required", False)),
                options=getattr(criterion, "options", {}) or {},
            )
        if desired_ref_ids:
            instance.criteria_items.exclude(reference_criterion_id__in=desired_ref_ids).delete()
        else:
            instance.criteria_items.all().delete()

    def _update_positions(self, instance, positions_data):
        if positions_data is None:
            return
        ProcurementTenderSerializer._validate_positions_no_duplicate_nomenclature(positions_data)
        ProcurementTenderSerializer._validate_online_auction_position_pricing(instance, positions_data)
        nom_id_key = lambda x: x if isinstance(x, int) else getattr(x, "id", None)
        current = {p.nomenclature_id: p for p in instance.positions.all()}
        seen_ids = set()
        for item in positions_data:
            nom = item.get("nomenclature") or item.get("nomenclature_id")
            nom_id = nom_id_key(nom) if nom is not None else None
            if not nom_id:
                continue
            existing = current.get(nom_id)
            quantity = item.get("quantity", 1)
            description = item.get("description", "")
            start_price = item.get("start_price")
            min_bid_step = item.get("min_bid_step")
            max_bid_step = item.get("max_bid_step")
            attribute_values = item.get("attribute_values") or {}
            if not isinstance(attribute_values, dict):
                attribute_values = {}
            if existing:
                existing.quantity = quantity
                existing.description = description
                existing.start_price = (
                    start_price if start_price not in ("", None) else None
                )
                existing.min_bid_step = (
                    min_bid_step if min_bid_step not in ("", None) else None
                )
                existing.max_bid_step = (
                    max_bid_step if max_bid_step not in ("", None) else None
                )
                existing.attribute_values = attribute_values
                existing.save()
                seen_ids.add(existing.id)
            else:
                new_pos = instance.positions.create(
                    nomenclature_id=nom_id,
                    quantity=quantity,
                    description=description,
                    start_price=start_price if start_price not in ("", None) else None,
                    min_bid_step=min_bid_step if min_bid_step not in ("", None) else None,
                    max_bid_step=max_bid_step if max_bid_step not in ("", None) else None,
                    attribute_values=attribute_values,
                )
                seen_ids.add(new_pos.id)
        for pos in list(instance.positions.all()):
            if pos.id not in seen_ids:
                pos.delete()

    def update(self, instance, validated_data):
        positions_data = validated_data.pop("positions", None)
        criterion_ids = validated_data.pop("tender_criteria", None)
        attribute_ids = validated_data.pop("tender_attributes", None)
        if criterion_ids is not None:
            instance.tender_criteria.set(criterion_ids)
            self._sync_criteria_items(instance, criterion_ids)
        if attribute_ids is not None:
            instance.tender_attributes.set(attribute_ids)
        super().update(instance, validated_data)
        if positions_data is not None:
            self._update_positions(instance, positions_data)
        return instance


class SalesParticipationTenderListSerializer(serializers.ModelSerializer):
    """Lightweight sales tender serializer for participation list."""

    number = serializers.SerializerMethodField()
    stage_label = serializers.CharField(source="get_stage_display", read_only=True)
    conduct_type_label = serializers.CharField(
        source="get_conduct_type_display", read_only=True
    )
    company = serializers.SerializerMethodField()
    cpv_categories = serializers.SerializerMethodField()
    current_user_has_proposal = serializers.BooleanField(read_only=True)

    class Meta:
        model = SalesTender
        fields = (
            "id",
            "number",
            "tour_number",
            "name",
            "stage",
            "stage_label",
            "conduct_type",
            "conduct_type_label",
            "company",
            "cpv_categories",
            "start_at",
            "end_at",
            "created_at",
            "updated_at",
            "current_user_has_proposal",
        )

    def get_company(self, obj):
        company = getattr(obj, "company", None)
        if not company:
            return None
        return {
            "id": company.id,
            "name": company.name,
            "edrpou": company.edrpou,
            "label": f"{company.name} ({company.edrpou})" if company.edrpou else company.name,
        }

    def get_number(self, obj):
        return f"s-{obj.company_id}-{obj.id}" if obj.company_id and obj.id else ""

    def get_cpv_categories(self, obj):
        return [
            {
                "id": c.id,
                "cpv_code": c.cpv_code,
                "name_ua": c.name_ua,
                "label": f"{c.cpv_code} - {c.name_ua}",
            }
            for c in obj.cpv_categories.all()
        ]


class SalesTenderProposalPositionSerializer(serializers.ModelSerializer):
    """Значення по позиції в пропозиції тендера на продаж."""

    tender_position_id = serializers.PrimaryKeyRelatedField(
        queryset=SalesTenderPosition.objects.none(), source="tender_position"
    )
    position_name = serializers.CharField(source="tender_position.nomenclature.name", read_only=True)
    position_quantity = serializers.DecimalField(
        source="tender_position.quantity", max_digits=18, decimal_places=4, read_only=True
    )
    position_unit = serializers.CharField(
        source="tender_position.nomenclature.unit.display_short_ua", read_only=True
    )

    class Meta:
        model = SalesTenderProposalPosition
        fields = (
            "id",
            "tender_position",
            "tender_position_id",
            "position_name",
            "position_quantity",
            "position_unit",
            "price",
            "criterion_values",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "context" in kwargs and "tender" in kwargs["context"]:
            self.fields["tender_position"].queryset = (
                SalesTenderPosition.objects.filter(tender=kwargs["context"]["tender"])
            )


class SalesTenderProposalSerializer(serializers.ModelSerializer):
    """Пропозиція контрагента в тендері на продаж."""

    supplier_company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(), source="supplier_company"
    )
    supplier_name = serializers.CharField(source="supplier_company.name", read_only=True)
    position_values = SalesTenderProposalPositionSerializer(many=True, read_only=True)

    class Meta:
        model = SalesTenderProposal
        fields = (
            "id", "tender", "supplier_company", "supplier_company_id", "supplier_name",
            "position_values", "created_at", "submitted_at",
        )
        read_only_fields = ("id", "tender", "created_at", "submitted_at")


class SalesTenderFileSerializer(serializers.ModelSerializer):
    """Файл, прикріплений до тендера на продаж."""

    file_url = serializers.SerializerMethodField()
    uploaded_by_display = serializers.SerializerMethodField()

    class Meta:
        model = SalesTenderFile
        fields = (
            "id", "tender", "file", "file_url", "name", "uploaded_at",
            "uploaded_by", "uploaded_by_display", "visible_to_participants",
        )
        read_only_fields = ("id", "tender", "uploaded_at", "uploaded_by")

    def get_file_url(self, obj):
        request = self.context.get("request")
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else ""

    def get_uploaded_by_display(self, obj):
        if not obj.uploaded_by:
            return ""
        return obj.uploaded_by.get_full_name() or obj.uploaded_by.email or str(obj.uploaded_by)
