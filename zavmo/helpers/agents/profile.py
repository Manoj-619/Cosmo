"""
# Stage 0: Profile
Fields:
"""
# TODO: Do not probe the user for any of the existing fields - remove code 

# TODO: Update the profile_agent to probe the user for:
# TODO: job_duration (how long they've been in their current job).
# TODO: reports_to (their manager or the person they report to).
# TODO: department (the department name manager runs).

# TODO: Update discover.yaml prompt

from pydantic import Field
from typing import Dict
from helpers._types import (
    Agent,
    StrictTool,
    Result,
)
from stage_app.models import UserProfile
from helpers.agents.a_discover import discover_agent
from helpers.agents.common import get_agent_instructions

### For handoff

class transfer_to_discover_stage(StrictTool):
    """Transfer to the Discovery stage when the learner has completed the Profile stage."""
    
    def execute(self, context: Dict):
        """Transfer to the Discovery stage when the learner has completed the Profile stage."""        
        profile = UserProfile.objects.get(user__email=context['email'])
        is_complete, error = profile.check_complete()
        if not is_complete:
            raise ValueError(error)
        summary = profile.get_summary()
        agent = discover_agent
        agent.start_message += f"Here is the learner's profile: {summary}"
        
        return Result(agent=agent, context=context)


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
        transfer_to_discover_stage
    ],
    tool_choice="auto",
    parallel_tool_calls=False
)
