from django.urls import path
from .views import CheckEmailView, CurrentUserView, CookieTokenRefreshView, CsrfTokenView, ResendVerificationEmailView, SignInView, SignOutView, SignupView, VerifyEmailView, PasswordResetConfirmView, PasswordResetRequestView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('check-email/', CheckEmailView.as_view(), name='check-email'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('sign-in/', SignInView.as_view(), name='login'),
    path('sign-out/', SignOutView.as_view(), name='logout'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('token-refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('csrf/', CsrfTokenView.as_view(), name='csrf_token'),
    path('resend-verification/', ResendVerificationEmailView.as_view(), name='resend-verification'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]
