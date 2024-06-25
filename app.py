from openai import OpenAI
import streamlit as st

def handle_user_input(user_input=None):
  flag = 0
  if user_input is None:
      user_input = st.session_state.user_input
      flag += 1

  if user_input:
      st.session_state.conversation_history.append({"role": "user", "content": user_input})

      client.beta.threads.messages.create(
          thread_id=st.session_state.thread.id,
          role="user",
          content=user_input
      )

      response_promt = ""

      while True:
        with client.beta.threads.runs.stream(
          thread_id=st.session_state.thread.id,
          assistant_id=assistant.id,
        ) as stream:
          stream.until_done()

        messages = client.beta.threads.messages.list(thread_id=st.session_state.thread.id)

        new_message = messages.data[0].content[0].text.value

        if new_message != user_input:
          response_promt = new_message
          break

      st.session_state.conversation_history.append({"role": "assistant", "content": response_promt})

      client.beta.threads.messages.create(
          thread_id=st.session_state.thread.id,
          role="user",
          content="Based on the last few messages between you and me, suggest three questions or statements that I might have. The questions should be from my perspecive. Don't add any additional text, JUST THREE SUGGESTED FOLLOWUP QUESTIONS, splitted by a single # sign"
      )

      while True:
        with client.beta.threads.runs.stream(
          thread_id=st.session_state.thread.id,
          assistant_id=assistant.id,
        ) as stream:
          stream.until_done()

        messages = client.beta.threads.messages.list(thread_id=st.session_state.thread.id)

        new_message = messages.data[0].content[0].text.value

        if new_message != response_promt:
          st.session_state.follow_ups = new_message.split('#')
          break

  if flag > 0:
    st.session_state.user_input = ""  

API_KEY = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=API_KEY)
assistant = client.beta.assistants.retrieve(st.secrets["ASSISTANT_ID"])

def initialize_conversation():

  if 'thread' not in st.session_state:
    st.session_state.thread = client.beta.threads.create()

  if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

  if 'follow_ups' not in st.session_state:
    st.session_state.follow_ups = None

  initial_messages = ["What does Passage Assistant do?", "What is Passage?", "What is GBC?"]

  st.session_state.follow_ups = initial_messages

if 'thread' not in st.session_state:
  initialize_conversation()

history_text = ""
for message in st.session_state.get('conversation_history', []):
    if message['role'] == 'assistant':
        history_text += f"Assistant: {message['content']}\n\n"
    elif message['role'] == 'user':
        history_text += f"You: {message['content']}\n\n"

st.container().markdown(history_text)

query = st.text_input(label="Enter your query:", key="user_input", on_change=handle_user_input, label_visibility="hidden", placeholder="Message Passage Assistant")

if st.session_state.follow_ups:
    for question in st.session_state.follow_ups:
        if st.button(question):
            handle_user_input(question)
            st.session_state.clicked_button = question
            st.rerun()