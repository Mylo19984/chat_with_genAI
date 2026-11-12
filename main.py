import os
import streamlit as st
import anthropic

from tools import get_stock_price, tools

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

            if response.stop_reason != "tool_use":
                break

            st.session_state.messages.append(
                {"role": "assistant", "content": response.content}
            )
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                if block.name != "get_stock_price":
                    raise ValueError(f"Claude requested an unknown tool: {block.name}")

                result = get_stock_price(block.input["ticker"])
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
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
    with st.chat_message("assistant"):
        st.markdown(reply)