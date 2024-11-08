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
from helpers.swarm import Agent, Response, Result, Tool
from helpers.chat import filter_history, get_prompt
from .common import get_agent_instructions
from .d_demonstrate import demonstrate_agent
from stage_app.models import DeliverStage
from openai import OpenAI
import logging

logging.basicConfig(level=logging.DEBUG)

load_dotenv()

def transfer_to_demonstration_agent():
    """Once all lessons are added, and the delivery stage data is updated, transfer to the Demonstration Agent."""
    return demonstrate_agent

class Lesson(BaseModel):
    """A lesson from the Lesson Specialist."""
    title: str = Field(description="The title of the lesson")
    lesson: str = Field(description="The lesson")
    content: str = Field(description="The content of the lesson")
    
    def __str__(self):
        return f"**Title**: {self.title}\n**Lesson**: {self.lesson}\n**Content**: {self.content}"

class request_lesson(Tool):
    """Request a new lesson from the Lesson Specialist."""
    
    learning_objective: str = Field(description="The learning objective for the lesson")
    instructions: str = Field(description="The instructions for the lesson specialist")
    
    def execute(self, context:Dict):
        openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        system_prompt = get_prompt("lesson")
        messages      = filter_history(context['history'], max_tokens=40000)
        
        user_message  = f"\n\nCurriculum: {context['stage_data']['discuss']['curriculum']}\n\n"
        user_message += f"Learning Objective: {self.learning_objective}\n\n"
        user_message += f"Instructions: {self.instructions}\n\n"
        
        messages.append({"role": "user", "content": user_message})
        
        response = openai_client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=messages,
            response_format=Lesson            
        )
        
        lesson = response.choices[0].message.parsed        
        if 'lessons' in context['stage_data']['deliver']:
            context['stage_data']['deliver']['lessons'].append(lesson.model_dump())            
        else:
            context['stage_data']['deliver']['lessons'] = [lesson.model_dump()]

        
        logging.debug("Current deliver lessons in context: %s", context['stage_data']['deliver']['lessons'])

            
        # Update the DeliverStage object
        email       = context['email']
        sequence_id = context['sequence_id']
        deliver_stage = DeliverStage.objects.get(user__email=email, sequence__id=sequence_id)
        lessons = context['stage_data']['deliver']['lessons']
        deliver_stage.lessons = lessons
        deliver_stage.save()
            
        return Result(value=str(lesson), context=context)        
        
    
class update_deliver_data(Tool):
    """Update the DeliverStage with the new lesson."""
    
    def execute(self, context:Dict):
        
        # Update the DeliverStage object
        email = context['email']
        sequence_id = context['sequence_id']
        if not email or not sequence_id:
            raise ValueError("Email and sequence id are required to update deliver data.")
        
        deliver_stage = DeliverStage.objects.get(user__email=email, sequence_id=sequence_id)
        lessons = context['stage_data']['deliver']['lessons']
        deliver_stage.lessons = lessons
        deliver_stage.save()
        
        value = f"Lesson added successfully for {email} with sequence id {sequence_id}. The following lessons was added:"
        
        for lesson in lessons:
            value += f"\n{lesson['title']}"
            
        return Result(value=value, context=context)
    

deliver_agent = Agent(
    name="Delivery",
    id="deliver",
    instructions=get_agent_instructions('deliver'),
    functions=[
        request_lesson,
        update_deliver_data,
        transfer_to_demonstration_agent
    ],
    parallel_tool_calls=True,
    tool_choice='auto',
    model="gpt-4o"
)