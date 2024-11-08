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
from helpers.utils import get_logger
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

load_dotenv()

logger = get_logger(__name__)


class TransferToDemonstrationStage(StrictTool):
    """Once all lessons have been delivered, and the DeliverStage is updated, transfer to the Demonstration stage."""
    def execute(self, context: Dict):
        logger.info(f"Transferred to the Demonstration stage for {context['email']}.")
        return Result(
            value="Transferred to the Demonstration stage.",
            agent=demonstrate_agent, 
            context=context
        )

class Lesson(StrictTool):
    """Generate a lesson for a module to be delivered to the learner."""
    module: str = Field(description="The module that the lesson belongs to")
    learning_objective: str = Field(description="The learning objective of the lesson")
    title: str   = Field(description="The title of the lesson")
    lesson: str = Field(description="A concise summary of the lesson")
        
    def execute(self, context: Dict):
        logger.info(f"Generated lesson:\n\n{str(self)}")
        lesson = self.model_dump()
        if 'lessons' in context['stage_data']['deliver']:
            context['stage_data']['deliver']['lessons'].append(lesson)
        else:
            context['stage_data']['deliver']['lessons'] = [lesson]
        return Result(
            value=str(self.model_dump()),
            context=context
        )

    
class UpdateDeliverData(StrictTool):
    """Update the DeliverStage after each lesson."""
    
    def execute(self, context:Dict):        
        # Update the DeliverStage object
        logger.info(f"Updating DeliverStage data for {context['email']}.")
        email       = context['email']
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
            sequence_id=sequence_id
        )
        deliver_stage.lessons = lessons
        deliver_stage.save()
    
        return Result(
            value=f"Delivery stage updated successfully for learner", 
            context=context
        )
    

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