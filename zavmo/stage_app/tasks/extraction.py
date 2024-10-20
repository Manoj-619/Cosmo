# Import Cache, celery
from django.core.cache import cache
from celery import shared_task
from sqlalchemy import desc
from zavmo.celery import app as celery_app
# Import models
from stage_app.models import LearnerJourney, UserProfile, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage, FourDSequence
from stage_app.serializers import UserProfileSerializer
# Import constants
from helpers.constants import USER_PROFILE_SUFFIX, HISTORY_SUFFIX, STAGE_ORDER
from helpers.chat import get_prompt, force_tool_call, get_openai_completion, create_message_payload, summarize_history, summarize_stage_data
from helpers.functions import create_model_fields, create_pydantic_model, get_yaml_data, create_system_message
from helpers.utils import timer, get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name='manage_stage_data')
def manage_stage_data(self, sequence_id, action=None):
    """Extract stage data from the user's history"""
    logger.info(f"Starting manage_stage_data task for sequence: {sequence_id}, action: {action}")
    
    sequence = FourDSequence.objects.get(id=sequence_id)
    user = sequence.user
    current_stage = sequence.current_stage
    stage_instance = getattr(sequence, f'{current_stage}_stage')
    
    profile_stage = UserProfile.objects.get(user=user)
    profile_data = UserProfileSerializer(profile_stage).data
    
    message_key = f"{user.email}_{sequence_id}_{current_stage}_{HISTORY_SUFFIX}"
    history_data = cache.get(message_key, [])
    
    conversation_summary = summarize_history(history_data)    
    stage_config = get_yaml_data(current_stage)
    
    required_fields = [f['title'] for f in stage_config['fields']]
    profile_summary = summarize_stage_data(profile_data, 'profile')
    stage_summary = summarize_stage_data(stage_instance.__dict__, current_stage)
    
    system_message = create_system_message(current_stage, stage_config, mode='extract')
    
    user_message = f"""
    Here is what we know about the learner:
        {profile_summary}
    
    Current stage ({current_stage}) information:
        {stage_summary}
           
    Here is the summary of the conversation:
        {conversation_summary}
                    
    Which of the following fields can we add or update about the learner?
        {', '.join(required_fields)}
    """
    message_payload = create_message_payload(user_message, system_message, [], max_tokens=10000)
    models = [create_pydantic_model(name=f['title'], description=f['description'], fields=[f]) for f in stage_config['fields']]
    
    extraction_tools = force_tool_call(models,
                                       message_payload, 
                                       model='gpt-4o',
                                       tool_choice='required',
                                       parallel_tool_calls=True)
    
    for tool in extraction_tools:
        for field, value in tool.dict().items():
            setattr(stage_instance, field, value)
    
    stage_instance.save()
    
    if action == 'finish':
        # Move to the next stage
        stages = ['discover', 'discuss', 'deliver', 'demonstrate']
        current_index = stages.index(current_stage)
        next_index = (current_index + 1) % len(stages)
        sequence.current_stage = stages[next_index]
        sequence.save()
        
        # Clear the cache for the completed stage
        cache.delete(message_key)
    
    return {'status': 'success', 'message': f"Extracted fields for {current_stage} stage"}
    
    
def finish_stage(user_email, stage_name, stage_data):
    profile_data = cache.get(f"{user_email}_{USER_PROFILE_SUFFIX}")
    stage_data   = profile_data['stage_data'][stage_name]
    
    stage_models = {
        'profile': UserProfile,
        'discover': DiscoverStage,
        'discuss': DiscussStage,
        'deliver': DeliverStage,
        'demonstrate': DemonstrateStage
    }
    
    # Get learner journey and user
    learner_journey = LearnerJourney.objects.get(user__email=user_email)
    user = learner_journey.user
    
    # Get the appropriate stage model
    StageModel = stage_models.get(stage_name)
    if not StageModel:
        return {'status': 'error', 'message': f"Invalid stage name: {stage_name}"}
    
    # Update or create the stage instance
    stage_instance = StageModel.objects.get(user=user)
    
    # Update fields
    for field, value in stage_data.items():
        setattr(stage_instance, field, value)
    stage_instance.save()
    
    # Increment the stage
    new_stage_index = min(STAGE_ORDER[stage_name] + 1, 5)
    learner_journey.stage = new_stage_index
    learner_journey.save()
    # get new stage name    
    new_stage_name = list(STAGE_ORDER.keys())[new_stage_index-1]
    
    # Also update cache for stage
    profile_data['stage_name'] = new_stage_name
    profile_data['stage'] = new_stage_index
    cache.set(f"{user_email}_{USER_PROFILE_SUFFIX}", profile_data)    
    # Delete the cache data
    # cache.delete_many([f"{user_email}_{stage_name}_{USER_PROFILE_SUFFIX}",f"{user_email}_{stage_name}_{HISTORY_SUFFIX}"])

