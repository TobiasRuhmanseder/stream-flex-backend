from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from . import functions

@receiver(post_save, sender=User)
def send_verification_email_signal(sender, instance: User, created, **kwargs):
    """On user creation, ensure a fresh token and send the verification email.
    Uses shared helpers from users/functions.py to avoid duplication.
    """
    if not created:
        return
    # Always (re)generate a fresh token on signup, then send mail via helper
    instance.generate_email_verification_token()
    functions.send_verification_email(instance)
