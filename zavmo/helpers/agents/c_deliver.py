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
    """A lesson from the Lesson Specialist."""
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
        
# class request_lesson(StrictTool):
#     """Request a new lesson from the Lesson Specialist."""
    
#     learning_objective: str = Field(description="The learning objective for the lesson")
#     instructions: str = Field(description="The instructions for the lesson specialist")
    
#     def execute(self, context:Dict):
#         openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
#         system_prompt = get_prompt("lesson")
#         messages      = filter_history(context['history'], max_tokens=40000)
        
#         user_message  = f"\n\nCurriculum: {context['stage_data']['discuss']['curriculum']}\n\n"
#         user_message += f"Learning Objective: {self.learning_objective}\n\n"
#         user_message += f"Instructions: {self.instructions}\n\n"
        
#         messages.append({"role": "user", "content": user_message})
        
#         response = openai_client.beta.chat.completions.parse(
#             model="gpt-4o",
#             messages=messages,
#             response_format=Lesson            
#         )
        
#         lesson = response.choices[0].message.parsed        
#         if 'lessons' in context['stage_data']['deliver']:
#             context['stage_data']['deliver']['lessons'].append(lesson.model_dump())            
#         else:
#             context['stage_data']['deliver']['lessons'] = [lesson.model_dump()]

        
#         logging.debug("Current deliver lessons in context: %s", context['stage_data']['deliver']['lessons'])

            
#         # Update the DeliverStage object
#         email       = context['email']
#         sequence_id = context['sequence_id']
#         deliver_stage = DeliverStage.objects.get(user__email=email, sequence__id=sequence_id)
#         lessons = context['stage_data']['deliver']['lessons']
#         deliver_stage.lessons = lessons
#         deliver_stage.save()
            
#         return Result(value=str(lesson), context=context)        
        
    
class UpdateDeliverData(StrictTool):
    """Update the DeliverStage after all lessons have been delivered."""
    
    def execute(self, context:Dict):        
        # Update the DeliverStage object
        email      = context['email']
        sequence_id = context['sequence_id']
        if not email or not sequence_id:
            raise ValueError("Email and sequence id are required to update deliver data.")
        
        lessons = context['stage_data']['deliver']['lessons']
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