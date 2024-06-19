from openai import OpenAI
import streamlit as st
import pickle
import utils 

api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

with open('embeddings.pkl', 'rb') as f:
    document_embeddings, document_chunks = pickle.load(f)

def handle_user_input():
    user_input = st.session_state.user_input

    if user_input:
        st.session_state.conversation_history.append({"role": "user", "content": user_input})
        response = utils.generate_response(client, st.session_state.conversation_history, document_embeddings, document_chunks)
        st.session_state.conversation_history.append({"role": "assistant", "content": response})
        st.session_state.user_input = ""


if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

st.title("Passage AI Assistant")

query = st.text_input("Enter your query:", key="user_input", on_change=handle_user_input)
submit_button = st.button("Send", on_click=handle_user_input)

st.markdown("### Conversation History")
for message in st.session_state.get('conversation_history', []):
    if message['role'] == 'assistant':
        st.markdown(f"**Assistant:** {message['content']}")
    elif message['role'] == 'user':
        st.markdown(f"**You:** {message['content']}")

    
st.markdown("""
<style>
    body {
        background-color: #F7F9FB;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #333;
    }
    .stTextInput input {
        border: 1px solid #D1D5DB;
        border-radius: 4px;
        padding: 8px;
        font-size: 14px;
        width: 100%;
    }
    .stButton button {
        background-color: #1F2937;
        color: #FFF;
        border: none;
        border-radius: 4px;
        padding: 10px 20px;
        font-size: 14px;
        cursor: pointer;
        transition: background-color 0.3s, color 0.3s;
    }
    .stButton button:hover {
        background-color: #FFF;
        color: #1F2937;
    }
    .stMarkdown p {
        font-size: 16px;
        line-height: 1.5;
    }
    .stContainer {
        max-width: 800px;
        margin: auto;
        padding: 20px;
        background-color: #FFF;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
</style>

            """, unsafe_allow_html=True)