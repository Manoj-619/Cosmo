from dotenv import load_dotenv
from typing import Union
from pydantic_ai.messages import ModelMessage
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.settings import ModelSettings
from _types import Ofqual, InvalidQualification
from utils import get_prompt
import logfire

load_dotenv()

logfire.configure(scrubbing=False)
Agent.instrument_all()



ofqual_agent = Agent(
    'openai:gpt-4o-mini',
    result_type=Union[Ofqual,InvalidQualification],
    model_settings=ModelSettings(parallel_tool_calls=True),
    system_prompt=get_prompt('system',prompt_dir="")
)

@ofqual_agent.tool_plain
def evaluate(evaluation:str, likelihood:str) -> str:
    """Evaluate whether the document is a valid qualification specification.

    Args:
        evaluation: Brief Assessment of the document.
        likelihood: Likelihood of the document being a valid qualification specification
    """
    return f"Evaluation:\n{evaluation}\n\nLikelihood:\n{likelihood}"