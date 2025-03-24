from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Union
  
class GradingScale(BaseModel):
    """An example of a response for the grading scale"""
    grade: Literal["fail", "pass", "merit", "distinction"] = Field(description="The grade of the response")
    example: str = Field(description="Examples of responses for the task that would be graded as the grade above")
    
class MarkSchemeItem(BaseModel):
    """The mark scheme item for a specific level of Bloom's Taxonomy"""
    bloom_taxonomy_level: Literal["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"] = Field(description="The level of Bloom's Taxonomy.")
    criteria: str = Field(description="Generate appropriately challenging criteria for the level of Bloom's Taxonomy based on the ofqual unit provided.")
    expectations: str = Field(description="Expectations to meet the criteria for the level of Bloom's Taxonomy.")
    task: str = Field(description="A task designed around the level of Bloom's Taxonomy based on the ofqual unit and criteria.")
    benchmarking_responses: List[GradingScale] = Field(description="An example of a response for the grading scale", min_items=4, max_items=4)
