
from agents.common import model, get_agent_instructions
from pydantic_ai.settings import ModelSettings
from pydantic_ai.tools import Tool
from pydantic_ai import Agent, RunContext
from agents.common import get_yaml_data, get_prompt
import logging
from pydantic import BaseModel, Field
from typing import Literal, Dict, List

from stage_app.models import FourDSequence, TNAassessment

class TNADeps(BaseModel):
    email: str = Field(description="The email of the user.")
    stage_name: str = Field(description="The stage of the user.")
    level: Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"] = Field(description="The level the user has assessed themselves in the assessment area.", default=None)

def get_ofqual_based_instructions(level: str, competency_to_assess: TNAassessment):
    level_based_marks_scheme = [item for item in competency_to_assess.ofqual_criterias if item['bloom_taxonomy_level'] == level][0]
    logging.info(f"\n\nLevel based marks scheme: {level_based_marks_scheme}\n\n")
    criteria     = level_based_marks_scheme['criteria']
    expectations = level_based_marks_scheme['expectations']
    task         = level_based_marks_scheme['task']

    benchmarking_responses = level_based_marks_scheme['benchmarking_responses']
    benchmarking_responses = "\n\n".join([f"   **{item['grade'].upper()}:** {item['example']}" for item in benchmarking_responses])
    
    ofqual_based_instructions = f"""- **Assessment Area:** {competency_to_assess.assessment_area}\n\n"
        - **Current Bloom's Taxonomy Level mapped to User facing scale is:** {level} (But While addressing about the level, use the level in User facing scale)\n\n"
        - **Criteria:** {criteria}\n\n
        - **Task:** {task}\n\n
        - **Expectations:** {expectations}\n\n"
        - **Benchmarking Responses for validation:** \n\n{benchmarking_responses}\n\n"""
    return ofqual_based_instructions

class CurrentLevel(BaseModel):
    """Validate the learner's response to advice on progression."""
    assessment_area: str = Field(description="Exact name of current assessment area.")
    current_bloom_taxonomy_level: Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"] = Field(description="The current Bloom's Taxonomy level of the assessment area the learner is currently on.")
    result: Literal["FAIL", "PASS", "MERIT", "DISTINCTION"] = Field(description="""The result of the assessment. It is based on the learner's response against the OFQUAL's benchmarking responses. 
                                                                    The learner's response could match one of the OFQUAL's benchmarking responses - Fail, Pass, Merit, Distinction. Evaluate strictly based on criterias and benchmarking responses shared from OFQUAL.""")
    
def validate_on_current_level(ctx: RunContext[TNADeps], current_level: CurrentLevel) -> str:
    email       = ctx.deps.email
    sequences   = FourDSequence.objects.filter(user__email=email, current_stage__in=[1, 2, 3, 4]).order_by('created_at')
    sequence_id = sequences.first().id if sequences else None

    all_levels = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
    tna_assessment = TNAassessment.objects.get(user__email=email, sequence_id=sequence_id, assessment_area=current_level.assessment_area)
    tna_assessment.finalized_blooms_taxonomy_level = current_level.current_bloom_taxonomy_level
    tna_assessment.save()
    if current_level.result == "FAIL":
        if current_level.current_bloom_taxonomy_level == "Remember":
            ctx.deps.level = "Remember"
            return f"Based on validation, it is advised to save the details of the assessment area and then move to next NOS assessment area."
        else:
            next_lower_level = all_levels[all_levels.index(current_level.current_bloom_taxonomy_level) - 1]
            ctx.deps.level = next_lower_level
            return f"Inform learner that based on validation, it is advised to move to next lower level {next_lower_level}."
    
    if current_level.result == "PASS" or current_level.result == "MERIT":
        ctx.deps.level = current_level.current_bloom_taxonomy_level
        return f"""Inform learner that based on evaluating the learner's response against the OFQUAL's benchmarking responses, {current_level.result} is achieved. 
                            It is advised to save the details of the assessment area and move to next NOS assessment area."""
    
    if current_level.result == "DISTINCTION":
        if current_level.current_bloom_taxonomy_level == "Create":
            ctx.deps.level = "Create"
            return f"""Inform learner that based on evaluating the learner's response against the OFQUAL's benchmarking responses, Distinction is achieved. 
                            The learner has reached the highest level. It is advised to save the details of the assessment area and move to next NOS assessment area."""
        else:
            next_higher_level = all_levels[all_levels.index(current_level.current_bloom_taxonomy_level) + 1]
            ctx.deps.level = next_higher_level
            return f"""Inform learner that based on evaluating the learner's response against the OFQUAL's benchmarking responses, {next_higher_level} is achieved. 
                            It is advised to move to next higher level and continue assessment process on next shared level and corresponding task."""

