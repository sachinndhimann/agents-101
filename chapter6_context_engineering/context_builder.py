"""
Chapter 6 — an explicit context assembler.

Every prior chapter assembled context implicitly (you just built the
`messages` list). This makes the assembly process a first-class,
inspectable object: named sources, a priority order, and a budget that
forces explicit truncation decisions instead of silently overflowing.

Token counting here is approximate (chars / 4) -- good enough to
demonstrate the mechanism. Production systems use a real tokenizer.
"""
from dataclasses import dataclass, field
from typing import List


def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


@dataclass
class ContextBuilder:
    max_tokens: int
    system_instructions: str = ""
    long_term_memory: List[str] = field(default_factory=list)
    tool_definitions: List[dict] = field(default_factory=list)
    retrieved_docs: List[str] = field(default_factory=list)
    conversation_history: List[dict] = field(default_factory=list)  # [{"role","content"}]
    current_user_input: str = ""

    def _section(self, label: str, text: str) -> str:
        return f"--- {label} ---\n{text}\n" if text else ""

    def build(self) -> str:
        """Assemble context in priority order. Items later in this list
        are dropped/truncated FIRST when the budget is exceeded.

        Priority (highest to lowest):
          1. system_instructions   -- never dropped
          2. current_user_input    -- never dropped
          3. relevant memory       -- dropped whole if over budget
          4. tool_definitions      -- dropped whole if over budget
          5. retrieved_docs        -- dropped whole if over budget
          6. conversation_history  -- truncated oldest-first, partial ok
        """
        fixed = (
            self._section("SYSTEM INSTRUCTIONS", self.system_instructions)
            + self._section("CURRENT USER INPUT", self.current_user_input)
        )
        budget_remaining = self.max_tokens - approx_tokens(fixed)

        optional_blocks = [
            ("RELEVANT MEMORY", "\n".join(f"- {m}" for m in self.long_term_memory)),
            ("TOOL DEFINITIONS", "\n".join(t["name"] for t in self.tool_definitions)),
            ("RETRIEVED DOCUMENTS", "\n".join(self.retrieved_docs)),
        ]

        assembled_optional = ""
        for label, text in optional_blocks:
            block = self._section(label, text)
            cost = approx_tokens(block)
            if cost <= budget_remaining:
                assembled_optional += block
                budget_remaining -= cost
            else:
                print(f"[context_builder] Dropping '{label}' entirely (budget exceeded)")

        # Conversation history: truncate oldest-first, keep as many
        # recent turns as fit.
        history_lines = []
        kept = []
        for turn in reversed(self.conversation_history):
            line = f"{turn['role']}: {turn['content']}"
            cost = approx_tokens(line)
            if cost <= budget_remaining:
                kept.insert(0, line)
                budget_remaining -= cost
            else:
                print(f"[context_builder] Truncating older history: '{line[:40]}...'")
                break
        history_block = self._section("CONVERSATION HISTORY", "\n".join(kept))

        return fixed + assembled_optional + history_block


if __name__ == "__main__":
    long_history = [
        {"role": "user", "content": f"This is filler turn number {i} about nothing important."}
        for i in range(50)
    ]

    builder = ContextBuilder(
        max_tokens=300,  # deliberately small to force truncation
        system_instructions="You are a concise, helpful assistant.",
        long_term_memory=["User's name is Sachin.", "User prefers no em-dashes."],
        tool_definitions=[{"name": "calculator"}, {"name": "search"}],
        retrieved_docs=["Doc: The Eiffel Tower is in Paris."],
        conversation_history=long_history,
        current_user_input="What's my name again?",
    )

    context = builder.build()
    print("\n=== FINAL ASSEMBLED CONTEXT ===\n")
    print(context)
    print(f"\nApprox tokens used: {approx_tokens(context)} / {builder.max_tokens}")
