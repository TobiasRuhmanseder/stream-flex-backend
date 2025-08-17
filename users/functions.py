from urllib.parse import urlencode
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from .models import User
from urllib.parse import urlencode
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth import get_user_model

User = get_user_model()


def ensure_email_verification_token(user):
    """Ensure the user has a verification token and return it.
    Generates and persists a new token if missing.
    """
    if not getattr(user, 'email_verification_token', None):
        user.generate_email_verification_token()
    return user.email_verification_token


def build_verify_url(user):
    """Build the frontend verification URL including token (+ email for prefill)."""
    token = ensure_email_verification_token(user)
    query = urlencode({'token': token, 'email': user.email})
    return f"{settings.FRONTEND_URL}/home/verify-email?{query}"


def render_verification_bodies(user, verify_url):
    """Return (subject, text_body, html_body) for the verification email."""
    context = {'user': user, 'verify_url': verify_url}
    subject = 'Please confirm your email at Streamflex'

    text_body = render_to_string('emails/verification_email.txt', context)
    html_body = render_to_string('emails/verification_email.html', context)

    if not text_body or not text_body.strip():
        text_body = strip_tags(html_body)
    return subject, text_body, html_body


def send_verification_email(user):
    """Send the verification email to the user (multipart plain+HTML)."""
    verify_url = build_verify_url(user)
    subject, text_body, html_body = render_verification_bodies(
        user, verify_url)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        to=[user.email],
    )
    msg.attach_alternative(html_body, 'text/html')
    msg.send()


def build_password_reset_url(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = PasswordResetTokenGenerator().make_token(user)
    query = urlencode({'uid': uid, 'token': token, 'email': user.email})
    return f"{settings.FRONTEND_URL}/home/password-reset?{query}"


def render_password_reset_bodies(user, reset_url):
    ctx = {'user': user, 'reset_url': reset_url}
    subject = 'Reset your password at Streamflex'
    text_body = render_to_string('emails/password_reset.txt', ctx)
    html_body = render_to_string('emails/password_reset.html', ctx)
    if not text_body or not text_body.strip():
        text_body = strip_tags(html_body)
    return subject, text_body, html_body


def send_password_reset_email(user):
    reset_url = build_password_reset_url(user)
    subject, text_body, html_body = render_password_reset_bodies(user, reset_url)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        to=[user.email],
    )
    msg.attach_alternative(html_body, 'text/html')
    msg.send()
