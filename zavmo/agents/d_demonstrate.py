from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from pydantic_ai.settings import ModelSettings
from pydantic_ai.tools import Tool

from agents.common import model, get_agent_instructions, Deps
from stage_app.models import UserProfile, FourDSequence
from stage_app.tasks import xAPI_stage_celery_task

def complete_sequence(ctx: RunContext[Deps]):
    """Mark the current sequence as complete and prepare for next sequence"""

    email = ctx.deps.email
    profile = UserProfile.objects.get(user__email=email)
    
    # Get and complete current sequence
    sequence = FourDSequence.objects.filter(
        user=profile.user,
        current_stage=FourDSequence.Stage.DEMONSTRATE
    ).order_by('created_at')
    
    if not sequence:
        raise ValueError("No active Demonstrate stage sequence found.")
    
    sequence.first().update_stage('completed')

    # Find next incomplete sequence and set it to Discover stage
    next_sequence = FourDSequence.objects.filter(
        user=profile.user,current_stage__in=[FourDSequence.Stage.DISCOVER]
    ).order_by('created_at').first()
    
    if next_sequence:
        next_sequence.current_stage = FourDSequence.Stage.DISCOVER
        next_sequence.save()
        return "Current sequence completed. Next sequence set to Discover stage."
    
    return "All sequences completed successfully!"

class demonstrate_data(BaseModel):
    """"""
    demonstration_evidence: str = Field(description="Evidence of skills demonstrated.")
    assessment_results: str = Field(description="Results of the demonstration assessment.")
    feedback: str = Field(description="Feedback on the demonstration phase.")
    
def update_demonstrate_data(ctx: RunContext[Deps], data: demonstrate_data):
    """Update the demonstration data for the current sequence."""
    email = ctx.deps.email
    profile = UserProfile.objects.get(user__email=email)
    
    sequence = FourDSequence.objects.filter(
        user=profile.user,
        current_stage=FourDSequence.Stage.DEMONSTRATE
    ).order_by('created_at').first()
    
    if not sequence:
        raise ValueError("No active Demonstrate stage sequence found.")
    
    sequence.demonstration_evidence = data.demonstration_evidence
    sequence.assessment_results = data.assessment_results
    sequence.demonstration_feedback = data.feedback
    sequence.save()
    
    return "Demonstration data updated successfully."

demonstrate_agent = Agent(
    model,
    model_settings=ModelSettings(parallel_tool_calls=True),
    system_prompt=get_agent_instructions('demonstrate'),
    # instrument=True,
    tools=[
        Tool(complete_sequence),
        Tool(update_demonstrate_data),
    ],
    retries=3) 
