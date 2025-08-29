# users/tests_validators.py
import pytest
from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError

from users.validators import validate_strong_password, validate_unique_email

User = get_user_model()


# ---------- validate_strong_password ----------

@pytest.mark.parametrize(
    "password",
    [
        # meets: ≥8 chars (Django’s default), has upper, lower, digit, special
        "GoodPass1!",
        "Aa1!aaaa",
        "Str0ng&P@ss",
        "Xx9_Valid*",
    ],
)
def test_validate_strong_password_ok(password):
    # Should not raise
    assert validate_strong_password(password) == password


@pytest.mark.parametrize(
    "password, expected_msg_part",
    [
        # missing special char
        ("NoSpecial1", "special"),
        # missing digit
        ("NoDigit!!A", "number"),
        # missing uppercase
        ("lower1!!", "uppercase"),
        # missing lowercase
        ("UPPER1!!", "lowercase"),
    ],
)
def test_validate_strong_password_regex_fail(password, expected_msg_part):
    with pytest.raises(serializers.ValidationError) as exc:
        validate_strong_password(password)
    # Make sure it’s our regex message, not a Django length error
    assert expected_msg_part in str(exc.value)


# If your project keeps Django’s MinimumLengthValidator(8) active,
# this ensures we also see the built-in validator fail clearly.
@pytest.mark.parametrize("password", ["Aa1!", "Ab1@", "Z9$a"])  # too short
def test_validate_strong_password_django_length_fail(password, settings):
    """Ensure Django's built-in length validator is active for this test.

    We explicitly set AUTH_PASSWORD_VALIDATORS so the outcome is stable
    regardless of the global project/test settings. With a minimum length
    of 8, these short passwords must trigger a ValidationError before
    our regex check even runs.
    """
    settings.AUTH_PASSWORD_VALIDATORS = [
        {
            "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
            "OPTIONS": {"min_length": 8},
        }
    ]

    with pytest.raises((DjangoValidationError, serializers.ValidationError)):
        validate_strong_password(password)


# ---------- validate_unique_email ----------

@pytest.mark.django_db
def test_validate_unique_email_ok_when_not_taken():
    # Should return the trimmed email unchanged when not in DB
    assert validate_unique_email(" new@example.com ") == "new@example.com"


@pytest.mark.django_db
def test_validate_unique_email_case_insensitive_collision():
    # Create existing user (use both username and email to be safe for custom model)
    User.objects.create_user(username="alice@example.com", email="alice@example.com", password="xX1!xxxx")
    with pytest.raises(serializers.ValidationError) as exc:
        validate_unique_email("  ALICE@example.com ")
    assert "already in use" in str(exc.value)