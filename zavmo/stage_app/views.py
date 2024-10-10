""" 
Contains views for the stage app.
- create_org: Creates a new organization or returns an existing one.
- sync_user: Synchronizes user data: creates a new user if not exists, or returns existing user data.
- get_user_profile: Retrieves the user's complete profile data.
- chat_view: Handles chat sessions between a user and the AI assistant.

"""
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
import logging

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
    learner_journey = user.learner_journey
    learner_journey_data = LearnerJourneySerializer(learner_journey).data

    # Add stage data
    stage_data = {}

    # ProfileStage
    try:
        profile_stage = ProfileStageSerializer(user.profile_stage).data
        stage_data['profile_stage'] = profile_stage
    except ProfileStage.DoesNotExist:
        pass

    # DiscoverStage
    try:
        discover_stage = DiscoverStageSerializer(user.discover_stage).data
        stage_data['discover_stage'] = discover_stage
    except DiscoverStage.DoesNotExist:
        pass

    # DiscussStage
    try:
        discuss_stage = DiscussStageSerializer(user.discuss_stage).data
        stage_data['discuss_stage'] = discuss_stage
    except DiscussStage.DoesNotExist:
        pass

    # DeliverStage
    try:
        deliver_stage = DeliverStageSerializer(user.deliver_stage).data
        stage_data['deliver_stage'] = deliver_stage
    except DeliverStage.DoesNotExist:
        pass

    # DemonstrateStage
    try:
        demonstrate_stage = DemonstrateStageSerializer(user.demonstrate_stage).data
        stage_data['demonstrate_stage'] = demonstrate_stage
    except DemonstrateStage.DoesNotExist:
        pass

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
    
    Request Body:
    - message (optional): The message sent by the user. If the session is new, no message is required.

    Response Structure:
    - type (str): "text" (Just text for now, can add more types later for example for mcqs etc)
    - message (str, list): The AI's response.
    - stage (int): The current stage of the user's journey.

    Workflow:
    - If a new chat session is initiated, the AI responds with an initial message and the current stage is set.
    - If a session already exists, the current stage is returned, and the user's message is processed based on their profile.
    - JWT token is used to authenticate the user and retrieve their profile information.
    """
    user    = request.user
    learner_journey = get_object_or_404(LearnerJourney, user=user)
    # Get current stage
    stage = learner_journey.stage
    
    return Response({
            "type": "text",
            "message": "test",
            "stage": stage
        }, status=status.HTTP_201_CREATED)