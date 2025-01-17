from pydantic import Field
from typing import Dict, List
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
        """Transfer to the Discovery stage when it is informed that all NOS areas are assessed."""       
        sequence_id = context['sequence_id']
        tna_assessments = TNAassessment.objects.filter(user__email=context['email'], sequence_id=sequence_id)
        for assessment in tna_assessments:
            if not assessment.evidence_of_assessment:
                raise ValueError("TNA Assessment is not complete for all NOS areas.")
        
        assessment_details = "\n".join(
            f"Assessment Area: {assessment.assessment_area}, "
            f"User Level: {assessment.user_assessed_knowledge_level}, "
            f"Zavmo Level: {assessment.zavmo_assessed_knowledge_level}, "
            f"Evidence: {assessment.evidence_of_assessment}"
            for assessment in tna_assessments
        )

        agent = discuss_agent
        agent.start_message = f"""
        Greet the learner and introduce to Discussion stage.
        """
        return Result(value="Transferred to Discussion stage.", agent=agent, context=context)

class SaveAssessmentArea(StrictTool):
    """
    Save the details of an assessment area.
    """
    assessment_area: str = Field(description="The assessment area that was assessed.")
    user_assessed_knowledge_level: int = Field(description="The knowledge level in the assessment area self-assessed by the user, rated on a scale of 1 to 7.")
    zavmo_assessed_knowledge_level: int = Field(description="The knowledge level determined by Zavmo based on the assessment, rated on a scale of 1 to 7.")
    evidence_of_assessment: str = Field(description="You will list the gaps you determined that will require improvements later.")
    
    def execute(self, context: Dict):
        """
        Save the details of an assessment area.
        """
        tna_assessment = TNAassessment.objects.get(user__email=context['email'], sequence_id=context['sequence_id'], assessment_area=self.assessment_area)
        tna_assessment.user_assessed_knowledge_level  = self.user_assessed_knowledge_level
        tna_assessment.zavmo_assessed_knowledge_level = self.zavmo_assessed_knowledge_level
        tna_assessment.evidence_of_assessment = self.evidence_of_assessment
        ofqual_text = fetch_ofqual_text(self.assessment_area)
        tna_assessment.raw_ofqual_text = ofqual_text
        tna_assessment.save()
        tna_assessment_agent.instructions = get_tna_assessment_instructions(context)
        
        # Update the assessments in context by appending updated assessments
        current_assessments = json.loads(context['tna_assessment']['assessments']) if context['tna_assessment']['assessments'] else []
        current_assessments.append(TNAassessmentSerializer(tna_assessment).data)
        context['tna_assessment']['assessments'] = json.dumps(current_assessments)
        
        context['tna_assessment']['current_assessment'] += 1
        return Result(value=f"""Saved details for the Assessment area: {self.assessment_area}.
                      
        **Learner's knowledge:** {self.evidence_of_assessment}.
            
        **OFQUAL unit:** 
        {ofqual_text}
        
        Next, determine gaps between learner's knowledge and OFQUAL unit shared.""", context=context)

class DetermineGaps(StrictTool):
    """Lists all knowledge gaps determined between the learner's knowledge and OFQUAL unit shared."""
    # all_items_of_qualification: List[str] = Field(description="List of all qualification items provided in the OFQUAL unit, ensuring to capture all numbered items (from 1, 1.1, to n.n) in sequence. Do not attach number to the items in the beginning.")
    gaps: List[str] = Field(description="List of all knowledge gaps determined between learner's knowledge and Qualification items provided in the OFQUAL unit.")
    
    def execute(self, context: Dict):
        """Determine the gaps between learner's knowledge and OFQUAL requirements."""
        tna_assessment = TNAassessment.objects.filter(user__email=context['email'], sequence_id=context['sequence_id']).order_by('-updated_at').first()
        tna_assessment.knowledge_gaps = self.gaps
        # tna_assessment.all_items_of_qualification = self.all_items_of_qualification
        tna_assessment.save()
        return Result(value=f"Do not share the gaps identified with the learner. Move to next NOS Assessment Area or transfer to Discussion stage if No NOS Assessment Areas is shared to assess.", context=context)

tna_assessment_agent = Agent(
    name="TNA Assessment",
    id="tna_assessment",
    model="gpt-4o",
    #instructions=get_agent_instructions('tna_assessment'),
    functions=[SaveAssessmentArea,
               DetermineGaps,
               transfer_to_discussion_stage],
    tool_choice="auto",
    parallel_tool_calls=True
)
