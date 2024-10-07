import json
from functools import wraps
from typing import Any, Callable, List, Type, Union
from pydantic import BaseModel, Field, validate_call

def remove_single_quotes(text: str) -> str:
    """
    Remove single quotes from a given text.

    Args:
        text (str): The input text.

    Returns:
        str: The text with single quotes removed.
    """
    return text.replace("'", "")

def _remove_a_key(d: Union[dict, list], remove_key: str) -> None:
    """
    Remove a key from a dictionary or a list of dictionaries recursively.

    Args:
        d (Union[dict, list]): The dictionary or list of dictionaries.
        remove_key (str): The key to be removed.
    """
    if isinstance(d, dict):
        for key in list(d.keys()):
            if key == remove_key:
                del d[key]
            else:
                _remove_a_key(d[key], remove_key)
    elif isinstance(d, list):
        for item in d:
            _remove_a_key(item, remove_key)

def generate_openai_schema(schema: dict, name: str, description: str) -> dict:
    """
    Generate OpenAI compatible schema from the given schema dictionary.

    Args:
        schema (dict): The Pydantic schema dictionary.
        name (str): The name of the function or class.
        description (str): The description of the function or class.

    Returns:
        dict: A dictionary in the format of OpenAI's schema as jsonschema.
    """
    parameters = {k: v for k, v in schema.items() if k not in ("title", "description")}
    parameters["required"] = sorted(parameters["properties"])
    _remove_a_key(parameters, "title")
    _remove_a_key(parameters, "additionalProperties")

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        }
    }

class openai_function:
    """
    Decorator to convert a function into an OpenAI function.

    This decorator validates the function using Pydantic, generates the schema from
    the function signature, and prepares it for use with OpenAI's API.

    Example:
        ```python
        @openai_function
        def sum(a: int, b: int) -> int:
            return a + b

        completion = openai.ChatCompletion.create(
            ...
            messages=[{
                "content": "What is 1 + 1?",
                "role": "user"
            }]
        )
        sum.from_response(completion)
        # 2
        ```
    """

    def __init__(self, func: Callable) -> None:
        self.func = func
        self.validate_func = validate_call(func)
        self.model = self.validate_func.model
        schema = self.validate_func.model.schema()
        self.openai_schema = generate_openai_schema(
            schema, self.func.__name__, self.func.__doc__
        )

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        @wraps(self.func)
        def wrapper(*args, **kwargs):
            return self.validate_func(*args, **kwargs)
        return wrapper(*args, **kwargs)

    def from_response(self, response: Any, throw_error: bool = True) -> Any:
        """
        Parse the response from OpenAI's API and return the function call result.

        Args:
            response (Any): The response from OpenAI's API.
            throw_error (bool): Whether to throw an error if the response does not contain a function call.

        Returns:
            Any: The result of the function call.
        """
        message = response.choices[0].message
        tool_calls = message.tool_calls

        if throw_error:
            assert len(tool_calls) > 0, "No tool calls detected"
            assert tool_calls[0].function.name == self.openai_schema['function']["name"], "Function name does not match"

        try:
            func_args = tool_calls[0].function.arguments
            arguments = json.loads(func_args)
        except json.JSONDecodeError:
            raise ValueError(f"Arguments {func_args} are not valid JSON")
        return self.validate_func(**arguments)

class OpenAISchema(BaseModel):
    @classmethod
    def openai_schema(cls) -> dict:
        """
        Return the schema in the format of OpenAI's schema as jsonschema.

        Note:
            It's important to add a docstring to describe how to best use this class,
            it will be included in the description attribute and be part of the prompt.

        Returns:
            dict: A dictionary in the format of OpenAI's schema as jsonschema.
        """
        schema = cls.schema()
        description = cls.__doc__ or f"Correctly extracted `{cls.__name__}` with all the required parameters with correct types"
        return generate_openai_schema(schema, cls.__name__, description)

    @classmethod
    def from_response(cls, completion: Any, throw_error: bool = True) -> 'OpenAISchema':
        """
        Execute the function from the response of an OpenAI chat completion.

        Args:
            completion (Any): The response from an OpenAI chat completion.
            throw_error (bool): Whether to throw an error if the function call is not detected.

        Returns:
            OpenAISchema: An instance of the class.
        """
        message = completion.choices[0].message
        tool_calls = message.tool_calls

        if throw_error:
            assert len(tool_calls) > 0, "No tool calls detected"
            assert tool_calls[0].function.name == cls.openai_schema()["function"]["name"], "Function name does not match"

        try:
            func_args = tool_calls[0].function.arguments
            arguments = json.loads(func_args)
        except json.JSONDecodeError:
            raise ValueError(f"Arguments {func_args} are not valid JSON")
        return cls(**arguments)

    @classmethod
    def from_arguments(cls, arguments: dict, throw_error: bool = True) -> 'OpenAISchema':
        """
        Create an instance of the class from a dictionary of arguments.

        Args:
            arguments (dict): The arguments to create the class instance.
            throw_error (bool): Whether to throw an error if the arguments are not valid.

        Returns:
            OpenAISchema: An instance of the class.
        """
        if throw_error:
            missing_fields = [field for field in cls.__fields__ if field not in arguments]
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
        return cls(**arguments)

def openai_schema(cls: Type[BaseModel]) -> Type[BaseModel]:
    """
    Decorator to convert a Pydantic BaseModel into an OpenAI schema-compatible class.

    Args:
        cls (Type[BaseModel]): The Pydantic BaseModel class to be decorated.

    Returns:
        Type[BaseModel]: The decorated class.
    """
    if not issubclass(cls, BaseModel):
        raise TypeError("Class must be a subclass of pydantic.BaseModel")

    @wraps(cls, updated=())
    class Wrapper(cls, OpenAISchema):  # type: ignore
        pass

    return Wrapper