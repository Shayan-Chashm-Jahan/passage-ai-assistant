import json
from threading import Thread
import time
from openai import OpenAI
import streamlit as st
import re
from streamlit_option_menu import option_menu
from logs_notion import write_row
from utils import cleaned_response, create_gauge
import random

API_KEY = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=API_KEY)
assistant = client.beta.assistants.retrieve(st.secrets["ASSISTANT_ID"])

SECOND_API_KEY = st.secrets["SECOND_API_KEY"]
second_client = OpenAI(api_key=SECOND_API_KEY)
suggestion_assistant = second_client.beta.assistants.retrieve(st.secrets["SECOND_ASSISTANT_ID"])

INTERVIEWER_API_KEY = st.secrets["INTERVIEWER_API_KEY"]
interviewer_client = OpenAI(api_key=INTERVIEWER_API_KEY)
interviewer_assistant = interviewer_client.beta.assistants.retrieve(st.secrets["INTERVIEWER_ID"])

st.set_page_config(layout="wide")

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

  if 'session_id' not in st.session_state:
    # st.session_state.session_id = str(uuid.uuid4())
    st.session_state.session_id = random.randint(1000, 10000)

  if 'have_error' not in st.session_state:
    st.session_state.have_error = False

  if 'gbc_logo' not in st.session_state:
    with open("./img/George_Brown_College_logo.svg", "r") as svg_file:
      st.session_state.gbc_logo = svg_file.read()


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

if selected == "Chat" and st.session_state.have_error == False:
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
  try:
    if st.session_state.interview == "":
      for step in range(3):
        st.session_state.all_user_messages += user_input + "\n\n"

        stream = client.beta.threads.create_and_run(
          assistant_id=assistant.id,
          thread={
            "messages": st.session_state.conversation_history
          },
          stream=True,
          timeout=5,
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
      for step in range(3):
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
        stream=True,
        timeout=5
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
          write_row(st.session_state.session_id, "-", "-", parts[1])

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
        
        if step == 2:
          raise Exception("timeout")
  except Exception as e:
    st.session_state.have_error = True
    st.error("Open AI is not responding. Please try again later.")
    print(f"{e} - {st.session_state.have_error}")

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

      write_row(st.session_state.session_id, st.session_state.showing_conversation_history[-2]['content'], st.session_state.showing_conversation_history[-1]['content'], "#".join(st.session_state.follow_ups))

  if flag > 0:
    st.session_state.user_input = ""  

if selected == "Chat" and st.session_state.have_error == False:
  query = st.text_input(label="Enter your query:", key="user_input", on_change=handle_user_input, label_visibility="hidden", placeholder="Message Passage Assistant")

  if st.session_state.interview != "":
    if st.session_state.interview == "END":
      st.session_state.interview = "The interview is over! You can view the assessment in the sidebar."

    # st.container().markdown("**" + st.session_state.interview + "**")
    st.container().markdown(f"""
      <div style="background-color: #ff8a4b; padding: 5px; border-radius: 5px; text-align: center; margin-bottom: 20px;">
          <p style="color: white; font-size: 20px; margin: 0;"> {st.session_state.interview}</p>
      </div>
      """, unsafe_allow_html=True)
    
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
          write_row(st.session_state.session_id, st.session_state.showing_conversation_history[-2]['content'], st.session_state.showing_conversation_history[-1]['content'], "#".join(st.session_state.follow_ups), feedback)
          st.rerun()

if selected == "About":
  st.container().markdown(f"""
    <div style="text-align: center;">
      {st.session_state.gbc_logo}
  """, unsafe_allow_html=True)
  st.container().markdown("This is George Brown College AI assistant. \n\n You can ask any questions regarding the programs and visa requirements. \n\nYou may also be interviewed by the interviewer. You just need to tell the assistant that you want to be interviewed.")
if selected == "Assessment":
  if st.session_state.interview_done:
    s = st.session_state.score
    s = re.sub(r'[“”]', '"', s)
    start = s.find('{')
    end = s.rfind('}')
    s = s[start:end+1]

    print(f"{s=}")

    scores = json.loads(s)

    top_row = st.columns(1)

    top_row[0].markdown("This is what our interviewer has told us. He also has several suggestions for you to increase your chances!")
    top_row[0].markdown("---")

    col1, col2 = st.columns((2, 2))
    columns = [col1, col2, col1, col2, col1]

    for (label, info), col in zip(scores.items(), columns):
      if info['score'] < 5:
          info['score'] = 5

      fig = create_gauge(info['score'], label)
      col.plotly_chart(fig, use_container_width=True)
      col.markdown(f"<div style='min-height: 150px;'>{info['reason']}</div>", unsafe_allow_html=True)

      with col.expander("How to improve?"):
          st.write(info['improvement'])
  else:
    st.container().markdown("The assessment will be available here once you do the interview.\n\nYou just need to tell the assistant that you want to be interviewed.")
    if st.button("interview"):
      selected = "Chat"

print(st.session_state.have_error)

if st.session_state.have_error:
  st.container().markdown("Unfortunately, OpenAI is not responding. Please try again later.")
  print("In...")