from celery import shared_task
import requests
import json
import logging
from .api_config import API_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
def build_and_execute_api(api_key, context):
    """Build and execute the API call for a given key."""
    api_details = API_CONFIG[api_key]
    payload = api_details["payload_builder"](context)
    url = api_details["url"]
    headers = {"Content-Type": "application/json"}
    
    # Execute the API call
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    # Handle response
    if response.status_code == 200:
        logger.info(f"{api_key} Success:", response.json())
    else:
        logger.error(f"{api_key} Failed with status code {response.status_code}: {response.text}")

# Keep track of which APIs have been called
called_apis = set()

@shared_task(name="xAPI_celery_task")
def xAPI_celery_task(context):
    """Main function to call APIs based on conditions."""
    
    # Define API groups based on conditions
    api_groups = {
        "discover": ["education_api", "learning_goals_api"],  
        "discuss": ["learning_style_api", "learning_schedule_api", "curriculum_registration_api"], 
    }
    
# Check and call APIs based on context
    for key, api_list in api_groups.items():
        if context.get(key):  # Check if the key (e.g., discover or discuss) is not empty
            logger.info(f"Context key '{key}' is not empty. Calling associated APIs...")
            for api_key in api_list:
                # Check if the API has already been called
                if api_key not in called_apis:
                    logger.info(f"Calling {api_key}...")
                    build_and_execute_api(api_key, context)
                    # Mark this API as called
                    called_apis.add(api_key)

    return "xAPI trigger Done"

