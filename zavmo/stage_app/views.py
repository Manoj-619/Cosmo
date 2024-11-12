""" 
Contains views for the stage app.
"""
import logging
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response as DRFResponse
from django.shortcuts import get_object_or_404
from zavmo.authentication import CustomJWTAuthentication
from django.db import IntegrityError
from django.core.cache import cache
from django.contrib.auth.models import User
from stage_app.models import Org, UserProfile, FourDSequence
from stage_app.serializers import (
    UserDetailSerializer, UserProfileSerializer, 
    DiscoverStageSerializer, DiscussStageSerializer, DeliverStageSerializer, DemonstrateStageSerializer,
    FourDSequenceSerializer
)
from helpers.constants import USER_PROFILE_SUFFIX, CONTEXT_SUFFIX, HISTORY_SUFFIX, DEFAULT_CACHE_TIMEOUT
from helpers.chat import validate_message_history
from helpers.swarm import run_step
from helpers.agents import a_discover,b_discuss,c_deliver,d_demonstrate, profile
from helpers.agents.common import get_agent_instructions

stage_order = ['profile', 'discover', 'discuss', 'deliver', 'demonstrate']

agents = { 'profile': profile.profile_agent,
           'discover': a_discover.discover_agent,
           'discuss': b_discuss.discuss_agent,
           'deliver': c_deliver.deliver_agent,
           'demonstrate': d_demonstrate.demonstrate_agent,
        }

