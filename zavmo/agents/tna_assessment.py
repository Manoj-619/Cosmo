
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
    level: Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"] = Field(description="The level the user has assessed themselves in the assessment area.", default=None)

def get_ofqual_based_instructions(ctx: RunContext[TNADeps], level: str, competency_to_assess: TNAassessment):
    level_based_marks_scheme = [item for item in competency_to_assess.ofqual_criterias if item['bloom_taxonomy_level'] == level][0]
            
    criteria     = level_based_marks_scheme['criteria']
    expectations = level_based_marks_scheme['expectations']
    task         = level_based_marks_scheme['task']

    benchmarking_responses = level_based_marks_scheme['benchmarking_responses']
    benchmarking_responses = "\n\n".join([f"   **{item['grade'].upper()}:** {item['example']}" for item in benchmarking_responses])
    
    ofqual_based_instructions = (
        f"- **Assessment Area:** {competency_to_assess.assessment_area}\n\n"
        f"- **Current Bloom's Taxonomy Level mapped to User facing scale is:** {level} (But While addressing about the level, use the level in User facing scale)\n\n"
        f"- **Criteria:** {criteria}\n\n"
        f"- **Task:** {task}\n\n"
        f"- **Expectations:** {expectations}\n\n"
        f"- **Benchmarking Responses for validation:** \n\n{benchmarking_responses}\n\n"
    )
    return ofqual_based_instructions

class ValidateOnCurrentLevel(BaseModel):
    """Validate the learner's response to advice on progression."""
    assessment_area: str = Field(description="Exact name of current assessment area.")
    result: Literal["FAIL", "PASS", "MERIT", "DISTINCTION"] = Field(description="""The result of the assessment. It is based on the learner's response against the OFQUAL's benchmarking responses. 
                                                                    The learner's response could match one of the OFQUAL's benchmarking responses - Fail, Pass, Merit, Distinction. Evaluate strictly based on criterias and benchmarking responses shared from OFQUAL.""")
    current_bloom_taxonomy_level: Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"] = Field(description="The current Bloom's Taxonomy level of the assessment area the learner is currently on.")
    
    async def execute(self, ctx: RunContext[TNADeps]) -> str:
        email       = ctx.deps.email
        sequences   = FourDSequence.objects.filter(user__email=email, current_stage__in=[1, 2, 3, 4]).order_by('created_at')
        sequence_id = sequences.first().id if sequences else None

        all_levels = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
        tna_assessment = TNAassessment.objects.get(user__email=email, sequence_id=sequence_id, assessment_area=self.assessment_area)
        tna_assessment.finalized_blooms_taxonomy_level = self.current_bloom_taxonomy_level
        tna_assessment.save()
        if self.result == "FAIL":
            if self.current_bloom_taxonomy_level == "Remember":
                ctx.deps.level = "Remember"
                return f"Based on validation, it is advised to save the details of the assessment area and then move to next NOS assessment area."
            else:
                next_lower_level = all_levels[all_levels.index(self.current_bloom_taxonomy_level) - 1]
                ctx.deps.level = next_lower_level
                return f"Inform learner that based on validation, it is advised to move to next lower level {next_lower_level}."
        
        if self.result == "PASS" or self.result == "MERIT":
            ctx.deps.level = self.current_bloom_taxonomy_level
            return f"""Inform learner that based on evaluating the learner's response against the OFQUAL's benchmarking responses, {self.result} is achieved. 
                                It is advised to save the details of the assessment area and move to next NOS assessment area."""
        
        if self.result == "DISTINCTION":
            if self.current_bloom_taxonomy_level == "Create":
                ctx.deps.level = "Create"
                return f"""Inform learner that based on evaluating the learner's response against the OFQUAL's benchmarking responses, Distinction is achieved. 
                              The learner has reached the highest level. It is advised to save the details of the assessment area and move to next NOS assessment area."""
            else:
                next_higher_level = all_levels[all_levels.index(self.current_bloom_taxonomy_level) + 1]
                ctx.deps.level = next_higher_level
                return f"""Inform learner that based on evaluating the learner's response against the OFQUAL's benchmarking responses, {next_higher_level} is achieved. 
                                It is advised to move to next higher level and continue assessment process on next shared level and corresponding task."""


