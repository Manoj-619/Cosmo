"""
# Stage 3: Delivery

Fields:
    curriculum: Curriculum
    current_module: str
    current_lesson: str
"""

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Dict
from helpers._types import (
    Agent,
    StrictTool,
    Result,
)
from helpers.utils import get_logger
from .common import get_agent_instructions
from .d_demonstrate import demonstrate_agent
from stage_app.models import DeliverStage, DiscussStage


load_dotenv()

logger = get_logger(__name__)


class TransferToDemonstrationStage(StrictTool):
    """Once all lessons have been delivered, and the DeliverStage is updated, transfer to the Demonstration stage."""
    is_complete: bool = Field(description="Whether all lessons have been delivered and the DeliverStage is updated.")
    
    def execute(self, context: Dict):
        # Get email and sequence id from context
        email       = context['email']
        sequence_id = context['sequence_id']
        
        if not email or not sequence_id:
            raise ValueError("Email and sequence id are required to transfer to the Demonstration stage.")
        
        # Get the DeliverStage object
        deliver_stage             = DeliverStage.objects.get(user__email=email, sequence_id=sequence_id)
        deliver_stage.is_complete = self.is_complete
        deliver_stage.save()        
        
        agent = demonstrate_agent
        
        # Create the start message for the Demonstration agent
        agent.start_message = f"""
        **Deliver Stage Summary:**
        {deliver_stage.get_summary()}
        
        Greet the learner and introduce the Demonstration stage.
        """
        
        return Result(
            value="Transferred to Demonstration stage.",
            agent=demonstrate_agent, 
            context=context
        )

        

class Lesson(StrictTool):
    """Generate a lesson for a module to be delivered to the learner."""
    module: str  = Field(description="The module that the lesson belongs to")
    learning_objective: str = Field(description="The learning objective of the lesson")
    title: str   = Field(description="The title of the lesson")
    lesson: str  = Field(description="A concise summary of the lesson")
        
    def __str__(self):
        return f"Module: {self.module}\nLearning Objective: {self.learning_objective}\nTitle: {self.title}\nLesson: {self.lesson}"
    
    def execute(self, context: Dict):
        # Get email and sequence id from context
        email       = context['email']
        sequence_id = context['sequence_id']
        
        # Get curriculum from previous stage
        curriculum = DiscussStage.objects.get(user__email=email, sequence_id=sequence_id).curriculum
        
        new_lesson           = self.model_dump()
        
        # TODO: Revaluate if this is needed
        deliver_stage = DeliverStage.objects.get(
            user__email=email, 
            sequence_id=sequence_id
        )
        previous_lessons = deliver_stage.lessons
        deliver_stage.lessons.append(new_lesson)
        deliver_stage.save()
        
        value = f"""Curriculum:
        {curriculum}
        
        **Previous Lessons:**
        {previous_lessons}
        
        **New Lesson Generated:**
        {new_lesson}
        """
        return Result(value=value, context=context)


    

deliver_agent = Agent(
    name="Delivery",
    id="deliver",
    instructions=get_agent_instructions('deliver'),
    functions=[
        Lesson,
        TransferToDemonstrationStage
    ],
    parallel_tool_calls=False,
    tool_choice='auto',
    model="gpt-4o"
)