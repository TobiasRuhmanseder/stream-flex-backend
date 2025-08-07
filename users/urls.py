from django.urls import path
from .views import CheckEmailView, CookieTokenObtainPairView, CookieTokenRefreshView, CsrfTokenView, SignupView, VerifyEmailView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('check-email/', CheckEmailView.as_view(), name='check-email'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('token/', CookieTokenObtainPairView.as_view(), name='token_obtain'),
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('csrf/', CsrfTokenView.as_view(), name='csrf_token'),
]
