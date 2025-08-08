from django.urls import path
from .views import CheckEmailView, CurrentUserView, LoginView, CookieTokenRefreshView, CsrfTokenView, SignupView, VerifyEmailView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('check-email/', CheckEmailView.as_view(), name='check-email'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('login/', LoginView.as_view(), name='token_obtain'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('token-refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('csrf/', CsrfTokenView.as_view(), name='csrf_token'),
]
