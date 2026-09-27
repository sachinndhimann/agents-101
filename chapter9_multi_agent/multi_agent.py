"""
Chapter 9 — a small multi-agent system.

Three narrowly-scoped sub-agents (Research, Coding, Review) coordinated
by a Manager. Each sub-agent is just a single-purpose LLM call with its
own system prompt -- there is no new mechanism here versus Chapter 1,
only role separation, sequencing, and controlled information flow
between agents (a manager-level version of Chapter 6's context choices).
"""
import anthropic

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-5"


def call_llm(system: str, user_message: str) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


# --- Mock tool the Research agent uses ---
def mock_web_lookup(query: str) -> str:
    return (
        f"[mock result for '{query}']: Python's built-in `bisect` module "
        "provides binary search in O(log n); a naive linear scan is O(n)."
    )


def research_agent(task: str) -> str:
    """Narrow role: gather relevant background, nothing else."""
    lookup = mock_web_lookup(task)
    system = (
        "You are a Research Agent. Summarize relevant background for a "
        "coding task in 2-3 sentences. Do not write code."
    )
    return call_llm(system, f"Task: {task}\nLookup result: {lookup}")


def coding_agent(task: str, research_notes: str) -> str:
    """Narrow role: write code, given research notes. Does not review itself."""
    system = (
        "You are a Coding Agent. Write a single Python function that "
        "accomplishes the task. Output ONLY the code, no explanation."
    )
    return call_llm(system, f"Task: {task}\nRelevant background:\n{research_notes}")


def review_agent(task: str, code: str) -> str:
    """Narrow role: critique code someone else wrote. Deliberately does
    not see the research notes -- it should judge the code on its own
    merits, the same way a human reviewer would."""
    system = (
        "You are a Review Agent. Critique the following code for "
        "correctness, edge cases, and style. Be concise and specific."
    )
    return call_llm(system, f"Task: {task}\nCode:\n{code}")


def manager(task: str) -> str:
    print(f"[Manager] Task received: {task}\n")

    print("[Manager] Delegating to Research Agent...")
    notes = research_agent(task)
    print(f"[Research Agent] {notes}\n")

    print("[Manager] Delegating to Coding Agent...")
    code = coding_agent(task, notes)
    print(f"[Coding Agent]\n{code}\n")

    print("[Manager] Delegating to Review Agent...")
    review = review_agent(task, code)
    print(f"[Review Agent] {review}\n")

    print("[Manager] Synthesizing final answer...")
    synthesis_system = (
        "You are the Manager. Combine the code and the review into one "
        "final response for the user: the code, followed by a short note "
        "on any issues the reviewer raised."
    )
    final = call_llm(
        synthesis_system,
        f"Task: {task}\nCode:\n{code}\nReview:\n{review}",
    )
    return final


if __name__ == "__main__":
    result = manager("Write a function that finds an item in a sorted list efficiently.")
    print("=== FINAL MANAGER OUTPUT ===")
    print(result)
