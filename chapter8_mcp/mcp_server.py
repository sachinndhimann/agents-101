"""
Chapter 8 — a real MCP server.

Exposes tools, a resource, and a prompt template using the official
`mcp` Python SDK. This process is launched by mcp_client_agent.py as a
subprocess and speaks MCP over stdio -- it is never run directly by a
user in normal operation (though `python3 mcp_server.py` will start it
and wait on stdin, which is expected).

Note: MCP SDK v2 renamed FastMCP -> MCPServer. If you have MCP SDK v1
installed, `from mcp.server.fastmcp import FastMCP as MCPServer` instead.
"""
from datetime import datetime, timezone
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("agents-101-toolserver")


@mcp.tool()
def calculator(a: float, b: float, op: str) -> float:
    """Perform a basic arithmetic operation (add, subtract, multiply, divide)."""
    ops = {"add": lambda: a + b, "subtract": lambda: a - b,
           "multiply": lambda: a * b, "divide": lambda: a / b}
    if op not in ops:
        raise ValueError(f"Unsupported operation: {op}")
    return ops[op]()


@mcp.tool()
def get_time() -> str:
    """Get the current UTC date and time."""
    return datetime.now(timezone.utc).isoformat()


@mcp.tool()
def reverse_string(text: str) -> str:
    """Reverse a string. (Add this kind of tool to test dynamic discovery --
    the client never needs to know this tool exists ahead of time.)"""
    return text[::-1]


# A RESOURCE: readable data, not an action. No arguments -- it's a GET.
@mcp.resource("notes://latest")
def latest_notes() -> str:
    """The most recent note from the (mock) notes system."""
    return "Note: remember to update the trip budget spreadsheet before Friday."


# A PROMPT TEMPLATE: a reusable, parameterized prompt the server provides.
@mcp.prompt()
def trip_planner(destination: str, budget: str) -> str:
    """Reusable prompt template for planning a budget trip."""
    return (
        f"Plan a trip to {destination} with a total budget of {budget}. "
        "Break the budget down into transport, stay, and food/activities."
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
