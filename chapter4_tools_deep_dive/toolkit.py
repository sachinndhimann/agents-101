"""
Chapter 4 — Tools, In Depth

A hardened tool execution layer: unknown-tool checks, permissions,
exception handling, and structured error results fed back to the model.
"""
import anthropic
from datetime import datetime, timezone

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-5"


# --- Tool implementations ---
def calculator(a: float, b: float, op: str) -> float:
    ops = {"add": lambda: a + b, "subtract": lambda: a - b,
           "multiply": lambda: a * b, "divide": lambda: a / b}
    if op not in ops:
        raise ValueError(f"Unsupported operation: {op}")
    if op == "divide" and b == 0:
        raise ValueError("Division by zero")
    return ops[op]()


def search(query: str) -> str:
    # Mock -- a real version would call a search API
    return f"Mock search results for: '{query}' (no real network call made)"


def get_weather(city: str) -> str:
    # Mock -- a real version would call a weather API
    return f"Mock weather for {city}: 24C, clear skies"


def get_time(timezone_name: str = "UTC") -> str:
    return datetime.now(timezone.utc).isoformat()


TOOLS = {
    "calculator": calculator,
    "search": search,
    "get_weather": get_weather,
    "get_time": get_time,
}

# Permission flags -- a real system loads this from config per-user/context
TOOL_PERMISSIONS = {
    "calculator": True,
    "search": True,
    "get_weather": True,
    "get_time": True,
}

tool_schemas = [
    {
        "name": "calculator",
        "description": "Perform basic arithmetic (add, subtract, multiply, divide) on two numbers.",
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
        "name": "search",
        "description": "Search the web for information on a topic. Use for facts you're unsure about.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "get_weather",
        "description": "Get current weather for a named city.",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
    {
        "name": "get_time",
        "description": "Get the current date and time.",
        "input_schema": {
            "type": "object",
            "properties": {"timezone_name": {"type": "string"}},
            "required": [],
        },
    },
]


def execute_tool(name: str, arguments: dict) -> str:
    # 1. Known tool?
    if name not in TOOLS:
        return f"ERROR: unknown tool '{name}'"

    # 2. Permitted?
    if not TOOL_PERMISSIONS.get(name, False):
        return f"ERROR: tool '{name}' is not permitted in this context"

    # 3. Execute, catching failure -- never let a bad tool crash the loop
    try:
        result = TOOLS[name](**arguments)
        return str(result)
    except TypeError as e:
        return f"ERROR: invalid arguments for '{name}': {e}"
    except Exception as e:
        return f"ERROR: '{name}' failed during execution: {e}"


def agent(user_input: str, max_steps: int = 6) -> str:
    messages = [{"role": "user", "content": user_input}]

    for step in range(max_steps):
        response = client.messages.create(
            model=MODEL, max_tokens=1024, tools=tool_schemas, messages=messages
        )

        if response.stop_reason != "tool_use":
            return response.content[0].text

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"[Step {step}] Calling {block.name}({block.input})")
                result = execute_tool(block.name, block.input)
                print(f"[Step {step}] -> {result}")
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                        "is_error": result.startswith("ERROR:"),
                    }
                )

        messages.append({"role": "user", "content": tool_results})

    return "Max steps reached without a final answer."


if __name__ == "__main__":
    print(agent("What's 10 divided by 0? Also tell me the weather in Mohali."))
