import json
from threading import Thread
import time
import numpy as np
from openai import OpenAI
import streamlit as st
import load_funcs
from datetime import datetime
import re
from streamlit_option_menu import option_menu
import matplotlib.pyplot as plt

from logs_notion import write_row

API_KEY = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=API_KEY)
assistant = client.beta.assistants.retrieve(st.secrets["ASSISTANT_ID"])

SECOND_API_KEY = st.secrets["SECOND_API_KEY"]
second_client = OpenAI(api_key=SECOND_API_KEY)
suggestion_assistant = second_client.beta.assistants.retrieve(st.secrets["SECOND_ASSISTANT_ID"])

INTERVIEWER_API_KEY = st.secrets["INTERVIEWER_API_KEY"]
interviewer_client = OpenAI(api_key=INTERVIEWER_API_KEY)
interviewer_assistant = interviewer_client.beta.assistants.retrieve(st.secrets["INTERVIEWER_ID"])

def cleaned_response(response):
  cleaned_response = re.sub(r'【\d+:\d+†source】', '', response)
  return cleaned_response


def initialize_conversation():
  if 'thread' not in st.session_state:
    st.session_state.thread = client.beta.threads.create()

  if 'second_thread' not in st.session_state:
    st.session_state.second_thread = client.beta.threads.create()

  if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

  if 'showing_conversation_history' not in st.session_state:
    st.session_state.showing_conversation_history = []

  if 'follow_ups' not in st.session_state:
    st.session_state.follow_ups = None

  if 'feedback_flag' not in st.session_state:
    st.session_state.feedback_flag = False

  if 'interview' not in st.session_state:
    st.session_state.interview = ""

  if 'all_user_messages' not in st.session_state:
    st.session_state.all_user_messages = ""

  if 'interviewer_messages' not in st.session_state:
    st.session_state.interviewer_messages = []

  if 'interview_done' not in st.session_state:
    st.session_state.interview_done = False

  if 'score' not in st.session_state:
    st.session_state.score = ""

  initial_messages = ["What are the benefits of studying at George Brown College?", "What are the admission requirements for international students?", "What support services are available for students at George Brown College?"]

  st.session_state.follow_ups = initial_messages

if 'thread' not in st.session_state:
  initialize_conversation()

with st.sidebar:
    selected = option_menu(
        "Main Menu", ["About", "Chat", "Assessment"],
        icons=['info', 'chat', 'clipboard-check'],
        menu_icon="cast", default_index=1
    )

if selected == "Chat":
  history_text = ""
  for message in st.session_state.get('showing_conversation_history', []):
    if message['role'] == 'assistant':
      history_text += f"Assistant: {message['content']}\n\n"
    elif message['role'] == 'user':
      history_text += f"You: {message['content']}\n\n"
    elif message['role'] == 'interviewer':
      history_text += f"Interviewer: {message['content']}\n\n"
        

  st.container().markdown(history_text)

  res_box = st.empty()

