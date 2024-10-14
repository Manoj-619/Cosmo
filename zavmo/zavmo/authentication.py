# zavmo/authentication.py
import os
import jwt
# Cryptography
from cryptography.hazmat.primitives import serialization
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.conf import settings
from django.contrib.auth import get_user_model
from stage_app.models import LearnerJourney  # Import the LearnerJourney model

User = get_user_model()

class CustomJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]
        try:

            public_key = serialization.load_pem_public_key(settings.JWT_PUBLIC_KEY.encode('utf-8'))

            decoded_token = jwt.decode(
                token,
                public_key,
                algorithms=[settings.JWT_ALGORITHM],
                audience='account',
                issuer=settings.JWT_ISSUER,
                options={"verify_signature": False}  # Make it false for now
            )
            
            print(f"Successfully decoded token: {decoded_token}")

            email = decoded_token.get('email')

            # Check if email is present
            if not email:
                raise exceptions.AuthenticationFailed('Email is required in token')

            try:
                user = User.objects.get(email=email)
                learner_journey = LearnerJourney.objects.get(user=user)  # Fetch the learner journey associated with the user

            except User.DoesNotExist:
                raise exceptions.AuthenticationFailed('User not found')
            except LearnerJourney.DoesNotExist:
                raise exceptions.AuthenticationFailed('Learner journey not found for the user')

            # Attach the learner journey to the request
            request.learner_journey = learner_journey

            return (user, None)
        
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        
        except jwt.InvalidTokenError as e:
            print(f"Invalid token error: {str(e)}")
            raise exceptions.AuthenticationFailed(f'Invalid token: {str(e)}')
        
        except Exception as e:
            print(f"Unexpected error during token verification: {str(e)}")
            raise exceptions.AuthenticationFailed(f'Token verification failed: {str(e)}')
