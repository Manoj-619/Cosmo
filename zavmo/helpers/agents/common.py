import os
import codecs
import yaml
from pydantic import BaseModel, Field
from typing import List
from helpers.swarm import Agent

def get_yaml_data(yaml_path, yaml_dir="assets/data"):
    """Load a YAML file containing field data.

    Args:
        yaml_path (str): Path to the YAML file.
        yaml_dir (str, optional): Directory containing the YAML file. Defaults to 'assets/data'.

    Returns:
        dict: A dictionary of field data.

    Raises:
        UnicodeDecodeError: If there's an encoding issue with the file.
        yaml.YAMLError: If there's an issue parsing the YAML content.
        FileNotFoundError: If the specified file doesn't exist.
    """
    # Check if yaml_path ends with .yaml or .yml
    if not yaml_path.endswith(('.yaml', '.yml')):
        yaml_path += '.yaml'
    yaml_path = os.path.join(yaml_dir, yaml_path)
    
    try:
        with codecs.open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except UnicodeDecodeError as e:
        print(f"Encoding error in file {yaml_path}: {e}")
        print("Make sure the file is saved with UTF-8 encoding.")
        raise
    except yaml.YAMLError as e:
        print(f"YAML parsing error in file {yaml_path}: {e}")
        raise
    except FileNotFoundError:
        print(f"File not found: {yaml_path}")
        raise
    

###### Curriculum Schema ######

class LearningOutcome(BaseModel):
    description: str = Field(..., description="Description of the learning outcome")
    assessment_criteria: List[str] = Field(..., description="List of assessment criteria for the learning outcome")


class Lesson(BaseModel):
    title: str = Field( description="The title of the lesson")
    content: str = Field( description="The main content of the lesson")
    examples: List[str] = Field( description="List of examples to illustrate the lesson")
    exercises: List[str] = Field( description="List of exercises for the learner to practice")

class Module(BaseModel):
    title: str = Field(description="The title of the module")
    learning_outcomes: List[str] = Field(description="Learning outcomes for the module")
    lessons: List[str] = Field(description="List of lessons in this module")
    duration: int = Field(description="The total duration of the module in hours")

class Curriculum(BaseModel):
    title: str = Field(description="The title of the curriculum")
    subject: str = Field(description="The main subject area of the curriculum")
    level: str = Field(description="The difficulty level of the curriculum (e.g., beginner, intermediate, advanced)")
    prerequisites: List[str] = Field(description="Any prerequisites needed to undertake this curriculum")
    modules: List[Module] = Field(description="List of modules included in the curriculum")


def get_agent_instructions(stage_name: str) -> str:
    """
    Compile instructions for the agent.
    
    Args:
        stage_name (str): The name of the current stage.

    Returns:
        str: Instructions for the agent.
    """
    conf_data       = get_yaml_data(stage_name.lower())
    prompt_path     = os.path.join("assets/prompts/probe.md")
    prompt_template = open(prompt_path, "r", encoding="utf-8").read()
    system_content  = prompt_template.format(NAME=conf_data['name'],
                                            DESCRIPTION=conf_data['description'],
                                            INSTRUCTIONS=conf_data['instructions'],
                                            EXAMPLES=conf_data['examples'],
                                            COMPLETION_CONDITION=conf_data['completion_condition'],
                                            NEXT_STAGE=conf_data['next_stage'],
                                            NEXT_STAGE_DESCRIPTION=conf_data['next_stage_description']
                                            )
    return system_content