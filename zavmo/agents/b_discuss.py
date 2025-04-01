"""
# Stage 2: Discussion
Fields:
    
    learning_style: str
    curriculum: dict
    timeline: str
"""
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.settings import ModelSettings
from typing import List, Dict, Literal, Optional
from helpers.utils import get_logger
from stage_app.models import DiscussStage, UserProfile, TNAassessment, DiscoverStag, FourDSequence
from helpers.agents.common import get_agent_instructions
from stage_app.tasks import xAPI_discuss_celery_task,xAPI_stage_celery_task
# from helpers.agents.c_deliver import deliver_agent

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
    title: str = Field(description="The title of the module. It can be an Assessment Area or OFQUAL Unit")
    learning_outcomes: List[str] = Field(description="List upto 5 learning outcomes.")
    lessons: List[str] = Field(description="List of lessons in this module based on the learning outcomes.")
    duration: int = Field(description="The total duration of the module in hours")

class Curriculum(BaseModel):
    """Generate a detailed curriculum for the learner based on the Assessment Areas and corresponding OFQUAL Units shared."""
    title: str = Field(description="The title of the curriculum")
    subject: str = Field(description="The main subject area of the curriculum.")
    level: str = Field(description="The difficulty level of the curriculum (e.g., beginner, intermediate, advanced)")
    prerequisites: List[str] = Field(description="Any prerequisites needed to undertake this curriculum")
    modules: List[Module] = Field(description="List upto 10 or more modules majorly designed on Assessment Areas and OFQUAL Units data shared. Include 1-2 modules on learner's interest areas as well.")


def generate_curriculum(ctx: RunContext, data: Curriculum):
    """Generate a detailed curriculum for the learner based on the Assessment Areas and corresponding OFQUAL Units shared."""
    email       = ctx.get('email')
    name        = ctx['profile']['first_name'] + " " + ctx['profile']['last_name']
    sequence_id = ctx.get('sequence_id')
    
    if not email or not sequence_id:
        raise ValueError("Email and sequence id are required to generate a curriculum.")   
    
    discuss_stage = DiscussStage.objects.get(user__email=email, sequence_id=sequence_id)
    discuss_stage.curriculum = data.model_dump()
    discuss_stage.save()
    
        
    logger.info(f"Curriculum: {discuss_stage.curriculum}.")
    xAPI_discuss_celery_task.apply_async(args=[json.loads(data.model_dump_json()),discuss_stage.learning_style,discuss_stage.interest_areas,discuss_stage.timeline,email,name])
        
    logger.info(f"Generated Curriculum for {email}:\n\n{str(data.model_dump())}")
    return f"Successfully generated Curriculum for {email}.\n\n{str(data.model_dump())}"


class DiscussionData(BaseModel):
    interest_areas: str = Field(description="The learner's interest areas")
    learning_style: str = Field(description="The learner's preferred conversational learning style, for example, role-play, storytelling, or case study discussions")
    timeline: int = Field(description="The learner's timeline for completing the curriculum")


def update_discussion_data(ctx: RunContext, data: DiscussionData):
    """Update the discussion data after the learner has expressed their interest areas, learning style, and timeline."""
    email       = ctx.get('email')
    name        = ctx['profile']['first_name'] + " " + ctx['profile']['last_name']
    sequence_id = ctx.get('sequence_id')
    
    if not email or not sequence_id:
        raise ValueError("Email and sequence id are required to update discussion data.")        
    
    discuss_stage = DiscussStage.objects.get(user__email=email, sequence_id=sequence_id)
                
    discuss_stage.interest_areas  = data.interest_areas
    discuss_stage.learning_style  = data.learning_style
    discuss_stage.timeline        = data.timeline
    discuss_stage.save()
                
    logger.info(f"Curriculum: {discuss_stage.curriculum}.")
        
    assessment_areas = TNAassessment.objects.filter(user__email=email, sequence_id=sequence_id)
    tna_assessment_data = ""
    for assessment_item in assessment_areas:
        tna_assessment_data += f"**Assessment Area:** {assessment_item.assessment_area}\n**Learner's Report:** {assessment_item.evidence_of_assessment}\n**Gaps Determined:** {assessment_item.knowledge_gaps}\n\n"

        ofqual_units = "\n\n".join([f"**OFQUAL ID: {ofqual.ofqual_id} (Unit: {ofqual.ofqual_unit_id}):**\n{ofqual.ofqual_unit_data}" for ofqual in assessment_areas])
       
    value = f"""Discussion data updated successfully for {email}
        
**Timeline**: {data.timeline}
**Learning Style**: {data.learning_style}

The following data sources are being used to inform the personalized curriculum design:
1. All TNA Assessment Data
2. All OFQUAL Units Data


- **All TNA Assessment Data provided below must be used for Curriculum Generation**:

{tna_assessment_data}

- **All OFQUAL Units Data provided below must be used for Curriculum Generation**:

{ofqual_units}
        """
        
    logger.info(f"Discussion data updated successfully for {email}:\n\n{value}")

    # Update context with the current stage data
    # NOTE: Again, do we need this?
    # context['discuss'] = {
    #     "interest_areas": data.interest_areas,
    #     "learning_style": data.learning_style,
    #     "timeline": data.timeline,
    #     "curriculum": discuss_stage.curriculum
    #     }
                
    return value
            
