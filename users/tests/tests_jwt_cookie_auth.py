import pytest
from unittest.mock import patch, MagicMock
from django.test import RequestFactory
from rest_framework import exceptions

from users.jwt_cookie_auth import CustomAuthentication, enforce_csrf
from rest_framework_simplejwt.exceptions import InvalidToken


rf = RequestFactory()


def test_enforce_csrf_returns_on_safe_methods():
    req = rf.get("/")
    # should not raise
    enforce_csrf(req)


def test_enforce_csrf_raises_on_post_without_csrf_token():
    req = rf.post("/")
    with pytest.raises(exceptions.PermissionDenied):
        enforce_csrf(req)


def test_authenticate_uses_authorization_header_get_raw_token():
    req = rf.get("/")
    req.META["HTTP_AUTHORIZATION"] = "Bearer something"

    auth = CustomAuthentication()
    with patch.object(auth, "get_raw_token", return_value="rawtok") as p_get_raw, \
         patch.object(auth, "get_validated_token", return_value="validated") as p_validate, \
         patch.object(auth, "get_user", return_value=MagicMock()) as p_user:
        user, validated = auth.authenticate(req)

    p_get_raw.assert_called_once()        # ensures we hit line 24
    p_validate.assert_called_once_with("rawtok")
    p_user.assert_called_once()
    assert validated == "validated"


def test_authenticate_calls_enforce_csrf_on_unsafe_method_with_cookie():
    req = rf.post("/")
    # simulate access token stored in cookie
    req.COOKIES["access_token"] = "cookie_token"

    auth = CustomAuthentication()
    # Patch enforce_csrf in the module to observe the call
    with patch("users.jwt_cookie_auth.enforce_csrf") as p_enforce, \
         patch.object(auth, "get_validated_token", return_value="validated") as p_validate, \
         patch.object(auth, "get_user", return_value=MagicMock()) as p_user:
        user, validated = auth.authenticate(req)

    p_validate.assert_called_once_with("cookie_token")
    p_user.assert_called_once()
    p_enforce.assert_called_once_with(req)  # ensures we hit line 34
    assert validated == "validated"


def test_authenticate_returns_none_on_invalid_token_from_cookie():
    req = rf.get("/")
    req.COOKIES["access_token"] = "bad"

    auth = CustomAuthentication()
    with patch.object(auth, "get_validated_token", side_effect=InvalidToken("bad")):
        result = auth.authenticate(req)

    assert result is None