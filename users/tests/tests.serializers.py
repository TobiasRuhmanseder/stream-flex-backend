# users/tests/tests_serializers.py
import pytest
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator

from users.serializers import (
    SignupSerializer,
    CustomTokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
)
from users import validators
from users.exeptions import AccountNotActivated

User = get_user_model()


@pytest.fixture(autouse=True)
def _relax_recaptcha_and_password(monkeypatch):
    """
    Macht ReCaptcha-Felder im Test harmlos (normale CharField)
    und schaltet die starke Passwortprüfung aus,
    damit wir uns auf die Serializer-Logik fokussieren können.
    """
    # ReCaptcha im SignupSerializer
    if "recaptchaToken" in SignupSerializer._declared_fields:
        SignupSerializer._declared_fields["recaptchaToken"] = serializers.CharField(required=False)
    # ReCaptcha im Token-Serializer
    if "recaptchaToken" in CustomTokenObtainPairSerializer._declared_fields:
        CustomTokenObtainPairSerializer._declared_fields["recaptchaToken"] = serializers.CharField(required=False)
    # ReCaptcha im Password-Reset-Confirm
    if "recaptchaToken" in PasswordResetConfirmSerializer._declared_fields:
        PasswordResetConfirmSerializer._declared_fields["recaptchaToken"] = serializers.CharField(required=False)

    # Starken Passwort-Validator neutralisieren
    monkeypatch.setattr(validators, "validate_strong_password", lambda v: v)


# ---------- SignupSerializer.create (Zeilen 49–52) ----------

@pytest.mark.django_db
def test_signup_serializer_creates_inactive_user():
    data = {"email": "newuser@example.com", "password": "Abcdef1!", "recaptchaToken": "x"}
    ser = SignupSerializer(data=data)
    assert ser.is_valid(), ser.errors
    user = ser.save()  # triggert create(...)
    assert isinstance(user, User)
    assert user.username == "newuser@example.com"
    assert user.email == "newuser@example.com"
    assert user.is_active is False  # wird in create explizit auf False gesetzt


# ---------- CustomTokenObtainPairSerializer.validate (Zeilen 65–91) ----------

@pytest.mark.django_db
def test_token_obtain_pair_success_with_remember_true():
    pwd = "Abcdef1!"
    u = User.objects.create_user(username="alice@example.com", email="alice@example.com", password=pwd, is_active=True)

    # USERNAME_FIELD ist bei CustomUser meist "username", bei E-Mail-Login evtl. auch "email".
    identifier_key = User.USERNAME_FIELD
    payload = {identifier_key: u.username, "password": pwd, "remember": True, "recaptchaToken": "x"}

    ser = CustomTokenObtainPairSerializer(data=payload)
    assert ser.is_valid(), ser.errors
    out = ser.validated_data

    # Tokens + remember + eingebetteter User
    assert "refresh" in out and out["refresh"]
    assert "access" in out and out["access"]
    assert out.get("remember") is True
    assert out.get("user", {}).get("id") == u.id
    # Ser hält referenz auf user
    assert getattr(ser, "user", None) == u


@pytest.mark.django_db
def test_token_obtain_pair_invalid_credentials_raises():
    pwd = "Abcdef1!"
    u = User.objects.create_user(username="bob@example.com", email="bob@example.com", password=pwd, is_active=True)

    identifier_key = User.USERNAME_FIELD
    bad = {identifier_key: u.username, "password": "WRONG", "recaptchaToken": "x"}

    ser = CustomTokenObtainPairSerializer(data=bad)
    with pytest.raises(AuthenticationFailed):
        ser.is_valid(raise_exception=True)


@pytest.mark.django_db
def test_token_obtain_pair_inactive_account_raises_account_not_activated():
    pwd = "Abcdef1!"
    u = User.objects.create_user(
        username="inactive@example.com", email="inactive@example.com", password=pwd, is_active=False
    )

    identifier_key = User.USERNAME_FIELD
    data = {identifier_key: u.username, "password": pwd, "recaptchaToken": "x"}

    ser = CustomTokenObtainPairSerializer(data=data)
    with pytest.raises(AccountNotActivated):
        ser.is_valid(raise_exception=True)


# ---------- PasswordResetConfirmSerializer.validate (Zeilen 112–123) ----------

@pytest.mark.django_db
def test_password_reset_confirm_validate_success():
    user = User.objects.create_user(username="pw@example.com", email="pw@example.com", password="OldPass123!")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = PasswordResetTokenGenerator().make_token(user)

    data = {
        "uid": uid,
        "token": token,
        "new_password": "NewPass123!",
        "recaptchaToken": "x",
    }
    ser = PasswordResetConfirmSerializer(data=data)
    assert ser.is_valid(), ser.errors
    # validate hängt den User in attrs
    assert ser.validated_data["user"].id == user.id


@pytest.mark.django_db
def test_password_reset_confirm_invalid_uid_raises_validation_error():
    data = {"uid": "!!!", "token": "whatever", "new_password": "NewPass123!", "recaptchaToken": "x"}
    ser = PasswordResetConfirmSerializer(data=data)
    with pytest.raises(ValidationError):
        ser.is_valid(raise_exception=True)


@pytest.mark.django_db
def test_password_reset_confirm_invalid_token_raises_validation_error():
    user = User.objects.create_user(username="tok@example.com", email="tok@example.com", password="OldPass123!")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    bad = {"uid": uid, "token": "obviously-wrong", "new_password": "NewPass123!", "recaptchaToken": "x"}
    ser = PasswordResetConfirmSerializer(data=bad)
    with pytest.raises(ValidationError):
        ser.is_valid(raise_exception=True)