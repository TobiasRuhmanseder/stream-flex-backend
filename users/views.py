from rest_framework import generics
from .serializers import SignupSerializer
from django.contrib.auth.models import User
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from django.contrib.auth import get_user_model

User = get_user_model()

class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = SignupSerializer


class CheckEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request, *args, **kwargs):
        email = request.query_params.get('email', '').strip()
        exists = False 
    
        if email:
            exists = User.objects.filter(email__iexact=email).exists()
            
        return Response({'exists': exists})
