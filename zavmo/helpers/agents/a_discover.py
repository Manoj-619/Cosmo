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
from helpers.swarm import Agent, Response, Result
# Handoff Agent for the next stage
from .b_discuss import discuss_agent
from .common import get_agent_instructions

### For handoff
def transfer_to_discussion_agent():
    """Transfer to the Discussion Agent when the learner is satisfied with the summary of the information gathered."""
    print("Transferring to Discussion Agent...")
    return discuss_agent

### For updating the data
class UpdateDiscoverData(BaseModel):
    """Update the learner's information gathered during the Discovery stage."""
    learning_goals: Optional[str] = Field(description="The learner's learning goals.")
    learning_goal_rationale: Optional[str] = Field(description="The learner's rationale for their learning goals.")
    knowledge_level: Optional[Literal['1','2','3','4']] = Field(description="The learner's self-assessed knowledge level in their chosen area of study. 1 -> 'Beginner', 2 -> 'Intermediate', 3 -> 'Advanced', 4 -> 'Expert'")
    application_area: Optional[str] = Field(description="A specific area or context where the learner plans to apply their new knowledge and skills.")
        
    def __str__(self):
        output = []
        for field, value in self.__dict__.items():
            field_name = field.replace('_', ' ').title()
            if field =='knowledge_level':
                if value:
                    if isinstance(value, str) and value.isdigit():
                        value = int(value)

            field_value = value if value is not None else "Not yet determined"
            output.append(f"{field_name}: {field_value}")
        return "\n".join(output)
    
#### For responding / handoff
discover_agent = Agent(
    name="Discover",
    model="gpt-4o-mini",
    instructions=get_agent_instructions('discover'),
    functions=[
        UpdateDiscoverData,
        transfer_to_discussion_agent
    ],
    tool_choice="auto",
    parallel_tool_calls=True
)
