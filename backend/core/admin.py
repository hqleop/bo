from django.contrib import admin
from .models import (
    User,
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
    ExpenseArticle,
    ExpenseArticleUser,
    Currency,
    TenderCriterion,
    ProcurementTender,
    SalesTender,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "phone", "is_active", "is_superuser")
    list_filter = ("is_active", "is_superuser")
    search_fields = ("email", "first_name", "last_name", "phone")


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "edrpou", "status", "goal_tenders", "goal_participation", "created_at")
    list_filter = ("status", "goal_tenders", "goal_participation")
    search_fields = ("name", "edrpou")


@admin.register(CompanySupplier)
class CompanySupplierAdmin(admin.ModelAdmin):
    list_display = ("owner_company", "supplier_company", "source", "created_at")
    list_filter = ("source", "owner_company")
    search_fields = ("supplier_company__name", "supplier_company__edrpou")


@admin.register(CompanyUser)
class CompanyUserAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "role", "status", "created_at")
    list_filter = ("status", "role", "company")
    search_fields = ("user__email", "company__name")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "is_system")
    list_filter = ("is_system", "company")
    filter_horizontal = ("permissions",)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "label")
    search_fields = ("code", "label")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "title", "is_read", "created_at")
    list_filter = ("type", "is_read", "created_at")
    search_fields = ("user__email", "title", "body")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "parent", "code", "created_at")
    list_filter = ("company", "parent")
    search_fields = ("name", "code", "company__name")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "parent", "created_at")
    list_filter = ("branch", "parent")
    search_fields = ("name", "branch__name")


@admin.register(BranchUser)
class BranchUserAdmin(admin.ModelAdmin):
    list_display = ("user", "branch", "created_at")
    list_filter = ("branch", "created_at")
    search_fields = ("user__email", "branch__name")


@admin.register(DepartmentUser)
class DepartmentUserAdmin(admin.ModelAdmin):
    list_display = ("user", "department", "created_at")
    list_filter = ("department", "created_at")
    search_fields = ("user__email", "department__name")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "code", "created_at")
    list_filter = ("company",)
    search_fields = ("name", "code", "company__name")


@admin.register(CategoryUser)
class CategoryUserAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("user__email", "category__name")


@admin.register(ExpenseArticle)
class ExpenseArticleAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "code", "year_start", "year_end", "created_at")
    list_filter = ("company", "year_start", "year_end")
    search_fields = ("name", "code", "company__name")


@admin.register(ExpenseArticleUser)
class ExpenseArticleUserAdmin(admin.ModelAdmin):
    list_display = ("user", "expense", "created_at")
    list_filter = ("expense", "created_at")
    search_fields = ("user__email", "expense__name")


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(TenderCriterion)
class TenderCriterionAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "type", "created_at")
    list_filter = ("company", "type")
    search_fields = ("name", "company__name")


def make_set_stage_action(stage_value: str, stage_label: str):
    """Повертає admin action для встановлення етапу тендера на закупівлю."""

    def set_stage_procurement(modeladmin, request, queryset):
        updated = queryset.update(stage=stage_value)
        modeladmin.message_user(request, f"Етап змінено на «{stage_label}» для {updated} тендер(ів).")

    set_stage_procurement.short_description = f"Перевести на етап: {stage_label}"
    set_stage_procurement.__name__ = f"set_stage_procurement_{stage_value}"
    return set_stage_procurement


def make_set_stage_action_sales(stage_value: str, stage_label: str):
    """Повертає admin action для встановлення етапу тендера на продаж."""

    def set_stage_sales(modeladmin, request, queryset):
        updated = queryset.update(stage=stage_value)
        modeladmin.message_user(request, f"Етап змінено на «{stage_label}» для {updated} тендер(ів).")

    set_stage_sales.short_description = f"Перевести на етап: {stage_label}"
    set_stage_sales.__name__ = f"set_stage_sales_{stage_value}"
    return set_stage_sales


@admin.register(ProcurementTender)
class ProcurementTenderAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "tour_number",
        "name",
        "company",
        "stage_display",
        "conduct_type",
        "created_at",
    )
    list_filter = ("company", "stage", "conduct_type", "publication_type")
    search_fields = ("name", "company__name")
    raw_id_fields = (
        "company",
        "category",
        "cpv_category",
        "expense_article",
        "branch",
        "department",
        "currency",
        "created_by",
        "parent",
    )
    actions = [
        make_set_stage_action("passport", "Паспорт тендера"),
        make_set_stage_action("preparation", "Підготовка процедури"),
        make_set_stage_action("acceptance", "Прийом пропозицій"),
        make_set_stage_action("decision", "Вибір рішення"),
        make_set_stage_action("approval", "Затвердження"),
        make_set_stage_action("completed", "Завершений"),
    ]

    @admin.display(description="Етап")
    def stage_display(self, obj):
        return obj.get_stage_display() if obj else ""


@admin.register(SalesTender)
class SalesTenderAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "tour_number",
        "name",
        "company",
        "stage_display",
        "conduct_type",
        "created_at",
    )
    list_filter = ("company", "stage", "conduct_type", "publication_type")
    search_fields = ("name", "company__name")
    raw_id_fields = (
        "company",
        "category",
        "cpv_category",
        "expense_article",
        "branch",
        "department",
        "currency",
        "created_by",
        "parent",
    )
    actions = [
        make_set_stage_action_sales("passport", "Паспорт тендера"),
        make_set_stage_action_sales("preparation", "Підготовка процедури"),
        make_set_stage_action_sales("acceptance", "Прийом пропозицій"),
        make_set_stage_action_sales("decision", "Вибір рішення"),
        make_set_stage_action_sales("approval", "Затвердження"),
        make_set_stage_action_sales("completed", "Завершений"),
    ]

    @admin.display(description="Етап")
    def stage_display(self, obj):
        return obj.get_stage_display() if obj else ""
