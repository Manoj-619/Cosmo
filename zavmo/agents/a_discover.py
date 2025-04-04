"""
# Stage 1: Discovery
Fields:
    learning_goals: str
    learning_goal_rationale: str
    knowledge_level: int
    application_area: str
"""

from pydantic import Field, BaseModel
from typing import Dict
from stage_app.models import DiscoverStage, UserProfile, FourDSequence
from agents.common import get_agent_instructions, Deps
from agents.utils import get_agent_instructions
from helpers.utils import get_logger
from stage_app.tasks import xAPI_discover_celery_task
from pydantic_ai import Agent, RunContext, Tool
import json

logger = get_logger(__name__)


### For updating the data
class DiscoverData(BaseModel):
    learning_goals: str = Field(description="The learner's learning goals.")
    learning_goal_rationale: str = Field(description="The learner's rationale for their learning goals.")
    knowledge_level: int = Field(description="The learner's self-assessed knowledge level in their chosen area of study. 1=Beginner, 2=Intermediate, 3=Advanced, 4=Expert")
    application_area: str = Field(description="A specific area or context where the learner plans to apply their new knowledge and skills.")

def update_discover_data(ctx: RunContext[Deps], data: DiscoverData):
    """Update the learner's information gathered during the Discovery stage."""
    
    # Get email and sequence_id from context
    email       = ctx.deps.email
    profile     = UserProfile.objects.get(user__email=email)
    name        = profile.first_name + " " + profile.last_name
    sequences   = FourDSequence.objects.filter(user=profile.user, current_stage__in=[1, 2, 3, 4]).order_by('created_at')
    sequence_id = sequences.first().id if sequences else None

    if not email or not sequence_id:
        raise ValueError("Email and sequence ID are required to update discovery data.")        
    # Attempt to get the DiscoverStage object
    
    discover_stage = DiscoverStage.objects.get(user__email=email, sequence_id=sequence_id)
    discover_stage.learning_goals = data.learning_goals
    discover_stage.learning_goal_rationale = data.learning_goal_rationale
    discover_stage.knowledge_level = data.knowledge_level
    discover_stage.application_area = data.application_area
    discover_stage.save() 

    xAPI_discover_celery_task.apply_async(args=[data.model_dump(),email,name])

    logger.info(f"Updated Discover stage Data for {email}. The following data was updated:\n\n{str(data)}")
    
    return f"Successfully updated Discover stage Data for {email}."
            
            
discover_agent = Agent(
    model="openai:gpt-4o",
    system_prompt=get_agent_instructions('discover'),
    tools=[
        Tool(update_discover_data)
    ],
    instrument=True,
)