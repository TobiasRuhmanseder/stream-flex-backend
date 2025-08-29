from core.settings import *  # Import all defaults
import os

# Always debug in tests
DEBUG = True

# Use SQLite in memory for speed (kein Postgres nötig)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Use local memory cache (kein Redis nötig)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-test",
    }
}

# Background tasks disabled (RQ nicht nötig)
RQ_QUEUES = {}

# E-Mail backend: alle Mails ins Array (kein SMTP nötig)
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Schnelleres Hashing (Passwörter)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# JWT Cookies für Tests unsicher machen
SIMPLE_JWT["AUTH_COOKIE_SECURE"] = False

# drf-recaptcha: in Tests immer bestehen lassen
DRF_RECAPTCHA_TESTING = True
DRF_RECAPTCHA_TESTING_PASS = True  # alle Prüfungen "grün"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Für Tasks: wohin Temp-Dateien zeigen dürfen (kann auch ein tmp-Ordner sein)
MEDIA_ROOT = BASE_DIR / "test_media"
