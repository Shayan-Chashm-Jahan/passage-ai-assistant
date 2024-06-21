from openai import OpenAI
import streamlit as st
import utils 
import json
import time
import load_funcs

ELLA_API_KEY = None
ella_client = None
ella_instructions = None

SPLITTER_API_KEY = None
splitter_client = None
splitter_instructions = None

MATCH_BUDDY_API_KEY = None
matchbuddy_client = None
matchbuddy_instructions = None

document_embeddings = None
document_chunks = None

tools = None

def initialize():
    global document_embeddings, document_chunks

    document_embeddings, document_chunks = load_funcs.load_embeddings("embeddings.pkl")

    global ELLA_API_KEY, ella_client, ella_instructions
    
    ELLA_API_KEY = st.secrets["ELLA_OPENAI_API_KEY"]
    ella_client = OpenAI(api_key=ELLA_API_KEY)
    ella_instructions = load_funcs.load_instructions("ella_instructions.txt")

    global SPLITTER_API_KEY, splitter_client, splitter_instructions

    SPLITTER_API_KEY = st.secrets["SPLITTER_OPENAI_API_KEY"]
    splitter_client = OpenAI(api_key=SPLITTER_API_KEY)
    splitter_instructions = load_funcs.load_instructions("splitter_instructions.txt")

    global MATCH_BUDDY_API_KEY, matchbuddy_client, matchbuddy_instructions

    MATCHBUDDY_API_KEY = st.secrets["MATCHBUDDY_API_KEY"]
    matchbuddy_client = OpenAI(api_key=MATCH_BUDDY_API_KEY)
    matchbuddy_instructions = load_funcs.load_instructions("matchbuddy_instructions.txt")

    global tools
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "find_matching_program",
                "description": "Find the matching program based on the interests of the user",
                "parameters": {
                    "type": "object",
                    "properties": { 
                        "interests":
                        {
                            "type": "string",
                            "description": "A text that explains the interests of the user",
                        },
                    },
                    "required": ["interests"],
                },
            },
        }
    ]

initialize()

if 'ella_conversation_history' not in st.session_state:
    st.session_state.ella_conversation_history = [{"role": "system", "content": ella_instructions}]

if 'splitter_conversation_history' not in st.session_state:
    st.session_state.splitter_conversation_history = [{"role": "system", "content": splitter_instructions}]

if 'matchbuddy_conversation_history' not in st.session_state:
    st.session_state.matchbuddy_conversation_history = [{"role": "system", "content": matchbuddy_instructions}]

st.title("Passage AI Assistant")

response_dict = {"respone": "", "follow-up": []}

def handle_user_input():
    user_input = st.session_state.user_input

    if user_input:
        st.session_state.splitter_conversation_history.append({"role": "user", "content": user_input})
        st.session_state.matchbuddy_conversation_history.append({"role": "user", "content": user_input})      
        st.session_state.ella_conversation_history.append({"role": "user", "content": user_input})

        parts = utils.question_parts(splitter_client, st.session_state.splitter_conversation_history)
        parts_dict = json.loads(parts)

        ella_response = utils.generate_response(ella_client, tools, st.session_state.ella_conversation_history, document_embeddings, document_chunks, parts_dict)
        
        response_text = ella_response.choices[0].message.content.strip()
        
        global response_dict
        response_dict = json.loads(response_text)

        st.session_state.ella_conversation_history.append({"role": "assistant", "content": response_dict["response"]})

        # st.session_state.ella_conversation_history.append({"role": "assistant", "content": final_response})
        st.session_state.user_input = ""

query = st.text_input("Enter your query:", key="user_input", on_change=handle_user_input)
submit_button = st.button("Send", on_click=handle_user_input)

st.markdown("### Conversation History")
for message in st.session_state.get('ella_conversation_history', []):
    if message['role'] == 'assistant':
        st.markdown(f"**Ella:** {message['content']}")
    elif message['role'] == 'user':
        st.markdown(f"**You:** {message['content']}")

for question in response_dict["follow-up"]:
    if st.button(question):
        st.session_state.clicked_button = question

if 'clicked_button' not in st.session_state:
    st.session_state.clicked_button = None