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
from stage_app.models import UserProfile, TNAassessment, FourDSequence, JobDescription
from stage_app.serializers import TNAassessmentSerializer
from helpers.agents.a_discover import discover_agent, tna_assessment_agent
from helpers.agents.common import get_agent_instructions, get_tna_assessment_instructions
from helpers.search import fetch_nos_text
import logging
import json


class GetSkillFromNOS(StrictTool):
    """Get a competency from the NOS document. Competency can be knowledge or performance based."""

    nos_id: str = Field(description="The NOS ID associated with knowledge and performace items provided from which the competency was taken. It will be a string of alphanumeric characters.")
    assessment_area:str = Field(description="""A competency from the NOS Data picked from either "Performance Criteria" or "Knowledge and Understanding" sections that represents a specific skill, knowledge or behavior required to meet National Occupational Standards and which is relevant to the learner's profile.""")

    def execute(self, context: Dict):
        return self.model_dump_json() 

class GetRequiredSkills(PermissiveTool):
    """Use this tool to collect all competencies from the NOS Data provided. First get the count of competencies relevant to the learner's profile and then generate based on the count a list of competencies from the NOS Data."""
    count_of_competencies: int = Field(description="Get the number of distinct items or elements to be extracted from the National Occupational Standards (NOS) Data, relevant to the learner's profile.")
    nos: List[GetSkillFromNOS] = Field(description=f"Based on the count of competencies, list competencies from the NOS Data relevant to the learner's profile along with the corresponding NOS ID from which each competency was taken.", 
                                       min_items=10, max_items=50)
    
    def execute(self, context: Dict):
        if not context.get('nos_docs'):
            raise ValueError("NOS data not found in context, use GetNOS tool first.")
        
        user_profile = UserProfile.objects.get(user__email=context['email'])
        
        ## Number of assessments per sequence
        n = 3
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
    FINANCIAL_CRIME_DUE_DILIGENCE_ANALYST_LEVEL_7 = "Financial Crime Due Diligence Analyst - Level 7"
    FINANCIAL_CRIME_DUE_DILIGENCE_MANAGER_LEVEL_6 = "Financial Crime Due Diligence Manager - Level 6"
    PEOPLE_PARTNER_LEVEL_5 = "People Partner - Level 5"
    PEOPLE_PARTNER_LEVEL_6 = "People Partner - Level 6"
    CUSTOMER_SERVICE_MANAGER_LEVEL_6 = "Customer Service Manager - Level 6"
    PEOPLE_LEADER_CUSTOMER_FULFILLMENT_LEVEL_7 = "People Leader - Customer Fulfilment - Level 6"
    POD_SOLVER = "Pod Solver"
    ETHICS_COMPLIANCE_GOVERNANCE_CONSULTANT_LEVEL_7 = "Ethics & Compliance Governance Consultant - Level 7"
    SENIOR_ASSURANCE_ASSESSOR_LEVEL_6 = "Senior Assurance Assessor - Ethics & Compliance - Level 6"
    ENERGY_COMPLIANCE_CONSULTANT_LEVEL_6 = "Energy Compliance Consultant - Level 6"
    FRAUD_INVESTIGATOR_LEVEL_7 = "Fraud Investigator - Level 7"
    ETHICS_COMPLIANCE_ASSURANCE_MANAGER_LEVEL_6 = "Ethics & Compliance Assurance Manager - Level 6"
    ETHICS_COMPLIANCE_HEAD_OF_ASSURANCE_LEVEL_5 = "Ethics & Compliance - Head of Assurance - Level 5"
    GROUP_HEAD_OF_ETHICS = "Group Head of Ethics"

    
class ExtractNOSData(StrictTool):
    def execute(self, context: Dict):
        profile  = UserProfile.objects.get(user__email=context['email'])
        all_nos  = profile.get_nos()
        nos_docs = "\n\n".join([f"-----------------------------------\n{nos.text}\n" for nos in all_nos])
        context['nos_docs'] = nos_docs
        return Result(value=f"""Providing NOS Data. Generate a list of competencies from the NOS data:\n\n{nos_docs}""", context=context)

### For handoff

