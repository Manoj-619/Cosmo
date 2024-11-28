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
from stage_app.models import DiscoverStage, UserProfile
from helpers.agents.b_discuss import discuss_agent
from helpers.agents.common import get_agent_instructions
from helpers.utils import get_logger

logger = get_logger(__name__)

# TODO: Update dicover.yaml prompt - making it more specific to the Job Description of the user

# TODO: Add tool for -> Training needs analysis



### For handoff
class transfer_to_discussion_stage(StrictTool):
    """Transfer to the Discussion stage when the learner approves the summary of the information gathered."""    
    def execute(self, context: Dict):
        email = context['email']
        sequence_id = context['sequence_id']
        
        logger.info(f"Transferring to the Discussion stage for {context['email']}.")
        discovery_object = DiscoverStage.objects.get(user__email=email, sequence_id=sequence_id)
        is_complete, error = discovery_object.check_complete()
        if not is_complete:
            raise ValueError(error)
        
        agent               = discuss_agent        
        agent.start_message = f"""
        **Discovery Data:**
                
        {discovery_object.get_summary()}
        """
        return Result(
            value=self.model_dump_json(),
            agent=agent, 
            context=context)

# TODO: Update knowledge_level field with options in scale of 1 - 7 (1 being a beginner and 7 being an expert)

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
        logger.info(f"Updated DiscoverStage Data for {email}. The following data was updated:\n\n{str(self)}")
        
        return Result(value=self.model_dump_json(),
                      context=context)
            
discover_agent = Agent(
    name="Discovery",
    id="discover",
    model="gpt-4o",
    instructions=get_agent_instructions('discover'),
    functions=[
        update_discover_data,
        transfer_to_discussion_stage
    ],
    tool_choice="auto",
    parallel_tool_calls=False
)
