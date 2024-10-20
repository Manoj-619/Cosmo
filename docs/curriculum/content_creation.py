from celery import shared_task
from django.contrib.auth.models import User
from django.core.cache import cache
from stage_app.models import Curriculum
from helpers.chat import force_tool_call, create_message_payload
from helpers.functions import create_pydantic_model, get_yaml_data, create_system_message
from stage_app.views import summarize_profile
from helpers.constants import USER_PROFILE_SUFFIX


@shared_task
def content_creation(user_email):
    profile_cache_key = f"{user_email}_{USER_PROFILE_SUFFIX}"
    profile_data = cache.get(profile_cache_key)

    if not profile_data:
        return {'status': 'error', 'message': 'No profile data found'}

    # TODO // Change the call to Curriculum_creation and instead make a call that is stage dependent.

    # Get the content creation config
    content_config = get_yaml_data('curriculum_creation')

    # TODO // Ensure that we are using stage sopecific system message
    # Create the system message
    system_message = create_system_message(
        'curriculum_creation', content_config, mode='create')

    # Create the user content
    user_content = f"""
    Here is what we know about the learner:
    {summarize_profile(profile_data)}
    
    Please create a curriculum based on this information.
    """

    # Create the message payload
    message_payload = create_message_payload(
        user_content, system_message, [], max_tokens=10000)

    # Create the response model
    resp_schema = content_config['response']
    resp_model = create_pydantic_model(name=resp_schema['title'],
                                       description=resp_schema['description'],
                                       fields=resp_schema['fields'])

    # Generate the curriculum
    response_tool = force_tool_call(resp_model,
                                    message_payload,
                                    model='gpt-4o',
                                    tool_choice='required')

    curriculum_content = response_tool.curriculum

    # Save the curriculum to the database
    curriculum = Curriculum.objects.create(
        user_email=user_email, content=curriculum_content)

    # Cache the curriculum
    cache_key = f"{user_email}_curriculum"
    cache.set(cache_key, curriculum_content)

    return curriculum.id

    # TODO purpose of this function is to take the user profile summary & context then apply a stage specific,
    # YAML & json schema This then enters into an gpt 4om-mini structured output request and is then returned with the request.
    # the DoD for this command is if this is called asycnhronously through celery, it collects the user's profile information collected from Discovery & Discussion
    # a large Curriculum schema is created an example one below.
    # the prompts that will be used for this will be a modified  version of probe called Content.md which will be sorted in the prompts file, this will detail the
    # requirements for content creation and the need for pulling user information
    #     [
    #  {
    #    "title": "Level 5 Diploma in Business Management",
    #    "subject": "Business Management",
    #    "level": "5",
    #    "modules": [
    #      {
    #        "title": "Organizational Behavior",
    #        "learning_outcomes": [
    #          {
    #            "description": "Understand and analyze organizational behavior concepts",
    #            "assessment_criteria": [
    #              "Explain key theories of organizational behavior",
    #              "Analyze the impact of organizational culture on performance"
    #            ]
    #          }
    #        ],
    #        "lessons": [
    #          {
    #            "title": "Introduction to Organizational Behavior",
    #            "content": "This lesson introduces the key concepts of organizational behavior...",
    #            "duration": 120
    #          },
    #          {
    #            "title": "Individual Behavior in Organizations",
    #            "content": "Learn about personality, perception, and individual decision making...",
    #            "duration": 120
    #          }
    #        ],
    #        "duration": 60
    #      }
    #    ],
    #    "prerequisites": ["Level 4 qualification in a related subject"],
    #    "qualification_level": 5,
    #    "guided_learning_hours": 240,
    #    "total_qualification_time": 480,
    #    "assessment_methods": ["Written examination", "Case study analysis", "Research project"]
    #  }
    # ]
