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
import openai