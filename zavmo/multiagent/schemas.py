"""
Schemas for functions/tools in the agent framework.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

###### Curriculum Schema ######

class LearningOutcome(BaseModel):
    description: str = Field(..., description="Description of the learning outcome")
    assessment_criteria: List[str] = Field(..., description="List of assessment criteria for the learning outcome")

class Lesson(BaseModel):
    title: str = Field(..., description="Title of the lesson")
    content: str = Field(..., description="A description of the lesson content")
    duration: int = Field(..., description="Number of hours to complete the lesson")


class Module(BaseModel):
    title: str = Field(..., description="Title of the module")
    learning_outcomes: List[LearningOutcome] = Field(..., description="List of learning outcomes for the module")
    lessons: List[Lesson] = Field(..., description="List of lessons in the module")
    duration: int = Field(..., description="Duration of the module in hours")


class Curriculum(BaseModel):
    """Represents a complete curriculum structure"""
    title: str = Field(..., description="The title of the curriculum")
    subject: str = Field(..., description="The main subject area of the curriculum")
    level: str = Field(..., description="The difficulty level of the curriculum")
    modules: List[Module] = Field(..., description="List of modules in the curriculum")
    prerequisites: List[str] = Field(..., description="List of prerequisites for the curriculum")
    qualification_level: int = Field(..., description="The qualification level of the curriculum")
    guided_learning_hours: int = Field(..., description="The number of guided learning hours")
    total_qualification_time: int = Field(..., description="The total qualification time")
    assessment_methods: List[str] = Field(..., description="List of assessment methods used in the curriculum")


###### Exam Creation Schema ######

# NOTE: This can be challenging: 
#
# -  We may need separate schemas for different types of questions (e.g. multiple choice, short answer, essay) because they don't overlap 
# -  We may need separte schemas for the question and for capturing and evaluating an answer (Especially for essay questions where the answer is not known a-priori)


class Question(BaseModel):
    """Represents a question in an exam"""
    question_type: Literal["multiple_choice", "short_answer"] = Field(..., description="The type of question")
    question_text: str = Field(..., description="The text of the question")
    options: Optional[List[str]] = Field(None, description="List of options for multiple-choice questions")
    # NOTE: This is a bit ambiguous, as the correct answer could be one of the options, or a free-form answer.
    correct_answer: str = Field(..., description="The correct answer to the question")

# NOTE: We can add section-level heirarchies later. Keeping it simple for now.
#class ExamSection(BaseModel):
 #   title: str = Field(..., description="The title of the exam section")
  #  questions: List[Question] = Field(..., description="List of questions in this section")

class Exam(BaseModel):
    exam_title: str = Field(..., description="The title of the exam")
    questions: List[Question] = Field(..., description="List of questions in the exam")
    