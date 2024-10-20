from core import Swarm
from agents.discover import discover_agent


def main():
    swarm    = Swarm()
    agent    = discover_agent
    messages = []

    print("Welcome to the 4D Learning System!")

    while True:
        user_input = input("User: ")
        messages.append({"role": "user", "content": user_input})

        response = swarm.run(
            agent=agent,
            messages=messages,
            context={},
            debug=True,
            max_turns=2,
        )

        messages.extend(response.messages)
        # If response contains an agent, switch to it else keep the same agent
        agent = response.agent or agent

        for msg in response.messages:
            if msg["role"] == "assistant":
                print(f"{agent.name}: {msg['content']}")



if __name__ == "__main__":
    main()
