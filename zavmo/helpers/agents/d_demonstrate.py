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
from openai import OpenAI
from stage_app.models import FourDSequence
from django.contrib.auth.models import User
# from .a_discover import discuss_agent

class Question(StrictTool):
    question: str = Field(description="The question to be answered")
    answer: str = Field(description="The answer to the question")
    explanation: str = Field(description="An explanation of the answer")
    
    def __str__(self):
        return f"Question: {self.question}\nExpected Answer: {self.answer}\nExplanation: {self.explanation}"
    
    def execute(self, context: Dict):
        question = self.model_dump()
        if 'questions' in context['stage_data']['demonstrate']:
            context['stage_data']['demonstrate']['questions'].append(question)
        else:
            context['stage_data']['demonstrate']['questions'] = [question]
        return Result(value=str(self), context=context)
'''
# class request_question(StrictTool):    
#     """Request a question and answer from an assessment specialist by providing instructions, lesson, and module."""
#     instructions: str = Field(description="The instructions for the assessment specialist")
#     lesson: str = Field(description="The lesson that the question is about")
#     module: str = Field(description="The module that the question is about")
    
#     def execute(self, context:Dict):
#         openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
#         response = openai_client.beta.chat.completions.parse(
            
#             messages=[{"role": "system", "content": get_prompt('assessment')},
#                      {"role": "user", "content": f"Generate a question and answer for the lesson: {self.lesson} and module: {self.module}\n\n{self.instructions}"}],
#             model="gpt-4o",
#             response_format=Question
#         )
#         model_result = response.choices[0].message.parsed
        
#         return Result(value=str(model_result), context=context)
'''
class Evaluation(StrictTool):
    """An evaluation of the learner's answer to a question."""
    question: str = Field(description="The question that was asked")
    answer: str = Field(description="A concise summary of the learner's answer to the question")
    evaluation: str = Field(description="An brief evaluation of the learner's answer to the question")
    
    def execute(self, context: Dict):
        evaluation = self.model_dump()
        if 'evaluations' in context['stage_data']['demonstrate']:
            context['stage_data']['demonstrate']['evaluations'].append(evaluation)
        else:
            context['stage_data']['demonstrate']['evaluations'] = [evaluation]
        return Result(value=str(self), context=context)
    
class UpdateDemonstrationData(StrictTool):
    """Ask the learner to assess their understanding level and provide feedback on the learning journey."""
    understanding_level: int = Field(description="The learner's self assessment of their understanding level, from 1 to 4 (Beginner, Intermediate, Advanced, Expert)")
    feedback_summary: str = Field(description="A summary of the learner's feedback on the learning journey")
    
    def execute(self, context:Dict):
        email = context['email']
        sequence_id = context['sequence_id']

        if not email or not sequence_id:
            raise ValueError("Email and sequence id are required to update demonstration data.")
        
        demonstrate_data = context['stage_data']['demonstrate']
        demonstrate_data['understanding_level'] = self.understanding_level
        demonstrate_data['feedback_summary']    = self.feedback_summary        
        context['stage_data']['demonstrate']    = demonstrate_data
        # Update the DemonstrateStage object
        demonstrate_stage = DemonstrateStage.objects.get(user__email=email, sequence__id=sequence_id)
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
