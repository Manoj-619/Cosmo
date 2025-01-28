from celery import shared_task
import requests
import json
import logging
from datetime import datetime,timezone
from .api_config import API_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# def build_and_execute_api(api_key, context):
#     """Build and execute the API call for a given key."""
#     api_details = API_CONFIG[api_key]
#     payload = api_details["payload_builder"](context)
#     url = api_details["url"]
#     headers = {"Content-Type": "application/json"}
    
#     # Execute the API call
#     response = requests.post(url, headers=headers, data=json.dumps(payload))
    
#     # Handle response
#     if response.status_code == 200:
#         logger.info(f"{api_key} Success:", response.json())
#     else:
#         logger.error(f"{api_key} Failed with status code {response.status_code}: {response.text}")

# # Keep track of which APIs have been called
# called_apis = set()

# @shared_task(name="xAPI_celery_task")
# def xAPI_celery_task(context):
#     """Main function to call APIs based on conditions."""
    
#     # Define API groups based on conditions
#     api_groups = {
#         "discover": ["education_api", "learning_goals_api"],  
#         "discuss": ["learning_style_api", "learning_schedule_api", "curriculum_registration_api"], 
#     }
    
# # Check and call APIs based on context
#     for key, api_list in api_groups.items():
#         if context.get(key):  # Check if the key (e.g., discover or discuss) is not empty
#             logger.info(f"Context key '{key}' is not empty. Calling associated APIs...")
#             for api_key in api_list:
#                 # Check if the API has already been called
#                 if api_key not in called_apis:
#                     try:
#                         logger.info(f"Calling {api_key}...")
#                         build_and_execute_api(api_key, context)
#                         logger.info(f"Finished calling {api_key}.")
#                         # Mark this API as called
#                         called_apis.add(api_key)
#                     except Exception as e:
#                         logger.error(f"Error calling {api_key}: {e}")

#     return "xAPI trigger Done"

@shared_task(name="xAPI_chat_celery_task")
def xAPI_chat_celery_task(latest_user_message, latest_stage,email):

    url = 'https://learninglocker.zavmo.ai/v1/statements/chat'
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        "chatData": {
            "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "chat": latest_user_message,
            "stage": latest_stage
        },
        "actor": {
            "name": email,
            "email": email,
        }
    }

    response = requests.post(url, headers=headers, json=data)
    logger.info(response.text)
    return response.json()

@shared_task(name="xAPI_profile_celery_task")
def xAPI_profile_celery_task(profile_data,email):
    url = 'https://learninglocker.zavmo.ai/v1/statements/profile'
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        "profile": {
            "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "first_name": profile_data.get('first_name','N/A'),
            "last_name": profile_data.get('last_name','N/A'),
            "current_role": profile_data.get('current_role','N/A'),
            "current_industry": profile_data.get('current_industry','N/A'),
            "experience": profile_data.get('years_of_experience','N/A'),
            "manager": profile_data.get('manager','N/A'),
            "department": profile_data.get('department','N/A'),
            "job_duration": profile_data.get('job_duration','N/A')
        },
        "actor": {
            "name": profile_data.get('first_name') + " " + profile_data.get('last_name'),
            "mbox": email
        }
    }
    response = requests.post(url, headers=headers, json=data)
    logger.info(response.text)
    return response.json()


@shared_task(name="xAPI_discover_celery_task")
def xAPI_discover_celery_task(discover_data,email,name):
    url = 'https://learninglocker.zavmo.ai/v1/statements/learningGoals'
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        "chat": {
            "learningGoals": discover_data.get('learning_goals','N/A'),
            "learningGoalRationale": discover_data.get('learning_goal_rationale','N/A'),
            "knowledgeLevel": discover_data.get('knowledge_level','N/A'),
            "applicationArea": discover_data.get('application_area','N/A')
        },
        "actor": {
            "name": name,
            "mbox": email
        }
    }
    response = requests.post(url, headers=headers, json=data)
    logger.info(response.text)
    return response.json()

