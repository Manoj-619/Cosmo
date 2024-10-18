import os
import ast
import json
import yaml  # Add this import at the top of the file
import codecs
from functools import wraps
from pydantic import BaseModel, create_model, Field, validate_call
from typing import Any, Callable, List, Type, Union, Dict, Optional, get_type_hints, Annotated
from helpers.chat import get_prompt
from enum import Enum

# Mapping of basic type names to actual Python types
basic_types = {
    'str': str, 'int': int, 'float': float, 'bool': bool, 
    'Any': Any, 'Dict': Dict, 'List': List, 'Optional': Optional, 'Union':Union,
}



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


def format_field(field, mode='probe'):
    """
    Create a markdown-formatted text for a given field.

    Args:
        field (dict): A dictionary containing field information.

    Returns:
        str: Markdown-formatted text for the field.
    """
    markdown = f"**{field['title']}**\n\n"
    markdown += f"{field['description']}\n\n"

    if mode == 'probe':
        if 'probe_questions' in field:
            markdown += "> Questions to probe for this attribute:\n"
            for question in field['probe_questions']:
                markdown += f"- {question}\n"
            markdown += "\n"
        
        if 'user_responses' in field:
            markdown += "> Examples of learner responses:\n"
            for example in field['user_responses']:
                markdown += f"- {example}\n"
            markdown += "\n"

        if 'probe_responses' in field:
            markdown += "> Examples of Zavmo's responses:\n"
            for response in field['probe_responses']:
                markdown += f"- {response}\n"
            markdown += "\n"
    else:
        if 'extract_examples' in field:
            markdown += "> Examples of learner responses and what we are extracting:\n"
            for example in field['extract_examples']:
                markdown += f"- {example}\n"
            markdown += "\n"

    return markdown



def eval_type_ast(node):
    """
    Recursively evaluates an AST node representing a type.
    """
    if isinstance(node, ast.Name):
        type_name = node.id
        if type_name in basic_types:
            return basic_types[type_name]
        else:
            raise ValueError(f"Unknown type '{type_name}'")
    elif isinstance(node, ast.Subscript):
        # Handle generic types like List[str], Optional[int]
        value = eval_type_ast(node.value)
        if isinstance(node.slice, ast.Index):
            # For Python <3.9
            slice_value = eval_type_ast(node.slice.value)
        else:
            # For Python 3.9+
            slice_value = eval_type_ast(node.slice)
        return value[slice_value]
    elif isinstance(node, ast.Tuple):
        # Handle Union types like Union[str, int]
        return tuple(eval_type_ast(elt) for elt in node.elts)
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        # Handle Union types using '|', e.g., str | int
        left = eval_type_ast(node.left)
        right = eval_type_ast(node.right)
        return Union[left, right]
    elif isinstance(node, ast.Attribute):
        # Handle types like typing.Any
        value = eval_type_ast(node.value)
        attr = node.attr
        return getattr(value, attr)
    else:
        raise ValueError(f"Unsupported type expression: {ast.dump(node)}")
    
def parse_type(type_str: str):
    """
    Parses a type string and returns the corresponding Python type.
    """
    try:
        # Parse the type string into an AST node
        type_ast = ast.parse(type_str, mode='eval').body
        # Recursively evaluate the AST node to get the type
        return eval_type_ast(type_ast)
    except Exception as e:
        raise ValueError(f"Error parsing type '{type_str}': {e}")        
    
    
def create_model_fields(fields, use_keys=['description', 'enum']):
    """
    Dynamically creates fields for the model using Annotated and Field.

    Args:
        fields (list): A list of dictionaries containing field data.
        use_keys (list): Keys to include in the Field object. Defaults to ['description', 'enum'].

    Returns:
        dict: A dictionary of model fields.
    """
    model_fields = {}
    for field_data in fields:
        field_name = field_data['title']
        annotation_str = field_data['annotation']
        
        if annotation_str == 'Enum' and 'enum' in field_data:
            # Create a dynamic Enum class
            enum_name = f"{field_name.capitalize()}Enum"
            enum_class = Enum(enum_name, {v: v for v in field_data['enum']})
            field_annotation = enum_class
        else:
            field_annotation = parse_type(annotation_str)
        
        field_kwargs = {k: v for k, v in field_data.items() if k in use_keys}
        field = Field(**field_kwargs)
        model_fields[field_name] = Annotated[field_annotation, field]
    
    return model_fields

def create_pydantic_model(name: str, fields: List[Dict[str, Any]], description: str = None):
    """
    Dynamically creates a Pydantic model based on the provided name, description (optional), and fields.

    Args:
        name (str): The name of the model.
        description (str, optional): The description of the model. Defaults to None.
        fields (List[Dict[str, Any]]): A list of dictionaries containing field data.

    Returns:
        Type[BaseModel]: A dynamically created Pydantic model.
    """
    model_fields = create_model_fields(fields)
    
    model_attributes = {
        'model_config': {'title': name},
    }
    
    if description:
        model_attributes['__doc__'] = description
    
    return create_model(name, **model_fields, **model_attributes)


def create_system_message(stage_name, conf_data, mode='probe'):
    """
    Create a system message for either probing or extracting.

    Args:
        stage_name (str): The name of the current stage.
        conf_data (dict): Configuration data containing model information.
        mode (str): Either 'probe' or 'extract'. Defaults to 'probe'.

    Returns:
        dict: A system message for the specified mode.
    """
    fields         = conf_data['fields']
    instructions   = '\n\n'.join([format_field(f, mode) for f in fields])
    system_content = get_prompt(f"{mode}").format(STAGE=stage_name.title(),
                                                  DESCRIPTION=conf_data['description'],
                                                  INSTRUCTIONS=instructions,
                                                  NEXT_STAGE=conf_data['next_stage'],
                                                  NEXT_STAGE_DESCRIPTION=conf_data['next_stage_description']
                                                  )
    return {"role": "system", "content": system_content}
