from core import Swarm
from agents import discover_agent


def main():
    swarm = Swarm()
    agent = discover_agent
    messages = []

    print("Welcome to the 4D Learning System!")

    while True:
        user_input = input("User: ")
        messages.append({"role": "user", "content": user_input})

        response = swarm.run(
            agent=agent,
            messages=messages,
            context={},
            debug=False,
            max_turns=1,
        )

        messages.extend(response.messages)
        agent = response.agent or agent

        for msg in response.messages:
            if msg["role"] == "assistant":
                print(f"{agent.name}: {msg['content']}")

        if input("Continue? (y/n): ").lower() != 'y':
            break


if __name__ == "__main__":
    main()
