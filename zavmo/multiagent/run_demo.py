from core import Swarm
from agents.a_discover import discover_agent
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown

DEBUG = True

console = Console()

def print_agent_message(agent_name, message):
    markdown = Markdown(message)
    console.print(Panel(markdown, title=f"[bold blue]{agent_name}[/bold blue]", expand=False))

def print_user_message(message):
    console.print(Panel(Text(message, style="green"), title="[bold green]User[/bold green]", expand=False))

def print_system_message(message):
    console.print(Text(message, style="yellow"))

def main():
    swarm = Swarm()
    agent = discover_agent
    messages = []

    console.print("[bold magenta]Welcome to the 4D Learning System![/bold magenta]")

    # Initiate the conversation with a model-generated response
    initial_response = swarm.run(
        agent=agent,
        messages=[{"role": "system", "content": "Initiate the conversation by introducing yourself and asking about the user's learning goals."}],
        context={},
        debug=DEBUG,
        max_turns=1,
    )
    
    initial_message = initial_response.messages[0]
    print_agent_message(agent.name, initial_message['content'])
    messages.append(initial_message)

    while True:
        user_input = console.input("[bold green]User: [/bold green]")
        print_user_message(user_input)
        messages.append({"role": "user", "content": user_input})

        response = swarm.run(
            agent=agent,
            messages=messages,
            context={},  # We can retrieve context and pass it in here
            debug=DEBUG,
            max_turns=3,
        )

        messages.extend(response.messages)
        
        # If response contains an agent, switch to it
        if response.agent and response.agent != agent:
            print_system_message(f"[bold]Switching to new agent: {response.agent.name}[/bold]")
            agent = response.agent
            # Generate a response for the new agent
            new_agent_response = swarm.run(
                agent=agent,
                messages=messages + [{"role": "system", "content": "Introduce yourself as the new agent and continue the conversation based on the context."}],
                context={},
                debug=DEBUG,
                max_turns=1,
            )
            new_agent_message = new_agent_response.messages[0]
            print_agent_message(agent.name, new_agent_message['content'])
            messages.append(new_agent_message)
        else:
            for msg in response.messages:
                if msg["role"] == "assistant":
                    print_agent_message(agent.name, msg['content'])
                elif msg["role"] == "tool":
                    print_system_message(f"[bold]{msg['tool_name']}:[/bold] {msg['content']}")

if __name__ == "__main__":
    main()
