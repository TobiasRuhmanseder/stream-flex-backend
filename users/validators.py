import re
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model

PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).+$')
User = get_user_model()


def validate_strong_password(value):
    validate_password(value)
    if not PASSWORD_REGEX.fullmatch(value):
        raise serializers.ValidationError(
            'Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character.'
        )
    return value


def validate_unique_email(value: str) -> str:
    v = (value or '').strip()
    if User.objects.filter(email__iexact=v).exists():
        raise serializers.ValidationError("Email is already in use.")
    return 