class SaveAssessmentArea(BaseModel):
    """
    Save the details of an assessment area.
    """
    assessment_area: str = Field(description="The exact name of the assessment area that was assessed.")
    user_assessed_knowledge_level: int = Field(description="The knowledge level in the assessment area self-assessed by the user, rated on a scale of 1 to 7.")
    zavmo_assessed_knowledge_level: int = Field(description="The knowledge level determined by Zavmo based on the assessment, rated on a scale of 1 to 7.")
    evidence_of_assessment: str = Field(description="A report of the assessment process for the assessment area and the learner's response to the proposed assessment questions.")
    gaps: List[str] = Field(description="List of all knowledge gaps determined for learner's responses validating against OFQUAL requirements such as benchmarking response (DISTINCTION), expectations, and criterias provided for the Assessment Area.")
    
    async def execute(self, ctx: RunContext[TNADeps]) -> str:
        """
        Save the details of an assessment area.
        """
        email       = ctx.deps.email
        sequences   = FourDSequence.objects.filter(user__email=email, current_stage__in=[1, 2, 3, 4]).order_by('created_at')
        sequence_id = sequences.first().id if sequences else None
        
        tna_assessment = TNAassessment.objects.get(user__email=email, sequence_id=sequence_id, assessment_area=self.assessment_area)
        tna_assessment.user_assessed_knowledge_level = self.user_assessed_knowledge_level
        tna_assessment.zavmo_assessed_knowledge_level = self.zavmo_assessed_knowledge_level
        tna_assessment.evidence_of_assessment = self.evidence_of_assessment
        tna_assessment.knowledge_gaps = self.gaps
        tna_assessment.status = 'Completed'
        tna_assessment.save()

        next_tna_assessment = TNAassessment.objects.filter(user__email=email, sequence_id=sequence_id).exclude(status='Completed').order_by('created_at').first()
        next_tna_assessment.status = 'In Progress'
        next_tna_assessment.save()

        return f"""Saved details for the Assessment area: {self.assessment_area}."""

tna_assessment_agent = Agent(
    model,
    model_settings=ModelSettings(parallel_tool_calls=True),
    # instrument=True,
    tools=[Tool(ValidateOnCurrentLevel),
           Tool(SaveAssessmentArea)],
    retries=3
)


@tna_assessment_agent.system_prompt(dynamic=True)
def get_system_prompt(ctx: RunContext[TNADeps]):
   
    email       = ctx.deps.email
    level       = ctx.deps.level

    sequences   = FourDSequence.objects.filter(user__email=email, current_stage__in=[1, 2, 3, 4]).order_by('created_at')
    sequence_id = sequences.first().id if sequences else None

    current_sequence_tna_items = TNAassessment.objects.filter(user__email=email, sequence_id=sequence_id)
    
    conf_data        = get_yaml_data('tna_assessment')
    agent_keys       = ['name', 'description', 'instructions', 'examples', 'completion_condition', 'next_stage', 'next_stage_description', ]
    prompt_context   = {k:v for k,v in conf_data.items() if k in agent_keys}
    
    prompt_context['total_number_of_assessment_areas'] = TNAassessment.objects.filter(user__email=email).count()
    prompt_context['no_of_assessment_areas_in_current_4D_sequence'] = current_sequence_tna_items.count()
    prompt_context['assessment_areas_with_ofqual_ids'] = "\n".join([f"   **{item['assessment_area']}:** {item['ofqual_id']}" for item in current_sequence_items.values_list('assessment_area', 'ofqual_id', flat=True)])

    competency_to_assess = TNAassessment.objects.filter(user__email=email, 
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

