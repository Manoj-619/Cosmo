from dataclasses import Field
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.fallback import FallbackModel
from pydantic import BaseModel
import logfire

import os
from dotenv import load_dotenv

load_dotenv()

# logfire.configure(scrubbing=False)

from helpers.chat import get_prompt
import codecs
import yaml

anthropic_model = AnthropicModel('claude-3-5-sonnet-latest')
openai_model    = OpenAIModel(model_name='gpt-4o')
azure_model     = OpenAIModel(
    'gpt-4o',
    provider=AzureProvider(
        azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
        api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
        api_key=os.getenv('AZURE_OPENAI_API_KEY'),
    )
)
model = FallbackModel(openai_model, azure_model)

class Deps(BaseModel):
    email: str
    stage_name: str = Field(default='profile')

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