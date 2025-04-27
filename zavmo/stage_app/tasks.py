from celery import shared_task
import requests
import json
import logging
from datetime import datetime,timezone
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define base URL from environment variable
BASE_API_URL = os.getenv('LRS_ENDPOINT')

@shared_task(name="xAPI_chat_celery_task")
def xAPI_chat_celery_task(latest_user_message, latest_stage, email, latest_zavmo_message, module_name=None):
    """Sends an xAPI statement about a chat interaction."""
    url = f'{BASE_API_URL}/chat'  # Assuming this endpoint can handle xAPI statements now
    headers = {
        'Content-Type': 'application/json'
    }
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    # Construct xAPI statement
    xapi_statement = {
        "actor": {
            "mbox": f"mailto:{email}",
            "name": email, # Consider fetching a proper name if available
            "objectType": "Agent"
        },
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/interacted",
            "display": {"en-US": "interacted"}
        },
        "object": {
            "id": f"urn:zavmo:chat:{email}:{timestamp}", # Unique ID for the interaction
            "definition": {
                "name": {"en-US": f"Chat Interaction - Stage: {latest_stage}"},
                "description": {"en-US": "A chat interaction between the user and Zavmo."},
                "type": "http://adlnet.gov/expapi/activities/interaction",
                "extensions": {
                    "urn:zavmo:extension:timestamp": timestamp,
                    "urn:zavmo:extension:zavmoChat": latest_zavmo_message,
                    "urn:zavmo:extension:userChat": latest_user_message,
                    "urn:zavmo:extension:stage": latest_stage,
                    "urn:zavmo:extension:module_name": module_name if module_name is not None else "N/A"
                }
            },
            "objectType": "Activity"
        },
        "timestamp": timestamp
    }

    response = requests.post(url, headers=headers, json=xapi_statement)
    logger.info(f"xAPI Chat Task Response: {response.text}")
    try:
        return response.json()
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON response for xAPI Chat Task: {response.text}")
        return {"status": "error", "message": "Invalid JSON response from server", "response_text": response.text}


@shared_task(name="xAPI_stage_celery_task")
def xAPI_stage_celery_task(stage_data, email, name, module_name=None):
    """Sends an xAPI statement when a user reaches a new stage."""
    url = f'{BASE_API_URL}/stage' # Assuming this endpoint can handle xAPI statements now
    headers = {
        'Content-Type': 'application/json'
    }
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    # Construct xAPI statement
    xapi_statement = {
        "actor": {
            "mbox": f"mailto:{email}",
            "name": name,
            "objectType": "Agent"
        },
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/experienced",
            "display": {"en-US": "experienced"}
        },
        "object": {
            "id": f"urn:zavmo:stage:{stage_data}", # Unique ID for the stage experience
            "definition": {
                "name": {"en-US": f"Reached Stage: {stage_data}"},
                "description": {"en-US": f"User reached the {stage_data} stage."},
                "type": "http://adlnet.gov/expapi/activities/milestone",
                "extensions": {
                     "urn:zavmo:extension:timestamp": timestamp,
                     "urn:zavmo:extension:stage": stage_data,
                     "urn:zavmo:extension:module_name": module_name if module_name is not None else "N/A"
                }
            },
            "objectType": "Activity"
        },
        "timestamp": timestamp
    }
    response = requests.post(url, headers=headers, json=xapi_statement)
    logger.info(f"xAPI Stage Task Response: {response.text}")
    try:
        return response.json()
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON response for xAPI Stage Task: {response.text}")
        return {"status": "error", "message": "Invalid JSON response from server", "response_text": response.text}


@shared_task(name="xAPI_profile_celery_task")
def xAPI_profile_celery_task(profile_data,email):
    url = f'{BASE_API_URL}/profile'
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
def xAPI_discover_celery_task(discover_data,email,name, module_name=None):
    """Sends an xAPI statement about the user's defined learning goals."""
    url = f'{BASE_API_URL}/learningGoals' # Assuming this endpoint can handle xAPI statements now
    headers = {
        'Content-Type': 'application/json'
    }
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    # Construct xAPI statement
    xapi_statement = {
         "actor": {
            "mbox": f"mailto:{email}",
            "name": name,
            "objectType": "Agent"
        },
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/answered", # Using 'answered' as it relates to discovery questions
            "display": {"en-US": "answered"}
        },
        "object": {
            "id": f"urn:zavmo:learningGoals:{email}", # Unique ID for this learning goal definition event
            "definition": {
                "name": {"en-US": "Learning Goals Definition"},
                "description": {"en-US": "User provided information about their learning goals during the Discover stage."},
                "type": "http://adlnet.gov/expapi/activities/profile", # Profile activity type seems appropriate
                "extensions": {
                    "urn:zavmo:extension:timestamp": timestamp,
                    "urn:zavmo:extension:learningGoals": discover_data.get('learning_goals', 'N/A'),
                    "urn:zavmo:extension:learningGoalRationale": discover_data.get('learning_goal_rationale', 'N/A'),
                    "urn:zavmo:extension:knowledgeLevel": discover_data.get('knowledge_level', 'N/A'),
                    "urn:zavmo:extension:applicationArea": discover_data.get('application_area', 'N/A'),
                    "urn:zavmo:extension:module_name": module_name if module_name is not None else "N/A"
                }
            },
            "objectType": "Activity"
        },
        "timestamp": timestamp
    }
    response = requests.post(url, headers=headers, json=xapi_statement)
    logger.info(f"xAPI Discover Task Response: {response.text}")
    try:
        return response.json()
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON response for xAPI Discover Task: {response.text}")
        return {"status": "error", "message": "Invalid JSON response from server", "response_text": response.text}


