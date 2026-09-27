"""
Chapter 10 — reusable guardrail primitives.

Each guardrail is a small, independent, testable unit. A production
agent composes several of these rather than relying on prompt
instructions ("please don't spend too much") which the model can ignore
or misjudge under pressure. Guardrails must be enforced in code, outside
the model's control.
"""
import re
from dataclasses import dataclass, field


class StepLimitExceeded(Exception):
    pass


class BudgetExceeded(Exception):
    pass


class ToolNotPermitted(Exception):
    pass


class HumanApprovalRequired(Exception):
    """Raised to pause execution and hand control back to a human."""
    def __init__(self, tool_name: str, arguments: dict):
        self.tool_name = tool_name
        self.arguments = arguments
        super().__init__(f"Tool '{tool_name}' requires human approval")


@dataclass
class StepLimiter:
    max_steps: int
    current_step: int = 0

    def check(self):
        if self.current_step >= self.max_steps:
            raise StepLimitExceeded(f"Exceeded max steps ({self.max_steps})")
        self.current_step += 1


@dataclass
class BudgetTracker:
    """Approximate token/cost budget. Real systems use actual usage
    fields from the API response; this approximates by character count
    to stay self-contained."""
    max_approx_tokens: int
    used_approx_tokens: int = 0

    def spend(self, text: str):
        cost = max(1, len(text) // 4)
        self.used_approx_tokens += cost
        if self.used_approx_tokens > self.max_approx_tokens:
            raise BudgetExceeded(
                f"Used ~{self.used_approx_tokens} tokens, budget was {self.max_approx_tokens}"
            )


@dataclass
class ToolPermissionGate:
    allowed_tools: set
    requires_approval: set = field(default_factory=set)

    def check(self, tool_name: str, arguments: dict):
        if tool_name not in self.allowed_tools:
            raise ToolNotPermitted(f"Tool '{tool_name}' is not in the allowed set")
        if tool_name in self.requires_approval:
            raise HumanApprovalRequired(tool_name, arguments)


# A heuristic only -- NOT a real security boundary. Demonstrates the
# CONCEPT of scanning tool output for injected instructions. A real
# defense is architectural: tool output should never be able to change
# what actions the agent is PERMITTED to take, regardless of its content.
INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"disregard (all )?(prior|previous) instructions",
    r"reveal your system prompt",
    r"you are now in .*mode",
]


def scan_for_injection(text: str) -> bool:
    """Return True if the text looks like it's trying to inject
    instructions into the agent via tool output. False negatives are
    expected -- this is illustrative, not a production-grade defense."""
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in INJECTION_PATTERNS)
