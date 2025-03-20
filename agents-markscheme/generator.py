from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext, Tool, ModelRetry
from typing import List
from pydantic_ai.settings import ModelSettings
from _types import MarkSchemeItem, GradingScale
from utils import get_prompt
import logfire

load_dotenv()

logfire.configure(scrubbing=False)


markscheme_agent = Agent(
    'openai:gpt-4o-mini',
    result_type=List[MarkSchemeItem],
    # model_settings=ModelSettings(parallel_tool_calls=False),
    system_prompt=get_prompt('system', prompt_dir=""),
    instrument=True,
    retries=3
)


@markscheme_agent.result_validator
def validate_markscheme(result: List[MarkSchemeItem]) -> List[MarkSchemeItem]:
    """Validate the markscheme for a given ofqual unit.

    Args:
        result: The markscheme to validate.
    """
    # Check if all Bloom's Taxonomy levels are present
    blooms_levels = set([item.bloom_taxonomy_level for item in result])
    missing_levels = set(["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]) - blooms_levels
    if missing_levels:
        raise ModelRetry("Missing Bloom's Taxonomy levels: " + ", ".join(missing_levels))
    
    # For each result item, check if all 4 grading scales are present
    for item in result:
        grading_scales = set([scale.grade for scale in item.benchmarking_responses])
        missing_scales = set(["fail", "pass", "merit", "distinction"]) - grading_scales
        if missing_scales:
            raise ModelRetry("Missing grading scales for " + item.bloom_taxonomy_level + ": " + ", ".join(missing_scales))    
    return result