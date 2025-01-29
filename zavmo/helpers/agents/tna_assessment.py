from pydantic import Field
from typing import Dict, List, Literal
from helpers._types import (
    Agent,
    StrictTool,
    Result,
)
from helpers.agents.common import get_tna_assessment_instructions
from helpers.utils import get_logger
from stage_app.models import  TNAassessment, FourDSequence
from stage_app.serializers import TNAassessmentSerializer
import json
from helpers.agents.b_discuss import discuss_agent
from helpers.search import fetch_ofqual_text

logger = get_logger(__name__)

## For handoff

class transfer_to_discussion_stage(StrictTool):
    """Transfer to the Discussion stage when the learner has completed the TNA Assessment step."""    
    def execute(self, context: Dict):
        """Transfer to the Discussion stage when the learner has completed the TNA Assessment step."""       
        sequence_id = context['sequence_id']
        tna_assessments = TNAassessment.objects.filter(user__email=context['email'], sequence_id=sequence_id)
        for assessment in tna_assessments:
            if not assessment.evidence_of_assessment:
                raise ValueError(f"Save the details of the assessment area: {assessment.assessment_area} before transitioning to Discussion stage. If Assessment is not taken on this area, start the assessment process on this area, before saving the details.")
        
        agent = discuss_agent
        agent.start_message = f"""
        Greet the learner and introduce to Discussion stage.
        """
        return Result(value="Transferred to Discussion stage.", agent=agent, context=context)

class MapNOSAssessmentAreaToOFQUAL(StrictTool):
    """Use this tool immediately after the learner has shared a self assessed level on the scale of 1-7 to map the NOS assessment area to OFQUAL."""
    assessment_area: str = Field(description="Exact name of current NOS assessment area.")
    level: Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"] = Field(description="The level mapped to Bloom's Taxonomy level based on the learner's proficiency level as input on the scale of 1-7.")
    
    def execute(self, context: Dict):
        # Fetch OFQUAL text and criteria
        raw_ofqual_text, criteria_of_qualification = fetch_ofqual_text(self.assessment_area)
        
        # Update the TNA assessment record
        tna_assessment = TNAassessment.objects.get(
            user__email=context['email'], 
            sequence_id=context['sequence_id'], 
            assessment_area=self.assessment_area
        )
        tna_assessment.raw_ofqual_text = raw_ofqual_text
        tna_assessment.criterias = criteria_of_qualification
        tna_assessment.save()
        
        tna_assessment_agent.instructions = get_tna_assessment_instructions(context, self.level)
        return Result(value=f"level: {self.level}", context=context)

class ValidateOnCurrentLevel(StrictTool):
    """Validate the learner's response to advice on progression."""
    assessment_area: str = Field(description="Exact name of current NOS assessment area.")
    result: Literal["FAIL", "PASS", "MERIT", "DISTINCTION"] = Field(description="""The result of the assessment. It is based on the learner's response against the OFQUAL's benchmarking responses. 
                                                                    The learner's response could match one of the OFQUAL's benchmarking responses - Fail, Pass, Merit, Distinction. Evaluate strictly based on criterias and benchmarking responses shared from OFQUAL.""")
    current_bloom_taxonomy_level: Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"] = Field(description="The current Bloom's Taxonomy level of the assessment area the learner is currently on.")
    
    def execute(self, context: Dict):
        all_levels = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
        tna_assessment = TNAassessment.objects.get(user__email=context['email'], sequence_id=context['sequence_id'], assessment_area=self.assessment_area)
        tna_assessment.finalized_blooms_taxonomy_level = self.current_bloom_taxonomy_level
        tna_assessment.save()
        if self.result == "FAIL":
            if self.current_bloom_taxonomy_level == "Remember":
                return Result(value=f"Based on validation, it is advised to save the details of the assessment area and then move to next NOS assessment area.", context=context)
            else:
                next_lower_level = all_levels[all_levels.index(self.current_bloom_taxonomy_level) - 1]
                tna_assessment_agent.instructions = get_tna_assessment_instructions(context, next_lower_level)
                return Result(value=f"Inform learner that based on validation, it is advised to move to next lower level.", context=context)
        
        if self.result == "PASS" or self.result == "MERIT":
            tna_assessment_agent.instructions = get_tna_assessment_instructions(context, "")
            return Result(value=f"""Inform learner that based on evaluating the learner's response against the OFQUAL's benchmarking responses, {self.result} is achieved. 
                                It is advised to save the details of the assessment area and move to next NOS assessment area.""", context=context)
        
        if self.result == "DISTINCTION":
            if self.current_bloom_taxonomy_level == "Create":
                return Result(value=f"""Inform learner that based on evaluating the learner's response against the OFQUAL's benchmarking responses, Distinction is achieved. 
                              The learner has reached the highest level. It is advised to save the details of the assessment area and move to next NOS assessment area.""", context=context)
            else:
                next_higher_level = all_levels[all_levels.index(self.current_bloom_taxonomy_level) + 1]
                tna_assessment_agent.instructions = get_tna_assessment_instructions(context, next_higher_level)
                return Result(value=f"""Inform learner that based on evaluating the learner's response against the OFQUAL's benchmarking responses, {self.result} is achieved. 
                                It is advised to move to next higher level and continue assessment process on next shared level and corresponding task.""", context=context)

