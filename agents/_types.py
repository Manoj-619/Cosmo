import re

from typing import List, Optional
import pandas as pd
from pydantic import BaseModel, Field, HttpUrl, field_validator


class LearningOutcome(BaseModel):
    """Learning Outcome"""
    description: str = Field(description="Learning Outcome Description")
    assessment_criteria: List[str] = Field(description="A list of assessment criteria that are relevant to the learning outcome.")
    
    def __str__(self):
        criteria_formatted = '\n'.join([f'  - {c}' for c in self.assessment_criteria])
        return f"{self.description}\n{criteria_formatted}"


class Unit(BaseModel):
    id: str = Field(description="Unit ID, usually a backslash separated string.")
    title: str = Field(description="Unit Title")
    description: str = Field(description="A description of the unit.")
    learning_outcomes: List[LearningOutcome] = Field(description="Learning Outcomes")
    
    def to_dict(self):
        return {
            "unit_id": self.id,
            "unit_title": self.title,
            "unit_description": self.description,
            "unit_learning_outcomes": "\n".join([f"{i+1}. {outcome}" for i, outcome in enumerate(self.learning_outcomes)])
        }

        
class Ofqual(BaseModel):
    """Ofqual Qualification Details"""
    id: str = Field(description="The qualification number/ID of the qualification in format like '603/4162/2'.")
    overview: str = Field(description="A brief overview of the qualification.")
    units: List[Unit] = Field(description="The units of the qualification.")
    
    @field_validator('id')
    def validate_id(cls, v):
        pattern = r'^\d{1,4}/\d{1,4}/\d{1,4}$'
        if not re.match(pattern, v):
            raise ValueError('Qualification number must be in the format of digits separated by slashes (e.g., "603/4162/2")')
        return v

    def to_dict(self):
        return {"ofqual_id":self.id,"overview":self.overview}

    def get_table(self):
        units = [{**self.to_dict(),
                  **unit.to_dict() } for unit in self.units]
        
        return pd.DataFrame(units)
            
    

class InvalidQualification(BaseModel):
    """Exception raised when the qualification is invalid"""
    rationale: str = Field(description="The rationale for the invalidity of the qualification")
    

class Metadata(BaseModel):
    id: str = Field(description="The qualification number/ID of the qualification in format like '603/4162/2'.")
    qualification_title: str = Field(description="The full title of the qualification.")
    status: str = Field(description="The status of the qualification, e.g. 'Available to learners'.")
    awarding_organisation: str = Field(description="The awarding organisation of the qualification.")
    qualification_type: str = Field(description="The type of qualification, e.g. 'Occupational Qualification'.")
    qualification_level: int = Field(description="The level of the qualification, e.g. 1, 2, 3, etc.")
    guided_learning_hours: int = Field(description="The guided learning hours of the qualification.")
    total_qualification_time: int = Field(description="The total qualification time of the qualification.")
    assessment_methods: str = Field(description="The assessment methods of the qualification.")
    specification_url: Optional[HttpUrl] = Field(description="The URL of the qualification specification.")
    sector_subject_area: str = Field(description="The sector subject area of the qualification.")
    european_qualification_level: str = Field(description="The European qualification level of the qualification.")
    
    
    @field_validator('id')
    def validate_id(cls, v):
        pattern = r'^\d{1,4}/\d{1,4}/\d{1,4}$'
        if not re.match(pattern, v):
            raise ValueError('Qualification number must be in the format of digits separated by slashes (e.g., "603/4162/2")')
        return v
        
