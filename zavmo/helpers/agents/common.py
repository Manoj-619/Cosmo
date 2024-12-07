import os
import codecs
import yaml
from typing import Dict
from helpers.chat import get_prompt
from stage_app.models import UserProfile, TNAassessment
import json

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

def load_nos_competencies():
    """
    Load NOS competencies JSON data from the specified file.

    Returns:
        dict: A dictionary containing the NOS competencies JSON data.
    """
    json_path = os.path.join("assets/nos/sales/INSSAL014.json")
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def compile_system_content(competencies_to_assess, all_competencies, prompt_context):
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
        criterias = [c['blooms_taxonomy_criteria'] for c in all_competencies if c['competency'] == competencies_to_assess[0]][0]  
        criterias = "\n".join([f"- {c['level']}: {c['criteria']}" for c in criterias])
        prompt_context['nos_competency_with criteria'] = f"Competency: {competencies_to_assess[0]}\nCriteria:\n{criterias}"
        
        attach = "**Important**:\n - The assessment for shared competency will be considered complete if details of the competency is saved."
    else:
        attach = f"""No NOS Competencies left to assess.\nHandoff instructions:\nWhen no NOS Competency is provided to assess, seamlessly hand off to the next stage: The Discovery stage of the 4-D Learning Journey.\nThis stage involves a detailed gap analysis between current competencies and future competencies required as per NOS. Learning goals, interests, and preferred learning styles will be identified, creating a roadmap for a personalized and engaging learning journey."""
    
    system_content  = get_prompt('tna_assessment.md', 
                                    context=prompt_context,
                                    prompt_dir="assets/prompts")
    system_content += attach 
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
    agent_keys       = ['name', 'description', 'instructions', 'examples']
    prompt_context   = {k:v for k,v in conf_data.items() if k in agent_keys}
    all_competencies = load_nos_competencies()

    user_profile = UserProfile.objects.get(user__email=context['email'])

    tna_assessments = TNAassessment.objects.filter(user__email=context['email'], sequence_id=context['sequence_id'])
    if tna_assessments.count()==1:  # Changed to check for zero assessments
        competency_names = [c['competency'] for c in all_competencies]
        # Create new TNAassessment objects for each competency
        for competency in competency_names:
            TNAassessment.objects.create(
                user=user_profile.user,
                sequence_id=context['sequence_id'],
                competency=competency
            )    
        # Delete TNAassessment objects with no competency, as it is no longer needed
        TNAassessment.objects.filter(user__email=context['email'], sequence_id=context['sequence_id']).first().delete()
        tna_assessments = TNAassessment.objects.filter(user__email=context['email'], sequence_id=context['sequence_id'])
    
    competencies_to_assess = [assessment.competency for assessment in tna_assessments 
                              if not assessment.evidence_of_competency]
    
    system_content = compile_system_content(competencies_to_assess, all_competencies, prompt_context)
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