class transfer_to_tna_assessment_step(StrictTool):
    """After the learner has completed the Discover stage, transfer to the TNA Assessment step."""
    
    def execute(self, context: Dict):
        """After the learner has completed the Discover stage, transfer to the TNA Assessment step"""
        profile = UserProfile.objects.get(user__email=context['email'])
        is_complete, error = profile.check_complete()
        if not is_complete:
            raise ValueError(error)
        if context['sequence_id'] == "":
            raise ValueError("Get Required skills from NOS first using the `GetRequiredSkills` tool, with minimum 10 competencies listed.")
        
        summary = profile.get_summary()

        all_assessments = context['tna_assessment']['total_nos_areas']
        assessments = TNAassessment.objects.filter(sequence_id=context['sequence_id'])
        assessment_areas = [(assessment.assessment_area, assessment.nos_id) for assessment in assessments]
        agent = tna_assessment_agent
        current_assessment_areas = '\n-'.join([f"Assessment Area: {area} (NOS ID: {nos_id})" for area, nos_id in assessment_areas])
        
        # Format the message with proper error handling
        agent.start_message = (
            f"Here is the learner's profile: {summary}\n\n"
            "Greet and introduce the TNA Assessment step, based on instructions and example shared in Introduction.\n"
            f"Total NOS Areas: {all_assessments}\n"
            f"Current Number Of Assessment Areas: {len(assessment_areas)}\n"
            "NOS Assessment Areas for current 4D Sequence to be presented:"
            f"\n-{current_assessment_areas}\n\n"
            "Present the NOS Assessment Areas for current 4D Sequence in a table form.\n\n"
            "Then start the TNA assessment on Current NOS Area."
        )

        agent.instructions = get_tna_assessment_instructions(context, level="")
        
        # Update context with proper integer values
        context['tna_assessment'] = {
            'current_nos_areas': len(assessments),
            'total_nos_areas': all_assessments,
            'assessments': [TNAassessmentSerializer(assessment).data for assessment in assessments]
        }
        
        return Result(value="Transferred to TNA Assessment step.",
            agent=agent, 
            context=context)


# class transfer_to_discover_stage(StrictTool):
#     """Transfer to the Discovery stage when the learner has completed the Profile stage."""
    
#     def execute(self, context: Dict):
#         """Transfer to the Discovery stage when the learner has completed the Profile stage."""        
#         profile = UserProfile.objects.get(user__email=context['email'])
#         is_complete, error = profile.check_complete()
#         if not is_complete:
#             raise ValueError(error)
#         if context['sequence_id'] == "":
#             raise ValueError("Get Required skills from NOS first using the `GetRequiredSkillsFromNOS` tool, with minimum 10 competencies listed.")
#         summary = profile.get_summary()
#         agent = discover_agent
#         agent.start_message += f"Here is the learner's profile: {summary}"
        
#         return Result(agent=agent, context=context)

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
        
        logging.info(f"Current role: {self.current_role}")    
        current_role = self.current_role.value.lower().title().replace("_Level_", " - Level ").replace("_", " ")

        # Update the UserProfile object
        profile.first_name = self.first_name
        profile.last_name = self.last_name
        profile.current_role = current_role
        profile.current_industry = self.current_industry
        profile.years_of_experience = self.years_of_experience
        profile.manager = self.manager
        profile.department = self.department
        profile.job_duration = self.job_duration
        
        # Update JD if role has changed
        if profile.job_description:
            if profile.job_description.job_role != current_role:
                try:
                    new_jd = JobDescription.objects.get(job_role=current_role)
                    profile.job_description = new_jd
                except JobDescription.DoesNotExist:
                    logging.warning(f"No JD found for role: {current_role}")
        else:
            profile.job_description = JobDescription.objects.get(job_role=current_role)
            
        profile.save()
        
        # Convert enum to string value before storing in context
        profile_data = self.model_dump()
        profile_data['current_role'] = current_role
        context['profile'] = profile_data

        JD_details = profile.job_description.summary
        return Result(value=f"""The JD details which matched with the user's current role is:\n\n{JD_details}. Your must briefly describe the JD and ask if it aligns with the learner's current role.""", context=context)
            
profile_agent = Agent(
    name="Profile",
    id="profile",
    model="gpt-4o",
    instructions=get_agent_instructions('profile'),
    functions=[
        update_profile_data,
        ExtractNOSData,
        GetRequiredSkills,
        transfer_to_tna_assessment_step
        # transfer_to_discover_stage
    ],
    tool_choice="auto",
    parallel_tool_calls=False
)