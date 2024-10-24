"""
# Stage 4: Demonstration

Fields:
    curriculum: Curriculum
    assessments: List[Assessment]
    overall_performance: float
    self_assessment: str
    feedback: str
"""

from pydantic import BaseModel, Field
from typing import List
from helpers.swarm import Agent, Response, Result
from .common import get_agent_instructions
    

def request_question():
    print("Requesting Assessment Consultant to generate a question...")
    return assessment_consultant_agent


def transfer_back_to_demonstration_agent():
    print("Transferring back to Demonstration Agent...")
    return demonstrate_agent

completion_agent = Agent(
    name="Completion",
    description="The final agent that gives the learner a summary of the learning journey and asks for feedback",
    instructions="""
    You are a completion agent. Your job is to give the learner a summary of the learning journey and ask for feedback.
    
    Once the user provides feedback, you should update the demonstration data and transfer back to the demonstration agent.
    """,
    model="gpt-4o",
    functions=[UpdateDemonstrationData],
    parallel_tool_calls=True,
    tool_choice='auto'
)


demonstrate_agent = Agent(
    name="Demonstration",
    instructions=get_agent_instructions('demonstrate'),
    functions=[
        request_question,
    ],
    parallel_tool_calls=True,
    tool_choice='auto',
    model="gpt-4o"
)

assessment_consultant_agent.functions.append(transfer_back_to_demonstration_agent)
completion_agent.functions.append(transfer_back_to_demonstration_agent)
