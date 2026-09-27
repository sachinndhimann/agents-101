"""
Chapter 5 — an agent with short-term + long-term memory.

Short-term memory = the `messages` list for this conversation (same as
every prior chapter).

Long-term memory = memory.py's JSON store, retrieved BEFORE each LLM
call and written to via an explicit `remember` tool the model can invoke
when it decides something is worth persisting.
"""
import anthropic
import memory

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-5"

tool_schemas = [
    {
        "name": "remember",
        "description": (
            "Persist an important fact about the user for future sessions "
            "(name, preferences, ongoing projects, decisions). Call this "
            "whenever the user shares something worth remembering long-term."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"fact": {"type": "string"}},
            "required": ["fact"],
        },
    }
]


def execute_tool(name: str, arguments: dict) -> str:
    if name == "remember":
        memory.remember(arguments["fact"])
        return f"Stored: {arguments['fact']}"
    return f"ERROR: unknown tool '{name}'"


def build_system_prompt(user_input: str) -> str:
    """This is retrieval: pull only the long-term facts relevant to the
    current input, not the entire memory store. Selecting what belongs
    in context is a real design decision -- see Chapter 6."""
    relevant = memory.retrieve(user_input)
    if not relevant:
        return "You are a helpful assistant with long-term memory of the user."
    facts_block = "\n".join(f"- {f}" for f in relevant)
    return (
        "You are a helpful assistant with long-term memory of the user.\n"
        "Relevant facts you remember about this user:\n"
        f"{facts_block}\n"
        "Use them naturally if relevant; don't force them into every reply."
    )


def agent(user_input: str, conversation: list, max_steps: int = 4) -> str:
    conversation.append({"role": "user", "content": user_input})
    system_prompt = build_system_prompt(user_input)

    for _ in range(max_steps):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system_prompt,
            tools=tool_schemas,
            messages=conversation,
        )

        if response.stop_reason != "tool_use":
            conversation.append({"role": "assistant", "content": response.content})
            return response.content[0].text

        conversation.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                print(f"[memory tool] {result}")
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                )
        conversation.append({"role": "user", "content": tool_results})

    return "Max steps reached."


if __name__ == "__main__":
    # Short-term memory: this list lives only for this process run.
    conversation = []

    print(agent("Hi, I'm Sachin. I prefer concise answers with no em-dashes.", conversation))
    print()
    print(agent("What's my name and how do I like my answers?", conversation))
    print()
    print("Long-term memory currently on disk:", memory.all_facts())
    print("Restart this script -- the facts above will still be there,")
    print("even though `conversation` (short-term memory) starts empty again.")
