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
    """Transfer to the Discovery stage when no NOS competency is left to assess."""
    
    def execute(self, context: Dict):
        """Transfer to the Discovery stage when it is informed that all NOS competencies are assessed."""        
        email       = context['email']
        sequence_id = context['sequence_id']
        tna_assessments = TNAassessment.objects.filter(user__email=email, sequence_id=sequence_id)
        if tna_assessments.count() >= 5:
            raise ValueError("TNA Assessment is not complete for all NOS competencies.")
        
        assessment_details = "\n".join(
            f"Competency: {assessment.competency}, "
            f"User Level: {assessment.user_assessed_knowledge_level}, "
            f"Zavmo Level: {assessment.zavmo_assessed_knowledge_level}, "
            f"Evidence: {assessment.evidence_of_competency}"
            for assessment in tna_assessments
        )

        agent = discover_agent
        agent.start_message = f"""
        **TNA Assessment Data:**
        {assessment_details}
        """
        context['nos_competencies_assessment'] = assessment_details
        return Result(agent=agent, context=context)

class SaveCompetency(StrictTool):
    """
    Save the competency details.
    """
    competency: str = Field(description="The competency that was assessed.")
    user_assessed_knowledge_level: int = Field(description="The knowledge level in the competency self-assessed by the user, rated on a scale of 1 to 7.")
    zavmo_assessed_knowledge_level: int = Field(description="The knowledge level determined by Zavmo based on the assessment, rated on a scale of 1 to 7.")
    evidence_of_competency: str = Field(description="A brief description of the evidence for the competency, based on the conversation.")
    
    def execute(self, context: Dict):
        """
        Save the details of a competency.
        """
        tna_assessment = TNAassessment.objects.get(user__email=context['email'], sequence_id=context['sequence_id'], competency=self.competency)
        tna_assessment.user_assessed_knowledge_level  = self.user_assessed_knowledge_level
        tna_assessment.zavmo_assessed_knowledge_level = self.zavmo_assessed_knowledge_level
        tna_assessment.evidence_of_competency = self.evidence_of_competency
        tna_assessment.save()
        tna_assessment_agent.instructions = get_tna_assessment_instructions(context)
        return Result(value=self.model_dump_json(), context=context)

    
tna_assessment_agent = Agent(
    name="TNA Assessment",
    id="tna_assessment",
    model="gpt-4o",
    #instructions=get_agent_instructions('tna_assessment'),
    functions=[SaveCompetency,
               transfer_to_discover_stage],
    tool_choice="auto",
    parallel_tool_calls=False
)
