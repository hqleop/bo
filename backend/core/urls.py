from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomTokenObtainPairView,
    registration_step1,
    registration_country_business_numbers,
    registration_company_lookup,
    registration_step2_new_company,
    registration_step2_existing_company,
    registration_step3_company_cpvs,
    company_current_cpvs,
    CompanyViewSet,
    CompanySupplierViewSet,
    CompanyUserViewSet,
    RoleViewSet,
    PermissionViewSet,
    NotificationViewSet,
    BranchViewSet,
    DepartmentViewSet,
    BranchUserViewSet,
    DepartmentUserViewSet,
    CategoryViewSet,
    CategoryUserViewSet,
    ExpenseArticleViewSet,
    ExpenseArticleUserViewSet,
    UnitOfMeasureViewSet,
    NomenclatureViewSet,
    CurrencyViewSet,
    TenderCriterionViewSet,
    TenderAttributeViewSet,
    ApprovalModelRoleViewSet,
    ApprovalModelRoleUserViewSet,
    ApprovalRangeMatrixViewSet,
    ApprovalModelViewSet,
    ApprovalModelStepViewSet,
    ProcurementTenderViewSet,
    SalesTenderViewSet,
    CpvDictionaryTreeView,
    CpvDictionaryChildrenView,
    CpvWithCompaniesView,
    me,
    me_avatar_upload,
    password_reset_request,
    password_reset_confirm,
    password_change,
)

router = DefaultRouter()
router.register(r"companies", CompanyViewSet, basename="company")
router.register(r"company-suppliers", CompanySupplierViewSet, basename="company-supplier")
router.register(r"memberships", CompanyUserViewSet, basename="membership")
router.register(r"roles", RoleViewSet, basename="role")
router.register(r"permissions", PermissionViewSet, basename="permission")
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"branches", BranchViewSet, basename="branch")
router.register(r"departments", DepartmentViewSet, basename="department")
router.register(r"branch-users", BranchUserViewSet, basename="branch-user")
router.register(r"department-users", DepartmentUserViewSet, basename="department-user")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"category-users", CategoryUserViewSet, basename="category-user")
router.register(r"expenses", ExpenseArticleViewSet, basename="expense")
router.register(r"expense-users", ExpenseArticleUserViewSet, basename="expense-user")
router.register(r"units", UnitOfMeasureViewSet, basename="unit")
router.register(r"nomenclatures", NomenclatureViewSet, basename="nomenclature")
router.register(r"currencies", CurrencyViewSet, basename="currency")
router.register(r"tender-criteria", TenderCriterionViewSet, basename="tender-criterion")
router.register(r"tender-attributes", TenderAttributeViewSet, basename="tender-attribute")
router.register(r"approval-model-roles", ApprovalModelRoleViewSet, basename="approval-model-role")
router.register(r"approval-model-role-users", ApprovalModelRoleUserViewSet, basename="approval-model-role-user")
router.register(r"approval-range-matrix", ApprovalRangeMatrixViewSet, basename="approval-range-matrix")
router.register(r"approval-models", ApprovalModelViewSet, basename="approval-model")
router.register(r"approval-model-steps", ApprovalModelStepViewSet, basename="approval-model-step")
router.register(r"procurement-tenders", ProcurementTenderViewSet, basename="procurement-tender")
router.register(r"sales-tenders", SalesTenderViewSet, basename="sales-tender")

urlpatterns = [
    # Auth
    path("auth/login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", me, name="me"),
    path("auth/me/avatar/", me_avatar_upload, name="me_avatar_upload"),
    path("auth/password-reset/", password_reset_request, name="password_reset_request"),
    path("auth/password-reset/confirm/", password_reset_confirm, name="password_reset_confirm"),
    path("auth/password-change/", password_change, name="password_change"),
    # Registration
    path("registration/step1/", registration_step1, name="registration_step1"),
    path("registration/country-business-numbers/", registration_country_business_numbers, name="registration_country_business_numbers"),
    path("registration/company-by-code/", registration_company_lookup, name="registration_company_lookup"),
    path("registration/step2/new/", registration_step2_new_company, name="registration_step2_new"),
    path("registration/step2/existing/", registration_step2_existing_company, name="registration_step2_existing"),
    path("registration/step3/company-cpvs/", registration_step3_company_cpvs, name="registration_step3_company_cpvs"),
    # CPV довідник
    path("cpv/tree/", CpvDictionaryTreeView.as_view(), name="cpv-tree"),
    path("cpv/children/", CpvDictionaryChildrenView.as_view(), name="cpv-children"),
    path("cpv/with-companies/", CpvWithCompaniesView.as_view(), name="cpv-with-companies"),
    # Company CPV settings for current user
    path("companies/current-cpvs/", company_current_cpvs, name="company_current_cpvs"),
    # Router viewsets
    path("", include(router.urls)),
]
