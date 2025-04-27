"""
# Stage 3: Delivery

Fields:
    curriculum: Curriculum
    current_module: str
    current_lesson: str
"""

import json
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.settings import ModelSettings
from typing import Dict
from helpers.utils import get_logger
from agents.utils import get_agent_instructions, get_module_ids # Import the new function
# from helpers.agents.d_demonstrate import demonstrate_agent
from stage_app.tasks import xAPI_lesson_celery_task, xAPI_curriculum_completion_celery_task,xAPI_stage_celery_task
from stage_app.models import DeliverStage, DiscussStage, UserProfile, FourDSequence, TNAassessment
from agents.common import model, get_agent_instructions, Deps


logger = get_logger(__name__)

      
class Lesson(BaseModel):
    """Generate a lesson for a module to be delivered to the learner."""
    module: str  = Field(description="The module that the lesson belongs to")
    learning_objective: str = Field(description="The learning objective of the lesson")
    title: str   = Field(description="The title of the lesson")
    lesson: str  = Field(description="A brief overview of the lesson in 2-3 sentences")
        
    def __str__(self):
        return f"Module: {self.module}\nLearning Objective: {self.learning_objective}\nTitle: {self.title}\nLesson: {self.lesson}"


def generate_lesson(ctx: RunContext[Deps], lesson: Lesson):
    """Generate a lesson for a module to be delivered to the learner."""
    email       = ctx.deps.email
    profile     = UserProfile.objects.get(user__email=email)
    name        = profile.first_name + " " + profile.last_name
    sequences   = FourDSequence.objects.filter(user__email=email, current_stage__in=[1, 2, 3, 4]).order_by('created_at')
    sequence_id = sequences.first().id if sequences else None

    if not email or not sequence_id:
        raise ValueError("Email and sequence id are required to generate a lesson.")

    deliver_stage = DeliverStage.objects.get(user__email=email, sequence_id=sequence_id)

    if not deliver_stage:
        raise ValueError("Deliver stage not found.")

    if deliver_stage.is_complete:
        raise ValueError("Deliver stage is already complete.")

    # Access the module name here
    module_name = lesson.module
    logger.info(f"Generating lesson for module: {module_name}")

    # --- Fetch NOS and OFQUAL IDs ---
    module_ids = get_module_ids(sequence_id)
    nos_id = module_ids.get('nos_id')
    ofqual_id = module_ids.get('ofqual_id')
    logger.info(f"Fetched IDs for sequence {sequence_id}: NOS ID={nos_id}, OFQUAL ID={ofqual_id}")
    # --- End fetching IDs ---

    # Append the lesson to the DeliverStage
    deliver_stage.lessons.append(lesson.model_dump()) # Use model_dump() instead of model_dump_json() if storing dict
    deliver_stage.save()
    logger.info(f"Lesson generated for {email}.")

    # --- Update Celery task call to include IDs ---
    # NOTE: You will need to modify the xAPI_lesson_celery_task function
    # in stage_app/tasks.py to accept and use these new arguments.
    xAPI_lesson_celery_task.apply_async(args=[
        lesson.model_dump(),
        email,
        name,
        module_name, # Pass module name
        nos_id,      # Pass NOS ID
        ofqual_id    # Pass OFQUAL ID
    ])
    # --- End update Celery task call ---

    # You can also include the module name in the return message if needed
    return f"Lesson generated for module '{module_name}' (NOS: {nos_id}, OFQUAL: {ofqual_id}) for {email}.\n\n{lesson}"



deliver_agent = Agent(
    model,
    model_settings=ModelSettings(parallel_tool_calls=True),
    system_prompt=get_agent_instructions('deliver'),
    instrument=True,
    tools=[
        Tool(generate_lesson)
    ],
    retries=3)