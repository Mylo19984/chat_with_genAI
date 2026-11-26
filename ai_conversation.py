import asyncio
import logging
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from tools import execute_tool_calls, tools as local_tools

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 1024
NUMBER_OF_ITERATIONS = 4


def _anthropic_tool(tool):
    """Convert an MCP tool definition to Anthropic's tool schema."""
    return {
        "name": tool.name,
        "description": tool.description or "",
        "input_schema": tool.inputSchema,
    }


def _mcp_text(result):
    """Flatten MCP text and structured content into a string."""
    parts = []
    for item in getattr(result, "content", []):
        if getattr(item, "type", None) == "text":
            parts.append(item.text)
    if parts:
        return "\n".join(parts)
    return str(result)


async def _chat_with_mcp(client, messages, system_prompt):
    server_path = os.path.join(os.path.dirname(__file__), "news_mcp_server.py")
    mcp_env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONUNBUFFERED": "1",
    }
    if gnews_api_key := os.environ.get("GNEWS_API_KEY"):
        mcp_env["GNEWS_API_KEY"] = gnews_api_key

    server = StdioServerParameters(
        command=sys.executable,
        args=[server_path],
        env=mcp_env,
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            mcp_result = await session.list_tools()
            local_tool_names = {tool["name"] for tool in local_tools}

            # Local tools take precedence. MCP tools with duplicate names are
            # excluded so Claude never receives two definitions or duplicate
            # tool_result entries for the same tool_use_id.
            mcp_tools = {
                tool.name: tool
                for tool in mcp_result.tools
                if tool.name not in local_tool_names
            }
            anthropic_tools = list(local_tools) + [
                _anthropic_tool(tool) for tool in mcp_tools.values()
            ]

            for iteration in range(1, NUMBER_OF_ITERATIONS + 1):
                response = await asyncio.to_thread(
                    client.messages.create,
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    tools=anthropic_tools,
                    system=system_prompt,
                    messages=messages,
                )
                logger.info(
                    "Claude response received: iteration=%s stop_reason=%s",
                    iteration,
                    response.stop_reason,
                )

                if response.stop_reason == "max_tokens":
                    messages.append({"role": "assistant", "content": response.content})
                    reply = "\n".join(
                        block.text
                        for block in response.content
                        if getattr(block, "type", None) == "text"
                    )
                    truncation_notice = (
                        "The response was truncated because it reached the token limit. "
                        "Please continue or simplify the request."
                    )
                    reply = "\n\n".join(part for part in (reply, truncation_notice) if part)
                    logger.warning("Claude response truncated at the token limit.")
                    logger.info("Final assistant response: %s", reply)
                    return reply

                if response.stop_reason == "pause_turn":
                    messages.append({"role": "assistant", "content": response.content})
                    logger.info("Claude paused the turn; continuing the conversation.")
                    continue

                if response.stop_reason != "tool_use":
                    messages.append({"role": "assistant", "content": response.content})
                    reply = "\n".join(
                        block.text
                        for block in response.content
                        if block.type == "text"
                    )
                    logger.info("Final assistant response: %s", reply)
                    return reply

                for block in response.content:
                    if block.type == "text":
                        logger.info("Claude intermediate text: %s", block.text)
                    elif block.type == "tool_use":
                        logger.info("Claude requested tool: %s", block.name)

                messages.append({"role": "assistant", "content": response.content})
                tool_results = []

                for block in response.content:
                    if getattr(block, "type", None) != "tool_use":
                        continue

                    if block.name in local_tool_names:
                        local_result = execute_tool_calls([block])
                        tool_results.extend(local_result)
                    elif block.name in mcp_tools:
                        try:
                            result = await session.call_tool(block.name, block.input)
                            content = _mcp_text(result)
                            is_error = bool(getattr(result, "isError", False))
                            logger.info(
                                "MCP tool result (%s, is_error=%s): %s",
                                block.name,
                                is_error,
                                content,
                            )
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": content,
                                "is_error": is_error,
                            })
                        except Exception as error:
                            logger.exception("MCP tool call failed: %s", block.name)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": (
                                    f"MCP tool '{block.name}' failed to execute: "
                                    f"{type(error).__name__}: {error}"
                                ),
                                "is_error": True,
                            })
                    else:
                        logger.warning("Unknown tool requested: %s", block.name)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": (
                                f"Error: Unknown tool '{block.name}'. "
                                "Available tools must be used exactly as listed."
                            ),
                            "is_error": True,
                        })

                if not tool_results:
                    raise RuntimeError("Claude requested tool use without any tool blocks.")
                messages.append({"role": "user", "content": tool_results})

    logger.warning("Stopped after reaching the %s-iteration tool-use limit.", NUMBER_OF_ITERATIONS)
    reply = (
        f"Stopped after {NUMBER_OF_ITERATIONS} tool-use iterations. "
        "Please continue with another message if you want me to keep going."
    )
    messages.append({"role": "assistant", "content": reply})
    logger.info("Final assistant response: %s", reply)
    return reply


def chat_with_ai(client, messages, system_prompt):
    """Exchange messages with Claude, executing local and MCP tools."""
    return asyncio.run(_chat_with_mcp(client, messages, system_prompt))
