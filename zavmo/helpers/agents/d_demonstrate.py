"""
# Stage 4: Demonstration

Fields:
    curriculum: Curriculum
    assessments: List[Assessment]
    overall_performance: float
    self_assessment: str
    feedback: str
"""

from pydantic import BaseModel, Field
from typing import List
from swarm import Agent, Response, Result
from .common import Lesson, get_agent_instructions
    


###### Exam Creation Schema ######

# NOTE: This can be challenging: 
#
# -  We may need separate schemas for different types of questions (e.g. multiple choice, short answer, essay) because they don't overlap 
# -  We may need separte schemas for the question and for capturing and evaluating an answer (Especially for essay questions where the answer is not known a-priori)


# class Question(BaseModel):
#     """Represents a question in an exam"""
#     question_type: Literal["multiple_choice", "short_answer"] = Field(..., description="The type of question")
#     question_text: str = Field(..., description="The text of the question")
#     options: Optional[List[str]] = Field(None, description="List of options for multiple-choice questions")
#     # NOTE: This is a bit ambiguous, as the correct answer could be one of the options, or a free-form answer.
#     correct_answer: str = Field(..., description="The correct answer to the question")

# # NOTE: We can add section-level heirarchies later. Keeping it simple for now.
# #class ExamSection(BaseModel):
#  #   title: str = Field(..., description="The title of the exam section")
#   #  questions: List[Question] = Field(..., description="List of questions in this section")

# class Exam(BaseModel):
#     exam_title: str = Field(..., description="The title of the exam")
#     questions: List[Question] = Field(..., description="List of questions in the exam")
    

class Assessment(BaseModel):
    module: str = Field(..., description="The module of the assessment")
    lesson: Lesson = Field(..., description="The lesson of the assessment")
    question: str = Field(..., description="The assessment question")
    user_response: str = Field(..., description="The user's response to the question")
    correct_response: str = Field(..., description="The correct response to the question")
    rating: float = Field(..., description="Rating of the user's response on a scale of 0 to 1")

class Question(BaseModel):
    module: str = Field(..., description="The module of the question")
    lesson: Lesson = Field(..., description="The lesson of the question")
    question: str = Field(..., description="The assessment question")
    correct_answer: str = Field(..., description="The correct answer to the question")

class UpdateDemonstrationData(BaseModel):
    assessments: List[Assessment] = Field(description="List of assessments completed by the user")
    overall_performance: float = Field(description="Overall performance rating of the user")
    self_assessment: str = Field(description="User's self-assessment of their learning")
    feedback: str = Field(description="User's feedback on the learning experience")

    def __str__(self):
        return "\n".join(f"{field.replace('_', ' ').title()}: {value}" 
                         for field, value in self.__dict__.items())

def request_question():
    print("Requesting Assessment Consultant to generate a question...")
    return assessment_consultant_agent

assessment_consultant_agent = Agent(
    name="Assessment Consultant",
    description="A specialist in creating assessment questions for learners",
    instructions=open("assets/prompts/assessment.md").read(),
    model="gpt-4o",
    functions=[Question],
    parallel_tool_calls=True,
    tool_choice='required'    
)



def transfer_back_to_demonstration_agent():
    print("Transferring back to Demonstration Agent...")
    return demonstrate_agent

completion_agent = Agent(
    name="Completion",
    description="The final agent that gives the learner a summary of the learning journey and asks for feedback",
    instructions="""
    You are a completion agent. Your job is to give the learner a summary of the learning journey and ask for feedback.
    
    Once the user provides feedback, you should update the demonstration data and transfer back to the demonstration agent.
    """,
    model="gpt-4o",
    functions=[UpdateDemonstrationData],
    parallel_tool_calls=True,
    tool_choice='auto'
)


demonstrate_agent = Agent(
    name="Demonstration",
    instructions=get_agent_instructions('demonstrate'),
    functions=[
        request_question,
    ],
    parallel_tool_calls=True,
    tool_choice='auto',
    model="gpt-4o"
)

assessment_consultant_agent.functions.append(transfer_back_to_demonstration_agent)
completion_agent.functions.append(transfer_back_to_demonstration_agent)
