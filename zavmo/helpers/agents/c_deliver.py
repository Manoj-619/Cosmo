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
from helpers.chat import filter_history, get_prompt
from .common import get_agent_instructions
from .d_demonstrate import demonstrate_agent
from stage_app.models import DeliverStage
from helpers._types import (
    Agent,
    StrictTool,
    PermissiveTool,
    Result,
    Response,
    AgentFunction,
    function_to_json,
)

from openai import OpenAI
import logging

logging.basicConfig(level=logging.DEBUG)

load_dotenv()

class TransferToDemonstrationStage(StrictTool):
    """Once all lessons have been delivered, and the DeliverStage is updated, transfer to the Demonstration stage."""
    def execute(self, context: Dict):
        return Result(agent=demonstrate_agent, context=context)

class Lesson(StrictTool):
    """Generate a lesson for a module to be delivered to the learner."""
    title: str = Field(description="The title of the lesson")
    lesson: str = Field(description="The lesson")
    content: str = Field(description="The content of the lesson")
    
    def __str__(self):
        return f"**Title**: {self.title}\n**Lesson**: {self.lesson}\n**Content**: {self.content}"
    
    def execute(self, context: Dict):
        lesson = self.model_dump()
        if 'lessons' in context['stage_data']['deliver']:
            context['stage_data']['deliver']['lessons'].append(lesson)
        else:
            context['stage_data']['deliver']['lessons'] = [lesson]
        return Result(value=str(self), context=context)

    
class UpdateDeliverData(StrictTool):
    """Update the DeliverStage after each lesson."""
    
    def execute(self, context:Dict):        
        # Update the DeliverStage object
        email      = context['email']
        sequence_id = context['sequence_id']
        if not email or not sequence_id:
            raise ValueError("Email and sequence id are required to update deliver data.")
        
        deliver_data = context['stage_data']['deliver']
        if 'lessons' not in deliver_data:
            raise ValueError("Lessons are required to update deliver data.")
        
        lessons = deliver_data['lessons']
        
        if not lessons:
            raise ValueError("Lessons are required to update deliver data.")
        
        deliver_stage = DeliverStage.objects.get(
            user__email=email, 
            sequence__id=sequence_id
        )
        deliver_stage.lessons = lessons
        deliver_stage.save()
        
        value = f"Delivery stage updated successfully for learner"
            
        return Result(value=value, context=context)
    

deliver_agent = Agent(
    name="Delivery",
    id="deliver",
    instructions=get_agent_instructions('deliver'),
    functions=[
        Lesson,
        UpdateDeliverData,
        TransferToDemonstrationStage
    ],
    parallel_tool_calls=False,
    tool_choice='auto',
    model="gpt-4o"
)