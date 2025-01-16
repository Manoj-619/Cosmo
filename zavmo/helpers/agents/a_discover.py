"""
# Stage 1: Discovery
Fields:
    learning_goals: str
    learning_goal_rationale: str
    knowledge_level: int
    application_area: str
"""

from pydantic import Field
from typing import Dict
from helpers._types import (
    Agent,
    StrictTool,
    Result,
)
from stage_app.models import DiscoverStage, UserProfile, TNAassessment, FourDSequence
from helpers.agents.tna_assessment import tna_assessment_agent
from helpers.agents.common import get_tna_assessment_instructions, get_agent_instructions
from helpers.utils import get_logger

logger = get_logger(__name__)

### For handoff
class transfer_to_tna_assessment_step(StrictTool):
    """After the learner has completed the Discover stage, transfer to the TNA Assessment step."""
    
    def execute(self, context: Dict):
        """After the learner has completed the Discover stage, transfer to the TNA Assessment step"""
        discover_stage = DiscoverStage.objects.get(user__email=context['email'], sequence=context['sequence_id'])
        discover_is_complete, error = discover_stage.check_complete()
        if not discover_is_complete:
            raise ValueError(error)
        all_assessments = context['total_assessments_from_all_4D_sequences']
        assessments = TNAassessment.objects.filter(sequence_id=context['sequence_id'])
        assessment_areas = [assessment.assessment_area for assessment in assessments]
        nos_id = assessments.first().nos_id
        logger.info(f"assessment_areas: {assessment_areas}")
        agent = tna_assessment_agent
        agent.start_message = (
            "Greet and introduce the TNA Assessment step, based on instructions and example shared on Introduction.\n"
            f"Total NOS Areas: {all_assessments}\n"
            f"Current Number Of Assessment Areas: {len(assessment_areas)}\n"
            f"NOS ID: {nos_id}\n"
            f"NOS Assessment Areas for current 4D Sequence to be presented: {', '.join(assessment_areas)}\n"
            "Present the NOS Assessment Areas for current 4D Sequence in the below shared table form.\n"
            
            "| **NOS ID** | [NOS ID] |"

            "|  **Assessments For Training Needs Analysis**  |"
            "|            [Assessment Area 1]                |"
            "|            [Assessment Area 2]                |"
            "|            [Assessment Area 3]                |"
            
            "Then start the TNA assessment on Current NOS Area."
        )
        agent.instructions = get_tna_assessment_instructions(context)
        return Result(value="Transferred to TNA Assessment step.",
            agent=agent, 
            context=context)

### For updating the data
class update_discover_data(StrictTool):
    """Update the learner's information gathered during the Discovery stage."""
    
    learning_goals: str = Field(description="The learner's learning goals.")
    learning_goal_rationale: str = Field(description="The learner's rationale for their learning goals.")
    knowledge_level: int = Field(description="The learner's self-assessed knowledge level in their chosen area of study. 1=Beginner, 2=Intermediate, 3=Advanced, 4=Expert")
    application_area: str = Field(description="A specific area or context where the learner plans to apply their new knowledge and skills.")

    def execute(self, context: Dict):
        # Get email and sequence_id from context
        email       = context.get('email')
        sequence_id = context.get('sequence_id')
        
        if not email or not sequence_id:
            raise ValueError("Email and sequence ID are required to update discovery data.")        
        # Attempt to get the DiscoverStage object
        
        discover_stage = DiscoverStage.objects.get(user__email=email, sequence_id=sequence_id)
        discover_stage.learning_goals = self.learning_goals
        discover_stage.learning_goal_rationale = self.learning_goal_rationale
        
        discover_stage.knowledge_level = self.knowledge_level
        discover_stage.application_area = self.application_area
        discover_stage.save()        
        context['discover'] = self.model_dump() # JSON dump of pydantic model
        logger.info(f"Updated Discover stage Data for {email}. The following data was updated:\n\n{str(self)}")
        
        return Result(value=f"Updated Discover stage Data for {email}.",
                      context=context)
            
discover_agent = Agent(
    name="Discovery",
    id="discover",
    model="gpt-4o",
    instructions=get_agent_instructions('discover'),
    functions=[
        update_discover_data,
        transfer_to_tna_assessment_step
    ],
    tool_choice="auto",
    parallel_tool_calls=False
)