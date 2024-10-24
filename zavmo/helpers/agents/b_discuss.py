"""
# Stage 2: Discussion
Fields:
    interest_areas: str 
    learning_style: str
    curriculum: dict
    timeline: str
"""
import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Dict, Literal, Optional
from helpers.chat import get_prompt
from helpers.swarm import Agent, Result, Tool, Response
from stage_app.models import DiscussStage
from .common import get_agent_instructions
from .c_deliver import deliver_agent

class LearningOutcome(BaseModel):
    description: str = Field(..., description="Description of the learning outcome")
    assessment_criteria: List[str] = Field(..., description="List of assessment criteria for the learning outcome")

class Lesson(BaseModel):
    title: str = Field( description="The title of the lesson")
    content: str = Field( description="The main content of the lesson")
    examples: List[str] = Field( description="List of examples to illustrate the lesson")
    exercises: List[str] = Field( description="List of exercises for the learner to practice")

class Module(BaseModel):
    title: str = Field(description="The title of the module")
    learning_outcomes: List[str] = Field(description="Learning outcomes for the module")
    lessons: List[str] = Field(description="List of lessons in this module")
    duration: int = Field(description="The total duration of the module in hours")

class Curriculum(BaseModel):
    title: str = Field(description="The title of the curriculum")
    subject: str = Field(description="The main subject area of the curriculum")
    level: str = Field(description="The difficulty level of the curriculum (e.g., beginner, intermediate, advanced)")
    prerequisites: List[str] = Field(description="Any prerequisites needed to undertake this curriculum")
    modules: List[Module] = Field(description="List of modules included in the curriculum")
    def __str__(self):
        return "\n".join(f"{field.replace('_', ' ').title()}: {value}" for field, value in self.__dict__.items())

def request_curriculum(learning_objectives: str, 
                       interest_areas: str,
                       time_available: str,
                       instructions: str, 
                       context: Dict):
    """Request the Curriculum Specialist to generate a curriculum with learning objectives, interest areas, time available and instructions."""
    
    if not context:
        print("Warning: Context is empty at the start of request_curriculum.")
    system_prompt = get_prompt('curriculum')
    user_prompt = f"Here is a history of the conversation so far: {context['history']}\n\n"
    user_prompt += f"Learning objectives: {learning_objectives}\n\n"
    user_prompt += f"Interest areas: {interest_areas}\n\n"
    user_prompt += f"Time available per week: {time_available}\n\n"
    user_prompt += f"Instructions: {instructions}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    response = openai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=messages,
        response_format=Curriculum
    )
    model_result = response.choices[0].message.parsed
    context['stage_data']['discuss']['curriculum'].update(model_result.model_dump())
    # Return a Response object instead of Result
    return Result(value=str(model_result), context=context)
        

def update_discussion_data(interest_areas: str,
                           learning_style: str,
                           timeline: str,
                           context: Dict):
    """Update the discussion data after the learner has agreed to the curriculum."""
    
    # Get email and sequence id from context
    email = context['email']
    sequence_id = context['sequence_id']
    if not email or not sequence_id:
        raise ValueError("Email and sequence id are required to update discussion data.")
    
    # Get the DiscussStage object
    discuss_stage = DiscussStage.objects.get(user__email=email, sequence_id=sequence_id)
    discuss_stage.interest_areas = interest_areas
    discuss_stage.learning_style = learning_style
    discuss_stage.curriculum = context['stage_data']['discuss']['curriculum']
    discuss_stage.timeline = timeline
    discuss_stage.save()
        
    result_message = f"""Discussion data updated successfully for {email} with sequence id {sequence_id}.
        
    **Discussion data:**         
        {str(discuss_stage)}
    """
    
    context['stage_data']['discuss'].update({
        'curriculum': discuss_stage.curriculum,
        'timeline': discuss_stage.timeline,
        'interest_areas': discuss_stage.interest_areas,
        'learning_style': discuss_stage.learning_style
    })
    return Result(message=result_message, agent=None, context=context)
         

# Handoff Agent for the next stage
def transfer_to_delivery_agent():
    """Transfer to the Delivery Agent once the Discussion stage is complete."""
    print("Transferring to Delivery Agent...")
    return deliver_agent


discuss_agent = Agent(
    name="Discussion",
    instructions=get_agent_instructions('discuss'),
    functions=[
        update_discussion_data,
        request_curriculum,
        transfer_to_delivery_agent
    ],
    parallel_tool_calls=True,
    tool_choice='auto',
    model="gpt-4o"
)
