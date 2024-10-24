"""
# Stage 1: Discovery

Fields:
    learning_goals: str
    learning_goal_rationale: str
    knowledge_level: int
    application_area: str
"""

from pydantic import BaseModel, Field, validator
from typing import Literal, List, Optional, Dict
from helpers.swarm import Agent, Response, Result, Tool
# from stage_app.models import DiscoverStage
from .b_discuss import discuss_agent
from .common import get_agent_instructions

### For handoff
def transfer_to_discussion_agent():
    """Transfer to the Discussion Agent when the learner is satisfied with the summary of the information gathered."""
    return discuss_agent

### For updating the data
class update_discover_data(Tool):
    """Update the learner's information gathered during the Discovery stage."""
    learning_goals: str = Field(description="The learner's learning goals.")
    learning_goal_rationale: str = Field(description="The learner's rationale for their learning goals.")
    knowledge_level: Literal["Beginner", "Intermediate", "Advanced", "Expert"] = Field(description="The learner's self-assessed knowledge level in their chosen area of study.")
    application_area: str = Field(description="A specific area or context where the learner plans to apply their new knowledge and skills.")
    
    def __str__(self):
        """Return a string representation of the UpdateDiscoverData object."""
        string = []
        for field, value in self.__dict__.items():
            string.append(f"{field}: {value}")
        return "\n".join(string)
    
    def execute(self, context: Dict):
        # Get email and sequence_id from context
        email       = context.get('email')
        sequence_id = context.get('sequence_id')
        if not email or not sequence_id:
            raise ValueError("Email and sequence ID are required to update discovery data.")
        
        # # Get the DiscoverStage object
        # discover_stage = DiscoverStage.objects.get(user_email=email, sequence_id=sequence_id)
        # if not discover_stage:
        #     raise ValueError("DiscoverStage not found")
        
        # # Update the DiscoverStage object
        # discover_stage.learning_goals = self.learning_goals
        # discover_stage.learning_goal_rationale = self.learning_goal_rationale
        # discover_stage.knowledge_level = self.knowledge_level
        # discover_stage.application_area = self.application_area
        # discover_stage.save()
        value = f"""Updated DiscoverStage for {email} with sequence ID {sequence_id}.
        The following data was updated:
        {str(self)}
        """
        context['stage_data']['discover'] = self.model_dump()    
        return Result(value=value, context=context)
            
discovery_agent = Agent(
    name="Discovery",
    model="gpt-4o-mini",
    instructions=get_agent_instructions('discover'),
    functions=[
        update_discover_data,
        transfer_to_discussion_agent
    ],
    tool_choice="auto",
    parallel_tool_calls=False
)
