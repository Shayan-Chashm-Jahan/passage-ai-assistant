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

EVALUATOR_API_KEY = st.secrets["EVALUATOR_API_KEY"]
evaluator_client = OpenAI(api_key=EVALUATOR_API_KEY)
evaluator_assistant = evaluator_client.beta.assistants.retrieve(st.secrets["EVALUATOR_ID"])

st.set_page_config(layout="wide")

def initialize_conversation():
	if 'chat_thread' not in st.session_state:
		st.session_state.thread = client.beta.threads.create()

	if 'second_thread' not in st.session_state:
		st.session_state.second_thread = second_client.beta.threads.create()

	if 'conversation_history' not in st.session_state:
		st.session_state.conversation_history = []

	if 'follow_ups' not in st.session_state:
		st.session_state.follow_ups = None

	if 'feedback_flag' not in st.session_state:
		st.session_state.feedback_flag = False

	if 'interview_mode' not in st.session_state:
		st.session_state.interview_mode = 0

	if 'all_user_messages' not in st.session_state:
		st.session_state.all_user_messages = ""

	if 'interview_messages' not in st.session_state:
		st.session_state.interview_messages = []

	if 'score' not in st.session_state:
		st.session_state.score = ""

	if 'session_id' not in st.session_state:
		# st.session_state.session_id = str(uuid.uuid4())
		st.session_state.session_id = random.randint(1000, 10000)

	if 'have_error' not in st.session_state:
		st.session_state.have_error = ""

	if 'gbc_logo' not in st.session_state:
		with open("./img/George_Brown_College_logo.svg", "r") as svg_file:
			st.session_state.gbc_logo = svg_file.read()

	if 'assistant_response' not in st.session_state:
		st.session_state.assistant_response = ""

	if 'clicked_button' not in st.session_state:
		st.session_state.clicked_button = None

	if 'temp' not in st.session_state:
		st.session_state.temp = []


	initial_messages = ["What are the benefits of studying at George Brown College?", "What are the admission requirements for international students?", "What support services are available for students at George Brown College?"]

	st.session_state.follow_ups = initial_messages

if 'thread' not in st.session_state:
	initialize_conversation()

def streamed_response_generator(stream):
	report = []

	for event in stream:
		if event.data.object == "thread.message.delta":
			for content in event.data.delta.content:
					if content.type == 'text':
						chunk = content.text.value
						report.append(content.text.value)
						if chunk != "" and chunk[0] != '&':
							yield chunk

	st.session_state.assistant_response = "".join(report)

def get_evaluation(interview_messages):
	stream = evaluator_client.beta.threads.create_and_run(
		assistant_id=evaluator_assistant.id,
		thread={
			"messages":[{"role": "user", "content": "\n".join(f"{interview_messages["role"]}: {interview_messages["content"]}")}]
		},
		stream=True,
		timeout=5,
	)

	streamed_response_generator(stream)

	s = st.session_state.assistant_response
	print(f"{s=}")
	s = re.sub(r'[“”]', '"', s)
	start = s.find('{')
	end = s.rfind('}')
	s = s[start:end+1]
	st.session_state.score = s

def generate_response_func(user_input):
	try:
		if st.session_state.interview_mode % 2 == 0:
				stream = client.beta.threads.create_and_run(
					assistant_id=assistant.id,
					thread={
						"messages": st.session_state.conversation_history
					},
					stream=True,
					timeout=5,
				)

				with st.chat_message("assistant"):
					st.write_stream(streamed_response_generator(stream))

				assistant_response = st.session_state.assistant_response

				if assistant_response == "&&":
					st.session_state.interview_mode += 1
					st.rerun()

				else:
					if assistant_response != "":
						st.session_state.conversation_history.append({"role": "assistant", "content": cleaned_response(assistant_response)})

		else:
				stream = interviewer_client.beta.threads.create_and_run(
				assistant_id=interviewer_assistant.id,
				thread={
					"messages": st.session_state.interview_messages
				},
				stream=True,
				timeout=5
			)
				with st.chat_message("assistant"):
					st.write_stream(streamed_response_generator(stream))
				
				assistant_response = st.session_state.assistant_response

				if "$$$" in assistant_response:
					parts = re.split(r'\$\$\$', assistant_response)
					assistant_response = parts[0]

					get_evaluation(st.session_state.interview_messages)
					st.session_state.interview_mode = 3

				if assistant_response != "":
					st.session_state.interview_messages.append({"role": "assistant", "content": cleaned_response(assistant_response)})
						
	except Exception as e:
		st.session_state.have_error = e

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

		messages = second_client.beta.threads.messages.list(thread_id=st.session_state.second_thread.id)

		new_message = messages.data[0].content[0].text.value

		if new_message != user_input:
			st.session_state.follow_ups = new_message.split('#')
			break


def handle_user_input(user_input=None):
	st.session_state.follow_ups = None

	flag = 0
	if user_input is None:
			user_input = st.session_state.user_input
			flag += 1

	if user_input:
			if st.session_state.interview_mode % 2 == 0:
				st.session_state.conversation_history.append({"role": "user", "content": user_input})
			else:
				st.session_state.interview_messages.append({"role": "user", "content": user_input})
	
			threads = [Thread(target=generate_response_func(user_input))]

			if st.session_state.interview_mode % 2 == 0:
				threads.append(Thread(target=suggest_prompt_func(user_input)))

			for t in threads:
				t.start()

			for t in threads:
				t.join()

			st.session_state.feedback_flag = True

			if st.session_state.interview_mode % 2 == 0:
				write_row(st.session_state.session_id, st.session_state.conversation_history[-2]['content'], st.session_state.conversation_history[-1]['content'], "#".join(st.session_state.follow_ups))
			else:
				# TODO
				pass

	if flag > 0:
		st.session_state.user_input = ""  

