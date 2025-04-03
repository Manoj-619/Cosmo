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
from agents.utils import get_agent_instructions
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
    
    # Append the lesson to the DeliverStage
    deliver_stage.lessons.append(lesson.model_dump_json())
    deliver_stage.save()
    logger.info(f"Lesson generated for {email}.")
    xAPI_lesson_celery_task.apply_async(args=[json.loads(lesson.model_dump_json()),email,name])

    return f"Lesson generated for {email}.\n\n{lesson}"



class deliver_data(BaseModel):
    """Update the delivery data for the current sequence."""
    learning_progress: str = Field(description="Progress made in learning objectives.")
    completion_status: str = Field(description="Status of completion for assigned tasks.")
    feedback: str = Field(description="Feedback on the delivery phase.")
    
def update_deliver_data(ctx: RunContext[Deps], data: deliver_data):
        email = ctx.deps.email
        profile = UserProfile.objects.get(user__email=email)
        
        sequence = FourDSequence.objects.filter(
            user=profile.user,
            current_stage=FourDSequence.Stage.DELIVER
        ).order_by('created_at').first()
        
        if not sequence:
            raise ValueError("No active Deliver stage sequence found.")
        
        sequence.learning_progress = data.learning_progress
        sequence.completion_status = data.completion_status
        sequence.delivery_feedback = data.feedback
        sequence.save()
        
        return "Delivery data updated successfully."

deliver_agent = Agent(
    model,
    model_settings=ModelSettings(parallel_tool_calls=True),
    system_prompt=get_agent_instructions('deliver'),
    instrument=True,
    tools=[
        Tool(update_deliver_data),
        Tool(generate_lesson)
    ],
    retries=3)