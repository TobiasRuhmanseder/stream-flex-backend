
from rest_framework import serializers
from drf_recaptcha.fields import ReCaptchaV3Field
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from users import validators
from .exeptions import AccountNotActivated
from django.db.models import Q
from rest_framework.exceptions import AuthenticationFailed
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import PasswordResetTokenGenerator


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username")
        read_only_fields = fields


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=60,
        error_messages={"blank": "Please enter a password."},
        validators=[validators.validate_strong_password],
    )
    email = serializers.EmailField(
        required=True,
        allow_blank=False,
        error_messages={
            "blank": "Please provide an email address.",
            "required": "Email is required.",
            "invalid": "Please enter a valid email address.",
        },
    )
    recaptchaToken = ReCaptchaV3Field(action="signup", required_score=0.5)

    class Meta:
        model = User
        fields = ("email", "password", "recaptchaToken")

    def create(self, validated_data):
        email = validated_data["email"]
        password = validated_data["password"]
        user = User.objects.create_user(username=email, email=email, password=password, is_active=False)
        return user


class CheckEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    recaptchaToken = ReCaptchaV3Field(action="check_email", required_score=0.5)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    remember = serializers.BooleanField(required=False, default=False)
    recaptchaToken = ReCaptchaV3Field(action="signin", required_score=0.5)

    def validate(self, attrs):
        identifier = attrs.get(User.USERNAME_FIELD)
        password = attrs.get("password")
        remember = attrs.pop("remember", False)

        user = (
            User.objects.filter(
                Q(**{f"{User.USERNAME_FIELD}__iexact": identifier}) | Q(email__iexact=identifier)
            ).first()
            if identifier
            else None
        )

        if not user or not user.check_password(password):
            raise AuthenticationFailed("Invalid credentials.", code="invalid_credentials")

        if not user.is_active:
            raise AccountNotActivated()

        refresh = self.get_token(user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserSerializer(user).data,
            "remember": remember,
        }
        self.user = user
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    recaptchaToken = ReCaptchaV3Field(action="resetpasswordrequest", required_score=0.5)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=60,
        error_messages={"blank": "Please enter a password."},
        validators=[validators.validate_strong_password],
    )
    recaptchaToken = ReCaptchaV3Field(action="resetpassword", required_score=0.5)

    def validate(self, attrs):
        uidb64 = attrs.get("uid")
        token = attrs.get("token")
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except Exception:
            raise serializers.ValidationError({"detail": "Invalid or expired reset link."})
        if not PasswordResetTokenGenerator().check_token(user, token):
            raise serializers.ValidationError({"detail": "Invalid or expired reset link."})

        attrs["user"] = user
        return attrs
