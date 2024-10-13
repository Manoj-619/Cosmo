# Import Cache, celery
from django.core.cache import cache
from celery import shared_task
from zavmo.celery import app as celery_app
# Import models
from stage_app.models import LearnerJourney, ProfileStage, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage
# Import utils
from helpers.utils import delete_keys_with_prefix
# Import constants
from helpers.constants import USER_PROFILE_SUFFIX, HISTORY_SUFFIX
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
        required_fields  = stage_config['required']
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
            save_stage_data(user_email, stage_name)
            
            # Extract the finish data
            pass
        
        elif action == 'edit':
            logger.info("Executing 'edit' action")
            pass
            
        elif action == 'summarize':
            logger.info("Executing 'summarize' action")
            # Extract the summarize data
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
    primary_config    = stage_config['primary']
    identified_fields = [f for f in primary_config['fields'] if f['title'] in attributes]
    primary_model     = create_pydantic_model(name=primary_config['title'],
                                              description=primary_config['description'],
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
    
    
    
def save_stage_data(user_email, stage_name):
    profile_data = cache.get(f"{user_email}_{USER_PROFILE_SUFFIX}")
    stage_data   = profile_data['stage_data'][stage_name]
    
    # Get learner journey
    learner_journey = LearnerJourney.objects.get(user_id=user_email)
    
    if stage_name == 'profile':
        # Update the profile stage
        profile_stage = ProfileStage.objects.get_or_create(user_id=user_email)
        for field, value in stage_data.items():
            setattr(profile_stage, field, value)
        profile_stage.save()
        # also increment the stage
        
    elif stage_name == 'discover':
        # Update the discover stage
        discover_stage = DiscoverStage.objects.get_or_create(user_id=user_email)        
        
        for field, value in stage_data.items():
            setattr(discover_stage, field, value)
        discover_stage.save()
        
    elif stage_name == 'discuss':
        # Update the discuss stage
        discuss_stage = DiscussStage.objects.get_or_create(user_id=user_email)
        for field, value in stage_data.items():
            setattr(discuss_stage, field, value)
        discuss_stage.save()
        
    elif stage_name == 'deliver':
        # Update the deliver stage
        deliver_stage = DeliverStage.objects.get_or_create(user_id=user_email)
        for field, value in stage_data.items():
            setattr(deliver_stage, field, value)
        deliver_stage.save()

    elif stage_name == 'demonstrate':
        # Update the demonstrate stage
        demonstrate_stage = DemonstrateStage.objects.get_or_create(user_id=user_email)
        for field, value in stage_data.items():
            setattr(demonstrate_stage, field, value)
        demonstrate_stage.save()
        
    learner_journey.increment_stage()
    
    
    # Delete the cache data
    delete_keys_with_prefix(user_email)
    
    # Send response to the client
    return {'status': 'success', 'message': f"Saved stage data for {stage_name}"}
