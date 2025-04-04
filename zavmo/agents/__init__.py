from .profile import profile_agent
from .a_discover import discover_agent
from .b_discuss import discuss_agent
from .c_deliver import deliver_agent
from .d_demonstrate import demonstrate_agent
from .tna_assessment import tna_assessment_agent
from .common import Deps
from pydantic_ai import RunContext
from stage_app.models import FourDSequence, UserProfile, DeliverStage, DemonstrateStage, DiscussStage, TNAassessment
from stage_app.tasks import xAPI_stage_celery_task

@profile_agent.tool
@demonstrate_agent.tool
def transfer_to_tna_assessment_step(ctx: RunContext[Deps]):
    """After the learner has completed the Discover stage, transfer to the TNA Assessment step"""

    email         = ctx.deps.email
    current_stage = ctx.deps.stage_name

    profile = UserProfile.objects.get(user__email=email)

    if current_stage=='profile':
        is_complete, error = profile.check_complete()
        if not is_complete:
            return error
        
    elif current_stage=='demonstrate':
        sequence = FourDSequence.objects.filter(
            user=profile.user,
            current_stage=FourDSequence.Stage.DEMONSTRATE
        ).order_by('created_at').first()
        if sequence:
            demonstrate_stage = DemonstrateStage.objects.get(
                user__email=email, 
                sequence_id=sequence.id
            )
            is_complete, error = demonstrate_stage.check_complete()
            if not is_complete:
                return error

    first_name = profile.first_name
    last_name  = profile.last_name
    name  = first_name + " " + last_name
    xAPI_stage_celery_task.apply_async(args=['tna_assessment', email, name])   

    ctx.deps.stage_name = 'tna_assessment'

    return tna_assessment_agent.run_sync(f"Greet {first_name} and Present the table", deps=Deps(email=email, stage_name='tna_assessment'))

@tna_assessment_agent.tool
def transfer_to_discuss_stage(ctx: RunContext[Deps]):
    """After the learner has completed the TNA Assessment step, transfer to the Discuss stage"""
    
    email = ctx.deps.email
    profile  = UserProfile.objects.get(user__email=email)
    
    sequence = FourDSequence.objects.filter(user=profile.user, current_stage__in=[1, 2, 3, 4]).order_by('created_at').first()
    tna_assessments = TNAassessment.objects.filter(user__email=email, sequence_id=sequence.id)
    for assessment in tna_assessments:
        if not assessment.evidence_of_assessment:
            return f"Save the details of the assessment area: **{assessment.assessment_area}** before transitioning to Discussion stage. If Assessment is not taken on this area, start the assessment process on this area, before saving the details. Otherwise, save the details of the assessment area using `save_assessment_area` tool."
        
    first_name = profile.first_name
    last_name  = profile.last_name
    name  = first_name + " " + last_name
    xAPI_stage_celery_task.apply_async(args=['discuss', email, name])  
    
    ctx.deps.stage_name = 'discuss'

    return discuss_agent.run_sync(f"Greet {first_name} the learner to the Discuss stage", deps=Deps(email=email, stage_name='discuss'))

@discuss_agent.tool
def transfer_to_deliver_stage(ctx: RunContext[Deps]):
    """After the learner has completed the Discuss stage, transfer to the Deliver stage"""
    email = ctx.deps.email
    profile = UserProfile.objects.get(user__email=email)
    
    sequence      = FourDSequence.objects.filter(user=profile.user, current_stage__in=[1, 2, 3, 4]).order_by('created_at').first()
    discuss_stage = DiscussStage.objects.get(user__email=email, sequence_id=sequence.id)

    is_complete, error = discuss_stage.check_complete()
    if not is_complete:
        return error
    
    first_name = profile.first_name
    last_name  = profile.last_name
    name  = first_name + " " + last_name
    xAPI_stage_celery_task.apply_async(args=['deliver', email, name])  
    
    ctx.deps.stage_name = 'deliver'

    return deliver_agent.run_sync(f"Greet {first_name} the learner to the Deliver stage", deps=Deps(email=email, stage_name='deliver'))

@deliver_agent.tool
def transfer_to_demonstrate_stage(ctx: RunContext[Deps]):
    """After the learner has completed the Deliver stage, transfer to the Demonstrate stage"""
    email = ctx.deps.email
    profile = UserProfile.objects.get(user__email=email)
     
    sequence      = FourDSequence.objects.filter(user=profile.user, current_stage__in=[1, 2, 3, 4]).order_by('created_at').first()
    deliver_stage = DeliverStage.objects.get(user__email=email, sequence_id=sequence.id)
    
    deliver_stage.is_complete = True
    deliver_stage.save()

    first_name = profile.first_name
    last_name  = profile.last_name
    name  = first_name + " " + last_name
    xAPI_stage_celery_task.apply_async(args=['demonstrate', email, name])  
    
    ctx.deps.stage_name = 'demonstrate'

    return demonstrate_agent.run_sync(f"Greet {first_name} the learner to the Demonstrate stage", deps=Deps(email=email, stage_name='demonstrate'))

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