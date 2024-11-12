from zavmo.authentication import CustomJWTAuthentication
from rest_framework.permissions import IsAuthenticated
from helpers.utils import get_logger
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response as DRFResponse
from rest_framework import status
from stage_app.views.utils import _get_user_and_sequence, _initialize_context, _determine_stage, _get_message_history, _process_agent_response, _update_context_and_cache


logger = get_logger(__name__)


@api_view(['POST', 'OPTIONS'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def chat_view(request):
    """Handles chat sessions between a user and the AI assistant."""
    user, sequence_id = _get_user_and_sequence(request)
    context = _initialize_context(user, sequence_id)
    stage_name = _determine_stage(user, context)
    
    if stage_name == 'completed':
        return DRFResponse({
            "type": "text",
            "message": "You have finished all stages for the sequence.",
            "stage": stage_name,
            "stages": {
                "profile": context.get('profile', {}),
                "discover": context.get('discover', {}),
                "discuss": context.get('discuss', {}),
                "deliver": context.get('deliver', {}),
                "demonstrate": context.get('demonstrate', {})
            }
        })

    message_history = _get_message_history(user.email, sequence_id, request.data.get('message'))
    response = _process_agent_response(stage_name, message_history, context)
    
    if not response.messages:
        return DRFResponse({
            "error": "No response generated from the agent",
            "stage": stage_name,
            "sequence_id": sequence_id,
            "stages": {
                "profile": context.get('profile', {}),
                "discover": context.get('discover', {}),
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
        "stages": {
            "profile": context.get('profile', {}),
            "discover": context.get('discover', {}),
            "discuss": context.get('discuss', {}),
            "deliver": context.get('deliver', {}),
            "demonstrate": context.get('demonstrate', {})
        }
    })

