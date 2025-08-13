from urllib.parse import urlencode
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from .models import User

def ensure_email_verification_token(user: User) -> str:
    """Ensure the user has a verification token and return it.
    Generates and persists a new token if missing.
    """
    if not getattr(user, 'email_verification_token', None):
        user.generate_email_verification_token()
    return user.email_verification_token

def build_verify_url(user: User) -> str:
    """Build the frontend verification URL including token (+ email for prefill)."""
    token = ensure_email_verification_token(user)
    query = urlencode({'token': token, 'email': user.email})
    return f"{settings.FRONTEND_URL}/home/verify-email?{query}"

def render_verification_bodies(user: User, verify_url: str) -> tuple[str, str, str]:
    """Return (subject, text_body, html_body) for the verification email."""
    context = {'user': user, 'verify_url': verify_url}
    subject = 'Please confirm your email at Streamflex'
    # Keep both txt + html templates for compatibility with different mail clients
    text_body = render_to_string('emails/verification_email.txt', context)
    html_body = render_to_string('emails/verification_email.html', context)
    # Fallback if txt template is missing: derive from html
    if not text_body or not text_body.strip():
        text_body = strip_tags(html_body)
    return subject, text_body, html_body

def send_verification_email(user: User) -> None:
    """Send the verification email to the user (multipart plain+HTML)."""
    verify_url = build_verify_url(user)
    subject, text_body, html_body = render_verification_bodies(user, verify_url)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        to=[user.email],
    )
    msg.attach_alternative(html_body, 'text/html')
    msg.send()
