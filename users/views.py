from rest_framework import generics
from .serializers import CheckEmailSerializer, SignupSerializer
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework import status
from django.shortcuts import get_object_or_404

User = get_user_model()

class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    throttle_classes = [AnonRateThrottle]
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


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request, *args, **kwargs):
        token = request.query_params.get('token')
        user = get_object_or_404(User, email_verification_token=token)
        user.is_active = True
        user.is_email_verified = True
        user.email_verification_token = ''
        user.save(update_fields=['is_active', 'is_email_verified', 'email_verification_token'])
        return Response({'detail': 'Email verified successfully'}, status=status.HTTP_200_OK)
