import json
import random
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from .models import Profile
from .serializers import OrgSerializer, UserSerializer, ProfileSerializer
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import User
from rest_framework.views import APIView
import jwt
from .models import ChatSession

@api_view(['POST'])
def create_org(request):
    """
    API to create a new organization.
    Accepts an organization name in the request and returns the org_id.
    """
    serializer = OrgSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def create_user(request):
    """
    Create a new user.
    This endpoint allows clients to create a user by sending a POST request
    with user details.
    Returns:
    Response: JSON object with user data or error messages.
    """
    if request.method == 'POST':
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(APIView):
    """
    API to retrieve the user's complete profile data.
    """

    @method_decorator(cache_page(3600))  # Cache this view for 1 hour
    def get(self, request):
        # Extract token from request headers
        token = request.headers.get('Authorization', None)
        
        if not token:
            raise AuthenticationFailed("Token not provided")

        try:
            # Decode the token to get the user ID
            payload = jwt.decode(token.split()[1], settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')  # Adjust according to your JWT payload structure
            user = get_object_or_404(User, id=user_id)
        except (jwt.ExpiredSignatureError, jwt.DecodeError):
            raise AuthenticationFailed("Invalid or expired token")

        # Attempt to get the profile from the cache
        cache_key = f'user_profile_{user.id}'
        profile = cache.get(cache_key)

        if not profile:
            # If not cached, fetch the profile and cache it
            profile = get_object_or_404(Profile, user=user)
            cache.set(cache_key, profile, 3600)  # Cache profile for 1 hour
        
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)
    
class ChatAPI(APIView):
    """
    ChatAPI handles chat sessions between a user and the AI assistant.

    Request Headers:
    - Authorization: Bearer <JWT_TOKEN> (required)
    
    Request Body:
    - message (optional): The message sent by the user. If the session is new, no message is required.

    Response Structure:
    - type (str): "text" (indicates the response is textual).
    - message (str): The AI's message or an empty string if no message is processed.
    - stage (int): The current stage of the user's journey. Possible stages:
        0 - Profile Collection
        1 - Discover
        3 - Discuss
        5 - Deliver
        7 - Demonstrate

    Workflow:
    - If a new chat session is initiated, the AI responds with an initial message and the current stage is set.
    - If a session already exists, the current stage is returned, and the user's message is processed based on their profile.
    - JWT token is used to authenticate the user and retrieve their profile information.
    """
    def post(self, request):
        token = request.headers.get('Authorization', None)

        if token:
            # Extract token without 'Bearer '
            try:
                token = token.split()[1]  # Strip 'Bearer' from token
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            except (jwt.ExpiredSignatureError, jwt.DecodeError, IndexError):
                return Response({"error": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED)

            # Get or create the chat session based on the token
            chat_session, created = ChatSession.objects.get_or_create(token=token)

            # Retrieve the user's profile based on the JWT token (assuming user ID is in the token)
            user_id = payload.get('user_id')  # Adjust according to your JWT payload structure
            profile = get_object_or_404(Profile, user__id=user_id)

            if created:
                # New session created, initialize the stage to the user's current stage
                chat_session.stage = self.get_stage_value(profile.stage)
                chat_session.save()

                # Send an initial message from the AI
                initial_ai_message = "Hello! I'm here to assist you."
                
                return Response({
                    "type": "text",  # Indicate that the response is a text message
                    "message": initial_ai_message,  # AI's initial message
                    "stage": chat_session.stage  # Return current stage
                }, status=status.HTTP_201_CREATED)

            # If a session already exists, just return the current stage without processing a message
            return Response({
                "type": "text",  # Indicate that the response is a text message
                "message": "",  # Empty message
                "stage": chat_session.stage  # Return current stage
            }, status=status.HTTP_200_OK)
        
        else:
            return Response({"error": "Token not provided"}, status=status.HTTP_401_UNAUTHORIZED)

    def get_stage_value(self, stage):
        """Convert stage string to corresponding numeric value."""
        stage_mapping = {
            'profile': 0,
            'discover': 1,
            'discuss': 3,
            'deliver': 5,
            'demonstrate': 7
        }
        return stage_mapping.get(stage, 0)  # Default to 0 if stage is not recognized
