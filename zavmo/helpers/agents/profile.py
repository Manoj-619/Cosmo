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

    - Remember: Can the user recall relevant facts, definitions, or procedures related to this competency?
    - Understand: Is the user able to explain or interpret the concepts associated with this competency?
    - Apply: Can the user effectively utilize the competency in real-world scenarios or simulated tasks?
    - Analyze: Is the user capable of deconstructing complex situations to identify components related to this competency?
    - Evaluate: Can the user assess situations and justify decisions involving this competency?
    - Create: Is the user able to design or innovate new approaches, presentations, or solutions based on this competency?    
    """
    level: Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"] = Field(description="The level of Bloom's Taxonomy")
    criteria: str = Field(description="Generate very challenging criteria for assessing the competency on the level of Bloom's Taxonomy")

    def execute(self, context: Dict):
        return self.model_dump_json()

class GetSkillFromNOS(StrictTool):
    """Get a competency from the NOS document and generate its corresponding Bloom's Taxonomy criteria."""

    assessment_area:str = Field(description="Name of the competency")
    blooms_taxonomy_criteria: List[BloomTaxonomyLevels] = Field(description="Criterias on Bloom's Taxonomy levels for the competency")
    # type: Literal["knowledge", "performance"] = Field(description="The type of the competency")

    def execute(self, context: Dict):
        return self.model_dump_json() 

class GetRequiredSkillsFromNOS(StrictTool):
    """Use this tool if NOS document is shared and generate TNA assessments data.

    Instructions:
    Count all numbered items in “Performance Criteria” and “Knowledge and Understanding” sections. 
    Add these to determine the total number of competencies to be listed (e.g., 12 + 10 = 22). 
    Generate a list of competencies and corresponding Bloom's Taxonomy criteria, covering all areas of the NOS document.
    """
    nos: List[GetSkillFromNOS] = Field(description="Generate a list of total number of competencies listed under **Performance Criteria** and **Knowledge and Understanding** sections with corresponding Bloom's Taxonomy criteria for each item, covering all areas of the NOS document.")
    
    def execute(self, context: Dict):
        if 'nos_docs' not in context:
            raise ValueError("NOS documents not found in context, use GetNOS tool first.")
        user_profile = UserProfile.objects.get(user__email=context['email'])
        
        # Create sequences for every 5 skills
        sequences = []
        for i in range(0, len(self.nos), 5):
            # First create the sequence
            sequence = FourDSequence.objects.create(
                user=user_profile.user,
                current_stage=FourDSequence.Stage.DISCOVER
            )
            
            # Create assessments for the sequence
            for skill in self.nos[i:i+5]:
                TNAassessment.objects.create(
                    user=user_profile.user,
                    assessment_area=skill.assessment_area,
                    blooms_taxonomy_criteria=[bt.model_dump() for bt in skill.blooms_taxonomy_criteria],
                    sequence=sequence
                )

            sequences.append(sequence)
        
        # Update context with first sequence info
        current_sequence = sequences[0]
        context.update({
            'sequence_id': current_sequence.id,
            'sequences_to_complete': [s.id for s in sequences],
            'tna_assessment': {
                'total_assessments': current_sequence.assessments.count(),
                'current_assessment': 1,
                'assessment_data': []
            }
        })
        
        # Get assessment areas from first sequence
        first_batch = self.nos[:5]
        assessment_areas = "\n".join([skill.assessment_area for skill in first_batch])
        return Result(value=f"assessment_areas: {assessment_areas}", context=context)
    

class GetNOSDocument(StrictTool):
    """Use this tool to get the NOS document."""
    
    def execute(self, context: Dict):
        user_profile = UserProfile.objects.get(user__email=context['email'])
        nos_docs = fetch_nos_text(
                industry=user_profile.current_industry, 
                current_role=user_profile.current_role)
        
        context['nos_docs'] = nos_docs
        return Result(value=f"This is the NOS document with competencies outlined: \n\n{nos_docs}", context=context)

class transfer_to_tna_assessment_step(StrictTool):
    """After getting the assessment areas, transfer to the TNA Assessment step."""
    
    def execute(self, context: Dict):
        """Transfer to the TNA Assessment step."""
        profile = UserProfile.objects.get(user__email=context['email'])
        is_complete, error = profile.check_complete()
        if not is_complete:
            raise ValueError(error)
        if not context['sequence_id']:
            raise ValueError("No TNA assessments found for the learner. Please get the NOS document, generate required skills and TNA assessments.")
        summary = profile.get_summary()
        assessments = FourDSequence.objects.get(id=context['sequence_id']).assessments.all()
        assessment_areas = ", ".join([assessment.assessment_area for assessment in assessments])
        agent = tna_assessment_agent
        agent.start_message = f"""Here is the learner's profile: {summary}
        
        TNA assessments that the learner needs to complete: {assessment_areas}

        Greet the learner and introduce about the TNA (Training Needs Analysis) Assessment step.
        Present the TNA assessments that the learner needs to complete in furture in the form of a table.

        |       Assessments       |
        |-------------------------|
        |     assessment area     |
        |     assessment area     | 
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
        GetNOSDocument,
        GetRequiredSkillsFromNOS
    ],
    tool_choice="auto",
    parallel_tool_calls=False
)