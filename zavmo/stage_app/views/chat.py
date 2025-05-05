

# --- Existing and Merged Imports ---
from zavmo.authentication import CustomJWTAuthentication # Assuming path from Code 1
from rest_framework.permissions import IsAuthenticated
from helpers.utils import get_logger # Assuming path from Code 1
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response as DRFResponse # Keep DRFResponse alias from Code 1
from rest_framework import status
# Utils specific to stage_app (adjust path if needed)
from stage_app.views.utils import _get_user_and_sequence, _determine_stage, _get_message_history, _update_message_history, _get_deps, _update_deps
from ..tasks import xAPI_chat_celery_task, xAPI_stage_celery_task # Relative import from Code 1
# Models and Serializers from Code 1
from stage_app.models import TNAassessment, DiscussStage, DeliverStage, DemonstrateStage, DiscoverStage, UserProfile
from stage_app.serializers import UserProfileSerializer, TNAassessmentSerializer, DiscussStageSerializer, DeliverStageSerializer, DemonstrateStageSerializer, DiscoverStageSerializer
from agents import get_agent # Assuming path from Code 1
from agents.common import Deps
from pydantic_ai.agent import Agent
import json

logger = get_logger(__name__)

# --- Added Verb Definitions and Lookup Functions (from Code 2) ---
STAGE_VERBS_MAP = {
    "profile": ["interacted", "updated", "viewed"],
    "discover": ["started", "answered", "viewed", "completed", "interacted", "experienced", "identified", "rated"],
    "tna_assessment": ["started", "completed", "failed", "interacted", "answered", "viewed", "experienced", "rated", "submitted"],
    "discuss": ["viewed", "discussed", "interacted", "completed", "answered", "experienced", "planned", "selected", "provided"],
    "deliver": ["responded", "learned", "interacted", "struggled", "completed", "viewed", "started", "experienced", "progressed", "asked", "received"],
    "demonstrate": ["viewed", "acknowledged", "completed", "submitted", "interacted", "experienced", "attempted", "passed", "failed", "demonstrated", "applied", "received", "mastered", "achieved", "assessed", "evaluated", "answered"],
}

XAPI_VERB_IDS = {
    # Map display names (lowercase) to their official xAPI Verb URIs
    # (Ensure these URIs are correct for your LRS/profile)
    "interacted": "http://adlnet.gov/expapi/verbs/interacted",
    "updated": "http://activitystrea.ms/update",
    "viewed": "http://id.tincanapi.com/verb/viewed",
    "started": "http://adlnet.gov/expapi/verbs/launched",
    "answered": "http://adlnet.gov/expapi/verbs/answered",
    "completed": "http://adlnet.gov/expapi/verbs/completed",
    "experienced": "http://adlnet.gov/expapi/verbs/experienced",
    "identified": "http://activitystrea.ms/schema/1.0/identify",
    "rated": "http://adlnet.gov/expapi/verbs/rated",
    "failed": "http://adlnet.gov/expapi/verbs/failed",
    "submitted": "http://activitystrea.ms/submit",
    "discussed": "http://purl.org/xapi/adl/verbs/discussed",
    "planned": "http://activitystrea.ms/plan",
    "selected": "http://activitystrea.ms/select",
    "provided": "http://activitystrea.ms/provide",
    "responded": "http://adlnet.gov/expapi/verbs/responded",
    "learned": "http://adlnet.gov/expapi/verbs/learned",
    "struggled": "urn:x-learninglocker:verb:struggled", # Example custom
    "progressed": "http://adlnet.gov/expapi/verbs/progressed",
    "asked": "http://adlnet.gov/expapi/verbs/asked",
    "received": "http://activitystrea.ms/receive",
    "acknowledged": "http://activitystrea.ms/acknowledge",
    "attempted": "http://adlnet.gov/expapi/verbs/attempted",
    "passed": "http://adlnet.gov/expapi/verbs/passed",
    "demonstrated": "urn:zavmo:verb:demonstrated", # Example custom
    "applied": "urn:zavmo:verb:applied", # Example custom
    "mastered": "http://adlnet.gov/expapi/verbs/mastered",
    "achieved": "http://adlnet.gov/expapi/verbs/achieved",
    "assessed": "http://adlnet.gov/expapi/verbs/assessed",
    "evaluated": "urn:zavmo:verb:evaluated", # Example custom
}

def get_verb_uri(verb_display):
    """Gets the URI for a given verb display name, defaulting to a custom URN if not found."""
    verb_key = str(verb_display).lower().strip() if verb_display else ""
    # Use XAPI_VERB_IDS map, default to custom URN structure if not found
    return XAPI_VERB_IDS.get(verb_key, f"urn:zavmo:verbs:{verb_key}")

