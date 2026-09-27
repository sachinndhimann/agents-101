"""
Chapter 8 — an agent that uses tools over MCP instead of local Python
functions.

This launches mcp_server.py as a subprocess, connects over stdio (MCP's
standard local transport), DISCOVERS its tools dynamically, converts
their schemas into Anthropic tool schemas, and runs a Chapter 3-style
agent loop where tool execution is dispatched over MCP instead of a
local function call.

Compare this file to chapter3_agent_loop/agent_loop.py: the loop
structure is identical. Only *how a tool call is executed* changed --
that's exactly the problem MCP solves: standardizing execution, not
reinventing the loop.
"""
import asyncio
import sys
import os

import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-5"

SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "mcp_server.py")


def mcp_tool_to_anthropic_schema(mcp_tool) -> dict:
    """Convert an MCP tool definition into the shape the Anthropic API
    expects. This conversion step is the bridge between 'MCP world' and
    'Claude API world' -- MCP doesn't dictate which model you use it with."""
    return {
        "name": mcp_tool.name,
        "description": mcp_tool.description or "",
        "input_schema": mcp_tool.inputSchema,
    }


async def run_agent(user_input: str, max_steps: int = 6) -> str:
    server_params = StdioServerParameters(command=sys.executable, args=[SERVER_SCRIPT])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # --- Tool discovery: no hardcoded schema list. Ask the server. ---
            tools_response = await session.list_tools()
            tool_schemas = [mcp_tool_to_anthropic_schema(t) for t in tools_response.tools]
            print("[Discovered tools over MCP]:", [t["name"] for t in tool_schemas])

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
                        print(f"[Step {step}] MCP tool call: {block.name}({block.input})")
                        # --- Execution dispatched over MCP, not a local function ---
                        result = await session.call_tool(block.name, block.input)
                        text_result = "".join(
                            c.text for c in result.content if hasattr(c, "text")
                        )
                        print(f"[Step {step}] Result: {text_result}")
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": text_result,
                                "is_error": result.isError,
                            }
                        )

                messages.append({"role": "user", "content": tool_results})

            return "Max steps reached without a final answer."


async def demo_resource_read():
    """Reading a RESOURCE is different from calling a TOOL: no
    arguments, just a URI to fetch. Uncomment the call in __main__ to try."""
    server_params = StdioServerParameters(command=sys.executable, args=[SERVER_SCRIPT])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.read_resource("notes://latest")
            for c in result.contents:
                print("[Resource notes://latest]:", c.text)


if __name__ == "__main__":
    answer = asyncio.run(
        run_agent("What is 25 times 17? Also tell me the current time.")
    )
    print("\nFinal answer:", answer)

    # Uncomment to see resource reading in action (separate from tool calls):
    # asyncio.run(demo_resource_read())
