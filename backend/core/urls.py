from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomTokenObtainPairView,
    registration_step1,
    registration_step2_new_company,
    registration_step2_existing_company,
    CompanyViewSet,
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
    ProcurementTenderViewSet,
    SalesTenderViewSet,
    CpvDictionaryTreeView,
    CpvDictionaryChildrenView,
    me,
    password_reset_request,
    password_reset_confirm,
    password_change,
)

router = DefaultRouter()
router.register(r"companies", CompanyViewSet, basename="company")
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
router.register(r"procurement-tenders", ProcurementTenderViewSet, basename="procurement-tender")
router.register(r"sales-tenders", SalesTenderViewSet, basename="sales-tender")

urlpatterns = [
    # Auth
    path("auth/login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", me, name="me"),
    path("auth/password-reset/", password_reset_request, name="password_reset_request"),
    path("auth/password-reset/confirm/", password_reset_confirm, name="password_reset_confirm"),
    path("auth/password-change/", password_change, name="password_change"),
    # Registration
    path("registration/step1/", registration_step1, name="registration_step1"),
    path("registration/step2/new/", registration_step2_new_company, name="registration_step2_new"),
    path("registration/step2/existing/", registration_step2_existing_company, name="registration_step2_existing"),
    # CPV довідник
    path("cpv/tree/", CpvDictionaryTreeView.as_view(), name="cpv-tree"),
    path("cpv/children/", CpvDictionaryChildrenView.as_view(), name="cpv-children"),
    # Router viewsets
    path("", include(router.urls)),
]

