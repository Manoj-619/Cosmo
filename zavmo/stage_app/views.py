""" 
Contains views for the stage app.
"""

import logging
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from zavmo.authentication import CustomJWTAuthentication
from django.db import IntegrityError
from django.core.cache import cache
from django.contrib.auth.models import User
from .models import Org, LearnerJourney, ProfileStage, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage
from .serializers import (
    UserSerializer, LearnerJourneySerializer, ProfileStageSerializer, DiscoverStageSerializer, 
    DiscussStageSerializer, DeliverStageSerializer, DemonstrateStageSerializer
)

from helpers.chat import get_prompt
from helpers.functions import create_model_fields, create_pydantic_model, get_fields


logger = logging.getLogger(__name__)

# Utility function to get stage data
def add_stage_data(stage_name, user):
    """
    Helper function to add non-empty stage data for a specific stage and user.
    """
    stages = {
        'profile': ProfileStageSerializer,
        'discover': DiscoverStageSerializer,
        'discuss': DiscussStageSerializer,
        'deliver': DeliverStageSerializer,
        'demonstrate': DemonstrateStageSerializer
    }

    if stage_name not in stages:
        return None

    serializer_class = stages[stage_name]
    try:
        stage_instance = getattr(user, f'{stage_name}_stage')
        stage_serializer = serializer_class(stage_instance)
        stage_data = stage_serializer.data
        if stage_data:  # Only return if there's non-null data
            return {f'{stage_name}_stage': stage_data}
    except AttributeError:
        pass

    return None

# Endpoint: /api/org/create/
@api_view(['POST'])
def create_org(request):
    """
    API to create a new organization or return an existing one.
    Accepts an organization name in the request and returns the org_id along with a message.
    """
    org_id   = request.data.get('org_id')
    org_name = request.data.get('org_name')
    if not org_name:
        return Response({"error": "Organization name is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        org, created = Org.objects.get_or_create(org_name=org_name, org_id=org_id)
        message = "Organization created successfully." if created else "Organization already exists."
        return Response({
            "message": message,
            "org_id": org.org_id,
            "org_name": org.org_name
        }, status=status.HTTP_200_OK)
    except IntegrityError:
        return Response({"error": "An error occurred while creating the organization."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Endpoint: /api/user/sync/
@api_view(['POST'])
def sync_user(request):
    """
    Synchronize user data: create a new user if not exists, or return existing user data.
    This endpoint allows clients to send user details via a POST request.
    If the user doesn't exist, it creates a new one. If the user exists, it returns the existing user data.
    
    Returns:
    Response: JSON object with user data, status message, or error messages.
    """
    serializer = UserSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        email = serializer.validated_data['email']
        org_id = request.data.get('org_id')

        # Validate org_id presence and existence
        if not org_id:
            return Response({"error": "Organization ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        org = Org.objects.filter(org_id=org_id).first()
        if not org:
            return Response({"error": "Organization with this ID does not exist."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'username': email, **serializer.validated_data}
            )
            
            if created:
                message = "User created successfully."
                status_code = status.HTTP_201_CREATED
                try:
                    learner_journey = LearnerJourney.objects.create(user=user, org=org)
                    stage = learner_journey.stage
                    logger.info(f"LearnerJourney created for user {user.username}")
                except Exception as e:
                    logger.error(f"Error creating learner journey for user {user.username}: {str(e)}")
                    user.delete()
                    return Response({"error": f"An error occurred while creating the learner journey: {str(e)}"},
                                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                message = "User already exists."
                status_code = status.HTTP_200_OK
                learner_journey = LearnerJourney.objects.filter(user=user).first()
                if learner_journey:
                    if learner_journey.org != org:
                        learner_journey.org = org
                        learner_journey.save()
                    stage = learner_journey.stage
                else:
                    try:
                        learner_journey = LearnerJourney.objects.create(user=user, org=org)
                        stage = learner_journey.stage
                        logger.info(f"LearnerJourney created for existing user {user.username}")
                    except Exception as e:
                        logger.error(f"Error creating learner journey for existing user {user.username}: {str(e)}")
                        return Response({"error": f"An error occurred while creating the learner journey: {str(e)}"},
                                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Fetch the organization details
            org = Org.objects.filter(org_id=org_id).first()
            org_name = org.org_name if org else None
            
            return Response({
                "message": message,
                "email": user.email,
                "stage": stage,
                "org_id": org_id,
                "org_name": org_name
            }, status=status_code)
        
        except IntegrityError as e:
            logger.error(f"IntegrityError during user sync: {str(e)}")
            return Response({"error": f"An error occurred while synchronizing the user data: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Endpoint: /api/user/profile
@api_view(['GET'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    """
    API to retrieve the user's complete profile data.
    """
    user = request.user
    learner_journey = request.learner_journey
    learner_journey_data = LearnerJourneySerializer(learner_journey).data

    # Get stage data for all stages
    stage_data = {}
    for stage_name in ['profile', 'discover', 'discuss', 'deliver', 'demonstrate']:
        stage_info = add_stage_data(stage_name, user)
        if stage_info:
            stage_data.update(stage_info)

    # Combine profile data with stage data
    response_data = {
        **learner_journey_data,
        'stage_data': stage_data
    }

    return Response(response_data)

# Endpoint: /api/chat/
@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def chat_view(request):
    """
    handles chat sessions between a user and the AI assistant.
    """
    user = request.user
    learner_journey = request.learner_journey
    # Get current stage
    stage = learner_journey.stage
    
    # This can be used to get the correct directory for prompts, or for loading any other assets.
    stage_name = learner_journey.get_stage_display().lower()
    
    xp = 10
    #  Get stage data for the current stage
    stage_data = add_stage_data(stage_name, user)
    
    fields          = get_fields(f"{stage_name}/extract")
    required_fields = fields.get('required_fields', [])
    missing_fields  = [f for f in required_fields if f['title'] not in stage_data]

#    probe_system = get_prompt()
    
    return Response({
            "type": "text",
            "message": "test",
            "stage": stage,
            "credits":xp,
            "stage_data": stage_data
        }, status=status.HTTP_201_CREATED)
