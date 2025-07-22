from rest_framework import generics
from .serializers import CheckEmailSerializer, SignupSerializer
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from django.contrib.auth import get_user_model

User = get_user_model()


class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = SignupSerializer


class CheckEmailView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]
    serializer_class = CheckEmailSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception=True)
        exists = False
        email = serializer.validated_data['email']
        if email:
            exists = User.objects.filter(email__iexact=email).exists()
        return Response({'exists': exists})
