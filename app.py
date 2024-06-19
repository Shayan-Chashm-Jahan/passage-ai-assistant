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
    st.session_state.conversation_history = [{"role": "system", "content": "Your name is Ella. And you are a helpful assistant for passage. You answer all the questions related to the documents provided to you. But if you don't find a relevant document you say that you cannot answer it. At the beginning, You introduce yourself and ask the user that how you can help them. You don't tell the user about the documents. You just tell them that you can talk about passage and migration and ask them if you can assist them related to Passage and immigration. You ask them that how you can assist them."}]

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
    .input-container {
        display: flex;
        align-items: center;
        margin-bottom: 10px;
    }
    .stTextInput input {
        border: 1px solid #D1D5DB;
        border-radius: 4px;
        padding: 12px;
        font-size: 16px;
        flex: 1;
        transition: border-color 0.3s;
    }
    .stTextInput input:focus {
        border-color: #1F2937;
        outline: none;
    }
    .stButton button {
        background-color: #1F2937;
        color: #FFF;
        border: none;
        border-radius: 4px;
        padding: 12px 20px;
        font-size: 16px;
        cursor: pointer;
        transition: background-color 0.3s, color 0.3s;
        margin-left: 10px;
    }
    .stButton button:hover {
        background-color: #FFF;
        color: #1F2937;
        border: 1px solid #1F2937;
    }
    .stMarkdown p {
        font-size: 16px;
        line-height: 1.6;
        margin-bottom: 10px;
    }
    .stContainer {
        max-width: 800px;
        margin: auto;
        padding: 20px;
        background-color: #FFF;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        border: 2px solid orange; /* Orange border around the chatbot */
    }
    .stTitle {
        font-size: 24px;
        font-weight: bold;
        color: #1F2937;
        margin-bottom: 20px;
    }
    .stSubheader {
        font-size: 20px;
        color: #1F2937;
        margin-bottom: 15px;
    }
    .chat-history {
        background-color: #FFF;
        border: 1px solid #D1D5DB;
        border-radius: 4px;
        padding: 10px;
        margin-bottom: 20px;
        max-height: 400px;
        overflow-y: auto;
    }
</style>
            """, unsafe_allow_html=True)