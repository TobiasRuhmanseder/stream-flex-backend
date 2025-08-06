from rest_framework import serializers
from drf_recaptcha.fields import ReCaptchaV3Field
from django.contrib.auth import get_user_model
import re

User = get_user_model()


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=60,
        style={'input_type': 'password'},
        error_messages={
            'blank': 'Please enter a password.'
        }
    )
    email = serializers.EmailField(
        required=True,
        allow_blank=False,
        error_messages={
            'blank': 'Please provide an email address.',
            'required': 'Email is required.',
            'invalid': 'Please enter a valid email address.',
        }
    )
    recaptchaToken = ReCaptchaV3Field(action='signup', required_score=0.5)

    class Meta:
        model = User
        fields = ('email', 'password', 'recaptchaToken')

    def validate_password(self, value):
        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).+$'
        if not re.fullmatch(pattern, value):
            raise serializers.ValidationError(
                'Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character.'
            )
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already in use.")
        return value

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            is_active=False
        )
        return user


class CheckEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    recaptchaToken = ReCaptchaV3Field(action='check_email', required_score=0.5)
