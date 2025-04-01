from helpers.utils import get_logger
from django.core.cache import cache
from stage_app.models import UserProfile, FourDSequence, DeliverStage, DiscoverStage, DiscussStage, DemonstrateStage, TNAassessment
from stage_app.serializers import (
    DiscoverStageSerializer, DiscussStageSerializer, DeliverStageSerializer, DemonstrateStageSerializer,
    UserProfileSerializer, TNAassessmentSerializer
)
# from helpers.agents import a_discover, b_discuss,c_deliver,d_demonstrate, profile
from agents import a_discover, b_discuss,c_deliver,d_demonstrate, profile
from helpers.agents.tna_assessment import get_tna_assessment_agent
from helpers.agents.common import get_tna_assessment_instructions, get_agent_instructions
from helpers.constants import CONTEXT_SUFFIX, HISTORY_SUFFIX, DEFAULT_CACHE_TIMEOUT
from helpers.swarm import run_step
from django.db import utils as django_db_utils
import logging
from copy import deepcopy
from pydantic_ai.models.message import ModelMessagesTypeAdapter


stage_order = ['profile', 'discover', 'tna_assessment', 'discuss', 'deliver', 'demonstrate']
stage_models = [UserProfile, DiscoverStage, TNAassessment, DiscussStage, DeliverStage, DemonstrateStage]

def get_agent(stage_name):
    if stage_name == 'profile':
        return deepcopy(profile.profile_agent)
    # elif stage_name == 'discover':
    #     return deepcopy(a_discover.discover_agent)
    # elif stage_name == 'tna_assessment':
    #     return deepcopy(get_tna_assessment_agent())
    # elif stage_name == 'discuss':
    #     return deepcopy(b_discuss.discuss_agent)
    # elif stage_name == 'deliver':
    #     return deepcopy(c_deliver.deliver_agent)
    # elif stage_name == 'demonstrate':
    #     return deepcopy(d_demonstrate.demonstrate_agent)


logger = get_logger(__name__)

def _get_user_and_sequence(request):
    """Get user and sequence_id from request."""
    user        = request.user
    sequence_id = request.data.get('sequence_id')
    
    if not sequence_id:
        # Get all incomplete sequences for the user, ordered by creation date
        sequences   = FourDSequence.objects.filter(user=user, current_stage__in=[1, 2, 3, 4]).order_by('created_at')
        sequence_id = sequences.first().id if sequences else None
    logger.info(f"Sequence ID: {sequence_id}")
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
            # discover_is_complete, discover_error = DiscoverStage.objects.get(user=profile.user, sequence=sequence).check_complete()
            # if not discover_is_complete:
            #     logger.info(f"Incomplete discover stage found. Running discover agent.")
            #     return 'discover'

            # Check if all assessments are complete
            incomplete_assessments = [assessment for assessment in TNAassessment.objects.filter(user=profile.user, sequence=sequence) if not assessment.evidence_of_assessment]
            
            if incomplete_assessments:
                logger.info(f"Incomplete assessments found. Running tna_assessment agent.")
                return 'tna_assessment'
            else:
                return 'discuss'
            
            # if discover_is_complete and not incomplete_assessments:
            #     logger.info(f"All assessments are complete. Running discuss agent.")
            #     return 'discuss'
    
    else:
        logger.info(f"No sequence ID found. Running profile agent.")
        return 'profile'
    
    return sequence.stage_display

def _get_message_history(email, sequence_id) -> List[Dict]:
    """Get or initialize message history."""
    message_history = cache.get(f"{email}_{sequence_id}_{HISTORY_SUFFIX}", [])
    if message_history:
        return ModelMessagesTypeAdapter.validate_python(message_history)
    return []

def _update_message_history(email, sequence_id, all_messages: List[Dict]):
    """Update message history."""

    if sequence_id:
        sequence = FourDSequence.objects.get(id=sequence_id)
        valid_stages = ['discover', 'discuss', 'deliver', 'demonstrate', 'completed']
        
        # Only update stage if it's different and valid
        if response.agent.id != sequence.stage_display and response.agent.id in valid_stages:
            # Check if stage already exists before updating
            try:
                sequence.update_stage(response.agent.id)
                context['stage'] = response.agent.id
            except django_db_utils.IntegrityError:
                logger.warning(f"Stage {response.agent.id} already exists for sequence {sequence_id}")
                pass
    # cache.set(f"{user.email}_{sequence_id}_{CONTEXT_SUFFIX}", context, timeout=DEFAULT_CACHE_TIMEOUT)
    cache.set(f"{email}_{sequence_id}_{HISTORY_SUFFIX}", all_messages, timeout=DEFAULT_CACHE_TIMEOUT)


def _process_agent_response(stage_name, message_history, user_input):
    """Process agent response with given context and messages."""
    agent = get_agent(stage_name)
    
    return agent.run_sync(user_input, message_history)

def _update_context_and_cache(user, sequence_id, context, message_history, response):
    """Update context and cache with response data."""
    # NOTE:  Add either last message or all recent messages
    # message_history.append(response.messages[-1])
    message_history.extend(response.messages)

    context.update(response.context)
    sequence_id = context['sequence_id']
    if sequence_id:
        sequence = FourDSequence.objects.get(id=sequence_id)
        valid_stages = ['discover', 'discuss', 'deliver', 'demonstrate', 'completed']
        
        # Only update stage if it's different and valid
        if response.agent.id != sequence.stage_display and response.agent.id in valid_stages:
            # Check if stage already exists before updating
            try:
                sequence.update_stage(response.agent.id)
                context['stage'] = response.agent.id
            except django_db_utils.IntegrityError:
                logger.warning(f"Stage {response.agent.id} already exists for sequence {sequence_id}")
                pass

    # cache.set(f"{user.email}_{sequence_id}_{CONTEXT_SUFFIX}", context, timeout=DEFAULT_CACHE_TIMEOUT)
    cache.set(f"{user.email}_{sequence_id}_{HISTORY_SUFFIX}", message_history, timeout=DEFAULT_CACHE_TIMEOUT)