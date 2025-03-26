"""
# Stage 3: Delivery

Fields:
    curriculum: Curriculum
    current_module: str
    current_lesson: str
"""

import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.settings import ModelSettings
from typing import Dict
from helpers.utils import get_logger
from agents.utils import get_agent_instructions
# from helpers.agents.d_demonstrate import demonstrate_agent
from stage_app.tasks import xAPI_lesson_celery_task, xAPI_curriculum_completion_celery_task,xAPI_stage_celery_task
from stage_app.models import DeliverStage, DiscussStage, UserProfile

load_dotenv()

logger = get_logger(__name__)


def transfer_to_demonstrate_stage(ctx: RunContext):
    """Once all lessons have been delivered, and the DeliverStage is updated, transfer to the Demonstration stage."""
    email       = ctx.get('email')
    name        = ctx['profile']['first_name'] + " " + ctx['profile']['last_name']
    sequence_id = ctx.get('sequence_id')
    
    if not email or not sequence_id:
        raise ValueError("Email and sequence id are required to transfer to the Demonstration stage.")
    
    profile = UserProfile.objects.get(user__email=email)
    
    deliver_stage = DeliverStage.objects.get(user__email=email, sequence_id=sequence_id)
    
    
    
# class transfer_to_demonstrate_stage(StrictTool):
#     """Once all lessons have been delivered, and the DeliverStage is updated, transfer to the Demonstration stage."""
#     is_complete: bool = Field(description="Whether all lessons have been delivered and the DeliverStage is updated.")
    
#     def execute(self, context: Dict):
#         # Get email and sequence id from context
#         email       = context['email']
#         name        = context['profile']['first_name'] + " " + context['profile']['last_name']
#         curriculum_title  = context["discuss"]['curriculum']['title']
#         sequence_id = context['sequence_id']
        
#         if not email or not sequence_id:
#             raise ValueError("Email and sequence id are required to transfer to the Demonstration stage.")
        
#         profile = UserProfile.objects.get(user__email=email)
        
#         # Get the DeliverStage object
#         curriculum = DiscussStage.objects.get(user__email=email, sequence_id=sequence_id).curriculum
        
#         deliver_stage             = DeliverStage.objects.get(user__email=email, sequence_id=sequence_id)
#         deliver_stage.is_complete = self.is_complete
#         deliver_stage.save()   

#         if deliver_stage.is_complete:
#             xAPI_curriculum_completion_celery_task.apply_async(args=[curriculum_title,email,name])

#         agent = demonstrate_agent
#         xAPI_stage_celery_task.apply_async(args=[agent.id, email, name])
#         # Create the start message for the Demonstration agent
#         agent.start_message = f"""
        
#         **Curriculum:**
#         {curriculum}
        
#         **Deliver Stage:**
#         {deliver_stage.get_summary()}
        
#         Greet the learner and introduce the Demonstration stage.
#         """
        
#         return Result(
#             value="Transferred to Demonstration stage.",
#             agent=agent, 
#             context=context
#         )

        
class Lesson(BaseModel):
    """Generate a lesson for a module to be delivered to the learner."""
    module: str  = Field(description="The module that the lesson belongs to")
    learning_objective: str = Field(description="The learning objective of the lesson")
    title: str   = Field(description="The title of the lesson")
    lesson: str  = Field(description="A brief overview of the lesson in 2-3 sentences")
        
    def __str__(self):
        return f"Module: {self.module}\nLearning Objective: {self.learning_objective}\nTitle: {self.title}\nLesson: {self.lesson}"


def generate_lesson(ctx: RunContext, lesson: Lesson):
    """Generate a lesson for a module to be delivered to the learner."""
    email       = ctx.get('email')
    name        = ctx['profile']['first_name'] + " " + ctx['profile']['last_name']
    sequence_id = ctx.get('sequence_id')
    
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


deliver_agent = Agent(
    model="openai:gpt-4o",
    system_prompt=get_agent_instructions('deliver'),
    functions=[
        Tool(generate_lesson, takes_ctx=True),
        Tool(transfer_to_demonstrate_stage, takes_ctx=True)
    ],
    settings=ModelSettings(
        parallel_tool_calls=False,
        tool_choice='auto',
    )
)