"""
# Stage 4: Demonstration

Fields:
    curriculum: Curriculum
    assessments: List[Assessment]
    overall_performance: float
    self_assessment: str
    feedback: str
"""
from pydantic import Field
from typing import Dict
from helpers._types import (
    Agent,
    StrictTool,
    Result,
)
from helpers.agents.common import get_agent_instructions
from stage_app.models import FourDSequence, DemonstrateStage
from django.contrib.auth.models import User
from helpers.utils import get_logger

logger = get_logger(__name__)

class question(StrictTool):
    """Use this tool to generate a single set of question, answer, and explanation for an assessment."""
    curriculum_module: str = Field(description="The name of the module that the question is about")
    question: str         = Field(description="The question to be answered")
    expected_answer: str = Field(description="A concise explanation of what the learner should say")

    def execute(self, context: Dict):
        """Generate a question set for an assessment."""        
        logger.info(f"Generating question set for module: {self.curriculum_module}")
        logger.info(f"Question: {self.question}")
        logger.info(f"Expected answer: {self.expected_answer}")
        
        return Result(value=self.model_dump_json(), context=context)
    
class evaluate_answer(StrictTool):
    """Use this tool after the learner has answered a question. An evaluation of the learner's answer to a question."""
    
    question: str   = Field(description="The question that was asked")
    answer: str     = Field(description="A concise summary of the learner's answer to the question")
    evaluation: str = Field(description="Whether the answer is correct or incorrect, and a brief explanation of why")
    
    def execute(self, context: Dict):        
        logger.info(f"Evaluating learner's answer to question: {self.question}")        
        email = context['email']
        sequence_id = context['sequence_id']
                
        evaluation         = self.model_dump()
        # Retrieve DemonstrateStage object
        demonstrate_object = DemonstrateStage.objects.get(user__email=email, sequence_id=sequence_id)        
        # Update evaluations in the DemonstrateStage object and save
        demonstrate_object.evaluations.append(evaluation)
        demonstrate_object.save()
        
        return Result(value=str(evaluation), context=context)


class update_self_assessment_and_feedback(StrictTool):
    """Use this tool after the learner has completed all assessments, and you have received their self-assessment and feedback."""
    understanding_level: int = Field(description="The learner's self assessment of their understanding level, from 1 to 4 (Beginner, Intermediate, Advanced, Expert)")
    feedback_summary: str = Field(description="A summary of the learner's feedback on the learning journey")
    
    def execute(self, context: Dict):
        logger.info(f"Updating demonstration data for {context['email']}.")
        
        email = context['email']
        sequence_id = context['sequence_id']
        
        # Update the DemonstrateStage object
        demonstrate_stage = DemonstrateStage.objects.get(
            user__email=email, 
            sequence_id=sequence_id
        )
        # If no evaluations are in the demonstrate_stage object, raise an error
        evaluations = demonstrate_stage.evaluations
        if not evaluations:
            raise ValueError("No evaluations found in demonstrate stage data.")
        
        demonstrate_stage.understanding_level = self.understanding_level
        demonstrate_stage.feedback_summary    = self.feedback_summary
        demonstrate_stage.save()
        
        return Result(value="Demonstration data updated successfully", context=context)
    

class mark_completed(StrictTool):
    """Mark the Demonstration stage as complete so that a new 4D learning journey can be created."""
    
    def execute(self, context: Dict):
        email = context['email']
        
        if not email:
            raise ValueError("Email is required to mark the Demonstration stage as complete.")
        
        # Retrieve user and create a new 4D Sequence
        user     = User.objects.get(email=email)
        sequence = FourDSequence.objects.create(user=user)
        
        value = f"4D Sequence {sequence.id} marked as completed. New 4D learning journey created."
        return Result(value=value, context=context)

demonstrate_agent = Agent(
    name="Demonstration",
    id="demonstrate",
    instructions=get_agent_instructions('demonstrate'),
    functions=[
        question,
        evaluate_answer,
        update_self_assessment_and_feedback,
        mark_completed
    ],
    parallel_tool_calls=False,
    tool_choice='auto',
    model="gpt-4o",
)
