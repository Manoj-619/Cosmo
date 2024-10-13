# Import Cache, celery
from django.core.cache import cache
from celery import shared_task
from sqlalchemy import desc
from zavmo.celery import app as celery_app
# Import models
from stage_app.models import LearnerJourney, ProfileStage, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage
# Import constants
from helpers.constants import USER_PROFILE_SUFFIX, HISTORY_SUFFIX, STAGE_ORDER
from helpers.chat import get_prompt, force_tool_call, get_openai_completion, create_message_payload
from helpers.functions import create_model_fields, create_pydantic_model, get_yaml_data, create_system_message
from helpers.utils import timer, get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name='manage_stage_data')
def manage_stage_data(self, user_email, stage_name='profile', action=None):
    """Extract stage data from the user's history"""
    logger.info(f"Starting manage_stage_data task for user: {user_email}, stage: {stage_name}, action: {action}")
    
    try:
        profile_cache_key = f"{user_email}_{USER_PROFILE_SUFFIX}"
        profile_data = cache.get(profile_cache_key)
        logger.debug(f"Retrieved profile data from cache: {profile_data}")
        
        if not profile_data:
            logger.error(f"No profile data found for user: {user_email}")
            return {'status': 'error', 'message': 'No profile data found'}
        
        stage_data = profile_data['stage_data'][stage_name]
        logger.debug(f"Stage data: {stage_data}")

        history_key = f"{user_email}_{stage_name}_{HISTORY_SUFFIX}"
        history_data = cache.get(history_key)
        logger.debug(f"Retrieved history data from cache: {history_data}")
        
        stage_config = get_yaml_data(stage_name)
        logger.debug(f"Stage config: {stage_config}")
        
        identify_config  = stage_config['identify']
        required_fields  = [f['title'] for f in stage_config['fields']]
        available_fields = list(stage_data.keys())
        missing_fields = [field for field in required_fields if field not in stage_data.keys()]
        logger.info(f"Missing fields: {missing_fields}")
        
        if action == 'probe':
            logger.info("Executing 'probe' action")
            system_message = create_system_message(stage_name, stage_config, mode='extract')
            
            user_message = f"""The learner is at the {stage_name} stage.
            The information we have about the learner is:
                {stage_data}
            Which of the following fields can we extract from the learner's last message? 
                {missing_fields}
            If any of the available fields need to be updated, please do so.
            The available fields are:
                {available_fields}
            """
            message_payload = create_message_payload(user_message, 
                                                     system_message,
                                                     history_data,
                                                     max_tokens=10000
                                                     )
            identification_model = create_pydantic_model(
                name=identify_config['title'],
                description=identify_config['description'],
                fields=identify_config['fields']
                )
            
            logger.debug("Calling force_tool_call for identification")
            identification_tool = force_tool_call(identification_model,
                                                  message_payload, 
                                                  model='gpt-4o-mini',
                                                  tool_choice='required',
                                                  parallel_tool_calls=False)
            
            attributes = identification_tool.attributes
            logger.info(f"Extracted attributes: {attributes}")
            if (not attributes) or (attributes == ['none']):
                logger.info("No attributes extracted or attributes are ['none']")
            else:
                logger.info(f"Calling extract_stage_data task for attributes: {attributes}")
                extract_stage_data.delay(user_email, stage_name, attributes)
            return {'status': 'success', 'message': f"Identified fields: {attributes}"}
        
        elif action == 'finish':
            logger.info("Executing 'finish' action")
            save_stage_data.delay(user_email, stage_name)
            
            # Extract the finish data
            pass
                    
        elif action == 'review':
            logger.info("Executing 'review' action")
            # Extract the review data
            pass
        
        else:
            logger.warning(f"Unknown action: {action}")
            return {'status': 'error', 'message': f"Unknown action: {action}"}
        
    except Exception as e:
        logger.exception(f"Error in manage_stage_data task: {str(e)}")
        return {'status': 'error', 'message': f"An error occurred: {str(e)}"}


@celery_app.task(bind=True, name='extract_stage_data')
def extract_stage_data(self, user_email, stage_name, attributes):
    stage_config      = get_yaml_data(stage_name)
    
    identified_fields = [f for f in stage_config['fields'] if f['title'] in attributes]
    primary_model     = create_pydantic_model(name=stage_config['extract']['title'],
                                              description=stage_config['extract']['description'],
                                              fields=identified_fields
                                              )
    
    history_key     = f"{user_email}_{stage_name}_{HISTORY_SUFFIX}"
    history_data    = cache.get(history_key)
    
    profile_data      = cache.get(f"{user_email}_{USER_PROFILE_SUFFIX}")
    stage_data        = profile_data['stage_data'][stage_name]
    system_message    = create_system_message(stage_name, stage_config, mode='extract')
    field_names       = [f['title'] for f in identified_fields]
    user_message      = f"""The learner is at the {stage_name} stage.
    The information we have about the learner is:
        {stage_data}
    
    Extract the following fields:
        {field_names}
    """
    message_payload = create_message_payload(user_message, 
                                             system_message, history_data, max_tokens=10000)
    
    primary_tool    = force_tool_call(primary_model, 
                                      message_payload, 
                                      model='gpt-4o-mini',
                                      tool_choice='required',
                                      parallel_tool_calls=False)
    
    # Update the stage data
    for field, value in primary_tool.dict().items():
        stage_data[field] = value
    # Stage config update
    profile_data['stage_data'][stage_name] = stage_data
    cache.set(f"{user_email}_{USER_PROFILE_SUFFIX}", profile_data)
        
    return {'status': 'success', 'message': f"Extracted data for {stage_name}"}
    
    
@celery_app.task(bind=True, name='save_stage_data')
def save_stage_data(self, user_email, stage_name):
    profile_data = cache.get(f"{user_email}_{USER_PROFILE_SUFFIX}")
    stage_data = profile_data['stage_data'][stage_name]
    
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
    stage_instance, created = StageModel.objects.get_or_create(user=user)
    
    # Update fields
    for field, value in stage_data.items():
        setattr(stage_instance, field, value)
    stage_instance.save()
    
    # Increment the stage
    learner_journey.stage = STAGE_ORDER[stage_name] + 1
    learner_journey.save()
    
    # Delete the cache data1
    cache.delete_many([f"{user_email}_{stage_name}_{USER_PROFILE_SUFFIX}",
                       f"{user_email}_{stage_name}_{HISTORY_SUFFIX}"])
    # Send response to the client
    return {'status': 'success', 'message': f"Saved stage data for {stage_name}"}
