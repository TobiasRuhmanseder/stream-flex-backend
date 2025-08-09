from django.urls import path
from .views import CheckEmailView, CurrentUserView, CookieTokenRefreshView, CsrfTokenView, SignInView, SignOutView, SignupView, VerifyEmailView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('check-email/', CheckEmailView.as_view(), name='check-email'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('sign-in/', SignInView.as_view(), name='login'),
    path('sign-out/', SignOutView.as_view(), name='logout'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('token-refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('csrf/', CsrfTokenView.as_view(), name='csrf_token'),
]
