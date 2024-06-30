from threading import Thread
import time
from openai import OpenAI
import streamlit as st
import load_funcs
from datetime import datetime

from logs_notion import write_row

API_KEY = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=API_KEY)
assistant = client.beta.assistants.retrieve(st.secrets["ASSISTANT_ID"])

SECOND_API_KEY = st.secrets["SECOND_API_KEY"]
second_client = OpenAI(api_key=SECOND_API_KEY)
suggestion_assistant = client.beta.assistants.retrieve(st.secrets["SECOND_ASSISTANT_ID"])

def initialize_conversation():
  if 'thread' not in st.session_state:
    st.session_state.thread = client.beta.threads.create()

  if 'second_thread' not in st.session_state:
    st.session_state.second_thread = client.beta.threads.create()

  if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

  if 'follow_ups' not in st.session_state:
    st.session_state.follow_ups = None

  if 'feedback_flag' not in st.session_state:
    st.session_state.feedback_flag = False

  initial_messages = ["What are the benefits of studying at George Brown College?", "What are the admission requirements for international students?", "What support services are available for students at George Brown College?"]

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
res_box = st.empty()

def generate_response_func():
  while True:
    stream = client.beta.threads.create_and_run(
      assistant_id=assistant.id,
      thread={
        "messages": st.session_state.conversation_history
      },
      stream=True
    )

    time.sleep(1)

    report = []

    for event in stream:
        if event.data.object == "thread.message.delta":
          for content in event.data.delta.content:
              if content.type == 'text':
                report.append(content.text.value)
                assistant_response = "".join(report).strip()
                res_box.markdown(f"Assistant: {assistant_response}")

    assistant_response = "".join(report).strip()

    print(f"{assistant_response=}")

    if assistant_response != "":
      st.session_state.conversation_history.append({"role": "assistant", "content": assistant_response})
      break

def suggest_prompt_func(user_input):
  second_client.beta.threads.messages.create(
     thread_id = st.session_state.second_thread.id,
     role="user",
     content=user_input
  )

  while True:
    with second_client.beta.threads.runs.stream(
      thread_id=st.session_state.second_thread.id,
      assistant_id=suggestion_assistant.id,
    ) as stream:
      stream.until_done()

    time.sleep(1)

    messages = second_client.beta.threads.messages.list(thread_id=st.session_state.second_thread.id)

    new_message = messages.data[0].content[0].text.value

    print(f"{new_message=}")

    if new_message != user_input:
      st.session_state.follow_ups = new_message.split('#')
      break


def handle_user_input(user_input=None):
  flag = 0
  if user_input is None:
      user_input = st.session_state.user_input
      flag += 1

  if user_input:
      st.session_state.conversation_history.append({"role": "user", "content": user_input})

      threads = [
        Thread(target=generate_response_func()),
        Thread(target=suggest_prompt_func(user_input))
      ]

      for t in threads:
        t.start()

      for t in threads:
        t.join()

      st.session_state.feedback_flag = True

      write_row("title", st.session_state.conversation_history[-2]['content'], st.session_state.conversation_history[-1]['content'], "#".join(st.session_state.follow_ups))

  if flag > 0:
    st.session_state.user_input = ""  

query = st.text_input(label="Enter your query:", key="user_input", on_change=handle_user_input, label_visibility="hidden", placeholder="Message Passage Assistant")

if st.session_state.follow_ups:
    for question in st.session_state.follow_ups:
        if st.button(question):
            handle_user_input(question)
            st.session_state.clicked_button = question
            st.rerun()

if st.session_state.feedback_flag:
  st.container().markdown("Was the answer helpful?")
  feedbacks = ["👍 Accurate", "🤔 Could have been better", "👎 Irrelevant or misinformation"]

  for feedback in feedbacks:
    if st.button(feedback):
        st.session_state.feedback_flag = False
        write_row("title", st.session_state.conversation_history[-2]['content'], st.session_state.conversation_history[-1]['content'], "#".join(st.session_state.follow_ups), feedback)
        st.rerun()