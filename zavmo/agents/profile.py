from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from pydantic_ai.settings import ModelSettings
from pydantic_ai.tools import Tool

from agents.common import model, get_agent_instructions, Deps
from helpers.search import retrieve_nos_from_neo4j, retrieve_ofquals_from_neo4j
from stage_app.models import UserProfile, FourDSequence, TNAassessment
from agents.tna_assessment import tna_assessment_agent
from stage_app.tasks import xAPI_profile_celery_task, xAPI_stage_celery_task

import time
import logging


class nos_query(BaseModel):
    """A query to find relevant NOS for the user's profile"""
    query: str = Field(description="A query invloving main purpose, responsibilities and manager responsibilities of the learner's current role.")

def FindNOSandOFQUAL(ctx: RunContext[Deps], nos_query: nos_query):
    """Find relevant NOS and OFQUAL for the user's profile"""
    # Get email from dependencies
    email        = ctx.deps.email
    time.sleep(2)
    user_profile = UserProfile.objects.get(user__email=email)
    is_complete, error = user_profile.check_complete()
    if not is_complete:
        return f"Please update profile data using `update_profile_data` tool. {error}"

    ## Number of 4D sequence to create for a user => length of NOS
    nos = retrieve_nos_from_neo4j(nos_query.query)
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
                    nos_id=nos_data['nos_id'],
                    status='In Progress' if total_assessments == 1 else 'To Assess'
                )
                assessments_for_sequence.append(assessment)
            
            TNAassessment.objects.bulk_create(assessments_for_sequence)
        else:
            logging.info(f"\n\nNo OFQUAL units found for NOS ID: {nos_data['nos_id']}. Skipping FourD Sequence creation.\n\n")

    return f"NOS to OFQUAL mapped, transfer to TNA Assessment step using `transfer_to_tna_assessment_step` tool."


class profile(BaseModel):
    """Learner's information gathered during the Profile stage."""
    
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
    
def update_profile_data(ctx: RunContext[Deps], data: profile):
    """Update the profile data of the learner. First name, last name, current role, etc."""
    # Get email from dependencies
    email = ctx.deps.email
    if not email:
        raise ValueError("Email is required to update profile data.")
        
    # Get the UserProfile object
    user_profile = UserProfile.objects.get(user__email=email)
    if not user_profile:
        raise ValueError("UserProfile not found")
    
    # Update the UserProfile object
    user_profile.first_name = data.first_name
    user_profile.last_name = data.last_name
    user_profile.current_role = data.current_role
    user_profile.current_industry = data.current_industry
    user_profile.years_of_experience = data.years_of_experience
    user_profile.manager = data.manager
    user_profile.department = data.department
    user_profile.job_duration = data.job_duration
    user_profile.role_purpose = data.role_purpose
    user_profile.key_responsibilities = data.key_responsibilities
    user_profile.stakeholder_engagement = data.stakeholder_engagement
    user_profile.processes_and_governance_improvements = data.processes_and_governance_improvements
    user_profile.save()

    xAPI_profile_celery_task.apply_async(args=[data.model_dump(), email])

    return "Profile Data updated successfully. Find NOS and OFQUAL matching with the learner's profile using the `FindNOSandOFQUAL` tool."



profile_agent = Agent(
    model,
    model_settings=ModelSettings(parallel_tool_calls=True),
    system_prompt=get_agent_instructions('profile'),
    instrument=True,
    tools=[
        Tool(FindNOSandOFQUAL),
        Tool(update_profile_data),
    ],
    retries=3
)