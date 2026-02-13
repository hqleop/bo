from django.contrib import admin
from .models import (
    User,
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


@admin.register(ProcurementTender)
class ProcurementTenderAdmin(admin.ModelAdmin):
    list_display = ("number", "tour_number", "name", "company", "stage", "conduct_type", "created_at")
    list_filter = ("company", "stage", "conduct_type", "publication_type")
    search_fields = ("name", "company__name")
    raw_id_fields = ("company", "category", "cpv_category", "expense_article", "branch", "department", "currency", "created_by", "parent")


@admin.register(SalesTender)
class SalesTenderAdmin(admin.ModelAdmin):
    list_display = ("number", "tour_number", "name", "company", "stage", "conduct_type", "created_at")
    list_filter = ("company", "stage", "conduct_type", "publication_type")
    search_fields = ("name", "company__name")
    raw_id_fields = ("company", "category", "cpv_category", "expense_article", "branch", "department", "currency", "created_by", "parent")
