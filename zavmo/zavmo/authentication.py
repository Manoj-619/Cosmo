# myapp/authentication.py
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]
        try:
            decoded_token = jwt.decode(
                token,
                settings.JWT_PUBLIC_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            email = decoded_token.get('email')
            if not email:
                raise exceptions.AuthenticationFailed('Email not found in token')
            try:
                user = User.objects.get(email=email)

            except User.DoesNotExist:
                raise exceptions.AuthenticationFailed('User not found')
            return (user, None)
        
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid token')