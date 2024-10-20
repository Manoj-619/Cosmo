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
from stage_app.models import Org, UserProfile, FourDSequence
from stage_app.serializers import (
    UserDetailSerializer, UserProfileSerializer, 
    FourDSequenceSerializer, DetailedFourDSequenceSerializer
)
from helpers.chat import force_tool_call, create_message_payload, summarize_history, summarize_stage_data, summarize_profile
from helpers.functions import create_model_fields, create_pydantic_model, get_yaml_data, create_system_message
from helpers.constants import USER_PROFILE_SUFFIX, HISTORY_SUFFIX
from stage_app.tasks.extraction import manage_stage_data


logger = logging.getLogger(__name__)


'''
# NOTE: with the new 4d sequence framework, we dont need this utility function.

# TODO: create a new utility function to get stage data from a specific sequence

# # Utility function to get stage data
# def add_stage_data(stage_name, user):
#     """
#     Helper function to add stage data for a specific stage and user.
#     Returns an empty dict if no data is found or all values are null.
#     """
#     stages = {
#         'profile': UserProfileSerializer,
#         'discover': DiscoverStageSerializer,
#         'discuss': DiscussStageSerializer,
#         'deliver': DeliverStageSerializer,
#         'demonstrate': DemonstrateStageSerializer
#     }

#     if stage_name not in stages:
#         return {}

#     serializer_class = stages[stage_name]
#     try:
#         stage_instance = getattr(user, f'{stage_name}')
#         stage_serializer = serializer_class(stage_instance)
#         stage_data = stage_serializer.data
#         if any(stage_data.values()):  # Check if any field has a non-null value
#             return {stage_name: stage_data}
#     except AttributeError:
#         pass

#     return {stage_name: {}}

'''

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
                UserProfile.objects.create(user=user)
                logger.info(f"UserProfile created for user {user.username}")
            else:
                message = "User already exists."
                status_code = status.HTTP_200_OK

            # Get or create the latest 4D sequence
            sequence = FourDSequence.objects.filter(user=user).order_by('-created_at').first()
            if not sequence:
                sequence = FourDSequence.objects.create(
                    user=user,
                    org=org,
                    title='Default Sequence'
                )
                logger.info(f"New FourDSequence created for user {user.username}")
            elif sequence.org != org:
                sequence.org = org
                sequence.save()
                logger.info(f"Updated org for existing FourDSequence of user {user.username}")

            return Response({
                "message": message,
                "email": user.email,
                "stage": sequence.current_stage,
                "org_id": org_id,
                "org_name": org.org_name,
                "sequence_id": sequence.id
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
    Retrieve user profile data and all 4D sequences.
    """
    user = request.user
    profile_stage = get_object_or_404(UserProfile, user=user)
    sequences = FourDSequence.objects.filter(user=user)
    
    profile_data   = UserProfileSerializer(profile_stage).data
    # NOTE: Perhaps we should just get some basic info about the last K sequences that have not been `completed`
    sequences_data = FourDSequenceSerializer(sequences, many=True).data
    
    return Response({
        'profile': profile_data,
        'sequences': sequences_data
    })

@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def create_sequence(request):
    """
    Create a new 4D sequence for the user.
    """
    user = request.user
    serializer = FourDSequenceSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def get_sequence_detail(request, sequence_id):
    """
    Retrieve details of a specific 4D sequence.
    """
    sequence = get_object_or_404(FourDSequence, id=sequence_id, user=request.user)
    serializer = DetailedFourDSequenceSerializer(sequence)
    return Response(serializer.data)

@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def chat_view(request):
    """Handles chat sessions between a user and the AI assistant."""
    user = request.user
    sequence_id = request.data.get('sequence_id')
    sequence = get_object_or_404(FourDSequence, id=sequence_id, user=user)
    
    profile_stage = get_object_or_404(UserProfile, user=user)
    current_stage = sequence.current_stage
    stage_data = getattr(sequence, f'{current_stage}_stage')
    
    message_key = f"{user.email}_{sequence_id}_{current_stage}_{HISTORY_SUFFIX}"
    message_history = cache.get_or_set(message_key, [])
    user_input = request.data.get('message', f'Send a personalized welcome message to the learner.')
    
    stage_config = get_yaml_data(current_stage)
    required_fields = [f['title'] for f in stage_config['fields']]
    
    profile_summary = summarize_profile(UserProfileSerializer(profile_stage).data)
    stage_summary = summarize_stage_data(stage_data.__dict__, current_stage)
    resp_schema = get_yaml_data('common')['response']
    resp_model = create_pydantic_model(name=resp_schema['title'],
                                       description=resp_schema['description'],
                                       fields=resp_schema['fields'])
    
    probe_system_message = create_system_message(current_stage, stage_config, mode='probe')
    
    user_content = f"""
    Here is what we know about the learner:
        {profile_summary}
           
    We need to probe the learner for the following fields: {required_fields}
    
    Learner's message: {user_input}
    """
    message_payload = create_message_payload(user_content, 
                                             probe_system_message, 
                                             message_history, 
                                             max_tokens=10000)
    
    response_tool = force_tool_call(resp_model, 
                                    message_payload, 
                                    model='gpt-4o',
                                    tool_choice='required')
    
    zavmo_response = response_tool.message
    zavmo_action = response_tool.action.value
    zavmo_credits = response_tool.credits
    
    message_history.append({'role':'user', 'content':user_input})
    message_history.append({'role':'assistant', 'content':zavmo_response})
    cache.set(message_key, message_history)
    
    # Trigger an extraction process
    manage_stage_data.apply_async(args=[sequence_id, zavmo_action])
    
    return Response({
        "type": "text",
        "message": zavmo_response,
        "stage": current_stage,
        "credits": zavmo_credits,
        "action": zavmo_action,
    }, status=status.HTTP_201_CREATED)



# NOTE: If we use the new 4d sequence framework, we DONT need this reset function
# @api_view(['POST'])
# @authentication_classes([CustomJWTAuthentication])
# @permission_classes([IsAuthenticated])
# def reset_all(request):
#     """Delet all cache, and reset learner journey"""
#     user = request.user
#     cache.delete_many([f"{user.email}_{USER_PROFILE_SUFFIX}",
#                       f"{user.email}_{HISTORY_SUFFIX}"])
#     # reset learner journey to 1st stage
#     learner_journey = LearnerJourney.objects.filter(user=user).first()
#     learner_journey.stage = 1
#     learner_journey.save()
    
#     stage_models = [UserProfile, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage]  
#     for stage_model in stage_models:
#         stage   = stage_model.objects.filter(user=user).first()
#         if stage:
#             stage.reset()
    
#     return Response({"message": "All cache and learner journey reset successfully"}, status=status.HTTP_200_OK)
    
    


