import logging

from tools import execute_tool_calls, tools

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 1024
NUMBER_OF_ITERATIONS = 4


def chat_with_ai(client, messages, system_prompt):
    """Exchange messages with Claude, executing any requested tools."""
    for iteration in range(1, NUMBER_OF_ITERATIONS + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            tools=tools,
            system=system_prompt,
            messages=messages,
        )
        logger.info(
            "Claude response received: iteration=%s stop_reason=%s",
            iteration,
            response.stop_reason,
        )

        if response.stop_reason != "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            reply = "\n".join(
                block.text for block in response.content if block.type == "text"
            )
            logger.info("Final assistant response: %s", reply)
            return reply

        for block in response.content:
            if block.type == "text":
                logger.info("Claude intermediate text: %s", block.text)
            elif block.type == "tool_use":
                logger.info("Claude requested tool: %s", block.name)

        messages.append({"role": "assistant", "content": response.content})
        tool_results = execute_tool_calls(response.content)
        if not tool_results:
            raise RuntimeError("Claude requested tool use without any tool calls.")

        messages.append({"role": "user", "content": tool_results})
    else:
        logger.warning(
            "Stopped after reaching the %s-iteration tool-use limit.",
            NUMBER_OF_ITERATIONS,
        )
        reply = (
            f"Stopped after {NUMBER_OF_ITERATIONS} tool-use iterations. "
            "Please continue with another message if you want me to keep going."
        )
        messages.append({"role": "assistant", "content": reply})
        logger.info("Final assistant response: %s", reply)
        return reply
