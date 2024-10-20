from core import Swarm
from agents.a_discover import discover_agent

DEBUG = True

def main():
    swarm = Swarm()
    agent = discover_agent
    messages = []

    print("Welcome to the 4D Learning System!")

    # Initiate the conversation with a model-generated response
    initial_response = swarm.run(
        agent=agent,
        messages=[{"role": "system", "content": "Initiate the conversation by introducing yourself and asking about the user's learning goals."}],
        context={},
        debug=DEBUG,
        max_turns=1,
    )
    
    initial_message = initial_response.messages[0]
    print(f"{agent.name}: {initial_message['content']}")
    messages.append(initial_message)

    while True:
        user_input = input("User: ")
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
            print(f"{agent.name}: {new_agent_message['content']}")
            messages.append(new_agent_message)
        else:
            for msg in response.messages:
                if msg["role"] == "assistant":
                    print(f"{agent.name}: {msg['content']}")

if __name__ == "__main__":
    main()
