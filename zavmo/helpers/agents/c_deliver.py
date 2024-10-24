"""
# Stage 3: Delivery

Fields:
    curriculum: Curriculum
    current_module: str
    current_lesson: str
"""
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Dict
from helpers.swarm import Agent, Response, Result
from .common import get_agent_instructions
from .d_demonstrate import demonstrate_agent
from stage_app.models import DeliverStage
from openai import OpenAI

load_dotenv()




def transfer_to_demonstration_agent():
    """Once the Delivery stage is complete, transfer to the Demonstration Agent."""
    print("Transferring to Demonstration Agent...")
    return demonstrate_agent

def request_lesson(learning_objective:str, module:str, context:Dict):
    """Request a new lesson from the Lesson Specialist."""
    print(f"Requesting Lesson Specialist to generate a lesson: {learning_objective} for module: {module}")
    # Get the Lesson Specialist agent
    openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
def update_deliver_data(lesson:str, context:Dict):
    """Update the DeliverStage with the new lesson."""
    print(f"Updating DeliverStage with new lesson: {lesson}")
    # Update the DeliverStage object
    

deliver_agent = Agent(
    name="Delivery",
    id="deliver",
    instructions=get_agent_instructions('deliver'),
    functions=[
        request_lesson,
        transfer_to_demonstration_agent
    ],
    parallel_tool_calls=True,
    tool_choice='auto',
    model="gpt-4o"
)

