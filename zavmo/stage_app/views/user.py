from rest_framework.response import Response as DRFResponse
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from django.contrib.auth.models import User
from stage_app.models import Org, UserProfile, FourDSequence, TNAassessment, DiscoverStage
from stage_app.serializers import UserDetailSerializer, UserProfileSerializer, FourDSequenceSerializer
from zavmo.authentication import CustomJWTAuthentication
from rest_framework.permissions import IsAuthenticated
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from helpers.utils import get_logger

logger = get_logger(__name__)

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
    # First check if org_id is provided
    org_id = request.data.get('org_id')
    if not org_id:
        return DRFResponse({"error": "Organization ID is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    org = Org.objects.filter(org_id=org_id).first()
    if not org:
        return DRFResponse({"error": "Organization with this ID does not exist."}, status=status.HTTP_400_BAD_REQUEST)

    serializer = UserDetailSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return DRFResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        email = serializer.validated_data['email']
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
        sequences_to_complete = FourDSequence.objects.filter(
            user=user, 
            current_stage__lt=FourDSequence.Stage.COMPLETED
        )
        if sequences_to_complete.exists():
            sequence = sequences_to_complete.order_by('created_at').first()
        else:
            sequence = None

        # Determine the stage_name
        profile = UserProfile.objects.filter(user=user).first()
        is_complete, error = profile.check_complete()
        if not is_complete:
            stage_name = 'profile'

        else:
            # discover_stage = DiscoverStage.objects.get(user=user, sequence=sequence)
            # discover_is_complete, error = discover_stage.check_complete()
            # if not discover_is_complete:
            #     stage_name = 'discover'
                    
            # else:
                tna_assessments = TNAassessment.objects.filter(user=user, sequence=sequence)
                for assessment in tna_assessments:
                    if not assessment.evidence_of_assessment:
                        stage_name = 'tna_assessment'
                        break
                    else:
                        stage_name = sequence.stage_display

        return DRFResponse({
            "message": message,
            "email": user.email,
            "stage": stage_name,
            "first_name": profile.first_name if is_complete else None,
            "last_name": profile.last_name if is_complete else None,
            "sequence_id": sequence.id if sequence else None
        }, status=status_code)
    
    except IntegrityError as e:
        logger.error(f"IntegrityError during user sync: {str(e)}")
        return DRFResponse({"error": f"An error occurred while synchronizing the user data: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    
    is_complete, error = profile_stage.check_complete()
    if is_complete:
        stage = sequences.order_by('-created_at').first().current_stage
    else:
        stage = 'profile'
    
    return DRFResponse({
        'profile': profile_data,
        'stage': stage,
        'sequences': sequences_data
    })


@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def clear_cache(request):
    """Clear all caches for entire system."""
    
    cache.delete_pattern(f"{request.user.email}_*")
    
    return DRFResponse({"message": "All caches cleared successfully"}, status=status.HTTP_200_OK)