"""
# Stage 0: Profile
Fields:
"""

from pydantic import Field
from typing import Literal, List, Optional, Dict
from helpers.swarm import Agent, Response, Result, Tool
from stage_app.models import UserProfile
from .a_discover import discover_agent
from .common import get_agent_instructions

### For handoff
def transfer_to_discover_agent():
    """Transfer to the Discovery Agent when the learner has completed the Profile stage."""
    return discover_agent


### For updating the data

class update_profile_data(Tool):
    """Update the learner's information gathered during the Profile stage."""
    first_name: str = Field(description="The learner's first name.")
    last_name: str  = Field(description="The learner's last name.")
    age: int = Field(description="The learner's age.")  
    edu_level: int    = Field(description="The learner's education level, represented as an integer. 1: Primary School, 2: Middle School, 3: High School, 4: Associate Degree, 5: Bachelor's Degree, 6: Master's Degree, 7: PhD")
    current_role: str = Field(description="The learner's current role.")
    current_industry: str    = Field(description="The industry in which the learner is currently working in.")
    years_of_experience: int = Field(description="The number of years the learner has worked in their current industry.")


    def __str__(self):
        """Return a string representation of the UpdateDiscoverData object."""
        string = []
        for field, value in self.__dict__.items():
            string.append(f"{field}: {value}")
        return "\n".join(string)
    
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
        value = f"""Updated UserProfile for {email}.
        The following data was updated:
        {str(self)}
        """
        context['stage_data']['profile'] = self.model_dump()
        
        return Result(value=value, context=context)
            
profile_agent = Agent(
    name="Profile",
    id="profile",
    model="gpt-4o",
    instructions=get_agent_instructions('profile'),
    functions=[
        update_profile_data,
        transfer_to_discover_agent
    ],
    tool_choice="auto",
    parallel_tool_calls=False
)
