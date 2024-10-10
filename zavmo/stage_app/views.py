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

from helpers.chat import get_prompt, force_tool_call, get_openai_completion, create_message_payload
from helpers.functions import create_model_fields, create_pydantic_model, get_yaml_data, create_system_message

logger = logging.getLogger(__name__)

def get_stage_model(stage_name, user=None):
    """
    Get the stage model for a given stage name.
    If a user is provided, return the user's instance of that stage model and its serialized data.
    """
    stage_models = {
        'profile': (ProfileStage, ProfileStageSerializer),
        'discover': (DiscoverStage, DiscoverStageSerializer),
        'discuss': (DiscussStage, DiscussStageSerializer),
        'deliver': (DeliverStage, DeliverStageSerializer),
        'demonstrate': (DemonstrateStage, DemonstrateStageSerializer)
    }
    
    model, serializer_class = stage_models.get(stage_name, (None, None))
    
    if user and model:
        instance = model.objects.filter(user=user).first()
        if instance:
            serialized_data = serializer_class(instance).data
            return instance, serialized_data
    
    return None, {}

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
        stage_instance = getattr(user, f'{stage_name}_stage')
        stage_serializer = serializer_class(stage_instance)
        stage_data = stage_serializer.data
        if any(stage_data.values()):  # Check if any field has a non-null value
            return {stage_name: stage_data}
    except AttributeError:
        pass

    return {stage_name: {}}

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
    user            = request.user    
    learner_journey = request.learner_journey
    stage           = learner_journey.stage
    stage_name      = learner_journey.get_stage_display()
    cache_key       = f"{user.email}_history"
    user_input      = request.data.get('message', None)    
    clear_history   = request.data.get('clear', False)
    if clear_history:
        cache.delete(cache_key)
    
    message_history = cache.get(cache_key, [])
    
    # This can be used to get the correct directory for prompts, or for loading any other assets.    
    stage_model, stage_data = get_stage_model(stage_name, user)
    logger.info(f"Stage data: {stage_data}")
    
    conf_data       = get_yaml_data(stage_name)
    required_fields = conf_data['required']
    # available_fields is the data that has already been collected for the learner for the current stage.
    available_fields = stage_data.keys()
    missing_fields   = [field for field in required_fields if field not in available_fields]

    p_model = conf_data['primary']
    i_model = conf_data['identify']
    
    identifier_model = create_pydantic_model(
        name=i_model['title'],  description=i_model['description'], fields=i_model['fields'])

    extract_system_message = create_system_message(stage_name, conf_data, mode='extract')
    probe_system_message   = create_system_message(stage_name, conf_data, mode='probe')
    
    if user_input:
        user_message     = {"role": "user", "content": user_input}
        message_history.append(user_message)
        extract_payload  = create_message_payload(user_message, extract_system_message, message_history, max_tokens=10000)
        id_response = force_tool_call(tools=[identifier_model], messages=extract_payload,
                                      model='gpt-4o-mini', tool_choice='required', parallel_tool_calls=False)[0]
        new_attributes   = id_response.attributes
        #  If new attributes were detected, parse the message and extract the new data.
        if new_attributes:
            extract_fields = [f for f in p_model['fields'] if f['title'] in new_attributes]
            xp = max(10, len(extract_fields) * 100)
            primary_model = create_pydantic_model(
                name=p_model['title'],  
                description=p_model['description'], 
                fields=extract_fields
            )
            
            extract_response = force_tool_call(tools=[primary_model], messages=extract_payload, model='gpt-4o-mini', tool_choice='required', parallel_tool_calls=False)[0]
            new_stage_data   = extract_response.model_dump() # as json
            if new_stage_data:
                for field, value in new_stage_data.items():
                    # Update stage model with new data
                    setattr(stage_model, field, value)
                stage_model.save()
                
                # Update available_fields and missing_fields
                available_fields = list(stage_data.keys()) + list(new_stage_data.keys())
                missing_fields = [field for field in required_fields if field not in available_fields]
        else:
            xp = 10 # Give 10 xp anyway for trying.                                                    
        
    else:
        xp = 0
        user_message = None
        
    probe_payload    = create_message_payload(user_message, probe_system_message, message_history, max_tokens=10000)
    probe_response   = get_openai_completion(probe_payload, model='gpt-4o-mini')
    message_history.append({'role':'assistant', 'content':probe_response})
    cache.set(cache_key, message_history)
        
    return Response({
            "type": "text",
            "message": probe_response,
            "stage": stage,
            "credits":xp,
            "stage_data": stage_data,
            "missing_fields": missing_fields,
            "available_fields": available_fields
        }, status=status.HTTP_201_CREATED)
