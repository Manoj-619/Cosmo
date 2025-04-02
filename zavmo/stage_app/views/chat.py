from zavmo.authentication import CustomJWTAuthentication
from rest_framework.permissions import IsAuthenticated
from helpers.utils import get_logger
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response as DRFResponse
from rest_framework import status
from stage_app.views.utils import _get_user_and_sequence, _determine_stage, _get_message_history, _update_message_history
from ..tasks import xAPI_chat_celery_task, xAPI_stage_celery_task
from stage_app.models import TNAassessment, DiscussStage, DeliverStage, DemonstrateStage, DiscoverStage
from stage_app.serializers import UserProfileSerializer, TNAassessmentSerializer, DiscussStageSerializer, DeliverStageSerializer, DemonstrateStageSerializer, DiscoverStageSerializer
from agents import profile, a_discover, tna_assessment, b_discuss, c_deliver, d_demonstrate
from agents.common import Deps
from pydantic_ai.agent import Agent
import json
logger = get_logger(__name__)

def get_agent(stage_name):
    if stage_name == 'profile':
        return profile.profile_agent
    elif stage_name == 'discover':
        return a_discover.discover_agent
    elif stage_name == 'tna_assessment':
        return tna_assessment.tna_assessment_agent
    elif stage_name == 'discuss':
        return b_discuss.discuss_agent
    elif stage_name == 'deliver':
        return c_deliver.deliver_agent
    elif stage_name == 'demonstrate':
        return d_demonstrate.demonstrate_agent

@api_view(['POST', 'OPTIONS'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def chat_view(request):
    """Handles chat sessions between a user and the AI assistant."""
    user, sequence_id = _get_user_and_sequence(request)
    stage_name        = _determine_stage(user, sequence_id)
    
    if stage_name == 'completed':
        return DRFResponse({
            "type": "text",
            "message": "You have finished all stages for the sequence.",
            "stage": stage_name
        })

    message_history = _get_message_history(user.email, sequence_id)
    email = user.email

    if stage_name == "profile" and message_history==[]:
        xAPI_stage_celery_task.apply_async(args=[stage_name, email, email])

    # Get the latest user message from the message history
    # if message_history and message_history[-1].get("role") == "user":
    #     latest_user_message = message_history[-1].get("content")
    #     if len(message_history) > 1 and message_history[-2].get("role")=="assistant":
    #         latest_stage=message_history[-2].get("sender")
    #         latest_zavmo_message=message_history[-2].get("content")
    #     else:
    #         latest_stage=None
    #         latest_zavmo_message=None
    # else:
    #     latest_user_message = None  # No new user message yet

    # if latest_user_message:
    #     xAPI_chat_celery_task.apply_async(args=[latest_user_message, latest_stage,email,latest_zavmo_message])
    
    agent = get_agent(stage_name)
    response=agent.run_sync(
        request.data.get('message'),
        message_history=message_history,
        deps=Deps(email=user.email)
    )
    
    if isinstance(response, Agent):  # Check if response is an Agent (transfer case)
        current_stage = response.name
        response      = ''
    else:
        current_stage = stage_name
        response      = response.data
        _update_message_history(email, sequence_id, json.loads(response.all_messages_json()))
    
    if not response:
        return DRFResponse({
            "error": "No response generated from the agent",
            "stage": current_stage,
            "sequence_id": sequence_id,
            "stage_data": {
                "profile": UserProfileSerializer(user.profile).data,
                "discover": DiscoverStageSerializer(DiscoverStage.objects.get(user=user, sequence=sequence_id)).data,
                "tna_assessment": [TNAassessmentSerializer(tna_assessment).data for tna_assessment in TNAassessment.objects.filter(user=user, sequence=sequence_id)],
                "discuss": DiscussStageSerializer(DiscussStage.objects.get(user=user, sequence=sequence_id)).data,
                "deliver": DeliverStageSerializer(DeliverStage.objects.get(user=user, sequence=sequence_id)).data,
                "demonstrate": DemonstrateStageSerializer(DemonstrateStage.objects.get(user=user, sequence=sequence_id)).data
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    return DRFResponse({
        "type": "text",
        "message": response,
        "stage": current_stage,
        "sequence_id": sequence_id,
        "stage_data": {
            "profile": UserProfileSerializer(user.profile).data,
            "discover": DiscoverStageSerializer(DiscoverStage.objects.get(user=user, sequence=sequence_id)).data,
            "tna_assessment": [TNAassessmentSerializer(tna_assessment).data for tna_assessment in TNAassessment.objects.filter(user=user, sequence=sequence_id)],
            "discuss": DiscussStageSerializer(DiscussStage.objects.get(user=user, sequence=sequence_id)).data,
            "deliver": DeliverStageSerializer(DeliverStage.objects.get(user=user, sequence=sequence_id)).data,
            "demonstrate": DemonstrateStageSerializer(DemonstrateStage.objects.get(user=user, sequence=sequence_id)).data
        }
    })