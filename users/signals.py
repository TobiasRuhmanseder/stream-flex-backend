from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from .models import User


@receiver(post_save, sender=User)
def send_verification_email(sender, instance: User, created, **kwargs):
    if not created:
        return

    instance.generate_email_verification_token()
    verify_url = f'{settings.FRONTEND_URL}/home/sign-in/verify-email?token={instance.email_verification_token}'
    context = {
        'user': instance,
        'verify_url': verify_url,
    }

    subject = 'Please confirm your email at Streamflex'
    text_body = render_to_string('emails/verification_email.txt', context)
    html_body = render_to_string('emails/verification_email.html', context)

    # send multi-part email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[instance.email],
    )
    email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=False)
