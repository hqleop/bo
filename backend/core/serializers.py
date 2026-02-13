from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
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

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """User serializer for read operations."""

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "middle_name", "phone", "is_active")
        read_only_fields = ("id", "email", "is_active")


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

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Користувач з таким email вже існує.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class CompanySerializer(serializers.ModelSerializer):
    """Company serializer."""

    class Meta:
        model = Company
        fields = ("id", "edrpou", "name", "goal_tenders", "goal_participation", "status", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class CompanyListSerializer(serializers.ModelSerializer):
    """Lightweight company serializer for listings."""

    class Meta:
        model = Company
        fields = ("id", "edrpou", "name", "status")


class CompanyRegistrationStep2Serializer(serializers.Serializer):
    """Step 2: New company registration."""

    user_id = serializers.IntegerField(required=True)
    edrpou = serializers.CharField(max_length=20, required=True)
    name = serializers.CharField(max_length=255, required=True)
    goal_tenders = serializers.BooleanField(required=True)
    goal_participation = serializers.BooleanField(required=True)

    def validate_edrpou(self, value):
        if Company.objects.filter(edrpou=value).exists():
            raise serializers.ValidationError("Компанія з таким ЄДРПОУ вже існує.")
        return value

    def validate(self, attrs):
        if not attrs.get("goal_tenders") and not attrs.get("goal_participation"):
            raise serializers.ValidationError("Потрібно обрати хоча б одну ціль (тендери або участь).")
        return attrs


class ExistingCompanyStep2Serializer(serializers.Serializer):
    """Step 2: Join existing company."""

    user_id = serializers.IntegerField(required=True)
    company_id = serializers.IntegerField(required=True)

    def validate_company_id(self, value):
        if not Company.objects.filter(id=value, status=Company.Status.ACTIVE).exists():
            raise serializers.ValidationError("Компанія не знайдена або неактивна.")
        return value


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

    def get_permissions(self, obj):
        """Aggregate permissions from all approved memberships."""
        user = obj
        permissions = set()
        for membership in user.memberships.filter(status=CompanyUser.Status.APPROVED).select_related("role"):
            permissions.update(membership.role.permissions.values_list("code", flat=True))
        return list(permissions)


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
        fields = ("id", "company", "name", "is_active")
        read_only_fields = ("id",)


class NomenclatureSerializer(serializers.ModelSerializer):
    """Серіалізатор номенклатури."""

    unit_name = serializers.CharField(source="unit.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    cpv_label = serializers.SerializerMethodField()

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
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_cpv_label(self, obj):
        cpv = obj.cpv_category
        if not cpv:
            return ""
        return f"{cpv.cpv_code} - {cpv.name_ua}"


class CurrencySerializer(serializers.ModelSerializer):
    """Довідник валют (тільки читання для API)."""

    class Meta:
        model = Currency
        fields = ("id", "code", "name")


class TenderCriterionSerializer(serializers.ModelSerializer):
    """Серіалізатор критерію тендеру."""

    type_label = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = TenderCriterion
        fields = (
            "id",
            "company",
            "name",
            "type",
            "type_label",
            "options",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ProcurementTenderSerializer(serializers.ModelSerializer):
    """Тендер на закупівлю (паспорт та етапи)."""

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
    expense_article_name = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()

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
            "start_at",
            "end_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "number",
            "created_at",
            "updated_at",
            "stage_label",
            "conduct_type_label",
            "publication_type_label",
            "currency_code",
            "category_name",
            "cpv_label",
            "expense_article_name",
            "branch_name",
            "department_name",
        )

    def get_category_name(self, obj):
        return obj.category.name if obj.category else ""

    def get_cpv_label(self, obj):
        if not obj.cpv_category_id:
            return ""
        return f"{obj.cpv_category.cpv_code} - {obj.cpv_category.name_ua}"

    def get_expense_article_name(self, obj):
        return obj.expense_article.name if obj.expense_article else ""

    def get_branch_name(self, obj):
        return obj.branch.name if obj.branch else ""

    def get_department_name(self, obj):
        return obj.department.name if obj.department else ""


class SalesTenderSerializer(serializers.ModelSerializer):
    """Тендер на продаж (паспорт та етапи)."""

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
    expense_article_name = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()

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
            "start_at",
            "end_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "number",
            "created_at",
            "updated_at",
            "stage_label",
            "conduct_type_label",
            "publication_type_label",
            "currency_code",
            "category_name",
            "cpv_label",
            "expense_article_name",
            "branch_name",
            "department_name",
        )

    def get_category_name(self, obj):
        return obj.category.name if obj.category else ""

    def get_cpv_label(self, obj):
        if not obj.cpv_category_id:
            return ""
        return f"{obj.cpv_category.cpv_code} - {obj.cpv_category.name_ua}"

    def get_expense_article_name(self, obj):
        return obj.expense_article.name if obj.expense_article else ""

    def get_branch_name(self, obj):
        return obj.branch.name if obj.branch else ""

    def get_department_name(self, obj):
        return obj.department.name if obj.department else ""
