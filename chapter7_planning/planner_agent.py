"""
Chapter 7 — Planning: separate a "produce a plan" phase from an
"execute the plan" phase, then a "synthesize" phase.

This is the structural difference between planning and the reactive
Chapter 3 loop: here the model commits to a full subtask list BEFORE any
execution happens, which you can log, validate, or show a user.
"""
import json
import anthropic

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-5"


# --- Mock "budget lookup" tools used during subtask execution ---
def lookup_transport_cost(origin: str, destination: str) -> str:
    return f"Estimated round-trip transport {origin}->{destination}: Rs 2,500 (train, mock data)"


def lookup_stay_cost(city: str, nights: int) -> str:
    return f"Estimated budget stay in {city} for {nights} night(s): Rs 3,000 (mock data)"


def lookup_food_activity_cost(city: str, days: int) -> str:
    return f"Estimated food + activities in {city} for {days} day(s): Rs 2,000 (mock data)"


SUBTASK_TOOLS = {
    "lookup_transport_cost": lookup_transport_cost,
    "lookup_stay_cost": lookup_stay_cost,
    "lookup_food_activity_cost": lookup_food_activity_cost,
}


# --- Phase 1: Planning ---
def plan(goal: str) -> list:
    """One LLM call, no tools -- just ask for a structured breakdown."""
    system = (
        "You are a planning module. Given a goal, break it into 2-5 concrete "
        "subtasks. Respond with ONLY a JSON array of strings, no other text. "
        'Example: ["Find transport options", "Find a place to stay"]'
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": goal}],
    )
    text = response.content[0].text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Planning output isn't guaranteed well-formed -- a real system
        # would retry or repair here. We fail loudly instead of silently.
        raise ValueError(f"Planner did not return valid JSON: {text}")


# --- Phase 2: Execution (sequential here, since subtasks share a budget) ---
def execute_subtask(subtask: str) -> str:
    """Run one subtask through a small tool-using loop, same shape as
    Chapter 3's agent loop, scoped to just this subtask."""
    tool_schemas = [
        {
            "name": "lookup_transport_cost",
            "description": "Estimate round-trip transport cost between two cities.",
            "input_schema": {
                "type": "object",
                "properties": {"origin": {"type": "string"}, "destination": {"type": "string"}},
                "required": ["origin", "destination"],
            },
        },
        {
            "name": "lookup_stay_cost",
            "description": "Estimate budget accommodation cost for a city and number of nights.",
            "input_schema": {
                "type": "object",
                "properties": {"city": {"type": "string"}, "nights": {"type": "integer"}},
                "required": ["city", "nights"],
            },
        },
        {
            "name": "lookup_food_activity_cost",
            "description": "Estimate food and activity cost for a city and number of days.",
            "input_schema": {
                "type": "object",
                "properties": {"city": {"type": "string"}, "days": {"type": "integer"}},
                "required": ["city", "days"],
            },
        },
    ]

    messages = [{"role": "user", "content": subtask}]
    for _ in range(3):
        response = client.messages.create(
            model=MODEL, max_tokens=512, tools=tool_schemas, messages=messages
        )
        if response.stop_reason != "tool_use":
            return response.content[0].text
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                fn = SUBTASK_TOOLS[block.name]
                result = fn(**block.input)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                )
        messages.append({"role": "user", "content": tool_results})
    return "Subtask did not resolve in time."


# --- Phase 3: Synthesis ---
def synthesize(goal: str, subtask_results: list) -> str:
    joined = "\n".join(f"- {r}" for r in subtask_results)
    prompt = (
        f"Original goal: {goal}\n\n"
        f"Subtask results:\n{joined}\n\n"
        "Combine these into one clear, actionable final answer for the user."
    )
    response = client.messages.create(
        model=MODEL, max_tokens=1024, messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def agent(goal: str) -> str:
    subtasks = plan(goal)
    print("=== PLAN ===")
    for i, t in enumerate(subtasks, 1):
        print(f"{i}. {t}")
    print()

    results = []
    for t in subtasks:
        print(f"[Executing] {t}")
        result = execute_subtask(t)
        print(f"[Result] {result}\n")
        results.append(result)

    return synthesize(goal, results)


if __name__ == "__main__":
    print(agent("Plan a weekend trip to Delhi under Rs 10,000."))
