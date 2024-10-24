from swarm import run_agent, Agent, Response
from agents.a_discover import discover_agent

DEBUG = True

console = Console()


def main():
    agent = discover_agent
    messages = []
    context = {}

    console.print("[bold magenta]Welcome to the 4D Learning System![/bold magenta]")

    # Initiate the conversation with a model-generated response
    initial_response = run_agent(
        agent=agent,
        messages=[{"role": "system", "content": "Initiate the conversation by introducing yourself and asking about the user's learning goals."}],
        context=context,
    )
    
    initial_message = initial_response.messages[0]
    print(agent.name, initial_message.get('content'))
    messages.append(initial_message)

    while True:
        user_input = console.input("[bold green]User: [/bold green]")
        print(user_input)
        messages.append({"role": "user", "content": user_input})

        response = run_agent(
            agent=agent,
            messages=messages,
            context=context,
        )

        messages.extend(response.messages)
        context.update(response.context)
        
        # If response contains an agent, switch to it
        if response.agent and response.agent != agent:
            print(f"[bold]Switching to new agent: {response.agent.name}[/bold]")
            agent = response.agent
            # Generate a response for the new agent
            new_agent_response = run_agent(
                agent=agent,
                messages=messages + [{"role": "system", "content": "Introduce yourself, describe your role, and continue the conversation based on the context."}],
                context=context,
            )
            new_agent_message = new_agent_response.messages[0]
            print(agent.name, new_agent_message.get('content'))
            messages.append(new_agent_message)
            context.update(new_agent_response.context)
        else:
            for msg in response.messages:
                if msg["role"] == "assistant":
                    print(agent.name, msg.get('content'))
                elif msg["role"] == "tool":
                    print(f"[bold]{msg['tool_name']}:[/bold] {msg.get('content', 'No content')}")

if __name__ == "__main__":
    main()
