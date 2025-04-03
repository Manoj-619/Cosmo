from .profile import profile_agent
from .a_discover import discover_agent
from .b_discuss import discuss_agent
from .c_deliver import deliver_agent
from .d_demonstrate import demonstrate_agent
from .tna_assessment import tna_assessment_agent
from .common import Deps
from pydantic_ai import RunContext
from stage_app.models import FourDSequence, UserProfile
from stage_app.tasks import xAPI_stage_celery_task

@profile_agent.tool
def transfer_to_tna_assessment_step(ctx: RunContext[Deps]):
    """After the learner has completed the Discover stage, transfer to the TNA Assessment step"""
    email = ctx.deps.email
    profile = UserProfile.objects.get(user__email=email)

    name  = profile.first_name + " " + profile.last_name
    xAPI_stage_celery_task.apply_async(args=['tna_assessment', email, name])   
    ctx.deps.stage_name = 'tna_assessment'

    return tna_assessment_agent

@tna_assessment_agent.tool
def transfer_to_discuss_stage(ctx: RunContext[Deps]):
    """After the learner has completed the TNA Assessment step, transfer to the Discuss stage"""
    
    email = ctx.deps.email
    profile = UserProfile.objects.get(user__email=email)

    name  = profile.first_name + " " + profile.last_name
    xAPI_stage_celery_task.apply_async(args=['discuss', email, name])  
    
    ctx.deps.stage_name = 'discuss'

    return discuss_agent

@discuss_agent.tool
def transfer_to_deliver_stage(ctx: RunContext[Deps]):
    """After the learner has completed the Discuss stage, transfer to the Deliver stage"""
    email = ctx.deps.email
    profile = UserProfile.objects.get(user__email=email)

    name  = profile.first_name + " " + profile.last_name
    xAPI_stage_celery_task.apply_async(args=['deliver', email, name])  
    
    ctx.deps.stage_name = 'deliver'

    return deliver_agent

@deliver_agent.tool
def transfer_to_demonstrate_stage(ctx: RunContext[Deps]):
    """After the learner has completed the Deliver stage, transfer to the Demonstrate stage"""
    email = ctx.deps.email
    profile = UserProfile.objects.get(user__email=email)

    name  = profile.first_name + " " + profile.last_name
    xAPI_stage_celery_task.apply_async(args=['demonstrate', email, name])  
    
    ctx.deps.stage_name = 'demonstrate'

    return demonstrate_agent    


def get_agent(stage_name):
    """Get the agent for the given stage name"""
    if stage_name == 'profile':
        return profile_agent
    elif stage_name == 'discover':
        return discover_agent
    elif stage_name == 'tna_assessment':
        return tna_assessment_agent
    elif stage_name == 'discuss':
        return discuss_agent
    elif stage_name == 'deliver':
        return deliver_agent
    elif stage_name == 'demonstrate':
        return demonstrate_agent