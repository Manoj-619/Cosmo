import os
import codecs
import yaml
from typing import Dict, List, Literal
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



def get_tna_assessment_instructions(context: Dict, level: str):
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
    
    competency_to_assess = [{'assessment_area':assessment.assessment_area, 
                               'criterias':assessment.criterias} 
                                for assessment in tna_assessments if assessment.status == 'In Progress']
    

    ## bloom's taxonomy level based instructions

    if competency_to_assess:
        criterias = competency_to_assess[0]['criterias']
        if level:
            level_based_marks_scheme = [item for item in criterias if item['bloom_taxonomy_level'] == level][0]
            criteria     = level_based_marks_scheme['criteria']
            expectations = level_based_marks_scheme['expectations']
            task         = level_based_marks_scheme['task']
            benchmarking_response = level_based_marks_scheme['benchmarking_responses']
            benchmarking_responses = "\n\n".join([f"**{grade.upper().replace('_', '')}:** {description}" for grade, description in benchmarking_response])
            
            criteria_text = "\n".join(criteria)
            expectations_text = "\n".join(expectations)
            
            ofqual_based_instructions = (
                f"- **Assessment Area:** {competency_to_assess[0]['assessment_area']}\n"
                f"- **Current Bloom's Taxonomy Level mapped to User facing level:** {level} (While addressing about the level, use the level in User facing scale)\n"
                f"- **Criteria:** {criteria_text}\n\n"
                f"- **Task:** {task}\n\n"
                f"- **Expectations:** {expectations_text}\n\n"
                f"- **Benchmarking Responses for validation:** \n\n{benchmarking_responses}\n\n"
            )
            logging.info(f"OFQUAL based instructions: {ofqual_based_instructions}")
            prompt_context['nos_area_with_criteria'] = ofqual_based_instructions
        else:
            prompt_context['nos_area_with_criteria'] = f"Assessment Area: **{competency_to_assess[0]['assessment_area']}**"
    else:
        prompt_context['nos_area_with_criteria'] = "No NOS Areas left to assess."

    system_content  = get_prompt('tna_assessment.md', 
                                    context=prompt_context,
                                    prompt_dir="assets/prompts")
                                    
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