from helpers.utils import get_logger
from django.core.cache import cache
from stage_app.models import UserProfile, FourDSequence, DeliverStage, DiscoverStage, DiscussStage, DemonstrateStage
from stage_app.serializers import (
    DiscoverStageSerializer, DiscussStageSerializer, DeliverStageSerializer, DemonstrateStageSerializer,
    UserProfileSerializer
)
from helpers.chat import filter_history
from helpers.agents import a_discover, b_discuss,c_deliver,d_demonstrate, profile

from helpers.constants import CONTEXT_SUFFIX, HISTORY_SUFFIX, DEFAULT_CACHE_TIMEOUT
from helpers.swarm import run_step

stage_order = ['profile', 'discover', 'discuss', 'deliver', 'demonstrate']
stage_models = [UserProfile, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage]

agents = { 'profile': profile.profile_agent,
           'discover': a_discover.discover_agent,
           'discuss': b_discuss.discuss_agent,
           'deliver': c_deliver.deliver_agent,
           'demonstrate': d_demonstrate.demonstrate_agent,
        }


logger = get_logger(__name__)

def _get_user_and_sequence(request):
    """Get user and sequence_id from request."""
    user = request.user
    sequence_id = request.data.get('sequence_id')
    if not sequence_id:
        sequence = FourDSequence.objects.filter(user=user).order_by('-created_at').first()
        sequence_id = sequence.id
    return user, sequence_id

def _initialize_context(user, sequence_id):
    """Initialize or retrieve cached context."""
    context = {
        'email': user.email,
        'sequence_id': sequence_id
    }
    
    cache_key = f"{user.email}_{sequence_id}_{CONTEXT_SUFFIX}"
    if cache.get(cache_key):
        return cache.get(cache_key)
    return context

def _determine_stage(user, context):
    """Determine current stage and update context."""
    profile = UserProfile.objects.get(user__email=user.email)
    
    is_complete, error = profile.check_complete()
    if not is_complete:
        context.update(_create_empty_context(user.email, context['sequence_id'], profile))
        return 'profile'
    
    sequence = FourDSequence.objects.filter(user=user).order_by('-created_at').first()
    context.update(_create_full_context(user.email, context['sequence_id'], profile, sequence))
    return sequence.stage_display

def _create_empty_context(email, sequence_id, profile):
    """Create context for incomplete profile."""
    return {
        'email': email,
        'sequence_id': sequence_id,
        'profile': UserProfileSerializer(profile).data if profile else {},
        'discover': {},
        'discuss': {},
        'deliver': {},
        'demonstrate': {}
    }

def _create_full_context(email, sequence_id, profile, sequence):
    """Create context with all stage data."""
    return {
        'email': email,
        'sequence_id': sequence_id,
        'profile': UserProfileSerializer(profile).data if profile else {},
        'discover': DiscoverStageSerializer(sequence_id=sequence_id).data if sequence.discover_stage else {},
        'discuss': DiscussStageSerializer(sequence_id=sequence_id).data if sequence.discuss_stage else {},
        'deliver': DeliverStageSerializer(sequence_id=sequence_id).data if sequence.deliver_stage else {},
        'demonstrate': DemonstrateStageSerializer(sequence_id=sequence_id).data if sequence.demonstrate_stage else {}
    }

def _get_message_history(email, sequence_id, user_message):
    """Get or initialize message history."""
    message_history = cache.get(f"{email}_{sequence_id}_{HISTORY_SUFFIX}", [])
    
    if user_message:
        message_history.append({"role": "user", "content": user_message})
    else:
        message_history.append({
            "role": "system",
            "content": "Send a personalized welcome message to the learner."
        })
# NOTE: Filtering history only in swarm.py
#    message_history = filter_history(message_history, max_tokens)
    return message_history

def _process_agent_response(stage_name, message_history, context, max_turns=10):
    """Process agent response with given context and messages."""
    agent = agents[stage_name]
    email = context['email']
    sequence_id = context['sequence_id']
    
    stage_level = stage_order.index(stage_name) + 1
    for i in range(stage_level):
        if i == 0:
            stage_model = UserProfile.objects.get(user__email=email)
        else:
            stage_model = stage_models[i].objects.get(user__email=email, sequence_id=sequence_id)
        summary = stage_model.get_summary()
        agent.start_message += f"""
        **{stage_order[i].capitalize()}:**
        
        {summary}        
        """        
    return run_step(
        agent=agent,
        messages=message_history,
        context=context,
        max_turns=max_turns
    )

def _update_context_and_cache(user, sequence_id, context, message_history, response):
    """Update context and cache with response data."""
    # NOTE:  Add either last message or all recent messages
    # message_history.append(response.messages[-1])
    message_history.extend(response.messages)
    
    context.update(response.context)
    
    sequence = FourDSequence.objects.get(id=sequence_id)
    
    if response.agent.id != sequence.stage_display:
        logger.info(f"Stage changed from {context.get('stage')} to {response.agent.id}.")
        if response.agent.id != 'profile':
            sequence.update_stage(response.agent.id)
        
        context['stage'] = response.agent.id

    cache.set(f"{user.email}_{sequence_id}_{CONTEXT_SUFFIX}", context, timeout=DEFAULT_CACHE_TIMEOUT)
    cache.set(f"{user.email}_{sequence_id}_{HISTORY_SUFFIX}", message_history, timeout=DEFAULT_CACHE_TIMEOUT)
    