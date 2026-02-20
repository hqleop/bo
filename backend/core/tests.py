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
