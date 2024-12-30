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
from stage_app.models import UserProfile, TNAassessment, FourDSequence
from helpers.agents.a_discover import discover_agent
from helpers.agents.tna_assessment import tna_assessment_agent
from helpers.agents.common import get_agent_instructions, get_tna_assessment_instructions
from helpers.chat import get_prompt
from helpers.search import fetch_nos_text
from helpers.swarm import openai_client
import json
import logging
from enum import Enum
from helpers.utils import chunk_items


### For handoff
class BloomTaxonomyLevels(StrictTool):
    """Use this tool to generate Bloom's Taxonomy levels for a given competency.

    - Remember: Can the user recall relevant facts, definitions, or procedures related to this skill?
    - Understand: Is the user able to explain or interpret the concepts associated with this skill?
    - Apply: Can the user effectively utilize the skill in real-world scenarios or simulated tasks?
    - Analyze: Is the user capable of deconstructing complex situations to identify components related to this skill?
    - Evaluate: Can the user assess situations and justify decisions involving this skill?
    - Create: Is the user able to design or innovate new approaches, presentations, or solutions based on this skill?    
    """
    level: Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"] = Field(description="The level of Bloom's Taxonomy")
    criteria: str = Field(description="Generate very challenging criteria for assessing the competency on the level of Bloom's Taxonomy")

    def execute(self, context: Dict):
        return self.model_dump_json()

class GetSkillFromNOS(StrictTool):
    """Use this tool to get a skill from the NOS document.
    assessment_area: Name of the competency
    blooms_taxonomy_criteria: Remember, Understand, Apply, Analyze, Evaluate, Create
    type: 
    - any competency listed right under **Performance criteria** is of type performance
    - any competency listed right under **Knowledge and understanding** is of type knowledge        
    """
    assessment_area:str = Field(description="Name of the competency")
    blooms_taxonomy_criteria: List[BloomTaxonomyLevels] = Field(description="Competency criterias on Bloom's Taxonomy levels")
#    type: Literal["knowledge", "performance"] = Field(description="The type of the competency")

    def execute(self, context: Dict):
        return self.model_dump_json() 

class GetRequiredSkillsFromNOS(PermissiveTool):
    """Use this tool if NOS document is shared by the user."""
    
    nos: List[GetSkillFromNOS] = Field(description="List all competencies mentioned in the NOS document with corresponding criteria on Bloom's Taxonomy levels and type of the competency."
                                        ,max_length=50)
    
    def execute(self, context: Dict):
        # Check whether nos_docs is in context
        if 'nos_docs' not in context:
            raise ValueError("NOS documents not found in context, use GetNOS tool first.")
        
            # Save generated skills.
        
        return Result(value=, context=context)
        

class GetNOSDocuments(StrictTool):
    """Use this tool to get the NOS document."""
    
    def execute(self, context: Dict):
        user_profile = UserProfile.objects.get(user__email=context['email'])
        nos_docs = fetch_nos_text(
                industry=user_profile.current_industry, 
                current_role=user_profile.current_role)
        
        context['nos_docs'] = nos_docs
        # knowledge_items = [
        # # assessment for assessment in assessments if assessment['type'] == "knowledge"]
        # # performance_items = [
        # # assessment for assessment in assessments if assessment['type'] == "performance"]


        return Result(value=nos_docs, context=context)


class GenerateTNAAssessments(StrictTool):
    """Use this tool to generate TNA assessments, after updating the profile data.
    As a proficient assistant, your task is to list all numberwise given  outlined in both the knowledge and performance sections of the shared NOS document.

    For each competency, develop assessment criteria based on the six levels of Bloom's Taxonomy:

    **Important**:
    Do not skip any competency mentioned in the NOS document, as it represents the skills that the learner needs to develop in future to meet the National Occupational Standards(NOS).
    """
    
    def execute(self, context: Dict):
        try:
            assessments = json.loads(completion.choices[0].message.tool_calls[0].function.arguments)['nos']
            logging.info(f"Assessments: {assessments}")

            # Create chunks of 3 knowledge and 3 performance items each

            
            # # Create chunks of 3 knowledge and 3 performance items each
            # knowledge_chunks = chunk_items(knowledge_items)
            # # performance_chunks = chunk_items(performance_items)

            # logging.info(f"Knowledge chunks: {len(knowledge_chunks)}")
            # logging.info(f"Performance chunks: {len(performance_chunks)}")

            # Delete existing sequence first
            FourDSequence.objects.filter(id=context['sequence_id']).delete()

            sequences_to_assess = []
            for n in range(max(len(knowledge_chunks), len(performance_chunks))):
                sequence = FourDSequence.objects.create(
                    user=user,
                    current_stage=FourDSequence.Stage.DISCOVER
                )
                sequences_to_assess.append(sequence)

                # Add knowledge chunk to this sequence if available
                if n < len(knowledge_chunks):
                    for assessment in knowledge_chunks[n]:
                        TNAassessment.objects.create(
                            user=user,
                            sequence=sequence,
                            assessment_area=assessment['assessment_area'],
                            blooms_taxonomy_criteria=assessment['blooms_taxonomy_criteria'],
                            type=assessment['type']
                        )
                
                # Add performance chunk to the same sequence if available
                if n < len(performance_chunks):
                    for assessment in performance_chunks[n]:
                        TNAassessment.objects.create(
                            user=user,
                            sequence=sequence,
                            assessment_area=assessment['assessment_area'],
                            blooms_taxonomy_criteria=assessment['blooms_taxonomy_criteria'],
                            type=assessment['type']
                        )
            
            # Use the first sequence object
            current_sequence = sequences_to_assess[0]
            assessments_for_current_sequence = TNAassessment.objects.filter(
                user=user, 
                sequence=current_sequence
            )

            context.update({
                'sequence_id': current_sequence.id,  # Convert UUID to string
                'sequences_to_complete': [s.id for s in sequences_to_assess if s.current_stage != FourDSequence.Stage.COMPLETED],
                'tna_assessment': {
                    'total_assessments': assessments_for_current_sequence.count(),
                    'current_assessment': 1,
                    'assessment_data': []
                }
            })

            # Convert assessment data to serializable format
            current_assessments_info = {
                str(a.assessment_area): str(a.type) 
                for a in assessments_for_current_sequence
            }
            
            return Result(
                value=f"TNA assessments: {current_assessments_info}", 
                context=context
            )
        except Exception as e:
            logging.error(f"Error in GenerateTNAAssessments: {e}")
            raise
 
class transfer_to_tna_assessment_step(StrictTool):
    """After updating the profile stage, transfer to the TNA Assessment step when the learner has completed the Profile stage."""
    
    def execute(self, context: Dict):
        """Transfer to the TNA Assessment stage when the learner has completed the Profile stage."""
        profile = UserProfile.objects.get(user__email=context['email'])
        is_complete, error = profile.check_complete()
        if not is_complete:
            raise ValueError(error)
        elif not TNAassessment.objects.filter(user=profile.user).exists():
            raise ValueError("No TNA assessments found for the learner. Please generate TNA assessments first.")
        summary = profile.get_summary()
        agent = tna_assessment_agent
        agent.start_message = f"""Here is the learner's profile: {summary}
        
        Greet the learner and introduce about the TNA (Training Needs Analysis) Assessment step.
        """
        agent.instructions = get_tna_assessment_instructions(context)
        return Result(value="Transferred to TNA Assessment step.",
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
        transfer_to_tna_assessment_step,
        GenerateTNAAssessments
    ],
    tool_choice="auto",
    parallel_tool_calls=False
)