def validate_stage_verb(stage, verb):
    """
    Validates if a stage exists and if a verb is valid for that stage.
    Returns True if valid, False otherwise, along with an error message if invalid.
    """
    if not stage or not verb: # Basic check for empty inputs
         return False, "Stage and verb cannot be empty."
    stage_lower = str(stage).lower()
    verb_lower = str(verb).lower()
    allowed_verbs = STAGE_VERBS_MAP.get(stage_lower)

    if allowed_verbs is None:
        error_msg = f"Stage '{stage}' does not exist. Valid stages are: {list(STAGE_VERBS_MAP.keys())}"
        logger.error(error_msg) # Log validation error
        return False, error_msg

    if verb_lower not in allowed_verbs:
        error_msg = f"Verb '{verb}' is not valid for stage '{stage}'. Valid verbs are: {allowed_verbs}"
        logger.error(error_msg) # Log validation error
        return False, error_msg

    return True, None # Valid
# --- End Verb Definitions ---


@api_view(['POST', 'OPTIONS'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def chat_view(request):
    """Handles chat sessions between a user and the AI assistant."""
    user, sequence_id = _get_user_and_sequence(request)
    message           = request.data.get('message','Initiate conversation with the user.')
    current_stage     = _determine_stage(user, sequence_id) # Renamed variable

    if current_stage == 'completed':
        # Keep existing logic for completed sequence
        return DRFResponse({
            "type": "text",
            "message": "You have finished all stages for the sequence.",
            "stage": current_stage
        })

    # Fetch user details (email and name) - Added from Code 2
    email = user.email
    name = user.email # Default to email
    try:
        # Use related name 'userprofile' if defined, otherwise direct filter/get
        # Assuming a OneToOneField from User to UserProfile with related_name='userprofile'
        # Adjust if your model relationship is different
        if hasattr(user, 'userprofile'):
             profile = user.userprofile
             name = f"{profile.first_name} {profile.last_name}".strip() or user.email
        else: # Fallback if no related_name or different structure
             profile = UserProfile.objects.get(user=user)
             name = f"{profile.first_name} {profile.last_name}".strip() or user.email
    except UserProfile.DoesNotExist:
        logger.warning(f"UserProfile not found for user {email}. Using email as name.")
    except Exception as e: # Catch other potential errors during profile fetch
        logger.error(f"Error fetching profile for user {email}: {e}. Using email as name.")

    # Use original method for getting message history
    message_history = _get_message_history(user.email, sequence_id)

    # Send stage start event if applicable (profile stage start) - Updated task args
    if current_stage == "profile" and not message_history: # Check if history is empty (as per code 2 logic check)
        logger.info(f"Sending xAPI stage start for profile stage for user {email}")
        # Pass name to the stage task as added in Code 2 logic
        xAPI_stage_celery_task.apply_async(args=[current_stage, email, name])

    # Get agent and deps - combine logic
    agent = get_agent(current_stage)
    if not agent: # Added check from Code 2
        logger.error(f"Could not find agent for stage: {current_stage}")
        return DRFResponse({"error": f"Configuration error: Agent for stage '{current_stage}' not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    deps = _get_deps(email, sequence_id) # Get existing deps first
    # Ensure deps object is correctly initialized/updated if needed (using logic from Code 1)
    # If _get_deps returns None or needs re-init:
    if not deps:
         deps = Deps(email=user.email, stage_name=current_stage)
         logger.info(f"Initialized new Deps for user {email}, sequence {sequence_id}")
    else:
         # Ensure stage name in deps is current, might be needed if deps structure is complex
         deps.stage_name = current_stage


    # Process the chat message with improved error handling
    response = None
    latest_user_message = None
    latest_zavmo_message = None
    try:
        # Use agent.run_sync from Code 1, assuming it returns a compatible response obj
        response = agent.run_sync(message, message_history=message_history, deps=deps)

        if not response or not hasattr(response, 'new_messages_json') or not callable(response.new_messages_json):
             logger.error("Agent response object is invalid or missing 'new_messages_json' method.")
             # Use Code 1's error response structure but indicate agent failure
             return DRFResponse({
                 "error": "Internal error processing chat response from agent",
                 "stage": current_stage,
                 "sequence_id": sequence_id,
                 "stage_data": {} # Avoid hitting DB on error if possible
             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Process response messages using Code 2's safer method
        new_messages_data = json.loads(response.new_messages_json())
        latest_user_message = next((parts['content'] for item in new_messages_data for parts in item.get('parts', []) if parts.get('part_kind') == 'user-prompt'), None)
        latest_zavmo_message = next((parts['content'] for item in new_messages_data for parts in item.get('parts', []) if parts.get('part_kind') == 'text'), None)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from agent response: {e}")
        return DRFResponse({"error": "Internal error processing agent response JSON."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        # Catch broader errors during agent execution/processing
        logger.error(f"Error during agent chat processing: {e}", exc_info=True) # Log traceback
        return DRFResponse({"error": "An error occurred during chat processing."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Update history and dependencies - Keep Code 1's logic here
    # Refresh sequence_id in case it was generated during agent run (as per Code 1 comment)
    user, sequence_id = _get_user_and_sequence(request)
    # Ensure stage name in deps is the final one before updating
    deps.stage_name = current_stage # Agent might have changed it, ensure we save current one
    _update_message_history(email, sequence_id, json.loads(response.all_messages_json()), current_stage)
    _update_deps(email, sequence_id, deps.model_dump()) # Use Pydantic's model_dump()

    # Send xAPI chat statement with validation - Added from Code 2
    if latest_user_message:
        # Default verb for chat interaction (can be made more dynamic later)
        chat_verb_display = "interacted" # Start with the default/intended verb
        chat_verb_uri = None # Initialize URI

        # Validate verb for the current stage
        is_valid, error_msg = validate_stage_verb(current_stage, chat_verb_display)

        if is_valid:
            chat_verb_uri = get_verb_uri(chat_verb_display)
        else:
            # Log validation error
            logger.error(f"xAPI Verb Validation Error: {error_msg}")
            # Fallback to a guaranteed valid verb (e.g., 'interacted')
            default_verb_display = "interacted"
            chat_verb_uri = get_verb_uri(default_verb_display)
            logger.warning(f"Using default verb '{default_verb_display}' (URI: {chat_verb_uri}) for xAPI statement due to validation failure for verb '{chat_verb_display}' in stage '{current_stage}'.")
            chat_verb_display = default_verb_display # Update display name to match the URI used

        # Prepare arguments for the task using Code 2's structure
        # This part now runs regardless of initial validation, using either the validated or default verb
        task_args = [
            latest_user_message,
            latest_zavmo_message if latest_zavmo_message else "N/A",
            email,
            name, # Pass the user's name
            sequence_id, # Pass the sequence ID
            current_stage, # Pass the current stage name
            chat_verb_uri, # Pass the looked-up or default verb URI
            chat_verb_display # Pass the validated or default verb display name
            # module_name is optional and defaults to None in the task
        ]
        logger.info(f"Sending xAPI chat interaction (verb: {chat_verb_display}) for user {email}, stage {current_stage}, sequence {sequence_id}")
        xAPI_chat_celery_task.apply_async(args=task_args)

    # Final logging
    logger.info(f"\n\nCurrent stage: {current_stage} - User: {user.email} - sequence_id: {sequence_id if sequence_id else 'Does not exist'}\n\n")

    # Return success response using Code 1's structure
    # Populate stage_data using serializers (handle potential DoesNotExist)
    stage_data = { "profile": {}, "discover": {}, "tna_assessment": [], "discuss": {}, "deliver": {}, "demonstrate": {} }
    try:
        stage_data["profile"] = UserProfileSerializer(UserProfile.objects.get(user=user)).data
        if sequence_id:
             try: stage_data["discover"] = DiscoverStageSerializer(DiscoverStage.objects.get(user=user, sequence=sequence_id)).data
             except DiscoverStage.DoesNotExist: pass
             try: stage_data["tna_assessment"] = [TNAassessmentSerializer(tna).data for tna in TNAassessment.objects.filter(user=user, sequence=sequence_id)]
             except TNAassessment.DoesNotExist: pass # Filter handles empty case
             try: stage_data["discuss"] = DiscussStageSerializer(DiscussStage.objects.get(user=user, sequence=sequence_id)).data
             except DiscussStage.DoesNotExist: pass
             try: stage_data["deliver"] = DeliverStageSerializer(DeliverStage.objects.get(user=user, sequence=sequence_id)).data
             except DeliverStage.DoesNotExist: pass
             try: stage_data["demonstrate"] = DemonstrateStageSerializer(DemonstrateStage.objects.get(user=user, sequence=sequence_id)).data
             except DemonstrateStage.DoesNotExist: pass
    except UserProfile.DoesNotExist:
         logger.error(f"UserProfile required for stage_data not found for user {email}.")
    except Exception as e:
         logger.error(f"Error retrieving stage_data for user {email}: {e}")


    return DRFResponse({
        "type": "text",
        "message": latest_zavmo_message if latest_zavmo_message else response.data if response else "", # Use extracted message, fallback to response.data
        "stage": current_stage,
        "sequence_id": sequence_id,
        "stage_data": stage_data
    })