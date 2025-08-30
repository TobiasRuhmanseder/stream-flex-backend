from rest_framework import generics
from .serializers import (
    CheckEmailSerializer,
    CustomTokenObtainPairSerializer,
    SignupSerializer,
    UserSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
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
from .functions import send_password_reset_email
from rest_framework.generics import GenericAPIView
from .jwt_cookie_auth import CustomAuthentication
from django.conf import settings


User = get_user_model()

COOKIE_SETTINGS = {
    "access_cookie_name": settings.SIMPLE_JWT.get("AUTH_COOKIE", "access_token"),
    "refresh_cookie_name": settings.SIMPLE_JWT.get("AUTH_REFRESH_COOKIE", "refresh_token"),
    "access_max_age": int(settings.SIMPLE_JWT.get("ACCESS_TOKEN_LIFETIME").total_seconds()) if settings.SIMPLE_JWT.get("ACCESS_TOKEN_LIFETIME") else 5 * 60,
    "refresh_max_age": int(settings.SIMPLE_JWT.get("REFRESH_TOKEN_LIFETIME").total_seconds()) if settings.SIMPLE_JWT.get("REFRESH_TOKEN_LIFETIME") else 24 * 3600,
    "httponly": True,
    "secure": settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", False),
    "samesite": settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
    "domain": settings.SIMPLE_JWT.get("AUTH_COOKIE_DOMAIN", None),
    "path": settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/"),
}


class SignupView(generics.CreateAPIView):
    """API endpoint for user signup (registration)."""
    queryset = User.objects.all()
    throttle_classes = [AnonRateThrottle]
    permission_classes = [AllowAny]
    serializer_class = SignupSerializer


class CheckEmailView(generics.GenericAPIView):
    """API endpoint to check if an email is already registered."""
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]
    serializer_class = CheckEmailSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exists = False
        email = serializer.validated_data["email"]
        if email:
            exists = User.objects.filter(email__iexact=email).exists()
        return Response({"exists": exists})


class VerifyEmailView(APIView):
    """API endpoint to verify a user's email address using a token."""
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request, *args, **kwargs):
        token = request.query_params.get("token")
        user = get_object_or_404(User, email_verification_token=token)
        user.is_active = True
        user.is_email_verified = True
        user.email_verification_token = ""
        user.save(update_fields=["is_active", "is_email_verified", "email_verification_token"])
        return Response({"detail": "Email verified successfully"}, status=status.HTTP_200_OK)


class ResendVerificationEmailView(APIView):
    """API endpoint to resend a verification email if the account is not yet verified."""
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request, *args, **kwargs):
        """Resend a new verification email if the account exists and is not verified.
        Always respond with 200 to avoid user enumeration.
        Expected JSON body: {"email": "user@example.com"}
        """
        email = (request.data.get("email") or "").strip()
        if not email:
            return Response({"email": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(email__iexact=email).first()
        neutral = Response(
            {"detail": "If the account exists and is not verified, a new verification email has been sent."},
            status=status.HTTP_200_OK,
        )
        if not user or getattr(user, "is_email_verified", False):
            return neutral
        try:
            if hasattr(user, "generate_email_verification_token"):
                user.generate_email_verification_token()
            functions.send_verification_email(user)
        except Exception:
            pass
        return neutral


class SignInView(TokenObtainPairView):
    """API endpoint for user login that issues JWT tokens in cookies."""
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]
    serializer_class = CustomTokenObtainPairSerializer

    def finalize_response(self, request, response, *args, **kwargs):
        refresh = response.data.get("refresh")
        access = response.data.get("access")
        remember = bool(response.data.pop("remember", False))
        common = {
            "httponly": COOKIE_SETTINGS["httponly"],
            "secure": COOKIE_SETTINGS["secure"],
            "samesite": COOKIE_SETTINGS["samesite"],
            "domain": COOKIE_SETTINGS["domain"],
            "path": COOKIE_SETTINGS["path"],
        }
        if refresh:
            if remember:
                response.set_cookie(key=COOKIE_SETTINGS["refresh_cookie_name"],value=refresh,max_age=COOKIE_SETTINGS["refresh_max_age"],**common,)
            else:
                response.set_cookie(key=COOKIE_SETTINGS["refresh_cookie_name"],value=refresh,**common,)  # session cookie
            del response.data["refresh"]

        if access:
            response.set_cookie(key=COOKIE_SETTINGS["access_cookie_name"],value=access,max_age=COOKIE_SETTINGS["access_max_age"],**common,)
            del response.data["access"]
        return super().finalize_response(request, response, *args, **kwargs)


class SignOutView(APIView):
    """API endpoint to log out a user and delete authentication cookies."""
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        refresh_cookie_name = COOKIE_SETTINGS["refresh_cookie_name"]
        access_cookie_name = COOKIE_SETTINGS["access_cookie_name"]
        ckw = {
            "path": COOKIE_SETTINGS["path"],
            "domain": COOKIE_SETTINGS["domain"],
            "samesite": COOKIE_SETTINGS["samesite"],
        }
        refresh_token = request.COOKIES.get(refresh_cookie_name)
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass
        resp = Response({"detail": "logged out"})
        resp.delete_cookie(access_cookie_name, path=ckw.get("path", "/"), domain=ckw.get("domain"), samesite=ckw.get("samesite"))
        resp.delete_cookie(refresh_cookie_name, path=ckw.get("path", "/"), domain=ckw.get("domain"), samesite=ckw.get("samesite"))
        return resp


class CookieTokenRefreshView(TokenRefreshView):
    """API endpoint to refresh access tokens using the refresh cookie."""
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request, *args, **kwargs):
        refresh_cookie_name = COOKIE_SETTINGS["refresh_cookie_name"]
        refresh_token = request.COOKIES.get(refresh_cookie_name)
        serializer = self.get_serializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except JWTTokenError as e:
            raise InvalidToken(e.args[0])
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

    def finalize_response(self, request, response, *args, **kwargs):
        data = response.data
        ckw = {
            "httponly": COOKIE_SETTINGS["httponly"],
            "secure": COOKIE_SETTINGS["secure"],
            "samesite": COOKIE_SETTINGS["samesite"],
            "domain": COOKIE_SETTINGS["domain"],
            "path": COOKIE_SETTINGS["path"],
        }
        access_cookie_name = COOKIE_SETTINGS["access_cookie_name"]
        access_max_age = COOKIE_SETTINGS["access_max_age"]
        access = data.get("access")
        if access:
            response.set_cookie(access_cookie_name, access, max_age=access_max_age, **ckw)
            del data["access"]
        return super().finalize_response(request, response, *args, **kwargs)


class CsrfTokenView(APIView):
    """API endpoint to get a CSRF token cookie for frontend use."""
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request, *args, **kwargs):
        token = get_token(request)
        return Response({"detail": "CSRF cookie set", "csrftoken": token}, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    """API endpoint to get details of the currently authenticated user."""
    authentication_classes = [CustomAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class PasswordResetRequestView(GenericAPIView):
    """API endpoint to request a password reset email."""
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        email = ser.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()
        detail = {"detail": "If the account exists, a reset email has been sent."}
        if user and getattr(user, "is_active", True):
            try:
                send_password_reset_email(user)
            except Exception:
                pass
        return Response(detail, status=status.HTTP_200_OK)


class PasswordResetConfirmView(GenericAPIView):
    """API endpoint to confirm password reset and set a new password."""
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user = ser.validated_data["user"]
        new_password = ser.validated_data["new_password"]
        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response({"detail": "Password has been changed."}, status=status.HTTP_200_OK)
