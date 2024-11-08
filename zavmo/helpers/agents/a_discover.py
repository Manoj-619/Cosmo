"""
# Stage 1: Discovery
Fields:
    learning_goals: str
    learning_goal_rationale: str
    knowledge_level: int
    application_area: str
"""

from pydantic import Field
from typing import Dict
from helpers._types import (
    Agent,
    StrictTool,
    PermissiveTool,
    Result,
    Response,
    AgentFunction,
    function_to_json,
)
from stage_app.models import DiscoverStage
from .b_discuss import discuss_agent
from .common import get_agent_instructions

### For handoff
class TransferToDiscussionStage(StrictTool):
    """Transfer to the Discussion stage when the learner approves the summary of the information gathered."""
    def execute(self, context: Dict):
        return Result(agent=discuss_agent, context=context)

### For updating the data
class UpdateDiscoverData(StrictTool):
    """Update the learner's information gathered during the Discovery stage."""
    learning_goals: str = Field(description="The learner's learning goals.")
    learning_goal_rationale: str = Field(description="The learner's rationale for their learning goals.")
    knowledge_level: int = Field(description="The learner's self-assessed knowledge level in their chosen area of study. 1=Beginner, 2=Intermediate, 3=Advanced, 4=Expert")
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
        try:
            # Attempt to get the DiscoverStage object
            discover_stage = DiscoverStage.objects.get(user__email=email, sequence__id=sequence_id)
        except DiscoverStage.DoesNotExist:
            raise ValueError(f"DiscoverStage not found for email {email} and sequence ID {sequence_id}")
        
        # Update the DiscoverStage object
        discover_stage.learning_goals = self.learning_goals
        discover_stage.learning_goal_rationale = self.learning_goal_rationale
        discover_stage.knowledge_level = self.knowledge_level
        discover_stage.application_area = self.application_area
        discover_stage.save()
        
        value = f"""Updated DiscoverStage for {email} and sequence ID {sequence_id}.
        The following data was updated:
        {str(self)}
        """
        context['stage_data']['discover'] = self.model_dump() # JSON dump of pydantic model
        return Result(value=value, context=context)
            
discover_agent = Agent(
    name="Discovery",
    id="discover",
    model="gpt-4o",
    instructions=get_agent_instructions('discover'),
    functions=[
        UpdateDiscoverData,
        TransferToDiscussionStage
    ],
    tool_choice="auto",
    parallel_tool_calls=False
)
