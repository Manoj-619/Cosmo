from zavmo.authentication import CustomJWTAuthentication
from rest_framework.permissions import IsAuthenticated
from helpers.utils import get_logger
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response as DRFResponse
from rest_framework import status
from stage_app.views.utils import _get_user_and_sequence, _initialize_context, _determine_stage, _get_message_history, _process_agent_response, _update_context_and_cache
from ..tasks import xAPI_chat_celery_task, xAPI_stage_celery_task


logger = get_logger(__name__)

has_called_profile_stage_xapi = False


@api_view(['POST', 'OPTIONS'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def chat_view(request):
    """Handles chat sessions between a user and the AI assistant."""
    user, sequence_id = _get_user_and_sequence(request)
    context    = _initialize_context(user, sequence_id)
    stage_name = _determine_stage(user, context, sequence_id)
    
    if stage_name == 'completed':
        return DRFResponse({
            "type": "text",
            "message": "You have finished all stages for the sequence.",
            "stage": stage_name,
            "stages": {
                "profile": context.get('profile', {}),
                "tna_assessment": context.get('tna_assessment', {}),
                "discover": context.get('discover', {}),
                "discuss": context.get('discuss', {}),
                "deliver": context.get('deliver', {}),
                "demonstrate": context.get('demonstrate', {})
            }
        })

    message_history = _get_message_history(user.email, sequence_id, request.data.get('message'))

    global has_called_profile_stage_xapi
    email = context['email']
    if stage_name == "profile" and not has_called_profile_stage_xapi:
        xAPI_stage_celery_task.apply_async(args=[stage_name, email, email])
        has_called_profile_stage_xapi = True

    # Get the latest user message from the message history
    if message_history and message_history[-1].get("role") == "user":
        latest_user_message = message_history[-1].get("content")
        if len(message_history) > 1 and message_history[-2].get("role")=="assistant":
            latest_stage=message_history[-2].get("sender")
            latest_zavmo_message=message_history[-2].get("content")
        else:
            latest_stage=None
            latest_zavmo_message=None
    else:
        latest_user_message = None  # No new user message yet

    if latest_user_message:
        xAPI_chat_celery_task.apply_async(args=[latest_user_message, latest_stage,context['email'],latest_zavmo_message])

    response = _process_agent_response(stage_name, message_history, context)

    if not response.messages:
        return DRFResponse({
            "error": "No response generated from the agent",
            "stage": response.agent.id,
            "sequence_id": sequence_id,
            "stage_data": {
                "profile": context.get('profile', {}),
                "discover": context.get('discover', {}),
                "tna_assessment": context.get('tna_assessment', {}),
                "discuss": context.get('discuss', {}),
                "deliver": context.get('deliver', {}),
                "demonstrate": context.get('demonstrate', {})
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    _update_context_and_cache(user, sequence_id, context, message_history, response)
    
    return DRFResponse({
        "type": "text",
        "message": response.messages[-1]['content'],
        "stage": response.agent.id,
        "sequence_id": sequence_id,
        "stage_data": {
            "profile": context.get('profile', {}),
            "discover": context.get('discover', {}),
            "tna_assessment": context.get('tna_assessment', {}),
            "assessments": context.get('assessments', {}),
            "discuss": context.get('discuss', {}),
            "deliver": context.get('deliver', {}),
            "demonstrate": context.get('demonstrate', {})
        }
    })

