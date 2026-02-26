from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, APITestCase

from .models import Company, CompanyUser, Role
from .views import _resolve_request_company_id

User = get_user_model()


class ResolveRequestCompanyIdTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(email="u@example.com", password="testpass123")

    def _approve_membership(self, company):
        role = Role.objects.create(company=company, name=f"Role-{company.edrpou}")
        CompanyUser.objects.create(
            user=self.user,
            company=company,
            role=role,
            status=CompanyUser.Status.APPROVED,
        )

    def test_returns_single_company_when_only_one_membership(self):
        company = Company.objects.create(edrpou="10000001", name="One")
        self._approve_membership(company)

        request = self.factory.post("/api/dummy/", {}, format="json")
        request.user = self.user

        company_id, error_response = _resolve_request_company_id(request)
        self.assertIsNone(error_response)
        self.assertEqual(company_id, company.id)

    def test_requires_explicit_company_id_for_multiple_memberships(self):
        company_a = Company.objects.create(edrpou="10000002", name="A")
        company_b = Company.objects.create(edrpou="10000003", name="B")
        self._approve_membership(company_a)
        self._approve_membership(company_b)

        request = self.factory.post("/api/dummy/", {}, format="json")
        request.user = self.user

        company_id, error_response = _resolve_request_company_id(request)
        self.assertIsNone(company_id)
        self.assertIsNotNone(error_response)
        self.assertEqual(error_response.status_code, 400)

    def test_accepts_explicit_company_id_from_query_params(self):
        company_a = Company.objects.create(edrpou="10000004", name="A")
        company_b = Company.objects.create(edrpou="10000005", name="B")
        self._approve_membership(company_a)
        self._approve_membership(company_b)

        request = self.factory.get(f"/api/dummy/?company_id={company_b.id}")
        request.user = self.user

        company_id, error_response = _resolve_request_company_id(request)
        self.assertIsNone(error_response)
        self.assertEqual(company_id, company_b.id)


@override_settings(DEBUG=True)
class PasswordResetFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="reset@example.com", password="oldpass123")

    def test_password_reset_request_returns_debug_token_for_existing_user(self):
        response = self.client.post("/api/auth/password-reset/", {"email": self.user.email}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.data)
        self.assertIn("reset_token", response.data)
        self.assertIn(":", response.data["reset_token"])

    def test_password_reset_confirm_changes_password(self):
        request_response = self.client.post("/api/auth/password-reset/", {"email": self.user.email}, format="json")
        token = request_response.data["reset_token"]

        confirm_response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"token": token, "new_password": "newpass123A!"},
            format="json",
        )
        self.assertEqual(confirm_response.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass123A!"))

    def test_password_reset_confirm_rejects_invalid_token(self):
        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"token": "bad:token", "new_password": "newpass123A!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class RegistrationCompanyLookupTests(APITestCase):
    def test_returns_not_exists_when_company_absent(self):
        response = self.client.get("/api/registration/company-by-code/?edrpou=99999999")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("exists"), False)
        self.assertEqual(response.data.get("has_registered_users"), False)
        self.assertIsNone(response.data.get("company"))

    def test_returns_company_and_registered_users_flag(self):
        company = Company.objects.create(
            edrpou="12345678",
            name="Test Company",
            subject_type=Company.SubjectType.LEGAL_RESIDENT,
            company_address="Kyiv",
            registration_country="UA",
        )
        user = User.objects.create_user(email="member@example.com", password="pass12345")
        role = Role.objects.create(company=company, name="Адміністратор")
        CompanyUser.objects.create(
            user=user,
            company=company,
            role=role,
            status=CompanyUser.Status.APPROVED,
        )

        response = self.client.get("/api/registration/company-by-code/?edrpou=12345678")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("exists"), True)
        self.assertEqual(response.data.get("has_registered_users"), True)
        self.assertEqual(response.data.get("company", {}).get("edrpou"), "12345678")


class RegistrationStep2ExistingFlowTests(APITestCase):
    def test_join_existing_company_with_approved_users_sets_registration_step_4(self):
        company = Company.objects.create(edrpou="55556666", name="Existing Co")
        admin_user = User.objects.create_user(email="admin@existing.co", password="pass12345")
        admin_role = Role.objects.create(company=company, name="Адміністратор")
        CompanyUser.objects.create(
            user=admin_user,
            company=company,
            role=admin_role,
            status=CompanyUser.Status.APPROVED,
        )

        new_user = User.objects.create_user(email="new@existing.co", password="pass12345", registration_step=2)

        response = self.client.post(
            "/api/registration/step2/existing/",
            {"user_id": new_user.id, "edrpou": company.edrpou},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        new_user.refresh_from_db()
        self.assertEqual(new_user.registration_step, 4)