class SaveAssessmentArea(StrictTool):
    """
    Save the details of an assessment area.
    """
    assessment_area: str = Field(description="The assessment area that was assessed.")
    user_assessed_knowledge_level: int = Field(description="The knowledge level in the assessment area self-assessed by the user, rated on a scale of 1 to 7.")
    zavmo_assessed_knowledge_level: int = Field(description="The knowledge level determined by Zavmo based on the assessment, rated on a scale of 1 to 7.")
    evidence_of_assessment: str = Field(description="A report of the assessment process for the assessment area and the learner's response to the proposed assessment questions.")
    gaps: List[str] = Field(description="List of all knowledge gaps determined for learner's responses validating against OFQUAL requirements such as benchmarking response (DISTINCTION), expectations, and criterias provided for the Assessment Area.")
    
    def execute(self, context: Dict):
        """
        Save the details of an assessment area.
        """
        logger.info(f"evidence_of_assessment: {self.evidence_of_assessment}")
        # Update the assessments data in context with proper status handling
        updated_assessments = []
        next_assessment_marked = False
        
        for item in context['tna_assessment']['assessments']:
            if item.get('assessment_area') == self.assessment_area:
                # completed assessment
                tna_assessment = TNAassessment.objects.get(user__email=context['email'], sequence_id=context['sequence_id'], assessment_area=self.assessment_area)
                tna_assessment.user_assessed_knowledge_level = self.user_assessed_knowledge_level
                tna_assessment.zavmo_assessed_knowledge_level = self.zavmo_assessed_knowledge_level
                tna_assessment.evidence_of_assessment = self.evidence_of_assessment
                tna_assessment.knowledge_gaps = self.gaps
                tna_assessment.status = 'Completed'
                tna_assessment.save()
            
            else:
                tna_assessment = TNAassessment.objects.get(user__email=context['email'], sequence_id=context['sequence_id'], assessment_area=item.get('assessment_area'))
                if not next_assessment_marked and item.get('evidence_of_assessment') is None:
                # Mark the next unassessed area as 'In Progress'
                    tna_assessment.status = 'In Progress'
                    tna_assessment.save()
                    next_assessment_marked = True
            
            updated_assessments.append(TNAassessmentSerializer(tna_assessment).data)
        
        tna_assessment_agent.instructions = get_tna_assessment_instructions(context, level="")
        context['tna_assessment']['assessments'] = updated_assessments
        
        return Result(value=f"""Saved details for the Assessment area: {self.assessment_area}.""", context=context)

tna_assessment_agent = Agent(
    name="TNA Assessment",
    id="tna_assessment",
    model="gpt-4o",
    #instructions=get_agent_instructions('tna_assessment'),
    functions=[SaveAssessmentArea,
               MapNOSAssessmentAreaToOFQUAL,
               ValidateOnCurrentLevel,
               transfer_to_discussion_stage],
    tool_choice="auto",
    parallel_tool_calls=True
)
