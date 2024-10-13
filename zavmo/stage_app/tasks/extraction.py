# Import Cache, celery
from django.core.cache import cache
from celery import shared_task
from zavmo.celery import app as celery_app
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
    profile_cache_key = f"{user_email}_{USER_PROFILE_SUFFIX}"
    profile_data      = cache.get(profile_cache_key)
    stage_data        = profile_data['stage_data'][stage_name]
    

    history_key     = f"{user_email}_{stage_name}_{HISTORY_SUFFIX}"
    history_data      = cache.get(history_key)
    
    stage_config      = get_yaml_data(stage_name)
    identify_config   = stage_config['identify']
    
    required_fields  = stage_config['required']
    missing_fields   = [field for field in required_fields if field not in stage_data.keys()]
    
    # Get the user's history        
    if action == 'probe':
        # Extract the probe data
        system_content = get_prompt('profile/extract')
        system_message = {"role": "system", "content": system_content}
        user_message   = f"""The learner is at the {stage_name} stage.
        The information we have about the learner is:
            {stage_data}
        Which of the following fields can we extract from the learner's last message?
            {missing_fields}
        """
        message_payload      = create_message_payload(user_message, system_message, history_data, max_tokens=10000)
        identification_model = create_pydantic_model(
            name=identify_config['title'],
            description=identify_config['description'],
            fields=identify_config['fields']
            )
        
        identification_tool = force_tool_call(identification_model, 
                                              message_payload, 
                                              model='gpt-4o-mini',
                                              tool_choice='required',
                                              parallel_tool_calls=False)
        
        # Modified part
        attributes = identification_tool.attributes
        logger.info(f"Extracted attributes: {attributes}")
        if (not attributes) or (attributes == ['none']):
            pass
        else:
            extract_stage_data.delay(user_email, stage_name, attributes)
        return {'status': 'success', 'message': f"Identified fields: {attributes}"}
    
    if action == 'finish':
        # Extract the finish data
        pass
    
    if action == 'edit':
        pass
        
    if action == 'summarize':
        # Extract the summarize data
        pass    


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
    system_content = get_prompt(f"{stage_name}/extract")
    system_message = {"role": "system", "content": system_content}
    field_names = [f['title'] for f in identified_fields]
    user_message   = f"""The learner is at the {stage_name} stage.
    The information we have about the learner is:
        {stage_data}
    
    Extract the following fields:
        {field_names}
    """
    message_payload = create_message_payload(user_message, system_message, history_data, max_tokens=10000)
    primary_tool    = force_tool_call(primary_model, 
                                      message_payload, 
                                      model='gpt-4o-mini',
                                      tool_choice='required',
                                      parallel_tool_calls=False)
    
    # Extract the data
    extracted_data = force_tool_call(primary_tool, message_payload, model='gpt-4o-mini', tool_choice='required', parallel_tool_calls=False)    
    # Update the stage data
    for field, value in extracted_data.dict().items():
        stage_data[field] = value
    # Stage config update
    profile_data['stage_data'][stage_name] = stage_data
    cache.set(f"{user_email}_{USER_PROFILE_SUFFIX}", profile_data)
        
    return {'status': 'success', 'message': f"Extracted data for {stage_name}"}
    
    