class AssessmentAreaDetails(BaseModel):
    """
    Save the details of an assessment area.
    """
    assessment_area: str = Field(description="The exact name of the assessment area that was assessed.")
    user_assessed_knowledge_level: int = Field(description="The knowledge level in the assessment area self-assessed by the user, rated on a scale of 1 to 7.")
    zavmo_assessed_knowledge_level: int = Field(description="The knowledge level determined by Zavmo based on the assessment, rated on a scale of 1 to 7.")
    evidence_of_assessment: str = Field(description="A report of the assessment process for the assessment area and the learner's response to the proposed assessment questions.")
    gaps: List[str] = Field(description="List of all knowledge gaps determined for learner's responses validating against OFQUAL requirements such as benchmarking response (DISTINCTION), expectations, and criterias provided for the Assessment Area.")
    
def save_assessment_area(ctx: RunContext[TNADeps], assessment_area_details: AssessmentAreaDetails) -> str:
    """
    Save the details of an assessment area.
    """
    email       = ctx.deps.email
    sequences   = FourDSequence.objects.filter(user__email=email, current_stage__in=[1, 2, 3, 4]).order_by('created_at')
    sequence_id = sequences.first().id if sequences else None
    tna_assessment = TNAassessment.objects.get(user__email=email, sequence_id=sequence_id, assessment_area=assessment_area_details.assessment_area)
    tna_assessment.user_assessed_knowledge_level = assessment_area_details.user_assessed_knowledge_level
    tna_assessment.zavmo_assessed_knowledge_level = assessment_area_details.zavmo_assessed_knowledge_level
    tna_assessment.evidence_of_assessment = assessment_area_details.evidence_of_assessment
    tna_assessment.knowledge_gaps = assessment_area_details.gaps
    tna_assessment.status = 'Completed'
    tna_assessment.save()

    next_tna_assessment = TNAassessment.objects.filter(user__email=email, sequence_id=sequence_id).exclude(status='Completed').order_by('created_at').first()
    next_tna_assessment.status = 'In Progress'
    next_tna_assessment.save()

    return f"""Saved details for the Assessment area: {assessment_area_details.assessment_area}."""

def set_current_level(ctx: RunContext[TNADeps], level: CurrentLevel):
    ctx.deps.level = level.current_bloom_taxonomy_level
    return f"Obtained Bloom's Taxonomy level  {level.current_bloom_taxonomy_level}."

tna_assessment_agent = Agent(
    model,
    model_settings=ModelSettings(parallel_tool_calls=True),
    # instrument=True,
    tools=[
        Tool(validate_on_current_level),
        Tool(save_assessment_area),
        Tool(set_current_level)
    ],
    retries=3
)

@tna_assessment_agent.system_prompt(dynamic=True)
def get_system_prompt(ctx: RunContext[TNADeps]):
   
    email  = ctx.deps.email
    level  = ctx.deps.level

    logging.info(f"Current level: {level}")

    sequences = FourDSequence.objects.filter(user__email=email, current_stage__in=[1, 2, 3, 4]).order_by('created_at')
    if sequences:
        sequence  = sequences.first()
        sequence_id = sequence.id
        nos_id = sequence.nos_id
        nos_title = sequence.nos_title

    current_sequence_tna_items = TNAassessment.objects.filter(user__email=email, sequence_id=sequence_id)
    
    conf_data        = get_yaml_data('tna_assessment')
    agent_keys       = ['name', 'description', 'instructions', 'examples', 'completion_condition', 'next_stage', 'next_stage_description', ]
    prompt_context   = {k:v for k,v in conf_data.items() if k in agent_keys}
    
    prompt_context['total_number_of_assessment_areas'] = TNAassessment.objects.filter(user__email=email).count()
    prompt_context['no_of_assessment_areas_in_current_4D_sequence'] = current_sequence_tna_items.count()
    prompt_context['assessment_areas_with_ofqual_ids'] = "\n".join([f"   **{item.assessment_area}:** {item.ofqual_id}" for item in current_sequence_tna_items])
    prompt_context['NOS_title_with_NOS_ID'] = f"**{nos_title} ({nos_id})**"
    competency_to_assess = TNAassessment.objects.get(user__email=email, 
                                                        sequence_id=sequence_id, 
                                                        status='In Progress')
    
    ## bloom's taxonomy level based instructions
    if competency_to_assess:
        if level:
            ofqual_based_instructions = get_ofqual_based_instructions(ctx, level, competency_to_assess)
            logging.info(f"OFQUAL based instructions for evaluation: {ofqual_based_instructions}")
            prompt_context['assessment_area_with_criteria'] = ofqual_based_instructions
        else:
            prompt_context['assessment_area_with_criteria'] = f"Assessment Area: **{competency_to_assess.assessment_area}**"
    else:
        prompt_context['assessment_area_with_criteria'] = "No Assessment Areas left to assess. Transfer to Discussion stage."

    system_content  = get_prompt('tna_assessment.md', 
                                    context=prompt_context,
                                    prompt_dir="assets/prompts")
                                    
    return system_content

