from rest_framework import generics
from .serializers import CheckEmailSerializer, CustomTokenObtainPairSerializer, SignupSerializer, UserSerializer
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.permissions import IsAuthenticated

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
        serializer = self.get_serializer(data=request.data)
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
        user.save(update_fields=[
            'is_active', 'is_email_verified', 'email_verification_token'])
        return Response({'detail': 'Email verified successfully'}, status=status.HTTP_200_OK)


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]
    serializer_class = CustomTokenObtainPairSerializer

    def finalize_response(self, request, response, *args, **kwargs):
        data = response.data
        refresh = data.get('refresh')
        access = data.get('access')
        remember = data.get('remember')
        common = dict(httponly=True, secure=True, samesite='Lax')

        if refresh:
            if remember:
                response.set_cookie('refresh_token', refresh,
                                    max_age=7*24*3600, **common)
            else:
                response.set_cookie('refresh_token', refresh,
                                    **common)  # session cookie
            del response.data['refresh']

        if access:
            response.set_cookie('access_token', access, max_age=5*60, **common)
            del response.data['access']
        return super().finalize_response(request, response, *args, **kwargs)


class CookieTokenRefreshView(TokenRefreshView):
    # actually inherits from the parent class TokenRefreshView - For learning support only
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def finalize_response(self, request, response, *args, **kwargs):
        data = response.data
        access = data.get('access')
        if access:
            response.set_cookie(
                'access_token', access,
                httponly=True, secure=True, samesite='Lax', max_age=5*60
            )
            del response.data['access']
        return super().finalize_response(request, response, *args, **kwargs)


class CsrfTokenView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request, *args, **kwargs):
        return Response({'detail': 'CSRF cookie set'}, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        if request.user and request.user.is_authenticated:
            return Response(UserSerializer(request.user).data, status=200)
        # nicht eingeloggt → 200 mit null
        return Response(None, status=200)