def generate_response_func(user_input):
  if st.session_state.interview == "":
    while True:
      st.session_state.all_user_messages += user_input + "\n\n"

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
                  if assistant_response != "" and assistant_response[0] != '&':
                    res_box.markdown(f"You: {user_input}\n\nAssistant: {cleaned_response(assistant_response)}")

      assistant_response = "".join(report).strip()

      if assistant_response == "&&":
        st.session_state.interview = "You entered the interview mode"
        break

      else:
        sources = re.findall(r'【\d+:\d+†source】', assistant_response)

        # print(f"{assistant_response=}")
        # print("Sources found in the response:", sources)

        if assistant_response != "":
          st.session_state.conversation_history.append({"role": "assistant", "content": cleaned_response(assistant_response)})
          st.session_state.showing_conversation_history.append({"role": "assistant", "content": cleaned_response(assistant_response)})
          break

  if st.session_state.interview != "":
     while True:
        if st.session_state.all_user_messages != "":
          if len(st.session_state.all_user_messages) > 10000:
             st.session_state.all_user_messages = st.session_state.all_user_messages[-10000:]

          st.session_state.interviewer_messages.append({"role": "user", "content": st.session_state.all_user_messages})

          st.session_state.all_user_messages = ""

        else:
          st.session_state.interviewer_messages.append({"role": "user", "content": user_input})

        stream = interviewer_client.beta.threads.create_and_run(
        assistant_id=interviewer_assistant.id,
        thread={
          "messages": st.session_state.interviewer_messages
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

                    if "$$$" in assistant_response:
                      parts = re.split(r'\$\$\$', assistant_response)
                      assistant_response = parts[0]
                    
                    res_box.markdown(f"You: {user_input}\n\nInterviewer: {cleaned_response(assistant_response)}")

        assistant_response = "".join(report).strip()

        if "$$$" in assistant_response:
          parts = re.split(r'\$\$\$', assistant_response)
          assistant_response = parts[0]
          st.session_state.score = parts[1]

          print(f"{len(parts)=}")
          print(f"{parts[0]=}")
          print(f"{parts[1]=}")


          st.session_state.interview_done = True

        sources = re.findall(r'【\d+:\d+†source】', assistant_response)

        # print(f"{assistant_response=}")
        # print("Sources found in the response:", sources)

        if assistant_response != "" or st.session_state.interview_done:
            if st.session_state.interview_done:
              st.session_state.interview = "END"

            st.session_state.interviewer_messages.append({"role": "assistant", "content": cleaned_response(assistant_response)})
            st.session_state.conversation_history.append({"role": "assistant", "content": cleaned_response(assistant_response)})
            st.session_state.showing_conversation_history.append({"role": "interviewer", "content": cleaned_response(assistant_response)})
            
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

    # print(f"{new_message=}")

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
      st.session_state.showing_conversation_history.append({"role": "user", "content": user_input})

      threads = [
        Thread(target=generate_response_func(user_input)),
        Thread(target=suggest_prompt_func(user_input))
      ]

      for t in threads:
        t.start()

      for t in threads:
        t.join()

      st.session_state.feedback_flag = True

      write_row("title", st.session_state.showing_conversation_history[-2]['content'], st.session_state.showing_conversation_history[-1]['content'], "#".join(st.session_state.follow_ups))

  if flag > 0:
    st.session_state.user_input = ""  

if selected == "Chat":
  query = st.text_input(label="Enter your query:", key="user_input", on_change=handle_user_input, label_visibility="hidden", placeholder="Message Passage Assistant")

def colored_box(text, color):
  return st.container().markdown(
    f"""
    <div style="background-color: {color}; padding: 10px; border-radius: 5px;">
        <p style="color: white;">{text}</p>
    </div>
    """,
    unsafe_allow_html=True
  )

if selected == "Chat":
  if st.session_state.interview != "":
    if st.session_state.interview == "END":
      st.session_state.interview = "The interview is over! You can view the assessment in the sidebar."

    # st.container().markdown("**" + st.session_state.interview + "**")
    st.container().markdown(f"""
      <div style="background-color: #000000; padding: 5px; border-radius: 5px; text-align: center; margin-bottom: 20px;">
          <p style="color: white; font-size: 20px; margin: 0;"> {st.session_state.interview}</p>
      </div>
      """, unsafe_allow_html=True)
    # colored_box("**" + st.session_state.interview + "**", "#FFFFFF")

    if st.session_state.interview == "The interview is over!":
      st.session_state.interview = ""
    else:
      st.session_state.interview = "You are in the interview mode..."

  if st.session_state.follow_ups and st.session_state.interview == "":
    for question in st.session_state.follow_ups:
      if st.button(f"{question[:-1]}❓"):
        handle_user_input(question)
        st.session_state.clicked_button = question
        st.rerun()

  if st.session_state.feedback_flag:
    st.container().markdown("Was the answer helpful?")
    feedbacks = ["👍 Accurate", "🤔 Could have been better", "👎 Irrelevant or misinformation"]

    for feedback in feedbacks:
      if st.button(feedback):
          st.session_state.feedback_flag = False
          write_row("title", st.session_state.showing_conversation_history[-2]['content'], st.session_state.showing_conversation_history[-1]['content'], "#".join(st.session_state.follow_ups), feedback)
          st.rerun()

if selected == "About":
  st.container().markdown("This is George Brown College AI assistant. \n\n You can ask any questions regarding the programs and visa requirements. \n\nYou may also be interviewed by the interviewer. You just need to tell the assistant that you want to be interviewed.")

def create_radial_bar(score, label, color):
    fig, ax = plt.subplots(subplot_kw=dict(polar=True), figsize=(5, 5))
    
    # Create the angles for the plot
    angles = np.linspace(0, 2 * np.pi, 100)
    
    # Create values for the plot
    values = np.zeros(100)
    values[:int(100 * score / 100)] = 1  # Only fill up to the score

    # Plot the radial bar
    ax.fill(angles, values, color=color, alpha=0.3)
    
    # Remove the radial ticks and labels
    ax.set_yticklabels([])
    ax.set_xticks([])

    # Add the title and score in the middle of the plot
    ax.set_title(f"{label.capitalize()}", size=15, color='black', y=1.1)
    ax.text(0, 0, f"{score}", ha='center', va='center', fontsize=20, color=color)
    
    ax.spines['polar'].set_visible(True)
    ax.spines['polar'].set_color(color)
    ax.spines['polar'].set_linewidth(2)

    ax.grid(False)

    return fig


if selected == "Assessment":
  if st.session_state.interview_done:
    s = st.session_state.score
    start = s.find('{')
    end = s.rfind('}')
    s = s[start:end+1]
    scores = json.loads(s)

    colors = ["red", "blue", "green", "orange"]

    for color, (label, info) in zip(colors, scores.items()):
      fig = create_radial_bar(info['score'], label, color)
      st.pyplot(fig)
      st.write(info['reason'])
  else:
    st.container().markdown("The assessment will be available here once you do the interview.\n\nYou just need to tell the assistant that you want to be interviewed.")