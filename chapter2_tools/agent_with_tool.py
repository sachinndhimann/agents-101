"""
Chapter 2 — Give the Agent a Tool

Two LLM calls: one to decide whether/how to use a tool, one to produce
the final answer once the tool's result is available. This is the entire
mechanism behind "function calling" -- no more, no less.
"""
import anthropic

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-5"


# --- Step A: a real Python function ---
def calculator(a: float, b: float, op: str) -> float:
    if op == "add":
        return a + b
    if op == "subtract":
        return a - b
    if op == "multiply":
        return a * b
    if op == "divide":
        return a / b
    raise ValueError(f"Unknown op: {op}")


# --- Step B: describe it to the LLM. The model sees only this schema,
# never the Python code above. ---
tools = [
    {
        "name": "calculator",
        "description": "Perform a basic arithmetic operation on two numbers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
                "op": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                },
            },
            "required": ["a", "b", "op"],
        },
    }
]


def agent(user_input: str) -> str:
    messages = [{"role": "user", "content": user_input}]

    # --- Call 1: let the model decide whether to use a tool ---
    response = client.messages.create(
        model=MODEL, max_tokens=1024, tools=tools, messages=messages
    )

    if response.stop_reason != "tool_use":
        return response.content[0].text

    # The model's turn (including its tool_use block) becomes history
    messages.append({"role": "assistant", "content": response.content})

    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            print(f"[Agent decided to call: {block.name}({block.input})]")
            if block.name == "calculator":
                result = calculator(**block.input)
            else:
                result = f"Unknown tool: {block.name}"
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,  # links result to this specific call
                    "content": str(result),
                }
            )

    messages.append({"role": "user", "content": tool_results})

    # --- Call 2: give the model the tool's result, get final answer ---
    final = client.messages.create(
        model=MODEL, max_tokens=1024, tools=tools, messages=messages
    )
    return final.content[0].text


if __name__ == "__main__":
    print(agent("What is 847293 * 9384?"))
    print()
    print(agent("What's the capital of Japan?"))  # should skip the tool
