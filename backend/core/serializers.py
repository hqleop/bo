from rest_framework import serializers
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

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """User serializer for read operations."""

    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "middle_name", "phone", "avatar", "is_active")
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
    """Зв'язок компанія → контрагент. Для списку контрагентів."""

    supplier_company = CompanyListSerializer(read_only=True)
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
    """Step 2: New company registration."""

    user_id = serializers.IntegerField(required=True)
    edrpou = serializers.CharField(max_length=20, required=True)
    name = serializers.CharField(max_length=255, required=True)
    goal_tenders = serializers.BooleanField(required=True)
    goal_participation = serializers.BooleanField(required=True)

    def validate_edrpou(self, value):
        code = (value or "").strip()
        if not code:
            raise serializers.ValidationError("Код компанії обов'язковий.")
        if Company.objects.filter(edrpou=code).exists():
            raise serializers.ValidationError("Компанія з таким ЄДРПОУ вже існує.")
        return code

    def validate(self, attrs):
        if not attrs.get("goal_tenders") and not attrs.get("goal_participation"):
            raise serializers.ValidationError("Потрібно обрати хоча б одну ціль (тендери або участь).")
        return attrs


class ExistingCompanyStep2Serializer(serializers.Serializer):
    """Step 2: Join existing company by code (ЄДРПОУ). Optional name — оновлює назву при першій реєстрації."""

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

    def get_permissions(self, obj):
        """Aggregate permissions from all approved memberships."""
        user = obj
        permissions = set()
        for membership in user.memberships.filter(status=CompanyUser.Status.APPROVED).select_related("role"):
            permissions.update(membership.role.permissions.values_list("code", flat=True))
        return list(permissions)


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
        fields = ("id", "company", "name", "is_active")
        read_only_fields = ("id",)


class NomenclatureSerializer(serializers.ModelSerializer):
    """Серіалізатор номенклатури."""

    unit_name = serializers.CharField(source="unit.name", read_only=True)
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


class ProcurementTenderPositionSerializer(serializers.ModelSerializer):
    """Позиція тендера на закупівлю."""

    nomenclature_id = serializers.PrimaryKeyRelatedField(
        queryset=Nomenclature.objects.all(), source="nomenclature"
    )
    name = serializers.CharField(source="nomenclature.name", read_only=True)
    unit_name = serializers.CharField(source="nomenclature.unit.name", read_only=True)

    class Meta:
        model = ProcurementTenderPosition
        fields = ("id", "tender", "nomenclature", "nomenclature_id", "name", "unit_name", "quantity", "description")
        read_only_fields = ("id", "tender", "name", "unit_name")
        extra_kwargs = {"nomenclature": {"required": False}}


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
    cpv_categories = serializers.SerializerMethodField()
    cpv_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=CpvDictionary.objects.all(), required=False, source="cpv_categories"
    )
    expense_article_name = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    positions = ProcurementTenderPositionSerializer(many=True, required=False)
    criterion_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=TenderCriterion.objects.all(), required=False, source="tender_criteria"
    )
    criteria = serializers.SerializerMethodField()

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
            "start_at",
            "end_at",
            "created_at",
            "updated_at",
            "price_criterion_vat",
            "price_criterion_delivery",
            "tender_criteria",
            "criterion_ids",
            "criteria",
            "positions",
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
            "cpv_categories",
            "expense_article_name",
            "branch_name",
            "department_name",
        )

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

    def get_criteria(self, obj):
        return [
            {"id": c.id, "name": c.name, "type": c.type}
            for c in obj.tender_criteria.all()
        ]

    def _update_positions(self, instance, positions_data):
        if positions_data is None:
            return
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
            if existing:
                existing.quantity = quantity
                existing.description = description
                existing.save()
                seen_ids.add(existing.id)
            else:
                new_pos = instance.positions.create(
                    nomenclature_id=nom_id, quantity=quantity, description=description
                )
                seen_ids.add(new_pos.id)
        for pos in list(instance.positions.all()):
            if pos.id not in seen_ids:
                pos.delete()

    def update(self, instance, validated_data):
        positions_data = validated_data.pop("positions", None)
        criterion_ids = validated_data.pop("tender_criteria", None)
        if criterion_ids is not None:
            instance.tender_criteria.set(criterion_ids)
        super().update(instance, validated_data)
        if positions_data is not None:
            self._update_positions(instance, positions_data)
        return instance


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
        source="tender_position.nomenclature.unit.name", read_only=True
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
        fields = ("id", "tender", "supplier_company", "supplier_company_id", "supplier_name", "position_values")
        read_only_fields = ("id", "tender")


