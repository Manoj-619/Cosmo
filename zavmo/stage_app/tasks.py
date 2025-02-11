from celery import shared_task
import requests
import json
import logging
from datetime import datetime,timezone
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define base URL from environment variable
BASE_API_URL = os.getenv('ZAVMO_XAPI_BASE_URL')

@shared_task(name="xAPI_chat_celery_task")
def xAPI_chat_celery_task(latest_user_message, latest_stage,email,latest_zavmo_message):

    url = f'{BASE_API_URL}/chat'
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        "chatData": {
            "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "zavmoChat": latest_zavmo_message,
            "userChat": latest_user_message,
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

@shared_task(name="xAPI_stage_celery_task")
def xAPI_stage_celery_task(stage_data,email,name):
    url = f'{BASE_API_URL}/stage'
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        "actor": {
            "name": name,
            "email": email
        },
        "stage":{
            "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "stage": stage_data
        }
    }
    response = requests.post(url, headers=headers, json=data)
    logger.info(response.text)
    return response.json()


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
def xAPI_discover_celery_task(discover_data,email,name):
    url = f'{BASE_API_URL}/learningGoals'
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
def xAPI_lesson_celery_task(lesson_data,email,name):
    url = f'{BASE_API_URL}/lessonStart'
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
