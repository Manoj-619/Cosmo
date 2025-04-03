
from agents.common import model, get_agent_instructions
from pydantic_ai.settings import ModelSettings
from pydantic_ai.tools import Tool
from pydantic_ai import Agent, RunContext
from agents.common import get_yaml_data, get_prompt, Deps
import logging
from pydantic import BaseModel, Field
from typing import Literal, Dict, List

from stage_app.models import FourDSequence, TNAassessment

def get_ofqual_based_instructions(competency_to_assess: TNAassessment):
    all_blooms_taxonomy_levels_criteria = competency_to_assess.ofqual_criterias 

    ofqual_based_instructions = f"Assessment Area: {competency_to_assess.assessment_area}"
    for item in all_blooms_taxonomy_levels_criteria:
        ofqual_based_instructions+=f"""\n\n**Blooms Taxonomy Level:** {item['bloom_taxonomy_level']}\nTask: {item['task']}\nCriteria and Expectations: {item['criteria']} {item['expectations']}\n"""
        benchmarking_responses = item['benchmarking_responses']
        ofqual_based_instructions+="Benchmarking Responses:\n"+"\n".join([f"**{item['grade'].upper()}:** {item['example']}" for item in benchmarking_responses])
    return ofqual_based_instructions

class CurrentLevel(BaseModel):
    """Validate the learner's response to advice on progression."""
    assessment_area: str = Field(description="Exact name of current assessment area.")
    current_bloom_taxonomy_level: Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"] = Field(description="The current Bloom's Taxonomy level of the assessment area the learner is currently on.")
    result: Literal["FAIL", "PASS", "MERIT", "DISTINCTION"] = Field(description="""The result of the assessment. It is based on the learner's response against the OFQUAL's benchmarking responses. 
                                                                    The learner's response could match one of the OFQUAL's benchmarking responses - Fail, Pass, Merit, Distinction. Evaluate strictly based on criterias and benchmarking responses shared from OFQUAL.""")
    
def validate_on_current_level(ctx: RunContext[Deps], current_level: CurrentLevel) -> str:
    email       = ctx.deps.email
    sequences   = FourDSequence.objects.filter(user__email=email, current_stage__in=[1, 2, 3, 4]).order_by('created_at')
    sequence_id = sequences.first().id if sequences else None

    all_levels = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
    tna_assessment = TNAassessment.objects.get(user__email=email, sequence_id=sequence_id, assessment_area=current_level.assessment_area)
    tna_assessment.finalized_blooms_taxonomy_level = current_level.current_bloom_taxonomy_level
    tna_assessment.save()
    if current_level.result == "FAIL":
        if current_level.current_bloom_taxonomy_level == "Remember":
            return f"Based on validation, it is advised to save the details of the assessment area and then move to next NOS assessment area."
        else:
            next_lower_level = all_levels[all_levels.index(current_level.current_bloom_taxonomy_level) - 1]
            return f"Inform learner that based on validation, it is advised to move to next lower level {next_lower_level}."
    
    if current_level.result == "PASS" or current_level.result == "MERIT":
        return f"""Inform learner that based on evaluating the learner's response against the OFQUAL's benchmarking responses, {current_level.result} is achieved. 
                            It is advised to save the details of the assessment area and move to next NOS assessment area."""
    
    if current_level.result == "DISTINCTION":
        if current_level.current_bloom_taxonomy_level == "Create":
            return f"""Inform learner that based on evaluating the learner's response against the OFQUAL's benchmarking responses, Distinction is achieved. 
                            The learner has reached the highest level. It is advised to save the details of the assessment area and move to next NOS assessment area."""
        else:
            next_higher_level = all_levels[all_levels.index(current_level.current_bloom_taxonomy_level) + 1]
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
    
def save_assessment_area(ctx: RunContext[Deps], assessment_area_details: AssessmentAreaDetails) -> str:
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

tna_assessment_agent = Agent(
    model,
    model_settings=ModelSettings(parallel_tool_calls=True),
    # instrument=True,
    tools=[
        Tool(validate_on_current_level),
        Tool(save_assessment_area),
    ],
    retries=3
)

@tna_assessment_agent.system_prompt(dynamic=True)
def get_system_prompt(ctx: RunContext[Deps]):
   
    email  = ctx.deps.email
    sequences = FourDSequence.objects.filter(user__email=email, current_stage__in=[1, 2, 3, 4]).order_by('created_at')
    if sequences:
        sequence    = sequences.first()
        sequence_id = sequence.id
        nos_id    = sequence.nos_id
        nos_title = sequence.nos_title

    current_sequence_tna_items = TNAassessment.objects.filter(user__email=email, sequence_id=sequence_id)
    prompt_context = {}
    prompt_context['total_number_of_assessment_areas'] = TNAassessment.objects.filter(user__email=email).count()
    prompt_context['no_of_assessment_areas_in_current_4D_sequence'] = current_sequence_tna_items.count()
    prompt_context['assessment_areas_with_ofqual_ids'] = "\n"+"\n".join([f"   **{item.assessment_area}:** {item.ofqual_id}" for item in current_sequence_tna_items])
    prompt_context['NOS_title_with_NOS_ID'] = f"**{nos_title} ({nos_id})**"
    competency_to_assess = TNAassessment.objects.get(user__email=email, 
                                                        sequence_id=sequence_id, 
                                                        status='In Progress')
    
    ## bloom's taxonomy level based instructions
    if competency_to_assess: 
        ofqual_based_instructions = get_ofqual_based_instructions(competency_to_assess)
        logging.info(f"OFQUAL based instructions for evaluation: {ofqual_based_instructions}")
        prompt_context['assessment_area_with_criteria'] = ofqual_based_instructions
    else:
        prompt_context['assessment_area_with_criteria'] = "No Assessment Areas left to assess. Transfer to Discussion stage."

    system_content  = get_prompt('tna_assessment.md', 
                                    context=prompt_context,
                                    prompt_dir="assets/prompts")
                                    
    return system_content

