"""
# Stage 2: Discussion

Fields:
    interest_areas: str 
    learning_style: str
    curriculum: dict
    timeline: str
"""

from pydantic import BaseModel, Field
from helpers.swarm import Agent, Response, Result
from .common import Curriculum, curriculum_agent, get_agent_instructions
from .c_deliver import deliver_agent

class UpdateDiscussionData(BaseModel):
    interest_areas: str = Field(description="The learner's interest areas.")
    learning_style: str = Field(description="The learner's learning style.")
    curriculum: Curriculum = Field(description="The curriculum plan agreed upon by the learner.")
    timeline: str = Field(description="The learner's timeline.")

    def __str__(self):
        return "\n".join(f"{field.replace('_', ' ').title()}: {value}" 
                         for field, value in self.__dict__.items())

# Handoff Agent for the next stage
def transfer_to_delivery_agent():
    """Transfer to the Delivery Agent once the Discussion stage is complete."""
    print("Transferring to Delivery Agent...")
    return deliver_agent

# Handoff back to main agent after curriculum is generated
def transfer_back_to_discussion_agent():
    """Transfer back to the Discussion Agent once the Curriculum stage is complete."""
    print("Transferring back to Discussion Agent...")
    return discuss_agent



discuss_agent = Agent(
    name="Discussion",
    instructions=get_agent_instructions('discuss'),
    functions=[
        UpdateDiscussionData,
        transfer_to_delivery_agent
    ],
    parallel_tool_calls=True,
    tool_choice='auto',
    model="gpt-4o"
)


def request_curriculum():
    """Request the Curriculum Specialist to generate a curriculum."""
    print("Requesting Curriculum Specialist to generate a curriculum...")
    return curriculum_agent


curriculum_agent.functions.append(transfer_back_to_discussion_agent)
discuss_agent.functions.append(request_curriculum)