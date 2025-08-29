# conftest.py
import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def create_user():
    def _make(**overrides):
        User = get_user_model()
        data = {
            "email": "user@example.com",
            "password": "pass12345",
            "is_active": True,
        }
        data.update(overrides)

        # If the model still uses 'username', supply one
        if getattr(User, "USERNAME_FIELD", "username") == "username":
            data.setdefault("username", (data.get("email") or "user").split("@")[0])

        # Some managers require REQUIRED_FIELDS too (e.g., first_name/last_name)
        for field in getattr(User, "REQUIRED_FIELDS", []):
            data.setdefault(field, f"default_{field}")

        return User.objects.create_user(**data)

    return _make


@pytest.fixture
def user(create_user):
    return create_user()
