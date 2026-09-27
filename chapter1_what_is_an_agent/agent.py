"""
Chapter 1 — What is an Agent?

The smallest possible unit: an LLM call wrapped in a function.
No tools, no loop. This is the baseline every later chapter builds on.
"""
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

MODEL = "claude-sonnet-4-5"


def agent(user_input: str) -> str:
    """A one-shot LLM call. Not yet an 'agent' in the full sense —
    there is no loop and no tool use. This is Level 0 plumbing."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": user_input}],
    )
    return response.content[0].text


if __name__ == "__main__":
    print(agent("What's the capital of France?"))
    print()
    # Try this: the model will likely hallucinate or approximate.
    # There is no calculator here yet -- see Chapter 2.
    print(agent("What is 847293 * 9384? Give only the number."))
