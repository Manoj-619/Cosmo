"""
# Stage 0: Profile
Fields:
"""

from pydantic import Field
from typing import Dict, List, Literal
from helpers._types import (
    Agent,
    StrictTool,
    PermissiveTool,
    Result,
    function_to_json
)
from stage_app.models import UserProfile, TNAassessment
from helpers.agents.a_discover import discover_agent
from helpers.agents.tna_assessment import tna_assessment_agent
from helpers.agents.common import get_agent_instructions, get_tna_assessment_instructions
from helpers.chat import get_prompt
from helpers.search import fetch_nos_text
from helpers.swarm import fetch_agent_response
import json
import logging

criteria_prompt ="""As a proficient assistant, your task is to list all competencies outlined in both the knowledge and performance sections of the shared NOS document. For each competency, develop assessment criteria based on the six levels of Bloom's Taxonomy:

Remember: Can the user recall relevant facts, definitions, or procedures related to this skill?
Understand: Is the user able to explain or interpret the concepts associated with this skill?
Apply: Can the user effectively utilize the skill in real-world scenarios or simulated tasks?
Analyze: Is the user capable of deconstructing complex situations to identify components related to this skill?
Evaluate: Can the user assess situations and justify decisions involving this skill?
Create: Is the user able to design or innovate new approaches, presentations, or solutions based on this skill?

**Note**: 
- Do not skip any competency mentioned in the NOS document, As it represents the skills that the learner needs to develop in future to meet the National Occupational Standards (NOS).
- The list might have more than 30 competencies at times, when considering from both sections (knowledge and performance).
"""

### For handoff
class BloomTaxonomyLevels(StrictTool):
    level: Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"] = Field(description="The level of Bloom's Taxonomy")
    criteria: str = Field(description="Generate very challenging criteria for assessing the competency on the level of Bloom's Taxonomy")

    def execute(self, context: Dict):
        return self.model_dump_json()
    
class GetSkillFromNOS(StrictTool):
    assessment_area:str = Field(description="Name of the competency")
    blooms_taxonomy_criteria: List[BloomTaxonomyLevels] = Field(description="Competency criterias on Bloom's Taxonomy levels")
    type: Literal["knowledge", "performance"] = Field(description="The type of the competency")

    def execute(self, context: Dict):
        return self.model_dump_json()

class GetRequiredSkillsFromNOS(PermissiveTool):
    """Use this tool if NOS document is shared by the user."""
    
    nos: List[GetSkillFromNOS] = Field(description="List all competencies mentioned in the NOS document from both sections (knowledge and performance) with corresponding criteria on Bloom's Taxonomy levels"
                                        ,max_length=3)
    
    def execute(self, context: Dict):
        return self.model_dump_json()

class GenerateTNAAssessments(StrictTool):
    """Use this tool, immediately after the user has provided the current role."""

    def execute(self, context: Dict):
        profile = UserProfile.objects.get(user__email=context['email'])
        nos_doc = fetch_nos_text(industry="Sales", current_role=profile.current_role)
        logging.info(f"NOS document for current role as {profile.current_role}: {nos_doc}")

        agent       = profile_agent
        agent.instructions  = criteria_prompt
        agent.functions     = [GetRequiredSkillsFromNOS]
        agent.start_message = f"Here is the NOS document:\n\n{nos_doc}"

        completion  = fetch_agent_response(agent=agent, history=[], context=context)
        assessments = json.loads(completion.choices[0].message.tool_calls[0].function.arguments)['nos']
        try:
            # Create all TNA assessments
            for item in assessments:
                assessment_area = item['assessment_area']
                TNAassessment.objects.create(
                    user=profile.user,
                    sequence_id=context['sequence_id'],
                    assessment_area=assessment_area,
                    blooms_taxonomy_criteria=item['blooms_taxonomy_criteria']
                    )
                
            # Update context with assessment counts
            total_assessments = len(assessments)
            context['tna_assessment'] = {
                'total_assessments': total_assessments,
                'current_assessment': 1,  # Starting with first assessment
                'assessments_data': []
            }
            logging.info(f"TNA assessments created: {TNAassessment.objects.filter(user=profile.user, sequence_id=context['sequence_id']).count()}")
            
            # Update the agent by bringing back previous instructions and functions
            agent.instructions = get_agent_instructions('profile')
            agent.functions = [update_profile_data, transfer_to_tna_assessment_stage]
            agent.start_message = ""

            return Result(
                value=f"TNA assessments: {[{assessment.get('assessment_area'): assessment.get('type')} for assessment in assessments]}",
                context=context)
        except Exception as e:
            logging.error(f"Error creating TNA assessments: {e}, Assessment Area: {assessment_area}")
            return Result(value="Unable to create TNA assessments", context=context)

class transfer_to_tna_assessment_stage(StrictTool):
    """After updating the profile stage, transfer to the TNA Assessment stage when the learner has completed the Profile stage."""
    
    def execute(self, context: Dict):
        """Transfer to the TNA Assessment stage when the learner has completed the Profile stage."""
        profile = UserProfile.objects.get(user__email=context['email'])
        is_complete, error = profile.check_complete()
        if not is_complete:
            raise ValueError(error)
        summary = profile.get_summary()
        agent = tna_assessment_agent
        agent.start_message = f"""Here is the learner's profile: {summary}
        
        Greet the learner and introduce about the TNA (Training Needs Analysis) Assessment step.
        """
        agent.instructions = get_tna_assessment_instructions(context)
        return Result(value="Transferred to TNA Assessment stage.",
            agent=agent, 
            context=context)

### For updating the data

class update_profile_data(StrictTool):
    """Update the learner's information gathered during the Profile stage."""
    
    first_name: str = Field(description="The learner's first name.")
    last_name: str        = Field(description="The learner's last name.")
    age: int              = Field(description="The learner's age.")  
    edu_level: int        = Field(description="The learner's education level, represented as an integer. 1: Primary School, 2: Middle School, 3: High School, 4: Associate Degree, 5: Bachelor's Degree, 6: Master's Degree, 7: PhD")
    current_role: str     = Field(description="The learner's current role.")
    current_industry: str = Field(description="The industry in which the learner is currently working in.")
    years_of_experience: int = Field(description="The number of years the learner has worked in their current industry.")
    department: str       = Field(description="The department the learner works in.")
    manager: str      = Field(description="The name of the person the learner reports to.")
    job_duration: int = Field(description="The number of years the learner has worked in their current job.")
   
    def execute(self, context: Dict):
        # Get email and sequence_id from context
        email       = context.get('email')
        if not email:
            raise ValueError("Email is required to update profile data.")
        
        # Get the UserProfile object
        profile = UserProfile.objects.get(user__email=email)
        if not profile:
            raise ValueError("UserProfile not found")        
        # Update the UserProfile object
        profile.first_name = self.first_name
        profile.last_name = self.last_name
        profile.age = self.age
        profile.edu_level = self.edu_level
        profile.current_role = self.current_role
        profile.current_industry = self.current_industry
        profile.years_of_experience = self.years_of_experience
        profile.manager = self.manager
        profile.department = self.department
        profile.job_duration = self.job_duration
        profile.save()
        
        context['profile'] = self.model_dump()
        return Result(value=self.model_dump_json(), context=context)
            
profile_agent = Agent(
    name="Profile",
    id="profile",
    model="gpt-4o",
    instructions=get_agent_instructions('profile'),
    functions=[
        update_profile_data,
        transfer_to_tna_assessment_stage,
        GenerateTNAAssessments
    ],
    tool_choice="auto",
    parallel_tool_calls=False
)