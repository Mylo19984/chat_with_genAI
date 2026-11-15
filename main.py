import os
import logging
import streamlit as st
import anthropic

from tools import (
    get_stock_price,
    get_youtube_transcript,
    search_youtube,
    send_telegram_message,
    tools,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

list_tools = [tool["name"] for tool in tools]

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError("Set the ANTHROPIC_API_KEY environment variable before running this script.")

client = anthropic.Anthropic(api_key=api_key)

st.title("Chat")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    content = m["content"]
    if isinstance(content, str):
        display_content = content
    else:
        display_content = "\n".join(
            block.text
            for block in content
            if getattr(block, "type", None) == "text"
        )

    if display_content:
        with st.chat_message(m["role"]):
            st.markdown(display_content)

if prompt := st.chat_input("Ask something"):
    logger.info("User prompt: %s", prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Thinking..."):
        while True:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=1024,
                tools=tools,
                system="You are a helpful assistant.",
                messages=st.session_state.messages,
            )
            logger.info("Claude response received: stop_reason=%s", response.stop_reason)

            if response.stop_reason != "tool_use":
                break

            for block in response.content:
                if block.type == "text":
                    logger.info("Claude intermediate text: %s", block.text)
                elif block.type == "tool_use":
                    logger.info("Claude requested tool: %s", block.name)

            st.session_state.messages.append(
                {"role": "assistant", "content": response.content}
            )
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                if block.name not in list_tools:
                    raise ValueError(f"Claude requested an unknown tool: {block.name}")

                if block.name == "get_stock_price":
                    result = get_stock_price(block.input["ticker"])
                if block.name == "search_youtube":
                    result = search_youtube(
                        block.input["query"],
                        block.input.get("max_results", 5),
                    )
                if block.name == "get_youtube_transcript":
                    result = get_youtube_transcript(
                        block.input["video_url"],
                        block.input.get("language", "en"),
                    )
                if block.name == "send_telegram_message":
                    result = send_telegram_message(block.input["text"])
                tool_result_content = str(result)
                logger.info("Tool result (%s): %s", block.name, tool_result_content)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tool_result_content,
                    }
                )

            if not tool_results:
                raise RuntimeError("Claude requested tool use without any tool calls.")

            st.session_state.messages.append(
                {"role": "user", "content": tool_results}
            )

    st.session_state.messages.append(
        {"role": "assistant", "content": response.content}
    )
    reply = "\n".join(
        block.text for block in response.content if block.type == "text"
    )
    logger.info("Final assistant response: %s", reply)
    with st.chat_message("assistant"):
        st.markdown(reply)