from click import style
from rest_framework import serializers
from django.contrib.auth.models import User
import re


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=60,
        style={'input_type': 'password'},)
    email = serializers.EmailField()

    class Meta:
        model = User
        fields = ('email', 'password')

    def validate_password(self, value):
        pattern = '^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).+$'
        if not re.fullmatch(pattern, value):
            raise serializers.ValidationError(
                "Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character."
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
            username=validated_data['email'],
            email=email,
            password=password
        )
        return user
