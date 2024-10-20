import inspect
import os
import codecs
import yaml
from datetime import datetime
from typing import Union, Callable
from pydantic import BaseModel
import openai
from rich.console import Console
from rich.text import Text

console = Console()

def debug_print(debug: bool, *args: str) -> None:
    if not debug:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = " ".join(map(str, args))
    console.print(Text(f"[{timestamp}] {message}", style="dim"))

def merge_fields(target, source):
    for key, value in source.items():
        if isinstance(value, str):
            target[key] += value
        elif value is not None and isinstance(value, dict):
            merge_fields(target[key], value)


def merge_chunk(final_response: dict, delta: dict) -> None:
    delta.pop("role", None)
    merge_fields(final_response, delta)

    tool_calls = delta.get("tool_calls")
    if tool_calls and len(tool_calls) > 0:
        index = tool_calls[0].pop("index")
        merge_fields(final_response["tool_calls"][index], tool_calls[0])




def function_to_json(func_or_model: Union[Callable, BaseModel]) -> dict:
    """
    Converts a Python function or Pydantic BaseModel into a JSON-serializable dictionary
    that describes the function's signature or model's schema.

    Args:
        func_or_model: The function or Pydantic BaseModel to be converted.

    Returns:
        A dictionary representing the function's signature or model's schema in JSON format.
    """
    # IMPORTANT: Extended to support pydantic models.
    if isinstance(func_or_model, type) and issubclass(func_or_model, BaseModel):
        return openai.pydantic_function_tool(func_or_model)
    
    elif callable(func_or_model):
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
            type(None): "null",
        }

        try:
            signature = inspect.signature(func_or_model)
        except ValueError as e:
            raise ValueError(
                f"Failed to get signature for function {func_or_model.__name__}: {str(e)}"
            )

        parameters = {}
        for param in signature.parameters.values():
            try:
                param_type = type_map.get(param.annotation, "string")
            except KeyError as e:
                raise KeyError(
                    f"Unknown type annotation {param.annotation} for parameter {param.name}: {str(e)}"
                )
            parameters[param.name] = {"type": param_type}

        required = [
            param.name
            for param in signature.parameters.values()
            if param.default == inspect._empty
        ]

        return {
            "type": "function",
            "function": {
                "name": func_or_model.__name__,
                "description": func_or_model.__doc__ or "",
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required,
                },
            },
        }
    
    else:
        raise ValueError("Input must be either a callable function or a Pydantic BaseModel")
