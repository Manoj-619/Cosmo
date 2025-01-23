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


class GetSkillFromNOS(StrictTool):
    """Get a competency from the NOS document. Competency can be knowledge or performance based."""

    assessment_area:str = Field(description="A competency from the NOS document that represents a specific skill, knowledge or behavior required to meet National Occupational Standards")
    def execute(self, context: Dict):
        return self.model_dump_json() 

class GetRequiredSkillsFromNOS(PermissiveTool):
    """Use this tool to collect all competencies from the NOS document, first get the count of competencies and then generate based on the count a list of competencies outlined in the NOS (National Occupational Standards) document."""
    count_of_competencies: int = Field(description="Analyze and extract the number of distinct items or elements present (with prefix 1,2,..n or K1,K2,..Kn) in a National Occupational Standards (NOS) document.")
    nos: List[GetSkillFromNOS] = Field(description=f"Based on the count of competencies, list competencies (basically all the numbered items, i.e items with prefix 1,2,..n or K1,K2,..Kn) present in the NOS document needs to be extracted by removing any index numbers in the beginning", 
                                       min_items=10, max_items=50)
    
    def execute(self, context: Dict):
        if not context.get('tna_assessment', {}).get('nos_id'):
            raise ValueError("NOS documents not found in context, use GetNOS tool first.")
        
        user_profile = UserProfile.objects.get(user__email=context['email'])
        
        ## Number of assessments per sequence
        n = 5
        sequences_to_create = []
        assessments_to_create = []
        total_assessments = 0

        # Create sequence objects
        for i in range(0, len(self.nos), n):
            sequence = FourDSequence(
                user=user_profile.user,
                current_stage=FourDSequence.Stage.DISCOVER
            )
            sequences_to_create.append(sequence)

        # Save sequences one by one to trigger signals
        created_sequences = []
        for sequence in sequences_to_create:
            sequence.save()  # This will trigger the post_save signal
            created_sequences.append(sequence)
        
        # Prepare assessment objects
        for seq_index, sequence in enumerate(created_sequences):
            start_idx = seq_index * n
            end_idx = min(start_idx + n, len(self.nos))
            
            for skill in self.nos[start_idx:end_idx]:
                total_assessments += 1
                assessment = TNAassessment(
                    user=user_profile.user,
                    assessment_area=skill.assessment_area,
                    sequence=sequence,
                    nos_id=context['tna_assessment']['nos_id'],
                    status='In Progress' if total_assessments == 1 else 'To Assess'
                )
                assessments_to_create.append(assessment)

        # Bulk create assessments
        TNAassessment.objects.bulk_create(assessments_to_create)

        # Get all sequence IDs
        all_sequences = list(FourDSequence.objects.filter(
            user=user_profile.user
        ).order_by('created_at').values_list('id', flat=True))
        
        # Update context
        context.update({'sequence_id': all_sequences[0]})
        context['sequences_to_complete'] = all_sequences
        context['tna_assessment']['total_nos_areas'] = total_assessments
        
        return Result(value=f"FourDSequences created, transfer to discovery stage", context=context)

class GetNOSDocument(StrictTool):
    def execute(self, context: Dict):
        profile = UserProfile.objects.get(user__email=context['email'])
        query = f"Current Role: {profile.current_role} \nCurrent Industry: {profile.current_industry} \nWork experience in current role: {profile.work_experience_in_current_role} \nMain purpose: {profile.main_purpose} \nResponsibilities: {profile.responsibilities} \nManager's responsibilities: {profile.manager_responsibilities}"
        nos_doc, nos_id = fetch_nos_text(query)
        
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
    work_experience_in_current_role: str = Field(description="A detailed description of the learner's work experience in their current role.")
    main_purpose:  str = Field(description="The main purpose of the learner's current role.")
    responsibilities: str = Field(description="The responsibilities of the learner's current role.")
    manager_responsibilities: str = Field(description="The responsibilities of the learner's manager.")

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
        profile.work_experience_in_current_role = self.work_experience_in_current_role
        profile.main_purpose = self.main_purpose
        profile.responsibilities = self.responsibilities
        profile.manager_responsibilities = self.manager_responsibilities
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
        GetRequiredSkillsFromNOS,
        transfer_to_discover_stage
    ],
    tool_choice="auto",
    parallel_tool_calls=True
)