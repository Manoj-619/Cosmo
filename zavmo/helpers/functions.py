import ast
import json
from functools import wraps
from pydantic import BaseModel, create_model, Field, validate_call
from typing import Any, Callable, List, Type, Union, Dict, Optional, get_type_hints, Annotated

# Mapping of basic type names to actual Python types
basic_types = {
    'str': str, 'int': int, 'float': float, 'bool': bool, 
    'Any': Any, 'Dict': Dict, 'List': List, 'Optional': Optional, 'Union':Union,
}
    
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
    
    
def create_model_fields(fields):
    """
    Dynamically creates fields for the model using Annotated and Field.

    Args:
        fields (list): A list of dictionaries containing field data.

    Returns:
        dict: A dictionary of model fields.
    """
    model_fields = {}
    for field_data in fields:
        field_name = field_data['title']
        annotation_str = field_data['annotation']  # Annotation is now required
        field_annotation = parse_type(annotation_str)
        field = Field(**{k: v for k, v in field_data.items() if k not in ['title', 'annotation']})
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
