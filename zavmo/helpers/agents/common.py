import os
import codecs
import yaml
from typing import Dict
from helpers.chat import get_prompt
from stage_app.models import TNAassessment
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
 
    competency_to_assess = TNAassessment.objects.filter(user__email=context['email'], 
                                                        sequence_id=context['sequence_id'], 
                                                        status='In Progress')
    
    ## bloom's taxonomy level based instructions
    if competency_to_assess.exists():
        competency_to_assess = competency_to_assess.first()
        if level:
            level_based_marks_scheme = [item for item in competency_to_assess.ofqual_criterias if item['bloom_taxonomy_level'] == level][0]
            
            criteria     = level_based_marks_scheme['criteria']
            expectations = level_based_marks_scheme['expectations']
            task         = level_based_marks_scheme['task']

            benchmarking_responses = level_based_marks_scheme['benchmarking_responses']
            benchmarking_responses = "\n\n".join([f"   **{item['grade'].upper()}:** {item['example']}" for item in benchmarking_responses])
            
            ofqual_based_instructions = (
                f"- **Assessment Area:** {competency_to_assess.assessment_area}\n\n"
                f"- **Current Bloom's Taxonomy Level mapped to User facing scale is:** {level} (But While addressing about the level, use the level in User facing scale)\n\n"
                f"- **Criteria:** {criteria}\n\n"
                f"- **Task:** {task}\n\n"
                f"- **Expectations:** {expectations}\n\n"
                f"- **Benchmarking Responses for validation:** \n\n{benchmarking_responses}\n\n"
            )
            logging.info(f"OFQUAL based instructions for evaluation: {ofqual_based_instructions}")
            prompt_context['assessment_area_with_criteria'] = ofqual_based_instructions
        else:
            prompt_context['assessment_area_with_criteria'] = f"Assessment Area: **{competency_to_assess.assessment_area}**"
    else:
        prompt_context['assessment_area_with_criteria'] = "No Assessment Areas left to assess. Transfer to Discussion stage."

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