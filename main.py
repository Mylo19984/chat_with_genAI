import os
import streamlit as st
import anthropic

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError("Set the ANTHROPIC_API_KEY environment variable before running this script.")

client = anthropic.Anthropic(api_key=api_key)

st.title("Chat")

print (st.session_state)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Ask something"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
            def stream():
                with client.messages.stream(
                    model="claude-sonnet-4-5",
                    max_tokens=1024,
                    system="You are a helpful assistant.",
                    messages=st.session_state.messages,
                ) as s:
                    yield from s.text_stream

            reply = st.write_stream(stream())
    
    st.session_state.messages.append({"role": "assistant", "content": reply})