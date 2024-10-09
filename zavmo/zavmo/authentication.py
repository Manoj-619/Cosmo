# zavmo/authentication.py
import os
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from stage_app.models import Profile  # Import the Profile model

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
                key=settings.JWT_PRIVATE_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            email = decoded_token.get('email')
            org_id = decoded_token.get('org_id')  # Fetch org_id from the token

            # Check if both email and org_id are present
            if not email or not org_id:
                raise exceptions.AuthenticationFailed('Email and org_id are required in token')

            try:
                user = User.objects.get(email=email)
                profile = Profile.objects.get(user=user)  # Fetch the profile associated with the user

            except User.DoesNotExist:
                raise exceptions.AuthenticationFailed('User not found')
            except Profile.DoesNotExist:
                raise exceptions.AuthenticationFailed('Profile not found for the user')

            # Attach the profile to the request
            request.profile = profile

            return (user, None)
        
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid token')