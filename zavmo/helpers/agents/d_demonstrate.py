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
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Dict
from stage_app.models import DemonstrateStage
from helpers.chat import get_prompt, summarize_history
from helpers.swarm import Agent, Response, Result, Tool
from .common import get_agent_instructions
from openai import OpenAI
from stage_app.models import FourDSequence
# from .a_discover import discuss_agent

class Question(BaseModel):
    question: str = Field(description="The question to be answered")
    answer: str = Field(description="The answer to the question")
    explanation: str = Field(description="An explanation of the answer")
    
    def __str__(self):
        return f"Question: {self.question}\nExpected Answer: {self.answer}\nExplanation: {self.explanation}"
    
class request_question(Tool):    
    """Request a question and answer from an assessment specialist by providing instructions, lesson, and module."""
    instructions: str = Field(description="The instructions for the assessment specialist")
    lesson: str = Field(description="The lesson that the question is about")
    module: str = Field(description="The module that the question is about")
    
    def execute(self, context:Dict):
        openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = openai_client.beta.chat.completions.parse(
            
            messages=[{"role": "system", "content": get_prompt('assessment')},
                     {"role": "user", "content": f"Generate a question and answer for the lesson: {self.lesson} and module: {self.module}\n\n{self.instructions}"}],
            model="gpt-4o",
            response_format=Question
        )
        model_result = response.choices[0].message.parsed
        
        return Result(value=str(model_result), context=context)

class update_demonstration_data(Tool):
    """Update the demonstration data with the questions and answers."""    
    understanding_level: int = Field(description="The learner's self assessment of their understanding level, from 1 to 4 (Beginner, Intermediate, Advanced, Expert)")
    feedback_summary: str = Field(description="A summary of the learner's feedback on the learning journey")
    
    def execute(self, context:Dict):
        openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        # Get history of the conversation
        history = context['history']
        # Get the curriculum
        curriculum = context['stage_data']['discuss']['curriculum']
        # Summarize the history of the conversation
        summary        = summarize_history(filter_history(history,max_tokens= 84000))
        system_message = get_prompt('demonstration')
        user_message = f"Here is a history of the conversation so far: {summary}\n\nHere is the curriculum: {curriculum}\n\nSummarize the evaluations:"
        response = openai_client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_message}, {"role": "user", "content": user_message}],
            response_format=Evaluations
        )
        model_result = response.choices[0].message.parsed
        demonstrate_data = model_result.model_dump()
        demonstrate_data['understanding_level'] = self.understanding_level
        demonstrate_data['feedback_summary'] = self.feedback_summary
        
        context['stage_data']['demonstrate'] = demonstrate_data
        
        # Update the DemonstrateStage object
        demonstrate_stage = DemonstrateStage.objects.get(sequence=context['sequence_id'])
        demonstrate_stage.evaluations = demonstrate_data['evaluations']
        demonstrate_stage.understanding_level = self.understanding_level
        demonstrate_stage.feedback_summary = self.feedback_summary
        demonstrate_stage.save()    
        
        value = f"Demonstration data updated successfully for {context['email']} with sequence id {context['sequence_id']}. The following data was updated:\n\n{str(demonstrate_data)}"
        return Result(value=value, context=context)


def mark_completed(context:Dict):
    """Mark the Demonstration stage as complete so that a new 4D learning journey can be created."""
    user = context['email']
    sequence_id = context['sequence_id']
    if not user or not sequence_id:
        raise ValueError("Email and sequence id are required to mark the Demonstration stage as complete.")
    sequence = FourDSequence.objects.create(user=user, name=f"4D Sequence {sequence_id}")  
    return "New 4D Sequence created. Restart the learning journey once again."
    

demonstrate_agent = Agent(
    name="Demonstration",
    id="demonstrate",
    instructions=get_agent_instructions('demonstrate'),
    functions=[
        request_question,
        update_demonstration_data,
        mark_completed
    ],
    parallel_tool_calls=False,
    tool_choice='auto',
    model="gpt-4o",
)