# Import Cache, celery
from django.core.cache import cache
from celery import shared_task
from sqlalchemy import desc
from zavmo.celery import app as celery_app
# Import models
from stage_app.models import LearnerJourney, ProfileStage, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage
# Import constants
from helpers.constants import USER_PROFILE_SUFFIX, HISTORY_SUFFIX, STAGE_ORDER
from helpers.chat import get_prompt, force_tool_call, get_openai_completion, create_message_payload, summarize_history, summarize_stage_data
from helpers.functions import create_model_fields, create_pydantic_model, get_yaml_data, create_system_message
from helpers.utils import timer, get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name='manage_stage_data')
def manage_stage_data(self, user_email, stage_name='profile', action=None):
    """Extract stage data from the user's history"""
    logger.info(f"Starting manage_stage_data task for user: {user_email}, stage: {stage_name}, action: {action}")
    
    profile_cache_key = f"{user_email}_{USER_PROFILE_SUFFIX}"
    profile_data      = cache.get(profile_cache_key)
    
    if not profile_data:
        logger.error(f"No profile data found for user: {user_email}")
        return {'status': 'error', 'message': 'No profile data found'}
    
    stage_data = profile_data['stage_data'][stage_name]
    logger.debug(f"Stage data: {stage_data}")

    history_key = f"{user_email}_{stage_name}_{HISTORY_SUFFIX}"
    history_data = cache.get(history_key)
    
    conversation_summary = summarize_history(history_data)    
    stage_config         = get_yaml_data(stage_name)
    
    required_fields  = [f['title'] for f in stage_config['fields']]
    profile_summary = summarize_stage_data(profile_data['stage_data'][stage_name], stage_name)
    
    system_message = create_system_message(stage_name, stage_config, mode='extract')
    
    user_message = f"""The learner is at the **{stage_name}** stage.
    This is the (unverified) information we have about the learner:
        {profile_summary}

    Here is the summary of the conversation:
        {conversation_summary}
                    
    Which of the following fields can we add or update about the learner?
        {', '.join(required_fields)}
    """
    message_payload = create_message_payload(user_message,  system_message, [], max_tokens=10000)
    models = [create_pydantic_model(name=f['title'], description=f['description'], fields=[f]) for f in stage_config['fields']]
        
    extraction_tools = force_tool_call(models,
                                       message_payload, 
                                       model='gpt-4o',
                                       tool_choice='required',
                                       parallel_tool_calls=True)
    

    for tool in extraction_tools:
        stage_data.update(tool.dict())
        
    # Update cache
    profile_data['stage_data'][stage_name] = stage_data
    cache.set(profile_cache_key, profile_data)
    
    if action == 'finish':
        finish_stage(user_email, stage_name, stage_data)
    else:
        return {'status': 'success', 'message': f"Extracted fields: {stage_data}"}
    
    
def finish_stage(user_email, stage_name, stage_data):
    profile_data = cache.get(f"{user_email}_{USER_PROFILE_SUFFIX}")
    stage_data   = profile_data['stage_data'][stage_name]
    
    stage_models = {
        'profile': ProfileStage,
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

