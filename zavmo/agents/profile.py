from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from pydantic_ai.settings import ModelSettings
from pydantic_ai.tools import Tool

from agents.common import model, get_agent_instructions, Deps
from helpers.search import retrieve_nos_from_neo4j, retrieve_ofquals_from_neo4j
from stage_app.models import UserProfile, FourDSequence, TNAassessment
from agents.tna_assessment import tna_assessment_agent
from stage_app.tasks import xAPI_profile_celery_task, xAPI_stage_celery_task

import json
import logging


class FindNOSandOFQUAL(BaseModel):
    """Finds relevant NOS and OFQUAL standards for the user's profile"""
    query: str = Field(description="A query invloving main purpose, responsibilities and manager responsibilities of the learner's current role.")

    async def execute(self, ctx: RunContext[Deps]):
        # Get email from dependencies
        email        = ctx.deps.email
        user_profile = UserProfile.objects.get(user__email=email)
        is_complete, error = user_profile.check_complete()
        if not is_complete:
            raise ValueError(error)

        ## Number of 4D sequence to create for a user => length of NOS
        nos = retrieve_nos_from_neo4j(self.query)
        for nos_data in nos:
            sequence = FourDSequence(
                user=user_profile.user,
                nos_id=nos_data['nos_id'],
                nos_title=nos_data['title'],
                nos_performance_items=nos_data['performance_criteria'],
                nos_knowledge_items=nos_data['knowledge_understanding'],
                current_stage=FourDSequence.Stage.DISCOVER
            )

            ofqual_units_for_nos = retrieve_ofquals_from_neo4j(nos_data['nos_id'])
            
            if len(ofqual_units_for_nos) > 0:
                sequence.save() # Create the sequence only if ofqual units are found for NOS
                logging.info(f"\n\nProcessing 4D sequence creation for NOS ID: {nos_data['nos_id']} - Found {len(ofqual_units_for_nos)} OFQUAL units\n\n")
            
                assessments_for_sequence = []  # Reset for each sequence
                total_assessments = 0
                for ofqual in ofqual_units_for_nos:
                    total_assessments += 1
                    assessment = TNAassessment(
                        user=user_profile.user,
                        assessment_area=ofqual['unit_title'],
                        sequence=sequence,
                        ofqual_unit_id=ofqual['unit_id'],
                        ofqual_unit_data=ofqual['learning_outcomes'],
                        ofqual_criterias=ofqual['markscheme'],
                        ofqual_id=ofqual['ofqual_id'],
                        status='In Progress' if total_assessments == 1 else 'To Assess'
                    )
                    assessments_for_sequence.append(assessment)
                
                TNAassessment.objects.bulk_create(assessments_for_sequence)
            else:
                logging.info(f"\n\nNo OFQUAL units found for NOS ID: {nos_data['nos_id']}. Skipping FourD Sequence creation.\n\n")

        return f"NOS to OFQUAL mapped, transfer to TNA Assessment step"


class update_profile_data(BaseModel):
    """Update the learner's information gathered during the Profile stage."""
    
    first_name: str   = Field(description="The learner's first name.")
    last_name: str    = Field(description="The learner's last name.")
    current_role: str = Field(description="The learner's current role.")
    current_industry: str    = Field(description="The industry in which the learner is currently working in.")
    years_of_experience: int = Field(description="The number of years the learner has worked in their current industry.")
    department: str   = Field(description="The department the learner works in.")
    manager: str      = Field(description="The name of the person the learner reports to.")
    job_duration: int = Field(description="The number of years the learner has worked in their current job.")
    role_purpose: str = Field(description="The main purpose of the learner in their current role.")
    key_responsibilities: str   = Field(description="The key responsibilities of the learner in their current role.")
    stakeholder_engagement: str = Field(description="The stakeholder engagement of the learner in their current role.")
    processes_and_governance_improvements: str = Field(description="The processes and governance improvements made by the learner in their current role.")
    
    async def execute(self, ctx: RunContext[Deps]):
        # Get email from dependencies
        email = ctx.deps.email
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
        profile.role_purpose = self.role_purpose
        profile.key_responsibilities = self.key_responsibilities
        profile.stakeholder_engagement = self.stakeholder_engagement
        profile.processes_and_governance_improvements = self.processes_and_governance_improvements
        profile.save()

        xAPI_profile_celery_task.apply_async(args=[json.loads(self.model_dump_json()), email])

        return "Profile Data updated successfully. Get NOS matching with the learner's current role using the `ExtractNOSData` tool."



profile_agent = Agent(
    model,
    model_settings=ModelSettings(parallel_tool_calls=True),
    system_prompt=get_agent_instructions('profile'),
    # instrument=True,
    tools=[
        Tool(FindNOSandOFQUAL),
        Tool(update_profile_data),
    ],
    retries=3
)