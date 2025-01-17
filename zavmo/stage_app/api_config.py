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
    }
}



