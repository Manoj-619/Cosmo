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
    Result
)
from stage_app.models import UserProfile, TNAassessment, FourDSequence
from stage_app.serializers import TNAassessmentSerializer
from helpers.agents.a_discover import discover_agent
from helpers.agents.common import get_agent_instructions
from helpers.search import fetch_nos_text
import logging
import json


### For handoff
class BloomTaxonomyLevels(StrictTool):
    """Use this tool to generate Bloom's Taxonomy levels for a given competency.

    - Remember: The user must be able to recall relevant facts, definitions, or procedures related to this [competency]?
    - Understand: The user must be able to explain or interpret the concepts associated with this [competency]?
    - Apply: The user must be able to effectively utilize the [competency] in real-world scenarios or simulated tasks?
    - Analyze: The user must be able to deconstruct complex situations to identify components related to this [competency]?
    - Evaluate: The user must be able to assess situations and justify decisions involving this [competency]?
    - Create: The user must be able to design or innovate new approaches, presentations, or solutions based on this [competency]?    
    """
    level: Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"] = Field(description="The level of Bloom's Taxonomy")
    criteria: str = Field(description="Generate very challenging criteria for assessing the [competency] on the level of Bloom's Taxonomy")

    def execute(self, context: Dict):
        return self.model_dump_json()

class GetSkillFromNOS(StrictTool):
    """Get a competency from the NOS document and generate its corresponding Bloom's Taxonomy criteria. Competency can be knowledge or performance based."""

    assessment_area:str = Field(description="Name of the competency")
    blooms_taxonomy_criteria: List[BloomTaxonomyLevels] = Field(description="Criterias on Bloom's Taxonomy levels for the [competency]")
    # type: Literal["knowledge", "performance"] = Field(description="The type of the competency")

    def execute(self, context: Dict):
        return self.model_dump_json() 

# class GetCountOfCompetencies(StrictTool):
#     """This tool is designed to analyze and extract the number of distinct items or elements present (with prefix 1,2,..etc or K1,K2,..etc) in a National Occupational Standards (NOS) document."""
#     count: int = Field(description="Analyze and extract the number of distinct items or elements present (with prefix 1,2,..etc or K1,K2,..etc) in a National Occupational Standards (NOS) document.")

#     def execute(self, context: Dict):
#         return Result(value=f"List atmost {self.count} competencies from the NOS document. Total count of competencies to be listed is {self.count}.", context=context)

class GetRequiredSkillsFromNOS(PermissiveTool):
    """Use this tool to get the Required Skills from the NOS document, first get the count of competencies and then generate based on the count a list of competencies outlined in the NOS (National Occupational Standards) document."""
    count_of_competencies: int = Field(description="Analyze and extract the number of distinct items or elements present (with prefix 1,2,..n or K1,K2,..Kn) in a National Occupational Standards (NOS) document.")
    nos: List[GetSkillFromNOS] = Field(description=f"Based on the count of competencies, list competencies (basically all the numbered items, i.e items with prefix 1,2,..n or K1,K2,..Kn) present in the NOS document along with corresponding Bloom's Taxonomy criteria at every level (Remember, Understand, Apply, Analyze, Evaluate, Create) for each competency", 
                                       min_items = 10, max_items=40)
    
    def execute(self, context: Dict):
        if not context.get('tna_assessment', {}).get('nos_id'):
            raise ValueError("NOS documents not found in context, use GetNOS tool first.")
        
        user_profile = UserProfile.objects.get(user__email=context['email'])

        ## Number of assessments per sequence
        n=5 
        total_assessments = 0
        # Create sequences for every n number of assessments
        for i in range(0, len(self.nos), n):
            # First create the sequence
            sequence = FourDSequence.objects.create(
                user=user_profile.user,
                current_stage=FourDSequence.Stage.DISCOVER
            )
            
            # Create assessments for the sequence
            for skill in self.nos[i:i+n]:
                TNAassessment.objects.create(
                    user=user_profile.user,
                    assessment_area=skill.assessment_area,
                    blooms_taxonomy_criteria=[bt.model_dump() for bt in skill.blooms_taxonomy_criteria],
                    sequence=sequence,
                    nos_id=context['tna_assessment']['nos_id']
                )
                total_assessments += 1

        # Convert QuerySet to list before storing in context
        all_sequences = list(FourDSequence.objects.filter(
            user=user_profile.user
        ).order_by('created_at').values_list('id', flat=True))

        # Update context with first sequence info
        context.update({'sequence_id': all_sequences[0]})
        context['sequences_to_complete']             = all_sequences
        context['tna_assessment']['total_nos_areas'] = total_assessments
        logging.info(context)
        return Result(value=f"FourDSequences created, transfer to discovery stage", context=context)

class GetNOSDocument(StrictTool):
    current_role: str = Field(description="The learner's current role.")

    def execute(self, context: Dict):
        nos_doc, nos_id = fetch_nos_text( 
                current_role=self.current_role)
        
        context['tna_assessment']['nos_id']   = nos_id
        context['nos_doc'] = nos_doc
        return Result(value=f"This is the NOS (National Occupational Standards) document with competencies outlined: \n\n{nos_doc}\n\n Now get the count of competencies using the `GetCountOfCompetencies` tool and then get the required skills using the `GetRequiredSkillsFromNOS` tool based on the count and NOS document shared here. Do not let the learner know about the NOS document.", context=context)

### For handoff

class transfer_to_discover_stage(StrictTool):
    """Transfer to the Discovery stage when the learner has completed the Profile stage."""
    
    def execute(self, context: Dict):
        """Transfer to the Discovery stage when the learner has completed the Profile stage."""        
        profile = UserProfile.objects.get(user__email=context['email'])
        is_complete, error = profile.check_complete()
        if not is_complete:
            raise ValueError(error)
        if context['sequence_id'] == "":
            raise ValueError("Get Required skills from NOS first.")
        summary = profile.get_summary()
        agent = discover_agent
        agent.start_message += f"Here is the learner's profile: {summary}"
        
        return Result(agent=agent, context=context)

### For updating the data

class update_profile_data(StrictTool):
    """Update the learner's information gathered during the Profile stage."""
    
    first_name: str = Field(description="The learner's first name.")
    last_name: str        = Field(description="The learner's last name.")
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
        GetNOSDocument,
        # GetCountOfCompetencies,
        GetRequiredSkillsFromNOS,
        transfer_to_discover_stage
    ],
    tool_choice="auto",
    parallel_tool_calls=True
)