"""
# IMPORTANT: Not using this right now.
# Opting for a custom authentication permission class instead of using a middleware
"""
import jwt
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model

User = get_user_model()  # Get the User model being used in the Django project

class CustomJWTMiddleware(MiddlewareMixin):
    def process_request(self, request):
        auth_header = request.headers.get('Authorization')

        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                # Verify the JWT using the public key and algorithm
                decoded_token = jwt.decode(
                    token,
                    settings.JWT_PUBLIC_KEY,
                    algorithms=[settings.JWT_ALGORITHM]
                )

                # Extract the email and org_id from the token
                email = decoded_token.get('email')
                org_id = decoded_token.get('org_id')

                # If email is missing, return an error
                if not email:
                    return JsonResponse({'error': 'Email not found in token'}, status=400)

                # Query the user using the email
                try:
                    user = User.objects.get(email=email)
                    request.user = user  # Attach the user to the request
                except User.DoesNotExist:
                    return JsonResponse({'error': 'User not found'}, status=404)

            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token has expired'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Invalid token'}, status=401)
        else:
            request.user = AnonymousUser()

    def process_response(self, request, response):
        return response