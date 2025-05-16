# _types.py
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
        # Ensure description is not None before any string operations like capitalize
        desc = self.description if self.description is not None else ""
        # Capitalize only if there's content
        desc_formatted = desc.capitalize() if desc else ""
        return f"{desc_formatted}\n{criteria_formatted}".strip() # strip to remove leading/trailing whitespace if fields are empty


class Unit(BaseModel):
    id: str = Field(description="Unit ID, usually a backslash separated string.")
    title: str = Field(description="Unit Title")
    description: str = Field(description="A description of the unit.")
    learning_outcomes: List[LearningOutcome] = Field(description="Learning Outcomes")

    def to_dict(self):
        # Format learning outcomes using their __str__ method
        learning_outcomes_formatted = []
        for i, outcome in enumerate(self.learning_outcomes):
             formatted_outcome_str = str(outcome).strip() # Use the __str__ method and strip whitespace
             if formatted_outcome_str: # Only add if the formatted string is not empty
                 learning_outcomes_formatted.append(f"{i+1}. {formatted_outcome_str}")

        return {
            "unit_id": self.id,
            "unit_title": self.title,
            "unit_description": self.description,
            "unit_learning_outcomes": "\n".join(learning_outcomes_formatted)
        }


class Ofqual(BaseModel):
    """Ofqual Qualification Details"""
    id: str = Field(description="The qualification number/ID of the qualification in format like '603/4162/2'.")
    overview: str = Field(description="A brief overview of the qualification.")
    units: List[Unit] = Field(description="The units of the qualification.")
    qualification_type: Optional[str] = Field(default=None, description="The type of qualification, e.g. 'Occupational Qualification'.")
    qualification_level: Optional[int] = Field(default=None, description="The level of the qualification, e.g. 1, 2, 3, etc.")
    assessment_methods: Optional[str] = Field(default=None, description="The assessment methods of the qualification.")
    sector_subject_area: Optional[str] = Field(default=None, description="The sector subject area of the qualification.")
    awarding_organisation: Optional[str] = Field(default=None, description="The awarding organisation of the qualification.")
    total_credits: Optional[int] = Field(default=None, description="The total credits for the qualification.")
    guided_learning_hours: Optional[int] = Field(default=None, description="The guided learning hours of the qualification.")
    total_qualification_time: Optional[int] = Field(default=None, description="The total qualification time of the qualification.")
    
    @field_validator('id')
    def validate_id(cls, v):
        pattern = r'^\d{1,4}/\d{1,4}/\d{1,4}$'
        if not re.match(pattern, v):
            raise ValueError('Qualification number must be in the format of digits separated by slashes (e.g., "603/4162/2")')
        return v

    def to_dict(self):
        return {
            "ofqual_id": self.id,
            "overview": self.overview,
            "qualification_type": self.qualification_type,
            "qualification_level": self.qualification_level,
            "assessment_methods": self.assessment_methods,
            "sector_subject_area": self.sector_subject_area,
            "awarding_organisation": self.awarding_organisation,
            "total_credits": self.total_credits,
            "guided_learning_hours": self.guided_learning_hours,
            "total_qualification_time": self.total_qualification_time,
        }

    def get_table(self):
        # This method combines the Ofqual-level details (now including metadata)
        # with the details of each unit to create rows for a DataFrame.
        units_data = []
        ofqual_base_data = self.to_dict()

        if self.units:
            for unit in self.units:
                # Merge Ofqual details with Unit details
                units_data.append({**ofqual_base_data, **unit.to_dict()})
        else:
             # Handle qualifications with no units - create a DataFrame with just the Ofqual details
             units_data.append(ofqual_base_data)

        return pd.DataFrame(units_data)


class InvalidQualification(BaseModel):
    """Exception raised when the qualification is invalid"""
    rationale: str = Field(description="The rationale for the invalidity of the qualification")