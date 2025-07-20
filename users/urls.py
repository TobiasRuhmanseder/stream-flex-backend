from django.urls import path
from .views import CheckEmailView, SignupView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('check-email/', CheckEmailView.as_view(), name='check-email'),
]
