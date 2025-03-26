"""
# Stage 1: Discovery
Fields:
    learning_goals: str
    learning_goal_rationale: str
    knowledge_level: int
    application_area: str
"""

from pydantic import Field, BaseModel
from typing import Dict
from stage_app.models import DiscoverStage, UserProfile, TNAassessment, FourDSequence
from stage_app.serializers import TNAassessmentSerializer
from agents.utils import get_agent_instructions
from helpers.utils import get_logger
from stage_app.tasks import xAPI_discover_celery_task, xAPI_stage_celery_task
from pydantic_ai import Agent, RunContext, Tool
import json

logger = get_logger(__name__)

### For handoff

# class transfer_to_tna_assessment_step(StrictTool):
#     """After the learner has completed the Discover stage, transfer to the TNA Assessment step."""
    
#     def execute(self, context: Dict):
#         """After the learner has completed the Discover stage, transfer to the TNA Assessment step"""
#         email = context['email']
#         name = context['profile']['first_name'] + " " + context['profile']['last_name']
#         discover_stage = DiscoverStage.objects.get(user__email=context['email'], sequence=context['sequence_id'])
#         discover_is_complete, error = discover_stage.check_complete()
#         if not discover_is_complete:

#             raise ValueError(f"Use the `update_discover_data` tool to update the discovery data if details are already shared, before proceeding to TNA Assessment step or ask the learner to share the details about the required item.\n\n{error}")
        
#         all_assessments = context['tna_assessment']['total_nos_areas']
#         assessments = TNAassessment.objects.filter(sequence_id=context['sequence_id'])
#         assessment_areas = [(assessment.assessment_area, assessment.nos_id) for assessment in assessments]
#         agent = get_tna_assessment_agent()
#         xAPI_stage_celery_task.apply_async(args=[agent.id, email, name])

#         current_assessment_areas = '\n-'.join([f"Assessment Area: {area} (NOS ID: {nos_id})" for area, nos_id in assessment_areas])
        
#         # Format the message with proper error handling
#         agent.start_message = (
#             "Greet and introduce the TNA Assessment step, based on instructions and example shared on Introduction.\n"
#             f"Total NOS Areas: {all_assessments}\n"
#             f"Current Number Of Assessment Areas: {len(assessment_areas)}\n"
#             "NOS Assessment Areas for current 4D Sequence to be presented:"
#             f"\n-{current_assessment_areas}\n\n"
#             "Present the NOS Assessment Areas for current 4D Sequence in the below shared table form.\n\n"
#             "Presenting NOS Areas:"
#             + "\n"
#             "|  **Assessments For Training Needs Analysis**  |   **NOS ID**  |\n"
#             "|-----------------------------------------------|---------------|\n"
#             "|            [Assessment Area 1]                |   [NOS ID 1]  |\n"
#             "|            [Assessment Area 2]                |   [NOS ID 2]  |\n"
#             "|            [Assessment Area 3]                |   [NOS ID 3]  |\n"
#             "Then start the TNA assessment on Current NOS Area."
#         )

#         agent.instructions = get_tna_assessment_instructions(context, level="")
        
#         # Update context with proper integer values
#         context['tna_assessment'] = {
#             'current_assessment_areas': len(assessments),
#             'total_assessment_areas': all_assessments,
#             'assessments': [TNAassessmentSerializer(assessment).data for assessment in assessments]
#         }
        
#         return Result(value="Transferred to TNA Assessment step.",
#             agent=agent, 
#             context=context)



### For updating the data
class DiscoverData(BaseModel):
    learning_goals: str = Field(description="The learner's learning goals.")
    learning_goal_rationale: str = Field(description="The learner's rationale for their learning goals.")
    knowledge_level: int = Field(description="The learner's self-assessed knowledge level in their chosen area of study. 1=Beginner, 2=Intermediate, 3=Advanced, 4=Expert")
    application_area: str = Field(description="A specific area or context where the learner plans to apply their new knowledge and skills.")

def update_discover_data(ctx: RunContext, data: DiscoverData):
    """Update the learner's information gathered during the Discovery stage."""
    
    # Get email and sequence_id from context
    email       = ctx.get('email')
    name        = ctx['profile']['first_name'] + " " + ctx['profile']['last_name']
    sequence_id = ctx.get('sequence_id')
    
    if not email or not sequence_id:
        raise ValueError("Email and sequence ID are required to update discovery data.")        
    # Attempt to get the DiscoverStage object
    
    discover_stage = DiscoverStage.objects.get(user__email=email, sequence_id=sequence_id)
    discover_stage.learning_goals = data.learning_goals
    discover_stage.learning_goal_rationale = data.learning_goal_rationale
    discover_stage.knowledge_level = data.knowledge_level
    discover_stage.application_area = data.application_area
    discover_stage.save() 

    xAPI_discover_celery_task.apply_async(args=[json.loads(data.model_dump_json()),email,name])

    # ctx['discover'] = data.model_dump() # JSON dump of pydantic model # NOTE: Do we need this?
    logger.info(f"Updated Discover stage Data for {email}. The following data was updated:\n\n{str(data)}")
    
    return f"Successfully updated Discover stage Data for {email}."
            
            
                        
discover_agent = Agent(
    model="openai:gpt-4o",
    system_prompt=get_agent_instructions('discover'),
    tools=[
        Tool(update_discover_data, takes_ctx=True)
    ],
    # NOTE: What should the dependencies be?
    # deps_type= 
    instrument=True
)