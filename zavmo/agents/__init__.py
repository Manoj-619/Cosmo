from .profile import profile_agent
# from a_discover import discover_agent
# from b_discuss import discuss_agent
# from c_deliver import deliver_agent
# from d_demonstrate import demonstrate_agent
from .tna_assessment import tna_assessment_agent
from agents.common import User
from pydantic_ai import RunContext
from stage_app.models import FourDSequence, UserProfile
from stage_app.tasks import xAPI_stage_celery_task

@profile_agent.tool
def transfer_to_tna_assessment_step(ctx: RunContext[User]):
    """After the learner has completed the Discover stage, transfer to the TNA Assessment step"""
    email = ctx.deps.email
    profile = UserProfile.objects.get(user__email=email)
    
    name  = profile.first_name + " " + profile.last_name
    xAPI_stage_celery_task.apply_async(args=['tna_assessment', email, name])   

    return tna_assessment_agent
