API_CONFIG = {
    "education_api": {
        "url": "https://learninglocker.zavmo.ai/v1/statements/education",
        "payload_builder": lambda context: {
            "chat": {
                "level": context['profile'].get('edu_level', "Unknown Level"),
                "field": context['profile'].get('current_industry', "Unknown Industry"),
            },
            "actor": {
                "name": f"{context['profile']['first_name']} {context['profile']['last_name']}",
                "mbox": context['email']
            }
        }
    },
    "learning_goals_api": {
        "url": "https://learninglocker.zavmo.ai/v1/statements/learningGoals",
        "payload_builder": lambda context: {
            "chat": {
                "learningGoals": context['discover'].get('learning_goals'),
                "learningGoalRationale": context['discover'].get('learning_goal_rationale'),
                "knowledgeLevel": context['discover'].get('knowledge_level'),
                "applicationArea": context['discover'].get('application_area')
            },
            "actor": {
                "name": f"{context['profile']['first_name']} {context['profile']['last_name']}",
                "mbox": context['email']
            }
        }
    },
    "learning_style_api": {
        "url": "https://learninglocker.zavmo.ai/v1/statements/learningStyle",
        "payload_builder": lambda context: {
            "chat": {
                "learningStyle": context['discuss'].get('learning_style')
            },
            "actor": {
                "name": f"{context['profile']['first_name']} {context['profile']['last_name']}",
                "mbox": context['email']
            }
        }
    },
    "learning_schedule_api": {
        "url": "https://learninglocker.zavmo.ai/v1/statements/learningSchedule",
        "payload_builder": lambda context: {
            "chat": {
                "preferredTimeline": context['discuss'].get('timeline')
            },
            "actor": {
                "name": f"{context['profile']['first_name']} {context['profile']['last_name']}",
                "mbox": context['email']
            }
        }
    },
    "curriculum_registration_api": {
    "url": "https://learninglocker.zavmo.ai/v1/statements/curriculumRegistration",
    "payload_builder": lambda context: {
        "chat": {
            "title": context['discuss']['curriculum'].get('title'),
            "subject": context['discuss']['curriculum'].get('subject'),
            "level": context['discuss']['curriculum'].get('level'),
            "prerequisites": context['discuss']['curriculum'].get('prerequisites'),
            "modules": context['discuss']['curriculum'].get('modules')
        },
        "actor": {
            "name": f"{context['profile']['first_name']} {context['profile']['last_name']}",
            "mbox": context['email']
            }
        }
    },
     "module_start_api": {
        "url": "https://learninglocker.zavmo.ai/v1/statements/moduleStart",
        "payload_builder": lambda context: {
            "actor": {
                "name": f"{context['profile']['first_name']} {context['profile']['last_name']}",
                "mbox": context['email']
            },
            "module": {
                "title": context['discuss']['module'].get('title', "Unknown Module"),
                "lessons": context['discuss']['module'].get('lessons', []),
                "duration": context['discuss']['module'].get('duration', "Unknown Duration"),
                "learning_outcomes": context['discuss']['module'].get('learning_outcomes', "No outcomes defined")
            }
        }
    },
    "lesson_start_api": {
        "url": "https://learninglocker.zavmo.ai/v1/statements/lessonStart",
        "payload_builder": lambda context: {
            "actor": {
                "name": f"{context['profile']['first_name']} {context['profile']['last_name']}",
                "mbox": context['email']
            },
            "lesson": {
                "title": context['discuss']['lesson'].get('title', "Unknown Title"),
                "description": context['discuss']['lesson'].get('description', "No description available"),
                "module": context['discuss']['lesson'].get('module', "Unknown Module"),
                "learningObjective": context['discuss']['lesson'].get('learningObjective', "No objectives specified")
            }
        }
    },
    "lesson_progression_api": {
        "url": "https://learninglocker.zavmo.ai/v1/statements/lessonProgression",
        "payload_builder": lambda context: {
            "actor": {
                "name": f"{context['profile']['first_name']} {context['profile']['last_name']}",
                "mbox": context['email']
            },
            "lesson": {
                "title": context['discuss']['lesson'].get('title', "Unknown Title"),
                "module": context['discuss']['lesson'].get('module', "Unknown Module")
            }
        }
    },
    "feedback_api": {
        "url": "https://learninglocker.zavmo.ai/v1/statements/feedback",
        "payload_builder": lambda context: {
            "actor": {
                "name": f"{context['profile']['first_name']} {context['profile']['last_name']}",
                "mbox": context['email']
            },
            "feedback": {
                "text": context['deliver'].get('feedback_text', "No feedback provided")
            }
        }
    },
    "assessment_api": {
        "url": "https://learninglocker.zavmo.ai/v1/statements/assessment",
        "payload_builder": lambda context: {
            "learner": {
                "name": f"{context['profile']['first_name']} {context['profile']['last_name']}",
                "email": context['email']
            },
            "assessment": {
                "evaluations": context['tna_assessment'].get('evaluations', [])
            }
        }
    }

}



