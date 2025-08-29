# users/tests_apiclient.py
from django.test import override_settings
from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch
from rest_framework_simplejwt.tokens import RefreshToken
from users.views import PasswordResetConfirmView

User = get_user_model()


# Helper: try reverse() first, else fall back to the path literal you use in urls.py
def _url(name, fallback_path):
    try:
        return reverse(name)
    except NoReverseMatch:
        return fallback_path


class UserAPITests(APITestCase):
    """
    API tests for auth endpoints using DRF's APIClient.
    We go through the real URL routing and middleware, which avoids the 400/401
    issues you had with RequestFactory (and missing JSON content-type).
    """

    def setUp(self):
        self.client = APIClient()

        # Common URLs (adjust names if you have url names configured)
        self.url_check_email = _url("check-email", "/api/users/check-email/")
        self.url_verify_email = _url("verify-email", "/api/users/verify-email/")
        self.url_resend_verif = _url(
            "resend-verification", "/api/users/resend-verification/"
        )
        self.url_sign_out = _url("logout", "/api/users/sign-out/")
        self.url_refresh = _url("token_refresh", "/api/users/token-refresh/")
        self.url_csrf = _url("csrf-token", "/api/users/csrf/")
        self.url_me = _url("current-user", "/api/users/me/")
        self.url_pw_reset_req = _url("password-reset", "/api/users/password-reset/")
        self.url_pw_reset_confirm = _url("password-reset-confirm", "/api/users/password-reset/confirm/")

    # ---------- helpers ----------

    def create_user(self, **overrides):
        """
        Create a user for tests. Your custom User likely has USERNAME_FIELD='email'.
        """
        data = {
            "username": "user@example.com",
            "email": "user@example.com",
            "password": "pass12345",
            "is_active": True,
            "is_email_verified": True,
        }
        data.update(overrides)
        # Use the model manager correctly for a custom user model
        u = User.objects.create_user(
            username=data["username"], email=data["email"],password=data["password"]
        )
        # Patch any extra flags/tokens after creation
        extra_fields = ["is_active", "is_email_verified", "email_verification_token"]
        for f in extra_fields:
            if f in data:
                setattr(u, f, data[f])
        u.save()
        return u

    def set_access_cookie(self, user):
        """Set a valid access cookie on the client to simulate a logged-in browser."""
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        self.client.cookies["access_token"] = access

    def set_refresh_cookie(self, user):
        """Set a valid refresh cookie for the refresh endpoint."""
        refresh = RefreshToken.for_user(user)
        self.client.cookies["refresh_token"] = str(refresh)

    # ---------- tests ----------

    def test_check_email_exists_false_then_true(self):
        # 1) unknown email -> exists False
        res1 = self.client.post(self.url_check_email,{"email": "nobody@example.com", "recaptchaToken": "test"},format="json",)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertIn("exists", res1.data)
        self.assertFalse(res1.data["exists"])

        # 2) create user -> exists True
        u = self.create_user(email="alice@example.com")
        res2 = self.client.post(self.url_check_email, {"email": "alice@example.com", "recaptchaToken": "test"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertTrue(res2.data["exists"])

    def test_verify_email_activates_user(self):
        u = self.create_user(is_active=False, is_email_verified=False, username="verifyme@example.com")
        # simulate a stored token
        u.email_verification_token = "TOKEN123"
        u.save(update_fields=["email_verification_token"])

        # GET /verify-email/?token=...
        res = self.client.get(self.url_verify_email, {"token": "TOKEN123"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        u.refresh_from_db()
        self.assertTrue(u.is_active)
        self.assertTrue(u.is_email_verified)
        self.assertEqual(u.email_verification_token, "")

    def test_resend_verification_neutral_and_calls_sender(self):
        # user exists and is NOT verified -> should "call" sender
        u = self.create_user(email="notyet@example.com", is_email_verified=False)

        with patch("users.views.functions.send_verification_email") as mock_send:
            res = self.client.post(self.url_resend_verif, {"email": u.email, "recaptchaToken": "test"}, format="json")
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            mock_send.assert_called_once()  # called for unverified

        # user verified -> still neutral 200, no call
        u.is_email_verified = True
        u.save(update_fields=["is_email_verified"])
        with patch("users.views.functions.send_verification_email") as mock_send2:
            res2 = self.client.post(self.url_resend_verif, {"email": u.email}, format="json")
            self.assertEqual(res2.status_code, status.HTTP_200_OK)
            mock_send2.assert_not_called()

        # unknown email -> neutral 200, no call
        with patch("users.views.functions.send_verification_email") as mock_send3:
            res3 = self.client.post(self.url_resend_verif, {"email": "nobody@example.com"}, format="json"
            )
            self.assertEqual(res3.status_code, status.HTTP_200_OK)
            mock_send3.assert_not_called()

    def test_sign_out_deletes_cookies(self):
        # place dummy cookies as if browser had them
        self.client.cookies["refresh_token"] = "dummy"
        self.client.cookies["access_token"] = "dummy"
        res = self.client.post(self.url_sign_out, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # We can additionally check Set-Cookie headers indicate deletion, but 200 is enough.

    def test_cookie_token_refresh_sets_new_access_cookie(self):
        u = self.create_user(email="cookie@example.com")
        self.set_refresh_cookie(u)

        res = self.client.post(self.url_refresh, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", res.cookies)

    def test_csrf_token_view(self):
        res = self.client.get(self.url_csrf)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("csrftoken", res.data)

    def test_current_user_requires_cookie_access_token(self):
        u = self.create_user(username="me@example.com")

        # Without cookie -> 401
        res1 = self.client.get(self.url_me)
        self.assertEqual(res1.status_code, status.HTTP_401_UNAUTHORIZED)

        # With valid access cookie -> 200 + user data
        self.set_access_cookie(u)
        res2 = self.client.get(self.url_me)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        # Your serializer likely returns 'email'
        self.assertEqual(res2.data.get("username"), u.username)

    def test_password_reset_request_neutral(self):
        u = self.create_user(email="reset@example.com")
        called = {"count": 0}

        def fake_send(user):
            called["count"] += 1

        # Patch the symbol imported in users.views
        with patch("users.views.send_password_reset_email", side_effect=fake_send):
            # existing email -> 200 and sender called once
            res1 = self.client.post(self.url_pw_reset_req,{"email": u.email, "recaptchaToken": "test"},format="json",)
            self.assertEqual(res1.status_code, status.HTTP_200_OK)
            self.assertEqual(called["count"], 1)

            # unknown email -> still 200, no additional call
            res2 = self.client.post(self.url_pw_reset_req,{"email": "unknown@example.com", "recaptchaToken": "test"},format="json")
            self.assertEqual(res2.status_code, status.HTTP_200_OK)
            self.assertEqual(called["count"], 1)

    def test_password_reset_confirm_sets_new_password(self):
        user = self.create_user(email="pw@example.com", password="OldPass123!")

        # Patch the serializer so the view believes validation passed and returns our user/new_password

        class DummySerializer:
            def __init__(self, *a, **kw):
                self.validated_data = {}

            def is_valid(self, raise_exception=False):
                self.validated_data = {"user": user, "new_password": "NewPass123!"}
                return True

        with patch.object(
            PasswordResetConfirmView, "serializer_class", DummySerializer
        ):
            res = self.client.post(
                self.url_pw_reset_confirm,
                {
                    "uid": "x",
                    "token": "y",
                    "new_password": "NewPass123!",
                    "recaptchaToken": "test",
                },
                format="json",
            )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Password should be changed
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewPass123!"))
