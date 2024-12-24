from pydantic import Field
from typing import Dict, List, Optional
from helpers._types import (
    Agent,
    StrictTool,
    Result,
)
from helpers.agents.common import get_tna_assessment_instructions
from helpers.utils import get_logger
from stage_app.models import  TNAassessment
from helpers.agents.a_discover import discover_agent


logger = get_logger(__name__)


class transfer_to_discover_stage(StrictTool):
    """Transfer to the Discovery stage when no NOS area is left to assess."""
    
    def execute(self, context: Dict):
        """Transfer to the Discovery stage when it is informed that all NOS areas are assessed."""        
        email       = context['email']
        sequence_id = context['sequence_id']
        tna_assessments = TNAassessment.objects.filter(user__email=email, sequence_id=sequence_id)
        if tna_assessments.count() >= 5:
            raise ValueError("TNA Assessment is not complete for all NOS areas.")
        
        assessment_details = "\n".join(
            f"Assessment Area: {assessment.assessment_area}, "
            f"User Level: {assessment.user_assessed_knowledge_level}, "
            f"Zavmo Level: {assessment.zavmo_assessed_knowledge_level}, "
            f"Evidence: {assessment.evidence_of_assessment}"
            for assessment in tna_assessments
        )

        agent = discover_agent
        agent.start_message = f"""
        **TNA Assessment Data:**
        {assessment_details}

        Greet the learner and introduce to Discovery stage.
        """
        context['nos_areas_assessed'] = assessment_details
        return Result(agent=agent, context=context)

class SaveAssessmentArea(StrictTool):
    """
    Save the details of an assessment area.
    """
    assessment_area: str = Field(description="The assessment area that was assessed.")
    user_assessed_knowledge_level: int = Field(description="The knowledge level in the assessment area self-assessed by the user, rated on a scale of 1 to 7.")
    zavmo_assessed_knowledge_level: int = Field(description="The knowledge level determined by Zavmo based on the assessment, rated on a scale of 1 to 7.")
    evidence_of_assessment: str = Field(description="Generate a report of the assessment area, based on the learner's response. Including gaps in knowledge, areas of strength, and recommendations for training.")
    
    def execute(self, context: Dict):
        """
        Save the details of an assessment area.
        """
        tna_assessment = TNAassessment.objects.get(user__email=context['email'], sequence_id=context['sequence_id'], assessment_area=self.assessment_area)
        tna_assessment.user_assessed_knowledge_level  = self.user_assessed_knowledge_level
        tna_assessment.zavmo_assessed_knowledge_level = self.zavmo_assessed_knowledge_level
        tna_assessment.evidence_of_assessment = self.evidence_of_assessment
        tna_assessment.save()
        tna_assessment_agent.instructions = get_tna_assessment_instructions(context)
        context['tna_assessment']['assessments_data'].append(self.model_dump())
        context['tna_assessment']['current_assessment'] += 1
        return Result(value=self.model_dump_json(), context=context)

    
tna_assessment_agent = Agent(
    name="TNA Assessment",
    id="tna_assessment",
    model="gpt-4o",
    #instructions=get_agent_instructions('tna_assessment'),
    functions=[SaveAssessmentArea,
               transfer_to_discover_stage],
    tool_choice="auto",
    parallel_tool_calls=False
)
