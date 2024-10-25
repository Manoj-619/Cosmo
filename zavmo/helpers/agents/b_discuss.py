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
from helpers.chat import get_prompt, summarize_history
from helpers.swarm import Agent, Result, Tool, Response
from stage_app.models import DiscussStage
from .common import get_agent_instructions
from .c_deliver import deliver_agent
from tabulate import tabulate

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
        """Return a tabular representation of the Curriculum object."""
        return tabulate(self.__dict__, headers="keys", tablefmt="grid")

class request_curriculum(Tool):
    """Request a curriculum from the curriculum design team."""
    instructions: str = Field(description="Instructions for generating the curriculum")
    learning_objectives: str = Field(description="The learner's learning objectives")
    interest_areas: str = Field(description="The learner's interest areas")
    time_available: str = Field(description="The time available for the learner to study per week")
    
    def execute(self, context: Dict):
        print(f"Curriculum request received for {context['email']} with sequence id {context['sequence_id']}")
        conversation_summary = summarize_history(filter_history(context['history'], max_tokens=60000))
        user_prompt  = f"Here is a summary of the conversation so far: {conversation_summary}\n\n"
        user_prompt += f"Learning objectives: {self.learning_objectives}\n\n"
        user_prompt += f"Interest areas: {self.interest_areas}\n\n"
        user_prompt += f"Time available per week: {self.time_available}\n\n"
        user_prompt += f"Instructions: {self.instructions}"
        
        messages = [
            {"role": "system", "content": get_prompt('curriculum')},
            {"role": "user", "content": user_prompt}
        ]
        openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = openai_client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=messages,
            response_format=Curriculum
        )
        model_result = response.choices[0].message.parsed
        
        context['stage_data']['discuss']['curriculum'] = model_result.model_dump()
        curriculum_text = str(model_result)
        value = f"Curriculum generated successfully:\n\n{curriculum_text}"
        return Result(value=value, context=context)
        

class update_discussion_data(Tool):
                           
    """Update the discussion data after the learner has agreed to the curriculum."""
    interest_areas: str = Field(description="The learner's interest areas")
    learning_style: str = Field(description="The learner's learning style")
    timeline: str = Field(description="The learner's timeline for completing the curriculum")
    
    def execute(self, context: Dict):
        # Get email and sequence id from context
        email = context['email']
        sequence_id = context['sequence_id']
        if not email or not sequence_id:
            raise ValueError("Email and sequence id are required to update discussion data.")
    
        # Get the DiscussStage object
        discuss_stage = DiscussStage.objects.get(user__email=email, sequence_id=sequence_id)
        discuss_stage.interest_areas = self.interest_areas
        discuss_stage.learning_style = self.learning_style
        discuss_stage.curriculum = context['stage_data']['discuss']['curriculum']
        discuss_stage.timeline = self.timeline
        discuss_stage.save()
        
        value = f"""Discussion data updated successfully for {email} with sequence id {sequence_id}.

        **Discussion data:**         
            
            {str(discuss_stage)}
        """
        stage_data = discuss_stage.model_dump()
        stage_data['curriculum'] = context['stage_data']['discuss']['curriculum']
        context['stage_data']['discuss'] = stage_data
        
        return Result(value=value, context=context)
         
# Handoff Agent for the next stage
def transfer_to_delivery_agent():
    """Transfer to the Delivery Agent once the Discussion stage is complete."""
    return deliver_agent


discuss_agent = Agent(
    name="Discussion",
    id="discuss",
    instructions=get_agent_instructions('discuss'),
    functions=[
        request_curriculum,
        update_discussion_data,        
        transfer_to_delivery_agent
    ],
    parallel_tool_calls=False,
    tool_choice='auto',
    model="gpt-4o"
)
