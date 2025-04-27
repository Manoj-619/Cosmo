
import os
import codecs
import yaml
from helpers.chat import get_prompt
# --- Add necessary imports ---
from stage_app.models import TNAassessment, FourDSequence, DeliverStage # Import models
from django.core.exceptions import ObjectDoesNotExist
# --- End imports ---

def get_yaml_data(yaml_path, yaml_dir="assets/data"):
    """Load a YAML file containing field data.

    Args:
        yaml_path (str): Path to the YAML file (with or without extension)
        yaml_dir (str, optional): Directory containing the YAML file. 
            Defaults to 'assets/data'. If None, uses absolute path from module.

    Returns:
        dict: Parsed YAML content as a dictionary

    Raises:
        UnicodeDecodeError: If there's an encoding issue with the file
        yaml.YAMLError: If there's an issue parsing the YAML content
        FileNotFoundError: If the specified file doesn't exist
        ValueError: If the file path is invalid

    Example:
        >>> data = get_yaml_data('profile')
        >>> data = get_yaml_data('profile.yaml')
    """
    # Convert relative path to absolute if default directory is used
    if yaml_dir == "assets/data":
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        yaml_dir = os.path.join(base_dir, 'assets', 'data')
    
    # Normalize path and add extension if needed
    if not yaml_path.lower().endswith(('.yaml', '.yml')):
        yaml_path += '.yaml'
    
    # Construct full path
    yaml_path = os.path.join(yaml_dir, yaml_path)
    
    try:
        with codecs.open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(f"Encoding error in file {yaml_path}: {e}\n"
                               "Make sure the file is saved with UTF-8 encoding.")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"YAML parsing error in file {yaml_path}: {e}")
    except FileNotFoundError:
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")


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


# +++ Add the new function +++
def get_module_ids(sequence_id):
    """
    Fetches the NOS ID and OFQUAL ID associated with a given sequence.

    Currently fetches from the first TNAassessment record linked to the sequence.
    Future enhancement could involve matching based on a specific module name
    if the TNAassessment or another model stores that relationship.

    Args:
        sequence_id: The ID of the FourDSequence.

    Returns:
        A dictionary containing 'nos_id' and 'ofqual_id', or None for each
        if not found or if the sequence doesn't exist. Returns {'nos_id': None, 'ofqual_id': None} on error.
    """
    nos_id = None
    ofqual_id = None

    try:
        # We don't strictly need the sequence object itself for this logic,
        # but it's good practice to ensure the sequence exists.
        # sequence = FourDSequence.objects.get(id=sequence_id) # Uncomment if needed later

        # Fetch the first TNA assessment linked to this sequence
        assessment = TNAassessment.objects.filter(sequence_id=sequence_id).first()

        if assessment:
            nos_id = assessment.nos_id
            ofqual_id = assessment.ofqual_id

        return {'nos_id': nos_id, 'ofqual_id': ofqual_id}

    except ObjectDoesNotExist:
        print(f"Warning: Sequence or related TNAAssessment not found for sequence_id: {sequence_id}")
        return {'nos_id': None, 'ofqual_id': None}
    except Exception as e:
        print(f"Error fetching module IDs for sequence_id {sequence_id}: {e}")
        return {'nos_id': None, 'ofqual_id': None}
# +++ End new function +++