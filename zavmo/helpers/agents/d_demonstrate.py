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
from helpers.swarm import Agent, Response, Result
from .common import get_agent_instructions
from openai import OpenAI



class Question(BaseModel):
    question: str = Field(description="The question to be answered")
    answer: str = Field(description="The answer to the question")
    explanation: str = Field(description="An explanation of the answer")
    def __str__(self):
        return f"Question: {self.question}\nExpected Answer: {self.answer}\nExplanation: {self.explanation}"
    
class Response(BaseModel):
    question: str = Field(description="The question to be answered")
    answer: str = Field(description="A summarized representation of the learner's answer")
    lesson: str = Field(description="The lesson that the question is about")
    module: str = Field(description="The module that the question is about")
    
    def __str__(self):
        return f"Question: {self.question}\nAnswer: {self.answer}\nLesson: {self.lesson}\nModule: {self.module}"
    
class Evaluations(BaseModel):
    evaluations: List[Response] = Field(description="A list of questions and answers")
    
def request_question(instructions:str, lesson:str, module:str, context:Dict):
    """Request a question and answer from an assessment specialist. Provide instructions for the assessment specialist."""
    print(f"Requesting Lesson Specialist to generate a lesson: {lesson} for module: {module}")
    openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    response = openai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[{"role": "system", "content": get_prompt('assessment')},
                 {"role": "user", "content": f"Generate a question and answer for the lesson: {lesson} and module: {module}\n\n{instructions}"}],
        response_format=Question
    )
    model_result = response.choices[0].message.parsed
    return Result(value=str(model_result), context=context)

def update_demonstration_data(context:Dict):
    """Update the demonstration data with the questions and answers."""    
    print(f"Updating demonstration data with")
    openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    # Get history of the conversation
    history = context['history']
    # Get the curriculum
    curriculum = context['stage_data']['discuss']['curriculum']
    # Summarize the history of the conversation
    summary = summarize_history(history)
    system_message = get_prompt('demonstration')
    user_message = f"Here is a history of the conversation so far: {summary}\n\nHere is the curriculum: {curriculum}\n\nSummarize the evaluations:"
    response = openai_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[{"role": "system", "content": system_message}, {"role": "user", "content": user_message}],
        response_format=Evaluations
    )
    model_result = response.choices[0].message.parsed
    context['stage_data']['demonstrate']['evaluations'] = model_result.model_dump()
    
    # Update the DemonstrateStage object
    demonstrate_stage = DemonstrateStage.objects.get(sequence=context['sequence_id'])
    demonstrate_stage.evaluations = model_result.model_dump()
    demonstrate_stage.save()    
    
    return Result(value=str(model_result), context=context)



def transfer_to_completion_agent():
    print("Transferring back to Completion Agent...")
    return None

demonstrate_agent = Agent(
    name="Demonstration",
    id="demonstrate",
    instructions=get_agent_instructions('demonstrate'),
    functions=[
        request_question,
        update_demonstration_data,
        transfer_to_completion_agent
    ],
    parallel_tool_calls=False,
    tool_choice='auto',
    model="gpt-4o",
)