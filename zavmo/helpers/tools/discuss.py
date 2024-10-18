from helpers.tools.common import BaseModel, Field, openai,List

############# required fields for discuss stage ###############
required_fields = [
    'interest_areas', 
    'learning_style', 
    'curriculum', 
    'timeline', 
    'goals_alignment'
]

############## Subject and Modules Classes ##############

# class Module(BaseModel):
#     "A specific module or topic within a subject"
#     module_name: str = Field(
#         description="The name of the module or topic, e.g., 'Data Visualization' or 'Confidence Building'."
#     )

class Subject(BaseModel):
    "A subject within the curriculum, consisting of modules and estimated duration"
    subject_name: str = Field(
        description="The name of the subject area, e.g., 'Data Science' or 'Public Speaking'."
    )
    modules: List[str] = Field(
        description="A list of modules under this subject."
    )
    duration: str = Field(
        description="Estimated duration to complete this subject, e.g., '2 weeks', '3 hours'."
    )

############## Curriculum Class ##############

class GetCurriculum(BaseModel):
    "Return the learner's proposed curriculum"
    curriculum: List[Subject] = Field(
        description="""
        A list of subjects, each containing:
        - 'subject_name': The main subject area for the curriculum.
        - 'modules': A list of modules under that subject.
        - 'duration': Estimated time to complete the subject.
        """,
        example=[
            {
                "subject_name": "Data Science",
                "modules": ["Introduction to Python", "Data Visualization"],
                "duration": "4 weeks"
            },
            {
                "subject_name": "Public Speaking",
                "modules": ["Presentation Skills", "Confidence Building"],
                "duration": "2 weeks"
            }
        ]
    )

############# Other Discuss Tools ##############

class GetInterestAreas(BaseModel):
    "Return the learner's specific areas of interest"
    interest_areas: str = Field(
        description="Specific areas of interest the learner wants to focus on."
    )

class GetLearningStyle(BaseModel):
    "Return the learner's preferred learning style"
    learning_style: str = Field(
        description="The preferred learning style of the learner (e.g., visual, auditory, kinesthetic)."
    )

class GetTimeline(BaseModel):
    "Return the learner's proposed timeline"
    timeline: str = Field(
        description="Propose a timeline for completing the learning plan."
    )

class GetGoalsAlignment(BaseModel):
    "Return confirmation of alignment between the learner's goals and the proposed plan"
    goals_alignment: str = Field(
        description="Confirmation that the proposed plan aligns with the learner's goals."
    )

############## discuss tools ##############

discuss_tools = [
    GetInterestAreas, 
    GetLearningStyle, 
    GetCurriculum, 
    GetTimeline, 
    GetGoalsAlignment
]

tools = [openai.pydantic_function_tool(i) for i in discuss_tools]
