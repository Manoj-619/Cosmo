from helpers.tools.common import BaseModel, Field, openai

############# required fields for discover stage ###############

required_fields = [
    'learning_goals', 
    'learning_goal_rationale', 
    'knowledge_level', 
    'application_area'
]

class GetLearningGoals(BaseModel):
    "Return the learner's learning goals"
    learning_goals: str = Field(
        description="A list of learning goals, each containing a topic and a reason."
    )

class GetLearningGoalRationale(BaseModel):
    "Return the rationale behind the learner's learning goals"
    learning_goal_rationale: str = Field(
        description="The learner's explanation of why their learning goals are important to them."
    )

class GetKnowledgeLevel(BaseModel):
    "Return the learner's self-assessed knowledge level"
    knowledge_level: int = Field(
        description="The learner's self-assessed knowledge level in their chosen area of study (1 for Beginner, 2 for Intermediate, 3 for Advanced, 4 for Expert)."
    )

class GetApplicationArea(BaseModel):
    "Return the learner's intended application area for their new knowledge"
    application_area: str = Field(
        description="The specific areas or contexts where the learner plans to apply their new knowledge and skills."
    )

############## discover tools ##############

discover_tools = [
    GetLearningGoals, 
    GetLearningGoalRationale, 
    GetKnowledgeLevel, 
    GetApplicationArea
]
tools = [openai.pydantic_function_tool(i) for i in discover_tools]