class TenderProposalPositionUpdateSerializer(serializers.Serializer):
    """Оновлення значень по позиціях пропозиції (bulk)."""

    position_values = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of { tender_position_id, price?, criterion_values? }",
    )


class ProcurementTenderFileSerializer(serializers.ModelSerializer):
    """Файл, прикріплений до тендера."""

    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ProcurementTenderFile
        fields = ("id", "tender", "file", "file_url", "name", "uploaded_at")
        read_only_fields = ("id", "tender", "uploaded_at")

    def get_file_url(self, obj):
        request = self.context.get("request")
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else ""


class SalesTenderPositionSerializer(serializers.ModelSerializer):
    """Позиція тендера на продаж."""

    nomenclature_id = serializers.PrimaryKeyRelatedField(
        queryset=Nomenclature.objects.all(), source="nomenclature"
    )
    name = serializers.CharField(source="nomenclature.name", read_only=True)
    unit_name = serializers.CharField(source="nomenclature.unit.name", read_only=True)

    class Meta:
        model = SalesTenderPosition
        fields = ("id", "tender", "nomenclature", "nomenclature_id", "name", "unit_name", "quantity", "description")
        read_only_fields = ("id", "tender", "name", "unit_name")
        extra_kwargs = {"nomenclature": {"required": False}}


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
    cpv_categories = serializers.SerializerMethodField()
    cpv_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=CpvDictionary.objects.all(), required=False, source="cpv_categories"
    )
    expense_article_name = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    positions = SalesTenderPositionSerializer(many=True, required=False)
    criterion_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=TenderCriterion.objects.all(), required=False, source="tender_criteria"
    )
    criteria = serializers.SerializerMethodField()

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
            "start_at",
            "end_at",
            "created_at",
            "updated_at",
            "price_criterion_vat",
            "price_criterion_delivery",
            "tender_criteria",
            "criterion_ids",
            "criteria",
            "positions",
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
            "cpv_categories",
            "expense_article_name",
            "branch_name",
            "department_name",
        )

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

    def get_criteria(self, obj):
        return [
            {"id": c.id, "name": c.name, "type": c.type}
            for c in obj.tender_criteria.all()
        ]

    def _update_positions(self, instance, positions_data):
        if positions_data is None:
            return
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
            if existing:
                existing.quantity = quantity
                existing.description = description
                existing.save()
                seen_ids.add(existing.id)
            else:
                new_pos = instance.positions.create(
                    nomenclature_id=nom_id, quantity=quantity, description=description
                )
                seen_ids.add(new_pos.id)
        for pos in list(instance.positions.all()):
            if pos.id not in seen_ids:
                pos.delete()

    def update(self, instance, validated_data):
        positions_data = validated_data.pop("positions", None)
        criterion_ids = validated_data.pop("tender_criteria", None)
        if criterion_ids is not None:
            instance.tender_criteria.set(criterion_ids)
        super().update(instance, validated_data)
        if positions_data is not None:
            self._update_positions(instance, positions_data)
        return instance


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
        source="tender_position.nomenclature.unit.name", read_only=True
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
        fields = ("id", "tender", "supplier_company", "supplier_company_id", "supplier_name", "position_values")
        read_only_fields = ("id", "tender")


class SalesTenderFileSerializer(serializers.ModelSerializer):
    """Файл, прикріплений до тендера на продаж."""

    file_url = serializers.SerializerMethodField()

    class Meta:
        model = SalesTenderFile
        fields = ("id", "tender", "file", "file_url", "name", "uploaded_at")
        read_only_fields = ("id", "tender", "uploaded_at")

    def get_file_url(self, obj):
        request = self.context.get("request")
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else ""
