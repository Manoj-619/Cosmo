"""
# Stage 2: Discussion

Fields:
    interest_areas: str 
    learning_style: str
    curriculum: dict
    timeline: str
"""

from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Any
from _types import Agent, Response, Result
# Handoff Agent for the next stage
from .deliver import deliver_agent
from .util import get_agent_instructions

### For handoff
def transfer_to_delivery_agent():
    """
    Transfer to the Delivery Agent when the learner is satisfied with the plan, timeline, and goals alignment.
    """
    print("Transferring to Deliver Agent...")
    return deliver_agent

### For updating the data
class update_discussion_data(BaseModel):
    """
    Update the learner's information gathered during the Discussion stage.
    """
    interest_areas: Optional[str] = Field(description="The learner's interest areas.")
    learning_style: Optional[str] = Field(description="The learner's learning style.")
    curriculum: Optional[Any] = Field(description="The learner's curriculum plan.")
    timeline: Optional[str] = Field(description="The learner's timeline.")
    goals_alignment: Optional[str] = Field(description="The learner's goals alignment.")

    def __str__(self):
        output = []
        for field, value in self.__dict__.items():
            field_name = field.replace('_', ' ').title()
            field_value = value if value is not None else "Not yet determined"
            output.append(f"{field_name}: {field_value}")
        return "\n".join(output)
    
#### For responding / handoff
discuss_agent = Agent(
    name="Discussion",
    instructions=get_agent_instructions('discuss'),
    functions=[
        update_discussion_data,
        transfer_to_delivery_agent
    ]
)