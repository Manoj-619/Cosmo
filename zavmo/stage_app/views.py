import json
import random
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveAPIView
from django.shortcuts import get_object_or_404
from .models import Profile
from .serializers import OrgSerializer, UserSerializer, ProfileSerializer
from django.conf import settings
from django.core.cache import cache

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

class UserProfileView(RetrieveAPIView):
    """
    API to retrieve the user's complete profile data.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        """
        Fetch the profile for the authenticated user.
        Caching is used to optimize performance for frequently accessed profiles.
        """
        user = self.request.user
        cache_key = f'user_profile_{user.id}'

        # Attempt to get the profile from the cache
        profile = cache.get(cache_key)
        if not profile:
            # If not cached, fetch the profile and cache it
            profile = get_object_or_404(Profile, user=user)
            cache.set(cache_key, profile, 3600)  # Cache profile for 1 hour
        return profile