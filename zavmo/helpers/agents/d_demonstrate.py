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
import json
from helpers.agents.common import get_agent_instructions, get_tna_assessment_instructions
from stage_app.models import FourDSequence, DemonstrateStage, TNAassessment, DiscoverStage
from stage_app.serializers import TNAassessmentSerializer
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
        name = context['profile']['first_name'] + " " + context['profile']['last_name']
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
        name = context['profile']['first_name'] + " " + context['profile']['last_name']
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
    """Mark the Demonstration stage as complete and transition to the next sequence."""    
    def execute(self, context: Dict):
        email = context['email']      
        if not email:
            raise ValueError("Email is required to mark the Demonstration stage as complete.")        
        
        current_sequence_id = context['sequence_id']
        user = User.objects.get(email=email)
        try:
            demonstrate_agent.id = "completed"  ## Important

            try:    
                sequences = FourDSequence.objects.filter(user=user).order_by('created_at')
                if sequences.exists():
                    return Result(
                            value=f"Completed sequence {current_sequence_id}, starting new sequence to continue with next NOS assessment areas. Greet the learner and inform about the completion of current FourD Sequence and the beginning of the next FourD Sequence with TNA Assessment step.",
                            context=context
                        )
            except Exception as e:
                logger.error(f"Error in sequence transition: {str(e)}")
                sequence = FourDSequence.objects.create(user=user)        
                value = f"4D Sequence {sequence.id} marked as completed. New 4D learning journey created."
                return Result(value=value, context=context)
      
        except Exception as e:
            logger.error(f"Error in sequence transition: {str(e)}")
            raise ValueError(f"Failed to transition to next FourD Sequence: {str(e)}")

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
