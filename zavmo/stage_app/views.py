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
from stage_app.models import Org, LearnerJourney, ProfileStage, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage
from stage_app.serializers import (
    UserDetailSerializer, LearnerJourneySerializer, ProfileStageSerializer, DiscoverStageSerializer, 
    DiscussStageSerializer, DeliverStageSerializer, DemonstrateStageSerializer
)
from helpers.chat import get_prompt, force_tool_call, get_openai_completion, create_message_payload
from helpers.functions import create_model_fields, create_pydantic_model, get_yaml_data, create_system_message
from helpers.constants import USER_PROFILE_SUFFIX, HISTORY_SUFFIX
from helpers.utils import delete_keys_with_prefix, timer
from django.conf import settings

logger = logging.getLogger(__name__)


# Utility function to get stage data
def add_stage_data(stage_name, user):
    """
    Helper function to add stage data for a specific stage and user.
    Returns an empty dict if no data is found or all values are null.
    """
    stages = {
        'profile': ProfileStageSerializer,
        'discover': DiscoverStageSerializer,
        'discuss': DiscussStageSerializer,
        'deliver': DeliverStageSerializer,
        'demonstrate': DemonstrateStageSerializer
    }

    if stage_name not in stages:
        return {}

    serializer_class = stages[stage_name]
    try:
        stage_instance = getattr(user, f'{stage_name}')
        stage_serializer = serializer_class(stage_instance)
        stage_data = stage_serializer.data
        if any(stage_data.values()):  # Check if any field has a non-null value
            return {stage_name: stage_data}
    except AttributeError:
        pass

    return {stage_name: {}}

def get_user_profile_data(user):
    """
    Retrieve user profile data from cache if available, otherwise from the database.
    """
    cache_key = f"{user.email}_{USER_PROFILE_SUFFIX}"
    
    # Try to get data from cache
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    # If not in cache, fetch from database
    learner_journey = LearnerJourney.objects.filter(user=user).first()
    if not learner_journey:
        return None

    learner_journey_data = LearnerJourneySerializer(learner_journey).data

    # Get stage data for all stages
    stage_data = {}
    for stage_name in ['profile', 'discover', 'discuss', 'deliver', 'demonstrate']:
        stage_info = add_stage_data(stage_name, user)
        if stage_info:
            stage_data.update(stage_info)
    
    # Combine profile data with stage data
    profile_data = {
        **learner_journey_data,
        'stage_data': stage_data
    }

    # Cache the data without a timeout
    cache.set(cache_key, profile_data)

    return profile_data


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
    serializer = UserDetailSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        email  = serializer.validated_data['email']
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
    profile_data = get_user_profile_data(user)
    
    if profile_data is None:
        return Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)

    return Response(profile_data)

# Endpoint: /api/chat/
@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def chat_view(request):
    """
    handles chat sessions between a user and the AI assistant.
    """
    user            = request.user    
    profile_data    = get_user_profile_data(user) # Get user profile data either from cache or database
    stage_data      = profile_data['stage_data']        
    stage_name      = profile_data['stage_name']
    message_key     = f"{user.email}_{stage_name}_{HISTORY_SUFFIX}"
    message_history = cache.get_or_set(message_key, [])
    user_input      = request.data.get('message', f'Send a personalized welcome message to the learner.')
    
    conf_data       = get_yaml_data(stage_name)
    required_fields = conf_data['required']
    
    # available_fields is the data that has already been collected for the learner for the current stage.
    available_fields = stage_data[stage_name].keys()
    missing_fields   = [field for field in required_fields if field not in available_fields]
    p_model          = conf_data['primary']
    probe_system_message   = create_system_message(stage_name, conf_data, mode='probe')
    
    user_content     = f"""The learner is at the {stage_name} stage.
    Learner's profile data: {stage_data[stage_name]}
    
    Learner's message: {user_input}
    """
    
    message_payload = create_message_payload(user_content, probe_system_message, message_history, max_tokens=10000)
    
    
    #probe_response   = get_openai_completion(probe_payload, model='gpt-4o-mini')
    # message_history.append({'role':'assistant', 'content':probe_response})
    #cache.set(cache_key, message_history)
        
    return Response({
            "type": "text",
            "message": '',
            "stage": stage_name,
            "credits":100,
            "stage_data": stage_data,
            "missing_fields": missing_fields,
            "available_fields": available_fields
        }, status=status.HTTP_201_CREATED)

