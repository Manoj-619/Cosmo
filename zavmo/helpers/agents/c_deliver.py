"""
# Stage 3: Delivery

Fields:
    curriculum: Curriculum
    current_module: str
    current_lesson: str
"""

from pydantic import BaseModel, Field
from typing import List
from helpers.swarm import Agent, Response, Result
from .common import get_agent_instructions
from .d_demonstrate import demonstrate_agent

class UpdateDeliveryData(BaseModel):
    """At the end of the Delivery stage, update the lessons and curriculum."""
    curriculum: Curriculum = Field(description="The curriculum plan agreed upon by the learner.")
    lessons: List[Lesson] = Field(description="The lessons to be taught.")

    def __str__(self):
        return "\n".join(f"{field.replace('_', ' ').title()}: {value}" 
                         for field, value in self.__dict__.items())

def transfer_to_demonstration_agent():
    """Once the Delivery stage is complete, transfer to the Demonstration Agent."""
    print("Transferring to Demonstration Agent...")
    return demonstrate_agent

def request_lesson():
    """Request the Lesson Specialist to generate a lesson."""
    print("Requesting Lesson Specialist to generate a lesson...")
    return lesson_specialist_agent

def transfer_back_to_delivery_agent():
    """Generate a lesson and transfer back to the Delivery Agent."""
    print("Transferring back to Delivery Agent...")
    return deliver_agent

deliver_agent = Agent(
    name="Delivery",
    instructions=get_agent_instructions('deliver'),
    functions=[
        request_lesson,
        UpdateDeliveryData,
        transfer_to_demonstration_agent
    ],
    parallel_tool_calls=True,
    tool_choice='auto',
    model="gpt-4o"
)

lesson_specialist_agent.functions.append(transfer_back_to_delivery_agent)