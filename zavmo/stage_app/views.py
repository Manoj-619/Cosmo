""" 
Contains views for the stage app.
"""
import json
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
from helpers.constants import USER_PROFILE_SUFFIX, CONTEXT_SUFFIX

from helpers.swarm import run_step
from helpers.agents import a_discover,b_discuss,c_deliver,d_demonstrate

agents = { 'discover': a_discover.discover_agent,
          'discussion': b_discuss.discuss_agent,
          'deliver': c_deliver.deliver_agent,
          'demonstrate': d_demonstrate.demonstrate_agent,
        }

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
    user        = request.user
    sequence_id = request.data.get('sequence_id', 1)

    # Get the sequence object for the given sequence_id
    cache_key = f"{user.email}_{sequence_id}_{CONTEXT_SUFFIX}"
    if cache.get(cache_key):
        context = cache.get(cache_key)
        message_history = context['history']
    else:
        # Check if user has a profile
        profile = UserProfile.objects.filter(user=user).first()
        if not profile:
            stage_name = 'profile'
        else:
            sequence    = get_object_or_404(FourDSequence, id=sequence_id, user=user)
            stage_name  = sequence.current_stage
        # Serialize the sequence to get the current stage details
        stage_data    = FourDSequenceSerializer(sequence).data
        current_stage = stage_data['stage_name']
        message_history = []
        context = {
            'sequence_id': sequence_id,
            'stage': stage_name,
            'email': user.email,
            'stage_data': {
                'profile': {},
                'discover': {},
                'discuss': {},
                'deliver': {},
                'demonstrate': {}
           },
            'history': message_history
        }
        cache.set(cache_key, context)
       
    if current_stage == 'completed':
        return Response({"type": "text",
                     "message": "You have finished all stages for the sequence.",
                     "stage": current_stage,
                     })

    if request.data.get('message'):
        message_history.append({"role": "user","content": request.data.get('message')})
    else:
        message_history.append({"role": "system","content": f'Send a personalized welcome message to the learner.'})


    # Initialize the agent
    agent = agents[current_stage]

    # Run the agent with the user's input and current message history
    response = run_step(
            agent=agent,
            messages=message_history,
            context=context,
            max_turns=5
        )
    new_messages = response.messages
    message_history.extend(new_messages)
    last_message = new_messages[-1]
    context.update(response.context)
    cache.set(cache_key, context)
    
    return Response({"type": "text",
                     "message": last_message['content'],
                     "stage": current_stage,
                     "sequence_id": sequence_id,
                     "log_history": message_history
                     })
    
    
    
    

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
    
    