@shared_task(name="xAPI_discuss_celery_task")
def xAPI_discuss_celery_task(discuss_data,learning_style,timeline,email,name):
    # API endpoints
    curriculum_url = "https://learninglocker.zavmo.ai/v1/statements/curriculumRegistration"
    discuss_url = "https://learninglocker.zavmo.ai/v1/statements/discuss"

    # Headers for both requests
    headers = {
        "Content-Type": "application/json"
    }

    # First API payload (Curriculum Registration)
    curriculum_payload = {
        "chat": {
            "title": discuss_data.get("title","N/A"),
            "subject": discuss_data.get("subject", "N/A"),
            "level": discuss_data.get("level", "N/A"),
            "prerequisites": discuss_data.get("prerequisites", ["N/A"]),
            "modules": discuss_data.get("modules", ["N/A"])
        },
        "actor": {
            "name": name,
            "email": email
        }
    }

    try:
        curriculum_response = requests.post(curriculum_url, json=curriculum_payload, headers=headers)
        curriculum_response.raise_for_status()
    except requests.RequestException as e:
        return {"status": "error", "message": f"Curriculum API failed: {str(e)}"}
    
    # Second API payload (Discuss API)
    discuss_payload = {
        "discuss":  {
            "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "learningStyle": learning_style,
            "timeline": timeline
        },
        "actor": {
            "name": name,
            "mbox": email
        }
    }

    try:
        discuss_response = requests.post(discuss_url, json=discuss_payload, headers=headers)
        discuss_response.raise_for_status()
    except requests.RequestException as e:
        return {"status": "error", "message": f"Discuss API failed: {str(e)}"}

    return {
        "status": "success",
        "curriculum_response": curriculum_response.json(),
        "discuss_response": discuss_response.json()
    }

@shared_task(name="xAPI_lesson_celery_task")
def xAPI_lesson_celery_task(lesson_data,email,name):
    url = 'https://learninglocker.zavmo.ai/v1/statements/lessonStart'
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        "actor": {  
            "name": name,
            "email": email
        },
        "lesson": {
            "title": lesson_data.get("title","N/A"),
            "description": lesson_data.get("lesson","N/A"),
            "module": lesson_data.get("module","N/A"),
            "learningObjective": lesson_data.get("learning_objective","N/A")
        }

    }
    response = requests.post(url, headers=headers, json=data)
    logger.info(response.text)
    return response.json()

@shared_task(name="xAPI_curriculum_completion_celery_task")
def xAPI_curriculum_completion_celery_task(curriculum_title,email,name):
    url = 'https://learninglocker.zavmo.ai/v1/statements/curriculumCompletion'
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        "actor": {
            "name": name,
            "email": email
        },
        "curriculum":{
            "title": curriculum_title
        },
        "completionData":{
            "success": True,
            "completionDate": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        }

    }
    response = requests.post(url, headers=headers, json=data)
    logger.info(response.text)
    return response.json()

@shared_task(name="xAPI_assessment_celery_task")
def xAPI_assessment_celery_task(assessment_data,email,name):
    url = 'https://learninglocker.zavmo.ai/v1/statements/assessment'
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        "learner": {
            "name": name,
            "email": email
        },
        "assessment": {
            "evaluations": assessment_data
        }
    }
    response = requests.post(url, headers=headers, json=data)
    logger.info(response.text)
    return response.json()

@shared_task(name="xAPI_feedback_celery_task")
def xAPI_feedback_celery_task(feedback_data,email,name):
    url = 'https://learninglocker.zavmo.ai/v1/statements/feedback'
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        "actor": {
            "name": name,
            "email": email
        },
        "feedback": {
            "text": feedback_data
        }
    }
    response = requests.post(url, headers=headers, json=data)
    logger.info(response.text)
    return response.json()
    