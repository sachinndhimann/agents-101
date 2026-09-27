"""
Chapter 3 — The Agent Loop

The generic OBSERVE -> THINK/DECIDE -> ACT loop. This single structure
is what lets an agent take an arbitrary number of steps before answering.
"""
import anthropic

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-5"


def calculator(a: float, b: float, op: str) -> float:
    ops = {
        "add": lambda: a + b,
        "subtract": lambda: a - b,
        "multiply": lambda: a * b,
        "divide": lambda: a / b,
    }
    return ops[op]()


def compare(a: float, b: float) -> str:
    if a > b:
        return f"{a} is greater than {b}"
    elif a < b:
        return f"{a} is less than {b}"
    return f"{a} equals {b}"


def is_even_or_odd(n: float) -> str:
    return "even" if int(n) % 2 == 0 else "odd"


TOOLS = {
    "calculator": calculator,
    "compare": compare,
    "is_even_or_odd": is_even_or_odd,
}

tool_schemas = [
    {
        "name": "calculator",
        "description": "Perform a basic arithmetic operation on two numbers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
                "op": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
            },
            "required": ["a", "b", "op"],
        },
    },
    {
        "name": "compare",
        "description": "Compare two numbers and say which is greater.",
        "input_schema": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    },
    {
        "name": "is_even_or_odd",
        "description": "Determine whether a number is even or odd.",
        "input_schema": {
            "type": "object",
            "properties": {"n": {"type": "number"}},
            "required": ["n"],
        },
    },
]


def agent(user_input: str, max_steps: int = 6) -> str:
    messages = [{"role": "user", "content": user_input}]

    for step in range(max_steps):
        response = client.messages.create(
            model=MODEL, max_tokens=1024, tools=tool_schemas, messages=messages
        )

        # THINK/DECIDE happened above.
        if response.stop_reason != "tool_use":
            return response.content[0].text  # FINAL ANSWER

        messages.append({"role": "assistant", "content": response.content})

        # ACT: execute every tool call requested this turn
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"[Step {step}] Agent calls: {block.name}({block.input})")
                fn = TOOLS[block.name]
                result = fn(**block.input)
                print(f"[Step {step}] Result: {result}")
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": str(result)}
                )

        # OBSERVE RESULT: feed back in, loop continues
        messages.append({"role": "user", "content": tool_results})

    return "Max steps reached without a final answer."


if __name__ == "__main__":
    print(agent("Calculate 25 * 17 and then tell me whether the result is greater than 400."))
    print()
    print(agent("Calculate 12 * 8, then add 50 to it, then tell me if that's even or odd."))
