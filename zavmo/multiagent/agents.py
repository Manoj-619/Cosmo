from core import Agent
from _types import Result

# Handoff functions


def transfer_to_discuss():
    """Transition to the Discuss Agent."""
    print("Transferring to Discuss Agent...")
    return discuss_agent


def transfer_to_discover():
    """Transition to the Discover Agent."""
    print("Transferring to Discover Agent...")
    return discover_agent


def transfer_to_deliver():
    """Transition to the Deliver Agent."""
    print("Transferring to Deliver Agent...")
    return deliver_agent


def transfer_to_demonstrate():
    """Transition to the Demonstrate Agent."""
    print("Transferring to Demonstrate Agent...")
    return demonstrate_agent


# Define the Discover Agent
discover_agent = Agent(
    name="Discover Agent",
    instructions="You are the Discover Agent. Gather learning goals and preferences from the user.",
    functions=[transfer_to_discuss],
)

# Define the Discuss Agent
discuss_agent = Agent(
    name="Discuss Agent",
    instructions="You are the Discuss Agent. Discuss and refine the learning goals with the user.",
    functions=[transfer_to_deliver],
)

# Define the Deliver Agent
deliver_agent = Agent(
    name="Deliver Agent",
    instructions="You are the Deliver Agent. Provide learning materials and resources.",
    functions=[transfer_to_demonstrate],
)

# Define the Demonstrate Agent
demonstrate_agent = Agent(
    name="Demonstrate Agent",
    instructions="You are the Demonstrate Agent. Evaluate the user's understanding through assessments.",
    functions=[],
)
