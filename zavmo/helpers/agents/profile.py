"""
# Stage 0: Profile
Fields:
"""
from enum import Enum
from pydantic import Field
from typing import Dict, List, Literal, Optional
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

    assessment_area:str = Field(description="A competency from the NOS document that represents a specific skill, knowledge or behavior required to meet National Occupational Standards and which is not present in the learner's responsibilities, main purpose, and work experience in current role.")
    nos_id: str = Field(description="The NOS ID to which the competency belongs.")
    def execute(self, context: Dict):
        return self.model_dump_json() 

class GetRequiredSkillsFromNOS(PermissiveTool):
    """Use this tool to collect all competencies from the NOS data provided. First get the count of competencies relevant to the learner's profile and then generate based on the count a list of competencies."""
    count_of_competencies: int = Field(description="Get the number of distinct items or elements to be extracted from the National Occupational Standards (NOS) data, relevant to the learner's profile. Minimum 10 is a must.")
    nos: List[GetSkillFromNOS] = Field(description=f"Based on the count of competencies (minimum 10 is a must), list competencies present in the NOS data relevant to the learner's profile along with the NOS ID to which the competency belongs.", 
                                       min_items=10, max_items=50)
    
    def execute(self, context: Dict):
        if not context.get('nos_docs'):
            raise ValueError("NOS data not found in context, use GetNOS tool first.")
        
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
            
            for item in self.nos[start_idx:end_idx]:
                total_assessments += 1
                assessment = TNAassessment(
                    user=user_profile.user,
                    assessment_area=item.assessment_area,
                    sequence=sequence,
                    nos_id=item.nos_id,
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

class JDBasedRole(Enum):
    FINANCIAL_CRIME_DUE_DILIGENCE_ANALYST = "Financial Crime Due Diligence Analyst"
    FINANCIAL_CRIME_DUE_DILIGENCE_MANAGER = "Financial Crime Due Diligence Manager"
    PEOPLE_PARTNER= "People Partner"
    CUSTOMER_SERVICE_MANAGER = "Customer Service Manager"
    PEOPLE_LEADER_CUSTOMER_FULFILLMENT = "People Leader - Customer Fulfilment"
    POD_SOLVER = "Pod Solver"
    ETHICS_COMPLIANCE_GOVERNANCE_CONSULTANT = "Ethics & Compliance Governance Consultant"
    SENIOR_ASSURANCE_ASSESSOR = "Senior Assurance Assessor - Ethics & Compliance"
    ENERGY_COMPLIANCE_CONSULTANT = "Energy Compliance Consultant"
    GROUP_HEAD_OF_ETHICS = "Group Head of Ethics"
    FRAUD_INVESTIGATOR = "Fraud Investigator"
    ETHICS_COMPLIANCE_ASSURANCE_MANAGER = "Ethics & Compliance Assurance Manager"
    ETHICS_COMPLIANCE_HEAD_OF_ASSURANCE = "Ethics & Compliance - Head of Assurance"

class GetNOSDocument(StrictTool):
    def execute(self, context: Dict):
        profile = UserProfile.objects.get(user__email=context['email'])
        # query = f"{profile.current_role}, {profile.current_industry}, \n\n{profile.work_experience_in_current_role} \n\n{profile.main_purpose} \n\n{profile.responsibilities} \n\n{profile.manager_responsibilities}"
        # query = f"Role: {profile.current_role}, Department/Industry: {profile.department} / {profile.current_industry}"
        # nos_docs, nos_ids = fetch_nos_text(query)
        # nos_ids = "\nNOS ID: ".join(nos_ids)
        if profile.get_nos():
            nos_docs = profile.get_nos()
            nos_ids = [nos.nos_id for nos in nos_docs]
            nos_docs = "\n\n".join([f"NOS ID: {nos.nos_id}\nPerformance Criteria: {nos.performance_criteria}\nKnowledge Criteria: {nos.knowledge_criteria}" for nos in nos_docs])
        context['nos_docs'] = nos_docs
        # return Result(value=f"""The NOS IDs shortlisted based on relevance to the learner's profile and query are: \nNOS ID: {nos_ids}\nProviding the NOS data with competencies outlined under Performance and Knowledge sections for the respective NOS IDs: \n{nos_docs}\n\nNext step is to identify competencies relevant to the learner's profile and query. Take a count of competencies and then list competencies using the `GetRequiredSkillsFromNOS` tool.\n\nThe NOS query is: **{query}**""", context=context)
        return Result(value=f"""Providing the NOS data from the NOS IDs: {nos_ids}.\n\nGenerate a list of competencies from the data shared:\n\n{nos_docs}""", context=context)

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
            raise ValueError("Get Required skills from NOS first using the `GetRequiredSkillsFromNOS` tool, with minimum 10 competencies listed.")
        summary = profile.get_summary()
        agent = discover_agent
        agent.start_message += f"Here is the learner's profile: {summary}"
        
        return Result(agent=agent, context=context)

### For updating the data

class update_profile_data(StrictTool):
    """Update the learner's information gathered during the Profile stage."""
    
    first_name: str = Field(description="The learner's first name.")
    last_name: str        = Field(description="The learner's last name.")
    current_role: Optional[JDBasedRole] = Field(description="The learner's current role.")
    current_industry: str = Field(description="The industry in which the learner is currently working in.")
    years_of_experience: int = Field(description="The number of years the learner has worked in their current industry.")
    department: str       = Field(description="The department the learner works in.")
    manager: str      = Field(description="The name of the person the learner reports to.")
    job_duration: int = Field(description="The number of years the learner has worked in their current job.")
    # work_experience_in_current_role: str = Field(description="A detailed description of the learner's work experience in their current role.")
    # main_purpose:  str = Field(description="The main purpose of the learner's current role.")
    # responsibilities: str = Field(description="The responsibilities of the learner's current role.")
    # manager_responsibilities: str = Field(description="The responsibilities of the learner's manager.")

    def execute(self, context: Dict):
        # Get email and sequence_id from context
        email = context.get('email')
        if not email:
            raise ValueError("Email is required to update profile data.")
        
        # Get the UserProfile object
        profile = UserProfile.objects.get(user__email=email)
        if not profile:
            raise ValueError("UserProfile not found")        
        
        # Update the UserProfile object
        profile.first_name = self.first_name
        profile.last_name = self.last_name
        # Store enum value instead of enum object
        profile.current_role = self.current_role.value.replace("_", " ").lower().title()
        profile.current_industry = self.current_industry
        profile.years_of_experience = self.years_of_experience
        profile.manager = self.manager
        profile.department = self.department
        profile.job_duration = self.job_duration
        profile.save()
        
        # Convert enum to string value before storing in context
        profile_data = self.model_dump()
        profile_data['current_role'] = self.current_role.value
        context['profile'] = profile_data

        JD_details = profile.job_description.summary
        return Result(value=f"""The JD details which matched with the user's current role is:\n\n{JD_details}. Briefly describe the JD and ask if it aligns with the user's current role.""", context=context)
            
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