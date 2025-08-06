from django.urls import path
from .views import CheckEmailView, SignupView, VerifyEmailView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('check-email/', CheckEmailView.as_view(), name='check-email'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
]
