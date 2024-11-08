"""
# Stage 4: Demonstration

Fields:
    curriculum: Curriculum
    assessments: List[Assessment]
    overall_performance: float
    self_assessment: str
    feedback: str
"""
import os
from pydantic import BaseModel, Field
from typing import List, Dict
from helpers.chat import filter_history, summarize_history, get_prompt
from stage_app.models import DemonstrateStage
from helpers._types import (
    Agent,
    StrictTool,
    PermissiveTool,
    Result,
    Response,
    AgentFunction,
    function_to_json,
)
from .common import get_agent_instructions
from stage_app.models import FourDSequence
from django.contrib.auth.models import User
from helpers.utils import get_logger

logger = get_logger(__name__)

class Question(StrictTool):
    """
    Use this tool to get a single set of question, answer, and explanation for an assessment.
    """
    question: str = Field(description="The question to be answered")
    expected_answer: str = Field(description="A concise explanation of what the learner should say")

    def execute(self, context: Dict):
        question = self.model_dump()
        if 'questions' in context['stage_data']['demonstrate']:
            context['stage_data']['demonstrate']['questions'].append(question)
        else:
            context['stage_data']['demonstrate']['questions'] = [question]
        return Result(value=str(self.model_dump()), context=context)


class Evaluation(StrictTool):
    """An evaluation of the learner's answer to a question."""
    question: str = Field(description="The question that was asked")
    answer: str = Field(description="A concise summary of the learner's answer to the question")
    evaluation: str = Field(description="Whether the answer is correct or incorrect, and a brief explanation of why")
    
    def execute(self, context: Dict):        
        logger.info(f"Evaluating learner's answer to question: {self.question}")
        email = context['email']
        sequence_id = context['sequence_id']
        evaluation  = self.model_dump()
        if not email or not sequence_id:
            raise ValueError("Email and sequence id are required to update demonstration data.")
        demonstrate_object = DemonstrateStage.objects.get(
            user__email=email, 
            sequence_id=sequence_id
        )
        demonstrate_context = context['stage_data']['demonstrate']
        if 'evaluations' not in demonstrate_context:
            demonstrate_context['evaluations'] = []
        
        demonstrate_context['evaluations'].append(evaluation)
        demonstrate_object.evaluations = demonstrate_context['evaluations']
        demonstrate_object.save()
        
        return Result(value=str(evaluation), context=context)
    
class UpdateDemonstrationData(StrictTool):
    """Use this tool after the learner has completed all assessments, and you have received their self-assessment and feedback."""
    understanding_level: int = Field(description="The learner's self assessment of their understanding level, from 1 to 4 (Beginner, Intermediate, Advanced, Expert)")
    feedback_summary: str = Field(description="A summary of the learner's feedback on the learning journey")
    
    def execute(self, context:Dict):
        logger.info(f"Updating demonstration data for {context['email']}.")
        email = context['email']
        sequence_id = context['sequence_id']

        if not email or not sequence_id:
            raise ValueError("Email and sequence id are required to update demonstration data.")
        
        demonstrate_data = context['stage_data']['demonstrate']
        demonstrate_data['understanding_level'] = self.understanding_level
        demonstrate_data['feedback_summary']    = self.feedback_summary        
        context['stage_data']['demonstrate']    = demonstrate_data
        # Update the DemonstrateStage object
        demonstrate_stage = DemonstrateStage.objects.get(
            user__email=email, 
            sequence_id=sequence_id
        )
        demonstrate_stage.evaluations = demonstrate_data['evaluations']
        demonstrate_stage.understanding_levels = self.understanding_level
        demonstrate_stage.feedback_summary = self.feedback_summary
        demonstrate_stage.save()    
        
        value = f"Demonstration data updated successfully"
        return Result(value=value, context=context)


class MarkCompleted(StrictTool):
    """Mark the Demonstration stage as complete so that a new 4D learning journey can be created."""
    
    def execute(self, context:Dict):
        email = context['email']
        if not email:
            raise ValueError("Email is required to mark the Demonstration stage as complete.")
        
        # Get the user first, then create sequence
        user = User.objects.get(email=email)
        sequence = FourDSequence.objects.create(user=user)  # Fix: use user=user instead of user__email
        
        value = f"4D Sequence {sequence.id} marked as completed. New 4D learning journey created."
        return Result(value=value, context=context)
    

demonstrate_agent = Agent(
    name="Demonstration",
    id="demonstrate",
    instructions=get_agent_instructions('demonstrate'),
    functions=[
        Question,
        Evaluation,
        UpdateDemonstrationData,
        MarkCompleted
    ],
    parallel_tool_calls=False,
    tool_choice='auto',
    model="gpt-4o",
)
