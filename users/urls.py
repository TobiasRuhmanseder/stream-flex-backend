from django.urls import path
from .views import CheckEmailView, LoginView, CookieTokenRefreshView, CsrfTokenView, SignupView, VerifyEmailView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('check-email/', CheckEmailView.as_view(), name='check-email'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('login/', LoginView.as_view(), name='token_obtain'),
    path('token-refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('csrf/', CsrfTokenView.as_view(), name='csrf_token'),
]