@shared_task(name="xAPI_discuss_celery_task")
def xAPI_discuss_celery_task(discuss_data,learning_style,interest_areas,timeline,email,name):
    # API endpoints
    curriculum_url = f"{BASE_API_URL}/curriculumRegistration"
    discuss_url = f"{BASE_API_URL}/discuss"

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
            "timeline": timeline,
            "interest_areas": interest_areas
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
def xAPI_lesson_celery_task(lesson, email, name, module_name=None, nos_id=None, ofqual_id=None):
    url = f'{BASE_API_URL}/lessonStart'
    headers = {
        'Content-Type': 'application/json'
    }
    xapi_statement = {
        "actor": {
            "mbox": f"mailto:{email}",
            "name": name,
            "objectType": "Agent"
        },
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/completed",
            "display": {"en-US": "completed"}
        },
        "object": {
            "id": f"lesson:{lesson.get('title', '')}",
            "definition": {
                "name": {"en-US": lesson.get('title', '')},
                "description": {"en-US": lesson.get('lesson', '')},
                "type": "http://adlnet.gov/expapi/activities/lesson",
                "extensions": {
                    "module_name": module_name,
                    "nos_id": nos_id,
                    "ofqual_id": ofqual_id
                }
            },
            "objectType": "Activity"
        },
    }
    response = requests.post(url, headers=headers, json=xapi_statement)
    logger.info(response.text)
    return response.json()

@shared_task(name="xAPI_curriculum_completion_celery_task")
def xAPI_curriculum_completion_celery_task(curriculum_title,email,name):
    url = f'{BASE_API_URL}/curriculumCompletion'
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

@shared_task(name="xAPI_evaluation_celery_task")
def xAPI_evaluation_celery_task(evaluation_data,email,name):
    url = f'{BASE_API_URL}/assessment'
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        "actor": {
            "name": name,
            "email": email
        },
        "assessment": {
            "evaluations": [evaluation_data],
        }
    }
    response = requests.post(url, headers=headers, json=data)
    logger.info(response.text)
    return response.json()

@shared_task(name="xAPI_feedback_celery_task")
def xAPI_feedback_celery_task(feedback_data,understanding_level,email,name):
    url = f'{BASE_API_URL}/feedback'
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        "actor": {
            "name": name,
            "email": email
        },
        "feedback": {
            "text": feedback_data,
            "understanding_level": understanding_level
        }
    }
    response = requests.post(url, headers=headers, json=data)
    logger.info(response.text)
    return response.json()
    


@shared_task(name="xAPI_tna_assessment_celery_task")
def xAPI_tna_assessment_celery_task(updated_assessments,email,name):

    # API Endpoints 
    COMPLETED_API_URL = f"{BASE_API_URL}/tna"
    IN_PROGRESS_API_URL = f"{BASE_API_URL}/tna-start"


    completed_assessment = None
    in_progress_assessment = None

    # Find the last "Completed" assessment
    for assessment in reversed(updated_assessments):
        if assessment.get("status") == "Completed" and "evidence_of_assessment" in assessment:
            completed_assessment = assessment
            break  # Stop after finding the last completed assessment

    # Find the first "In progress" assessment
    for assessment in updated_assessments:
        if assessment.get("status") == "In Progress":
            in_progress_assessment = assessment
            break  # Stop after finding the first in-progress assessment

    # Headers for the API requests
    headers = {
        "Content-Type": "application/json"
    }

    results = {}

    # Send request for "Completed" assessment
    if completed_assessment:
        completed_payload = {
            "tna": {
                "assessment_area": completed_assessment.get("assessment_area", "N/A"),
                "status": completed_assessment.get("status", "N/A"),
                "evidence_type": completed_assessment.get("evidence_of_assessment", "N/A"),
                "user_assessed_knowledge_level": completed_assessment.get("user_assessed_knowledge_level", "N/A"),
                "zavmo_assessed_knowledge_level": completed_assessment.get("zavmo_assessed_knowledge_level", "N/A"),
                "nos_id": completed_assessment.get("nos_id", "N/A"),
                "knowledge_gaps": completed_assessment.get("gaps",["N/A"]),
            },
            "actor": {  
                "name": name,
                "email": email
            }
        }
        try:
            response = requests.post(COMPLETED_API_URL, json=completed_payload, headers=headers)

            response.raise_for_status()
            results["completed_status"] = response.json()
        except requests.RequestException as e:
            results["completed_error"] = f"Completed API failed: {str(e)}"

    # Send request for "In Progress" assessment
    if in_progress_assessment:
        in_progress_payload = {
            "tna": {
                "assessment_area": in_progress_assessment.get("assessment_area", "N/A"),
                "status": in_progress_assessment.get("status", "N/A"),
                "nos_id": in_progress_assessment.get("nos_id", "N/A"),
            },

            "actor": {
                "name": name,
                "email": email
            }
        }

        try:
            response = requests.post(IN_PROGRESS_API_URL, json=in_progress_payload, headers=headers)
            response.raise_for_status()
            results["in_progress_status"] = response.json()
        except requests.RequestException as e:
            results["in_progress_error"] = f"In Progress API failed: {str(e)}"

    return results