# Handoff Agent for the next stage
# class transfer_to_delivery_stage(StrictTool):
#     """Transfer to the Delivery stage once the Discussion stage is complete."""

#     def execute(self, context: Dict):        
#         logger.info(f"Transferred to the Delivery stage for {context['email']}.")
#         # Get discussion data from DB
#         email       = context['email']
#         name        = context['profile']['first_name'] + " " + context['profile']['last_name']
#         sequence_id = context['sequence_id']
        
#         discuss_stage  = DiscussStage.objects.get(user__email=email, sequence_id=sequence_id)
#         is_complete, error = discuss_stage.check_complete()
#         if not is_complete:
#             raise ValueError(error)
        
#         discuss_data   = discuss_stage.get_summary()    
#         # Get the DeliverStage object
#         agent = deliver_agent
#         xAPI_stage_celery_task.apply_async(args=[agent.id, email, name])
#         # Create the start message for the Delivery agent
#         agent.start_message = f"""        
# **Discussion Data:**
# {discuss_data}
        
# Greet the learner and introduce the Delivery stage."""
        
#         return Result(
#             value="Transferred to Delivery stage.",
#             agent=agent, 
#             context=context
#         )


class Deps(BaseModel):
    email: str

class transfer_to_deliver_step(BaseModel):
    """After the learner has completed the Discuss stage, transfer to the Deliver step."""
    
    async def execute(self, ctx: RunContext[Deps]):
        """Transfer the learner to the Deliver stage"""
        email = ctx.deps.email
        profile = UserProfile.objects.get(user__email=email)
        name = profile.first_name + " " + profile.last_name
        
        # Update the current sequence to Deliver stage
        sequences = FourDSequence.objects.filter(
            user=profile.user, 
            current_stage=FourDSequence.Stage.DISCUSS
        ).order_by('created_at')
        
        if not sequences:
            raise ValueError("No active Discuss stage sequence found.")
        
        current_sequence = sequences.first()
        current_sequence.current_stage = FourDSequence.Stage.DELIVER
        current_sequence.save()
        
        xAPI_stage_celery_task.apply_async(args=["deliver_agent", email, name])
        return "Transferred to Deliver step."

class update_discuss_data(BaseModel):
    """Update the discussion data for the current sequence."""
    discussion_notes: str = Field(description="Notes from the discussion with the learner.")
    action_items: str = Field(description="Action items identified during the discussion.")
    
    async def execute(self, ctx: RunContext[Deps]):
        email = ctx.deps.email
        profile = UserProfile.objects.get(user__email=email)
        
        sequence = FourDSequence.objects.filter(
            user=profile.user,
            current_stage=FourDSequence.Stage.DISCUSS
        ).order_by('created_at').first()
        
        if not sequence:
            raise ValueError("No active Discuss stage sequence found.")
        
        sequence.discussion_notes = self.discussion_notes
        sequence.action_items = self.action_items
        sequence.save()
        
        return "Discussion data updated successfully."

discuss_agent = Agent(
    model="openai:gpt-4o",
    system_prompt=get_agent_instructions('discuss'),
    tools=[
        Tool(transfer_to_deliver_step, takes_ctx=True),
        Tool(update_discuss_data, takes_ctx=True)
    ],
    instrument=True,
    model_settings=ModelSettings(
        tool_choice='auto',
        parallel_tool_calls=False
    ),
    retries=3
)
