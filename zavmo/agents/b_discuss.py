"""
# Stage 2: Discussion
Fields:
    
    learning_style: str
    curriculum: dict
    timeline: str
"""
import json
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.settings import ModelSettings
from typing import List
from helpers.utils import get_logger
from stage_app.models import DiscussStage, UserProfile, TNAassessment,FourDSequence
from agents.common import get_agent_instructions, Deps, model
from stage_app.tasks import xAPI_discuss_celery_task,xAPI_stage_celery_task
# from helpers.agents.c_deliver import deliver_agent

logger = get_logger(__name__)

# class LearningOutcome(BaseModel):
#     description: str = Field(..., description="Description of the learning outcome")
#     assessment_criteria: List[str] = Field(..., description="List of assessment criteria for the learning outcome")

# class Lesson(BaseModel):
#     title: str = Field( description="The title of the lesson")
#     content: str = Field( description="The main content of the lesson")
#     examples: List[str] = Field( description="List of examples to illustrate the lesson")
#     exercises: List[str] = Field( description="List of exercises for the learner to practice")

class Module(BaseModel):
    title: str = Field(description="The title of the module. It can be an Assessment Area or OFQUAL Unit")
    learning_outcomes: List[str] = Field(description="List upto 5 learning outcomes.")
    lessons: List[str] = Field(description="List of lessons in this module based on the learning outcomes.")
    duration: int = Field(description="The total duration of the module in hours")

class Curriculum(BaseModel):
    """Generate a detailed curriculum for the learner based on the Assessment Areas and corresponding OFQUAL Units shared."""
    title: str = Field(description="The title of the curriculum")
    subject: str = Field(description="The main subject area of the curriculum.")
    level: str = Field(description="The difficulty level of the curriculum (e.g., beginner, intermediate, advanced)")
    prerequisites: List[str] = Field(description="Any prerequisites needed to undertake this curriculum")
    modules: List[Module] = Field(description="List upto 10 or more modules majorly designed on Assessment Areas and OFQUAL Units data shared. Include 1-2 modules on learner's interest areas as well.")


def generate_curriculum(ctx: RunContext[Deps], curriculum: Curriculum):
    """Generate a detailed curriculum for the learner based on the Assessment Areas and corresponding OFQUAL Units shared."""
    email       = ctx.deps.email
    profile     = UserProfile.objects.get(user__email=email)
    name        = profile.first_name + " " + profile.last_name
    sequences   = FourDSequence.objects.filter(user=profile.user, current_stage__in=[1, 2, 3, 4]).order_by('created_at')
    sequence_id = sequences.first().id if sequences else None
    
    if not email or not sequence_id:
        raise ValueError("Email and sequence id are required to generate a curriculum.")   
    
    discuss_stage = DiscussStage.objects.get(user__email=email, sequence_id=sequence_id)
    discuss_stage.curriculum = curriculum.model_dump()
    discuss_stage.save()
    
    xAPI_discuss_celery_task.apply_async(args=[curriculum.model_dump(),discuss_stage.learning_style,discuss_stage.interest_areas,discuss_stage.timeline,email,name])
        
    return f"Successfully generated Curriculum for {email}.\n\n{str(curriculum.model_dump())}"


class discussion_data(BaseModel):
    interest_areas: str = Field(description="The learner's interest areas")
    learning_style: str = Field(description="The learner's preferred conversational learning style, for example, role-play, storytelling, or case study discussions")
    timeline: int = Field(description="The learner's timeline for completing the curriculum")

def update_discussion_data(ctx: RunContext[Deps], data: discussion_data):
    """Update the discussion data after the learner has expressed their interest areas, learning style, and timeline."""
    email       = ctx.deps.email
    sequences   = FourDSequence.objects.filter(user__email=email, current_stage__in=[1, 2, 3, 4]).order_by('created_at')
    sequence_id = sequences.first().id if sequences else None
    
    if not email or not sequence_id:
        raise ValueError("Email and sequence id are required to update discussion data.")        
    
    discuss_stage = DiscussStage.objects.get(user__email=email, sequence_id=sequence_id)
                
    discuss_stage.interest_areas  = data.interest_areas
    discuss_stage.learning_style  = data.learning_style
    discuss_stage.timeline        = data.timeline
    discuss_stage.save()
        
    assessment_areas = TNAassessment.objects.filter(user__email=email, sequence_id=sequence_id)
    tna_assessment_data = ""
    for assessment_item in assessment_areas:
        tna_assessment_data += f"**Assessment Area:** {assessment_item.assessment_area}\n**Learner's Report:** {assessment_item.evidence_of_assessment}\n**Gaps Determined:** {assessment_item.knowledge_gaps}\n\n"

        ofqual_units = "\n\n".join([f"**OFQUAL ID: {ofqual.ofqual_id} (Unit: {ofqual.ofqual_unit_id}):**\n{ofqual.ofqual_unit_data}" for ofqual in assessment_areas])
    
    value = f"""Discussion data updated successfully for {email}
            
    **Timeline**: {data.timeline}
    **Learning Style**: {data.learning_style}

    The following data sources are being used to inform the personalized curriculum design:
    1. All TNA Assessment Data
    2. All OFQUAL Units Data


    - **All TNA Assessment Data provided below must be used for Curriculum Generation**:

    {tna_assessment_data}

    - **All OFQUAL Units Data provided below must be used for Curriculum Generation**:

    {ofqual_units}
            """
            
    logger.info(f"Discussion data updated successfully for {email}:\n\n{value}")  
    return value
 
discuss_agent = Agent(
    model=model,
    system_prompt=get_agent_instructions('discuss'),
    tools=[
        Tool(update_discussion_data),
        Tool(generate_curriculum)
    ],
    instrument=True,
    model_settings=ModelSettings(
        tool_choice='auto',
        parallel_tool_calls=False
    ),
    retries=3
)