logger = logging.getLogger(__name__)




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
        return DRFResponse({"error": "Organization name is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        org, created = Org.objects.get_or_create(org_name=org_name, org_id=org_id)
        message = "Organization created successfully." if created else "Organization already exists."
        return DRFResponse({
            "message": message,
            "org_id": org.org_id,
            "org_name": org.org_name
        }, status=status.HTTP_200_OK)
    except IntegrityError as e:
        logger.error(f"IntegrityError during organization creation: {str(e)}")
        return DRFResponse({"error": f"An error occurred while creating the organization: {str(e)}"},
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
        org    = Org.objects.filter(org_id=org_id).first()
        if not org:
            return DRFResponse({"error": "Organization with this ID does not exist."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'username': email, **serializer.validated_data}
            )
            
            if created:
                message = "User created successfully."
                status_code = status.HTTP_201_CREATED
                UserProfile.objects.create(user=user, org=org)
                logger.info(f"UserProfile created for user {user.username}")
            else:
                message = "User already exists."
                status_code = status.HTTP_200_OK
            # Check if there are any sequences for this user
            sequences = FourDSequence.objects.filter(user=user)
            if not sequences:
                # Create a new sequence
                sequence = FourDSequence(user=user)
                sequence.save()
            else:
                sequence = sequences.order_by('-created_at').first()    # Initialize related stages with user_id
                sequence.save()

            # Determine the stage_name
            profile = UserProfile.objects.filter(user=user).first()
            if not profile or not profile.is_complete():
                stage_name = 'profile'
            else:
                stage_name = sequence.stage_display

            return DRFResponse({
                "message": message,
                "email": user.email,
                "stage": stage_name,
                "sequence_id": sequence.id
            }, status=status_code)
        
        except IntegrityError as e:
            logger.error(f"IntegrityError during user sync: {str(e)}")
            return DRFResponse({"error": f"An error occurred while synchronizing the user data: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return DRFResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
    # Check if there are any sequences for this user
    sequences_data = FourDSequenceSerializer(sequences, many=True).data
    if profile_stage.is_complete():
        stage = sequences.order_by('-created_at').first().current_stage
    else:
        stage = 'profile'
    
    return DRFResponse({
        'profile': profile_data,
        'stage': stage,
        'sequences': sequences_data
    })


@api_view(['POST'])
def delete_all_caches(request):
    """Clear all caches for entire system."""
    cache.clear()
    return DRFResponse({"message": "All caches cleared successfully"}, status=status.HTTP_200_OK)
    
@api_view(['POST', 'OPTIONS'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def chat_view(request):
    """Handles chat sessions between a user and the AI assistant."""
    # Define the stage order at the start of the function
    user       = request.user
    sequence_id = request.data.get('sequence_id')
    if not sequence_id:
        # Get first sequence for this user
        sequence   = FourDSequence.objects.filter(user=user).order_by('-created_at').first()
        sequence_id = sequence.id

    # Initialize context and message_history
    context = {
        'email': user.email,  # Initialize with email
        'sequence_id': sequence_id  # Add sequence_id to context
    }
    
    # Generate cache key
    cache_key = f"{user.email}_{sequence_id}_{CONTEXT_SUFFIX}"

    if cache.get(cache_key):
        context    = cache.get(cache_key)
        stage_name = context['stage']  # Ensure current_stage is set from cached context
        
    profile = UserProfile.objects.get(user__email=user.email)
    
    if (not profile) or (not profile.is_complete()):  # Check if profile is empty
        stage_name = 'profile'
        context = {
            'email': user.email,
            'sequence_id': sequence_id,
            'profile': UserProfileSerializer(profile).data if profile else {},
            'discover': {},
            'discuss': {},
            'deliver': {},
            'demonstrate': {}
        }
    else:
        sequence   = FourDSequence.objects.filter(user=user).order_by('-created_at').first()
        stage_name = sequence.stage_display
        context= {
            'email': user.email,
            'sequence_id': sequence_id,
            'profile': UserProfileSerializer(profile).data if profile else {},
            'discover': DiscoverStageSerializer(sequence.discover_stage).data if sequence.discover_stage else {},
            'discuss': DiscussStageSerializer(sequence.discuss_stage).data if sequence.discuss_stage else {},
            'deliver': DeliverStageSerializer(sequence.deliver_stage).data if sequence.deliver_stage else {},
            'demonstrate': DemonstrateStageSerializer(sequence.demonstrate_stage).data if sequence.demonstrate_stage else {}
        }

    message_history = cache.get(f"{user.email}_{sequence_id}_{HISTORY_SUFFIX}", [])
    
    if stage_name == 'completed':
        return DRFResponse({"type": "text",
                         "message": "You have finished all stages for the sequence.",
                         "stage": stage_name,
                         })

    if request.data.get('message'):
        # Added user message to message history
        message_history.append({"role": "user", "content": request.data.get('message')})
    else:
        message_history.append({
            "role": "system",
            "content": f'Send a personalized welcome message to the learner.'
        })
    
    # Initialize the agent
    agent = agents[stage_name]
    # agent.start_message += "\n\nHere is the learning journey so far:\n\n" + summary_text
    
    # Run the agent with the user's input and current message history
    response = run_step(
            agent=agent,
            messages=message_history,
            context=context,
            max_turns=10
        )
    
    # Check if there are any messages in the response
    if not response.messages:
        return DRFResponse({
            "error": "No response generated from the agent",
            "stage": stage_name,
            "sequence_id": sequence_id
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    last_message = response.messages[-1]
    # Added agent response to message history
    message_history.append(last_message)
    context.update(response.context)
    stage_name = response.agent.id
    
    if response.agent != agent:
        logger.info(f"Stage changed from {agent.id} to {response.agent.id}.")
        sequence.update_stage(stage_name)
        
    context['stage'] = response.agent.id
    
    cache.set(f"{user.email}_{sequence_id}_{CONTEXT_SUFFIX}", context, timeout=DEFAULT_CACHE_TIMEOUT)
    cache.set(f"{user.email}_{sequence_id}_{HISTORY_SUFFIX}", message_history, timeout=DEFAULT_CACHE_TIMEOUT)
    
    return DRFResponse({
        "type": "text",
        "message": last_message['content'],
        "stage": stage_name,
        "sequence_id": sequence_id,
                     })
