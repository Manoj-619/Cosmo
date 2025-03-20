"""
# Stage 0: Profile
Fields:
"""
from enum import Enum
from pydantic import Field
from typing import Dict, List, Optional
import json
from helpers._types import (
    Agent,
    StrictTool,
    PermissiveTool,
    Result
)
from stage_app.models import UserProfile, TNAassessment, FourDSequence
from stage_app.serializers import TNAassessmentSerializer
from helpers.agents.a_discover import discover_agent
from helpers.agents.tna_assessment import get_tna_assessment_agent
from helpers.agents.common import get_agent_instructions, get_tna_assessment_instructions
from helpers.search import retrieve_ofquals_from_neo4j, retrieve_nos_from_neo4j
from stage_app.tasks import xAPI_profile_celery_task,xAPI_stage_celery_task
import logging


class MapNOStoOFQUAL(PermissiveTool):
    """Maps NOS to OFQUAL."""
    
    def execute(self, context: Dict):
        nos = context.get('nos_docs',[])
        if not nos:
            raise ValueError("NOS data not found in context, use `ExtractNOSData` tool first.")
        
        user_profile = UserProfile.objects.get(user__email=context['email'])
        
        ## Number of 4D sequence to create for a user = length of NOS
        
        for nos_data in nos:
            sequence = FourDSequence(
                user=user_profile.user,
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
                        nos_id=nos_data['nos_id'],
                        nos_title=nos_data['title'],
                        nos_performance_items=nos_data['performance_criteria'],
                        nos_knowledge_items=nos_data['knowledge_understanding'],
                        ofqual_unit_id=ofqual['unit_id'],
                        ofqual_unit_data=ofqual['learning_outcomes'],
                        ofqual_criterias=ofqual['marksscheme'],
                        ofqual_id=ofqual['ofqual_id'],
                        status='In Progress' if total_assessments == 1 else 'To Assess'
                    )
                    assessments_for_sequence.append(assessment)
                
                TNAassessment.objects.bulk_create(assessments_for_sequence)
            else:
                logging.info(f"\n\nNo OFQUAL units found for NOS ID: {nos_data['nos_id']}. Skipping FourD Sequence creation.\n\n")
            
        # Get all sequence IDs
        all_sequences = list(FourDSequence.objects.filter(
            user=user_profile.user
        ).order_by('created_at').values_list('id', flat=True))

        if all_sequences:
            # Update context
            context.update({'sequence_id': all_sequences[0]})
            return Result(value=f"NOS to OFQUAL mapped, transfer to TNA Assessment step", context=context)
        else:
            return Result(value="No sequences found, execute `ExtractNOSData` tool again.", context=context)

    
class ExtractNOSData(StrictTool):
    """Extract NOS data from the user's profile."""
    query: str = Field(description="A query invloving main purpose, responsibilities and manager responsibilities of the learner's current role.")
    
    def execute(self, context: Dict):
        """Extract NOS for the user's profile."""
        if not context.get('profile'):
            raise ValueError("Profile data not found in context, use `update_profile_data` tool first.")
        
        nos = retrieve_nos_from_neo4j(self.query)

        context['nos_docs'] = nos
        return Result(value=f"""Extracted NOS for the user's profile. Next Map NOS to OFQUAL.""", context=context)

### For handoff
class transfer_to_tna_assessment_step(StrictTool):
    """After the learner has completed the Discover stage, transfer to the TNA Assessment step."""
    
    def execute(self, context: Dict):
        """After the learner has completed the Discover stage, transfer to the TNA Assessment step"""
        profile   = UserProfile.objects.get(user__email=context['email'])
        email     = context['email']
        is_complete, error = profile.check_complete()
        if not is_complete:
            raise ValueError(error)
        if not context['sequence_id']:
            logging.info(f"No sequence ID found. Running profile agent.")
            raise ValueError("Map NOS to OFQUAL first.")
        
        name    = context['profile']['first_name'] + " " + context['profile']['last_name']
        summary = profile.get_summary()

        all_assessments = TNAassessment.objects.filter(user=profile.user).count()

        assessments = TNAassessment.objects.filter(sequence_id=context['sequence_id'])
        nos_title   = assessments.first().nos_title
        nos_id      = assessments.first().nos_id

        assessment_areas = [(assessment.assessment_area, assessment.ofqual_id, assessment.ofqual_unit_id) for assessment in assessments]
        agent = get_tna_assessment_agent()
        xAPI_stage_celery_task.apply_async(args=[agent.id, email, name])
        current_assessment_areas = '\n-'.join([f"Assessment Area: {area} (OFQUAL ID: {ofqual_id} (Unit: {ofqual_unit_id}))" for area, ofqual_id, ofqual_unit_id in assessment_areas])
        
        # Format the message with proper error handling
        new_message = (
            f"Here is the learner's profile: {summary}\n\n"
            "Greet and introduce the TNA Assessment step, based on instructions and example shared in Introduction.\n"
            f"NOS_TITLE: **{nos_title}**\n"
            f"NOS_ID: **{nos_id}**\n"
            f"Total Assessment Areas: {all_assessments}\n"
            f"Current Number Of Assessment Areas: {len(assessment_areas)}\n"
            "Assessment Areas for current 4D Sequence to be presented:"
            f"\n-{current_assessment_areas}\n\n"
            "Present the Assessment Areas for current 4D Sequence in a Table form.\n\n"
            "Then start the TNA assessment on Current Assessment Area."
        )

        agent.instructions = get_tna_assessment_instructions(context, level="")
        agent.start_message = new_message
        # Update context with proper integer values
        context['tna_assessment'] = {
            'current_assessment_areas': len(assessments),
            'total_assessment_areas': all_assessments,
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
    current_role: str = Field(description="The learner's current role.")
    current_industry: str = Field(description="The industry in which the learner is currently working in.")
    years_of_experience: int = Field(description="The number of years the learner has worked in their current industry.")
    department: str       = Field(description="The department the learner works in.")
    manager: str      = Field(description="The name of the person the learner reports to.")
    job_duration: int = Field(description="The number of years the learner has worked in their current job.")
    role_purpose: str = Field(description="The main purpose of the learner in their current role.")
    key_responsibilities: str = Field(description="The key responsibilities of the learner in their current role.")
    stakeholder_engagement: str = Field(description="The stakeholder engagement of the learner in their current role.")
    processes_and_governance_improvements: str = Field(description="The processes and governance improvements made by the learner in their current role.")
    
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

        xAPI_profile_celery_task.apply_async(args=[json.loads(self.model_dump_json()),email])
        
        # Convert enum to string value before storing in context
        profile_data = self.model_dump()
        context['profile'] = profile_data

        return Result(value="Profile data updated successfully. Get NOS matching with the learner's current role using the `ExtractNOSData` tool.", context=context)
 
profile_agent = Agent(
    name="Profile",
    id="profile",
    model="gpt-4o",
    instructions=get_agent_instructions('profile'),
    functions=[
        update_profile_data,
        ExtractNOSData,
        MapNOStoOFQUAL,
        transfer_to_tna_assessment_step
        # transfer_to_discover_stage
    ],
    tool_choice="auto",
    parallel_tool_calls=False
)