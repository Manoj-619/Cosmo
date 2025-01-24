"""
# Stage 2: Discussion
Fields:
    
    learning_style: str
    curriculum: dict
    timeline: str
"""
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Dict, Literal, Optional
from helpers._types import (
    Agent,
    StrictTool,
    Result,
)
from helpers.utils import get_logger
from stage_app.models import DiscussStage, UserProfile, TNAassessment, DiscoverStage
from helpers.agents.common import get_agent_instructions
from helpers.agents.c_deliver import deliver_agent

logger = get_logger(__name__)

# class LearningOutcome(BaseModel):
#     description: str = Field(..., description="Description of the learning outcome")
#     assessment_criteria: List[str] = Field(..., description="List of assessment criteria for the learning outcome")

# class Lesson(BaseModel):
#     title: str = Field( description="The title of the lesson")
#     content: str = Field( description="The main content of the lesson")
#     examples: List[str] = Field( description="List of examples to illustrate the lesson")
#     exercises: List[str] = Field( description="List of exercises for the learner to practice")

class Module(BaseModel):
    title: str = Field(description="The title of the module. It can be an Assessment Area or a learner's interest area")
    learning_outcomes: List[str] = Field(description="List upto 5 learning outcomes.")
    lessons: List[str] = Field(description="List of lessons in this module based on the learning outcomes")
    duration: int = Field(description="The total duration of the module in hours")

class Curriculum(StrictTool):
    """Generate a detailed curriculum for the learner based on the NOS Assessment Areas and OFQUAL standards shared."""
    title: str = Field(description="The title of the curriculum")
    subject: str = Field(description="The main subject area of the curriculum based on the NOS Assessment Areas.")
    level: str = Field(description="The difficulty level of the curriculum (e.g., beginner, intermediate, advanced)")
    prerequisites: List[str] = Field(description="Any prerequisites needed to undertake this curriculum")
    modules: List[Module] = Field(description="List upto 7 modules majorly designed on NOS Assessment Areas shared.")

    def execute(self, context: Dict):
        email       = context['email']
        name        = context['profile']['first_name'] + " " + context['profile']['last_name']
        sequence_id = context['sequence_id']
        
        if not email or not sequence_id:
            raise ValueError("Email and sequence id are required to generate a curriculum.")   
             
        discuss_stage = DiscussStage.objects.get(user__email=email, sequence_id=sequence_id)
        discuss_stage.curriculum = self.model_dump()
        logger.info(f"interest_areas: {discuss_stage.interest_areas}")
        logger.info(f"learning_style: {discuss_stage.learning_style}")
        logger.info(f"timeline: {discuss_stage.timeline}")
        discuss_stage.save()
        
        #TODO: xAPI call to update the discuss data (curriculum)

        context['discuss']['curriculum'] = self.model_dump()
        
        logger.info(f"Generated Curriculum for {email}:\n\n{str(self.model_dump())}")
        return Result(value=str(self.model_dump()), context=context)    

class update_discussion_data(StrictTool):
    """Update the discussion data after the learner has expressed their interest areas, learning style, and timeline."""
    interest_areas: str = Field(description="The learner's interest areas")
    learning_style: str = Field(description="The learner's preferred conversational learning style, for example, role-play, storytelling, or case study discussions")
    timeline: int = Field(description="The learner's timeline for completing the curriculum")
    
    def execute(self, context: Dict):
        # Get email and sequence id from context
        email       = context['email']
        sequence_id = context['sequence_id']
        if not email or not sequence_id:
            raise ValueError("Email and sequence id are required to update discussion data.")        
        
        # Get the DiscussStage object
        discuss_stage = DiscussStage.objects.get(user__email=email, sequence_id=sequence_id)
                
        discuss_stage.interest_areas  = self.interest_areas
        discuss_stage.learning_style  = self.learning_style
        discuss_stage.timeline        = self.timeline
        logger.info(f"Curriculum: {discuss_stage.curriculum}.")
        discuss_stage.save()
        
        #TODO: xAPI call to update the discuss data (interest_areas, learning_style, timeline)

        assessment_areas = TNAassessment.objects.filter(user__email=email, sequence_id=sequence_id)
        nos_areas_with_ofqual_standards = "\n\n".join([f"**NOS Assessment Area**: {i.assessment_area}\n\n**OFQUAL Standards identified based on learner's knowledge gaps for the NOS Assessment Area**: \n{i.knowledge_gaps}" for i in assessment_areas])
        
        value = f"""Discussion data updated successfully for {email}
        
**Timeline**: {self.timeline}
**Learning Style**: {self.learning_style}

**Data for Curriculum Generation**:

{nos_areas_with_ofqual_standards}"""
        
        logger.info(f"Discussion data updated successfully for {email}:\n\n{value}")

        # Update context with the current stage data
        context['discuss'] = {
            "interest_areas": self.interest_areas,
            "learning_style": self.learning_style,
            "timeline": self.timeline,
            "curriculum": discuss_stage.curriculum
        }
                
        return Result(value=value, context=context)
            
# Handoff Agent for the next stage
class transfer_to_delivery_stage(StrictTool):
    """Transfer to the Delivery stage once the Discussion stage is complete."""

    def execute(self, context: Dict):        
        logger.info(f"Transferred to the Delivery stage for {context['email']}.")
        # Get discussion data from DB
        email       = context['email']
        sequence_id = context['sequence_id']
        
        discuss_stage  = DiscussStage.objects.get(user__email=email, sequence_id=sequence_id)
        is_complete, error = discuss_stage.check_complete()
        if not is_complete:
            raise ValueError(error)
        
        discuss_data   = discuss_stage.get_summary()    
        # Get the DeliverStage object
        agent = deliver_agent
        # Create the start message for the Delivery agent
        agent.start_message = f"""        
**Discussion Data:**
{discuss_data}
        
Greet the learner and introduce the Delivery stage."""
        
        return Result(
            value="Transferred to Delivery stage.",
            agent=agent, 
            context=context
        )


discuss_agent = Agent(
    name="Discussion",
    id="discuss",
    instructions=get_agent_instructions('discuss'),
    functions=[
        Curriculum,
        update_discussion_data,
        transfer_to_delivery_stage
    ],
    parallel_tool_calls=False,
    tool_choice='auto',
    model="gpt-4o"
)
