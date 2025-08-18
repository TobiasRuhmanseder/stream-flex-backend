from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid


class User(AbstractUser):
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=64, blank=True, null=True)
    email_token_created = models.DateTimeField(blank=True, null=True)

    def generate_email_verification_token(self):
        self.email_verification_token = uuid.uuid4().hex
        self.email_token_created = timezone.now()
        self.save(update_fields=["email_verification_token", "email_token_created"])
