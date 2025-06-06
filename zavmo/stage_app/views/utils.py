from helpers.utils import get_logger
from django.core.cache import cache
from stage_app.models import UserProfile, FourDSequence, DeliverStage, DiscoverStage, DiscussStage, DemonstrateStage, TNAassessment
from helpers.constants import HISTORY_SUFFIX, DEFAULT_CACHE_TIMEOUT, CONTEXT_SUFFIX, STAGE_ORDER
from copy import deepcopy

from typing import List, Dict
from pydantic_ai.messages import ModelMessagesTypeAdapter 

stage_models = [UserProfile, DiscoverStage, TNAassessment, DiscussStage, DeliverStage, DemonstrateStage]

logger = get_logger(__name__)

def _get_user_and_sequence(request):
    """Get user and sequence_id from request."""
    user        = request.user
    sequence_id = request.data.get('sequence_id')
    
    if not sequence_id:
        # Get all incomplete sequences for the user, ordered by creation date
        sequences   = FourDSequence.objects.filter(user=user, current_stage__in=[1, 2, 3, 4]).order_by('created_at')
        sequence_id = sequences.first().id if sequences else None
    return user, sequence_id


def _determine_stage(user, sequence_id):
    """Determine current stage and update context."""
    profile = UserProfile.objects.get(user__email=user.email)

    profile_is_complete, profile_error = profile.check_complete()
    
    if not profile_is_complete:
        return 'profile'
    
    if sequence_id:
        sequence = FourDSequence.objects.get(id=sequence_id)
        if sequence.stage_display == 'discover':
            # Check if all assessments are complete
            incomplete_assessments = [assessment for assessment in TNAassessment.objects.filter(user=profile.user, sequence=sequence) if not assessment.evidence_of_assessment]
            
            if incomplete_assessments:
                logger.info(f"Incomplete assessments found. Running tna_assessment agent.")
                return 'tna_assessment'
            else:
                return 'discuss'
    
    else:
        logger.info(f"No sequence ID found. Running profile agent.")
        return 'profile'
    
    return sequence.stage_display


def _get_message_history(email, sequence_id) -> List[Dict]:
    """Get or initialize message history."""
    message_history = cache.get(f"{email}_{sequence_id}_{HISTORY_SUFFIX}", [])
    return ModelMessagesTypeAdapter.validate_python(message_history)
   

def _get_deps(email, sequence_id) -> Dict:
    """Get or initialize dependencies."""
    deps = cache.get(f"{email}_{sequence_id}_{CONTEXT_SUFFIX}", {})
    return deps

def _update_message_history(email, sequence_id, all_messages: List[Dict], current_stage: str):
    """Update message history."""
    # Get valid stages from STAGE_ORDER keys, excluding 'profile' and 'tna_assessment'
    # as they're special stages not directly tied to the FourDSequence model
    valid_stages = [stage for stage in STAGE_ORDER.keys() 
                   if stage not in ['profile', 'tna_assessment']]
    
    ## Update the stage of the sequence
    if sequence_id and current_stage in valid_stages:
        sequence = FourDSequence.objects.get(
                user__email=email,
                id=sequence_id
            )
            
        sequence.update_stage(current_stage)
        sequence.save()
    
    ## Update the message history
    cache.set(f"{email}_{sequence_id}_{HISTORY_SUFFIX}", all_messages, timeout=DEFAULT_CACHE_TIMEOUT)

def _update_deps(email, sequence_id, deps: Dict):
    """Update dependencies."""
    cache.set(f"{email}_{sequence_id}_{CONTEXT_SUFFIX}", deps, timeout=DEFAULT_CACHE_TIMEOUT)