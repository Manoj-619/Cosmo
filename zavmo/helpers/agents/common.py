import os
import codecs
import yaml
from typing import Dict
from helpers.chat import get_prompt
from stage_app.models import UserProfile, TNAassessment
import json
import logging

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


def compile_system_content(competencies_to_assess,prompt_context):
    """
    Compile system content for the TNA assessment agent.

    Args:
        competencies_to_assess (list): List of competencies to assess.
        all_competencies (list): List of all NOS competencies with criteria from a JSON file.
        prompt_context (dict): Context for the prompt.

    Returns:
        str: System content for the TNA assessment agent.
    """
    if len(competencies_to_assess)>=1:
        criterias = competencies_to_assess[0]['blooms_taxonomy_criteria']
        criterias = "\n".join([f"- {c['level']}: {c['criteria']}" for c in criterias])
        prompt_context['nos_area_with_criteria'] = f"""Assessment Area: {competencies_to_assess[0]['assessment_area']}\nCriteria:\n{criterias}\n\n**Important**:\n - The assessment for shared Assesment area will be considered complete if details of the assessment area is saved."""
    else:
        prompt_context['nos_area_with_criteria'] = "No NOS Areas left to assess."

    system_content  = get_prompt('tna_assessment.md', 
                                    context=prompt_context,
                                    prompt_dir="assets/prompts")
    return system_content

def get_tna_assessment_instructions(context: Dict):
    """
    Compile instructions for the tna assessment agent.

    Args:
        context (dict): Context for the TNA assessment.

    Returns:
        str: Instructions for the agent.
    """

    conf_data        = get_yaml_data('tna_assessment')
    agent_keys       = ['name', 'description', 'instructions', 'examples', 'completion_condition', 'next_stage', 'next_stage_description']
    prompt_context   = {k:v for k,v in conf_data.items() if k in agent_keys}
 
    tna_assessments = TNAassessment.objects.filter(user__email=context['email'], sequence_id=context['sequence_id'])
    
    competencies_to_assess = [{'assessment_area':assessment.assessment_area, 'blooms_taxonomy_criteria':assessment.blooms_taxonomy_criteria} 
                              for assessment in tna_assessments if not assessment.evidence_of_assessment]
    
    system_content = compile_system_content(competencies_to_assess, prompt_context)
    return system_content 

###### Agent Instructions ######


def get_agent_instructions(stage_name: str) -> str:
    """
    Compile instructions for the agent.
    
    Args:
        stage_name (str): The name of the current stage.

    Returns:
        str: Instructions for the agent.
    """
    conf_data       = get_yaml_data(stage_name.lower())
    agent_keys      = ['name', 'description', 'instructions', 'examples', 'completion_condition', 'next_stage', 'next_stage_description']
    prompt_context  = {k:v for k,v in conf_data.items() if k in agent_keys}

    system_content  = get_prompt('probe.md', 
                                    context=prompt_context,
                                    prompt_dir="assets/prompts")
    return system_content   