if st.session_state.interview_mode % 2 == 0:
	with st.sidebar:
		selected = option_menu(
				"Main Menu", ["About", "Chat", "Interview", "Assessment"],
				icons=['info', 'chat', 'person-lines-fill', 'clipboard-check'],
				menu_icon="cast", default_index=1
		)
else:
	with st.sidebar:
		selected = option_menu(
				"Main Menu", ["About", "Chat", "Interview", "Assessment"],
				icons=['info', 'chat', 'person-lines-fill', 'clipboard-check'],
				menu_icon="cast", default_index=2
		)

if selected == "Chat" and st.session_state.have_error == "":
	if st.session_state.interview_mode % 2:
		st.session_state.interview_mode -= 1

	# container_css = """
	# <style>
	#     .scrollable-container {
	#         min-height: 2000px;
	#         max-height: 100vh; /* Ensure it doesn't exceed the viewport height */
	#         overflow-y: scroll;
	#         padding: 20px;
	#         border: 1px solid #ccc;
	#     }
	# </style>
	# """

	# # Apply the custom CSS
	# st.markdown(container_css, unsafe_allow_html=True)

	for message in st.session_state.get('conversation_history', []):
		with st.chat_message(message['role']):
			st.write(message['content'])

	if prompt := st.chat_input(
		"Ask a question",
		disabled= not (st.session_state.clicked_button is None)
	):
		with st.chat_message("user"):
					st.write(prompt)
		handle_user_input(prompt)

	if st.session_state.clicked_button:
		str = st.session_state.clicked_button
		st.session_state.clicked_button = None

		if str[-1] == '?':
			with st.chat_message("user"):
				st.write(str)
			handle_user_input(str)
		else:
			write_row(st.session_state.session_id, st.session_state.conversation_history[-2]['content'], st.session_state.conversation_history[-1]['content'], "#".join(st.session_state.follow_ups), str)

		st.rerun()

	c = st.container()
	col1, col2, col3 = c.columns((1, 1, 3))

	with col1:
		with st.popover("Question", use_container_width=True):
			if st.session_state.follow_ups:
				for question in st.session_state.follow_ups:
					if st.button(f"{question[:-1]}❓"):
						st.session_state.clicked_button = question

	with col2:
		with st.popover("Report", use_container_width=True):
			if st.session_state.feedback_flag:
				st.container().markdown("Was the answer helpful?")
				feedbacks = ["👍 Accurate", "🤔 Could have been better", "👎 Irrelevant or misinformation"]

				for feedback in feedbacks:
					if st.button(feedback):
							st.session_state.feedback_flag = False
							st.session_state.clicked_button = feedback

	if st.session_state.clicked_button:
		st.rerun()

if selected == "About":
	st.container().markdown(f"""
		<div style="text-align: center;">
			{st.session_state.gbc_logo}
	""", unsafe_allow_html=True)
	st.container().markdown("This is George Brown College AI assistant. \n\n You can ask any questions regarding the programs and visa requirements. \n\nYou may also be interviewed by the interviewer. You just need to tell the assistant that you want to be interviewed.")
if selected == "Assessment":
	if st.session_state.interview_mode >= 2:
		s = st.session_state.score

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

if st.session_state.have_error != "":
	st.container().markdown(st.session_state.have_error)

if selected == "Interview":
	if st.session_state.interview_mode % 2 == 0:
		st.session_state.interview_mode += 1
	
	for message in st.session_state.get('interview_messages', []):
		with st.chat_message(message['role']):
			st.write(message['content'])

	if prompt := st.chat_input(
		"Ask a question",
		disabled= not (st.session_state.clicked_button is None)
	):
		with st.chat_message("user"):
			st.write(prompt)
		handle_user_input(prompt)

	if st.session_state.clicked_button:
		str = st.session_state.clicked_button
		st.session_state.clicked_button = None

		if str[-1] == '?':
			with st.chat_message("user"):
				st.write(str)
			handle_user_input(str)
		else:
			write_row(st.session_state.session_id, st.session_state.conversation_history[-2]['content'], st.session_state.conversation_history[-1]['content'], "#".join(st.session_state.follow_ups), str)

		st.rerun()

	c = st.container()
	col1, col2, col3 = c.columns((1, 1, 3))

	with col1:
		with st.popover("Report", use_container_width=True):
			if st.session_state.feedback_flag:
				st.container().markdown("Was the answer helpful?")
				feedbacks = ["👍 Accurate", "🤔 Could have been better", "👎 Irrelevant or misinformation"]

				for feedback in feedbacks:
					if st.button(feedback):
						st.session_state.feedback_flag = False
						st.session_state.clicked_button = feedback

	if st.session_state.clicked_button:
		st.rerun()

if len(st.session_state.conversation_history) > 26:
	st.session_state.conversation_history = st.session_state.conversation_history[-26:]

if len(st.session_state.interview_messages) > 26:
	st.session_state.interview_messages = st.session_state.interview_messages[-26:]

