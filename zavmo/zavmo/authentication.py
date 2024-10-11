# zavmo/authentication.py
import os
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
import jwt
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
            decoded_token = jwt.decode(
                token,
                key=settings.JWT_PRIVATE_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
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
        
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid token')
