from rest_framework import generics
from .serializers import CheckEmailSerializer, CustomTokenObtainPairSerializer, SignupSerializer, UserSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError as JWTTokenError
from django.middleware.csrf import get_token
from . import functions

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


class ResendVerificationEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request, *args, **kwargs):
        """Resend a new verification email if the account exists and is not verified.
        Always respond with 200 to avoid user enumeration.
        Expected JSON body: {"email": "user@example.com"}
        """
        email = (request.data.get('email') or '').strip()
        if not email:
            return Response({'email': ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email__iexact=email).first()
        neutral = Response({'detail': 'If the account exists and is not verified, a new verification email has been sent.'}, status=status.HTTP_200_OK)

        if not user or getattr(user, 'is_email_verified', False):
            return neutral

        # Ensure a fresh token and send using shared helpers
        try:
            if hasattr(user, 'generate_email_verification_token'):
                user.generate_email_verification_token()
            functions.send_verification_email(user)
        except Exception:
            pass

        return neutral


class SignInView(TokenObtainPairView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]
    serializer_class = CustomTokenObtainPairSerializer

    def finalize_response(self, request, response, *args, **kwargs):
        refresh = response.data.get('refresh')
        access = response.data.get('access')
        remember = bool(response.data.pop('remember', False))
        common = dict(httponly=True, secure=True, samesite='None')

        if refresh:
            if remember:
                response.set_cookie(key='refresh_token', value=refresh,
                                    max_age=7*24*3600, **common)
            else:
                response.set_cookie(key='refresh_token', value=refresh,
                                    **common)  # session cookie
            del response.data['refresh']

        if access:
            response.set_cookie(key='access_token',
                                value=access, max_age=5*60, **common)
            del response.data['access']
        return super().finalize_response(request, response, *args, **kwargs)


class SignOutView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        resp = Response({'detail': 'logged out'})
        resp.delete_cookie('access_token', path='/', samesite='None')
        resp.delete_cookie('refresh_token', path='/', samesite='None')
        return resp


class CookieTokenRefreshView(TokenRefreshView):
    # actually inherits from the parent class TokenRefreshView - For learning support only
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request, *args, **kwargs):
        """Allow refresh token via JSON body OR HttpOnly cookie.
        If the client doesn't send a body, we fall back to the 'refresh_token' cookie.
        """
        refresh_token = request.COOKIES.get('refresh_token')
        serializer = self.get_serializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except JWTTokenError as e:
            # Match SimpleJWT behaviour
            raise InvalidToken(e.args[0])
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

    def finalize_response(self, request, response, *args, **kwargs):
        data = response.data
        access = data.get('access')
        if access:
            response.set_cookie(
                'access_token', access,
                httponly=True, secure=True, samesite='Lax', max_age=5*60
            )
            del data['access']
        return super().finalize_response(request, response, *args, **kwargs)


class CsrfTokenView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request, *args, **kwargs):
        # Force Django to generate/set the CSRF cookie via CsrfViewMiddleware
        token = get_token(request)
        return Response({'detail': 'CSRF cookie set', 'csrftoken': token}, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        if request.user and request.user.is_authenticated:
            return Response(UserSerializer(request.user).data, status=200)
        return Response(None, status=200)
