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

def get_tna_assessment_agent():

    from helpers.agents.tna_assessment import tna_assessment_agent
    return tna_assessment_agent

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
        
        try:
            # Get current sequence and user
            current_sequence = FourDSequence.objects.select_related('user').get(id=current_sequence_id)
            user = current_sequence.user
            
            # Mark current sequence as completed
            if current_sequence.current_stage != FourDSequence.Stage.COMPLETED:
                current_sequence.current_stage = FourDSequence.Stage.COMPLETED
                current_sequence.save()
                logger.info(f"Marked sequence {current_sequence_id} as completed")
            
            # Find next incomplete sequence
            next_sequence = FourDSequence.objects.filter(
                user=user,
                current_stage__lt=FourDSequence.Stage.COMPLETED
            ).order_by('created_at').first()
            
            if not next_sequence:
                logger.info(f"No more sequences to process for user {email}")
                return Result(
                    value="All sequences completed successfully.",
                    context=context
                )
            
            # Get assessments for the next sequence
            assessments = TNAassessment.objects.filter(
                user=user,
                sequence=next_sequence
            ).order_by('created_at')
            
            if not assessments.exists():
                logger.warning(f"No assessments found for sequence {next_sequence.id}")
                return Result(
                    value=f"No assessments found for next sequence {next_sequence.id}",
                    context=context
                )
            
            # Update context with new sequence information
            context['sequence_id'] = str(next_sequence.id)
            context['previous_sequence_id'] = str(current_sequence_id)
            
            # Update context with assessment information
            context['tna_assessment'] = {
                'total_assessments': assessments.count(),
                'current_assessment': 1,
                'assessments': json.dumps([
                    TNAassessmentSerializer(assessment).data 
                    for assessment in assessments
                ])
            }
            
            # Set up TNA Assessment Agent
            agent = get_tna_assessment_agent()
            assessment_areas = [
                (assessment.assessment_area, assessment.nos_id) 
                for assessment in assessments
            ]
            
            # Format assessment areas table
            areas_table = "\n".join([
                f"|            {area}                |   {nos_id}  |" 
                for area, nos_id in assessment_areas
            ])
            
            agent.start_message = (
                f"Welcome back! Starting new sequence {next_sequence.id} with TNA Assessment.\n\n"
                f"Total NOS Areas: {len(assessment_areas)}\n"
                "NOS Assessment Areas:\n"
                "|  **Assessments For Training Needs Analysis**  |   **NOS ID**  |\n"
                "|-----------------------------------------------|---------------|\n"
                f"{areas_table}\n"
                "\nLet's begin with the first assessment area."
            )
            
            agent.instructions = get_tna_assessment_instructions(context, level="")
            
            logger.info(f"Successfully transitioned to sequence {next_sequence.id}")
            return Result(
                value=f"Starting new sequence {next_sequence.id} with {len(assessment_areas)} assessment areas",
                context=context,
                agent=agent
            )
                
        except Exception as e:
            logger.error(f"Error in sequence transition: {str(e)}")
            raise ValueError(f"Failed to transition to next sequence: {str(e)}")

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
