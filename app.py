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
import sys

API_KEY = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=API_KEY)
assistant = client.beta.assistants.retrieve(st.secrets["ASSISTANT_ID"])

SECOND_API_KEY = st.secrets["SECOND_API_KEY"]
second_client = OpenAI(api_key=SECOND_API_KEY)
suggestion_assistant = second_client.beta.assistants.retrieve(st.secrets["SECOND_ASSISTANT_ID"])

INTERVIEWER_API_KEY = st.secrets["INTERVIEWER_API_KEY"]
interviewer_client = OpenAI(api_key=INTERVIEWER_API_KEY)
interviewer_assistant = interviewer_client.beta.assistants.retrieve(st.secrets["INTERVIEWER_ID"])

PROGRAM_SUGGESTER_API_KEY = st.secrets["PROGRAM_SUGGESTER_API_KEY"]
program_suggester_client = OpenAI(api_key=PROGRAM_SUGGESTER_API_KEY)
program_suggester_assistant = program_suggester_client.beta.assistants.retrieve(st.secrets["PROGRAM_SUGGESTER_ID"])

EVALUATOR_API_KEY = st.secrets["EVALUATOR_API_KEY"]
evaluator_client = OpenAI(api_key=EVALUATOR_API_KEY)
evaluator_assistant = evaluator_client.beta.assistants.retrieve(st.secrets["EVALUATOR_ID"])

ENGLISH_EVAL_API_KEY = st.secrets["ENGLISH_EVAL_API_KEY"]
english_evaluator_client = OpenAI(api_key=ENGLISH_EVAL_API_KEY)
english_evaluator_assistant = english_evaluator_client.beta.assistants.retrieve(st.secrets["ENGLISH_EVAL_ID"])

st.set_page_config(
	layout="wide",
    page_title="GBC AI Assistant",
    page_icon="./img/page-icon.png" 
)

# st.write("Currently down, please check back later!")
# sys.exit(0)

def initialize_conversation():
	if 'chat_thread' not in st.session_state:
		st.session_state.thread = client.beta.threads.create()

	if 'second_thread' not in st.session_state:
		st.session_state.second_thread = second_client.beta.threads.create()

	if 'evaluator_thread' not in st.session_state:
		st.session_state.evaluator_thread = evaluator_client.beta.threads.create()

	if 'english_evaluator_thread' not in st.session_state:
		st.session_state.english_evaluator_thread = english_evaluator_client.beta.threads.create()

	if 'program_suggester_thread' not in st.session_state:
		st.session_state.program_suggester_thread = program_suggester_client.beta.threads.create()

	if 'interviewer_thread' not in st.session_state:
		st.session_state.interviewer_thread = interviewer_client.beta.threads.create()

	if 'conversation_history' not in st.session_state:
		st.session_state.conversation_history = []

	if 'follow_ups' not in st.session_state:
		st.session_state.follow_ups = None

	if 'feedback_flag' not in st.session_state:
		st.session_state.feedback_flag = False

	if 'interview_mode' not in st.session_state:
		st.session_state.interview_mode = 0

	if 'interview_started' not in st.session_state:
		st.session_state.interview_started = False

	if 'interview_messages' not in st.session_state:
		st.session_state.interview_messages = []

	if 'interview_messages_copy' not in st.session_state:
		st.session_state.interview_messages_copy = []

	if 'score' not in st.session_state:
		st.session_state.score = {}

	if 'program_suggestion' not in st.session_state:
		st.session_state.program_suggestion = ""

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

	if 'chat_disabled' not in st.session_state:
		st.session_state.chat_disabled = False


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
						if chunk[0] == '&':
							st.session_state.assistant_response = "Please follow me to the interview room..."
							yield st.session_state.assistant_response
							return

	print(f" ---- {report=}")
	st.session_state.assistant_response = "".join(report)

def get_messages_string(interview_messages):
	messages_list = []
	for message in interview_messages:
		messages_list.append(f"""{message["role"]}: {message["content"]}""")

	modified_list = [f"\"{message}\"" for message in messages_list]
	return f"[{', '.join(modified_list)}]"

def get_program():
	interview_messages = get_messages_string(st.session_state.interview_messages_copy)

	print(" ### The LIST: ###")
	print(interview_messages)

	program_suggester_client.beta.threads.messages.create(
		 thread_id = st.session_state.program_suggester_thread.id,
		 role="user",
		 content=interview_messages
	)

	with program_suggester_client.beta.threads.runs.stream(
		thread_id=st.session_state.program_suggester_thread.id,
		assistant_id=program_suggester_assistant.id,
	) as stream:
		stream.until_done()

	messages = program_suggester_client.beta.threads.messages.list(thread_id=st.session_state.program_suggester_thread.id)

	st.session_state.program_suggestion = messages.data[0].content[0].text.value


def get_evaluation():
	interview_messages = get_messages_string(st.session_state.interview_messages_copy)

	evaluator_client.beta.threads.messages.create(
		 thread_id = st.session_state.evaluator_thread.id,
		 role="user",
		 content=interview_messages
	)

	with evaluator_client.beta.threads.runs.stream(
		thread_id=st.session_state.evaluator_thread.id,
		assistant_id=evaluator_assistant.id,
	) as stream:
		stream.until_done()

	messages = evaluator_client.beta.threads.messages.list(thread_id=st.session_state.evaluator_thread.id)

	new_message = messages.data[0].content[0].text.value

	s = new_message
	s = re.sub(r'[“”]', '"', s)
	start = s.find('{')
	end = s.rfind('}')
	s = s[start:end+1]

	english_evaluator_client.beta.threads.messages.create(
		 thread_id = st.session_state.english_evaluator_thread.id,
		 role="user",
		 content=interview_messages
	)

	with english_evaluator_client.beta.threads.runs.stream(
		thread_id=st.session_state.english_evaluator_thread.id,
		assistant_id=english_evaluator_assistant.id,
	) as stream:
		stream.until_done()

	messages = english_evaluator_client.beta.threads.messages.list(thread_id=st.session_state.english_evaluator_thread.id)

	new_message = messages.data[0].content[0].text.value

	t = new_message
	t = re.sub(r'[“”]', '"', t)
	start = t.find('{')
	end = t.rfind('}')
	t = t[start:end+1]

	sd = json.loads(s)

	print(f" ------ This is t:  ----- \n {t}")

	td = json.loads(t)

	sd["english"] = td["english"]

	st.session_state.score = sd	


def generate_response_func(user_input):
		st.session_state.chat_disabled = True
	# try:
		if st.session_state.interview_mode % 2 == 0:
				st.session_state.conversation_history.append({"role": "user", "content": user_input})
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

				if assistant_response == "Please follow me to the interview room...":
					st.session_state.conversation_history.append({"role": "assistant", "content": cleaned_response(assistant_response)})
					st.session_state.interview_mode += 1
					st.session_state.chat_disabled = False
					st.rerun()

				else:
					if assistant_response != "":
						st.session_state.conversation_history.append({"role": "assistant", "content": cleaned_response(assistant_response)})

		else:
				print("in func...")

				st.session_state.interview_messages.append({"role": "user", "content": user_input})
				st.session_state.interview_messages_copy.append({"role": "user", "content": user_input})

				interviewer_client.beta.threads.messages.create(
					thread_id = st.session_state.interviewer_thread.id,
					role="user",
					content=user_input
				)

				while True:
					print("in while...")
					with interviewer_client.beta.threads.runs.stream(
						thread_id=st.session_state.interviewer_thread.id,
						assistant_id=interviewer_assistant.id,
					) as stream:
						stream.until_done()

					messages = interviewer_client.beta.threads.messages.list(thread_id=st.session_state.interviewer_thread.id)

					new_message = messages.data[0].content[0].text.value

					print(f"{new_message=}")

					if new_message != user_input:
						st.session_state.interview_messages.append({"role": "assistant", "content": new_message})
						st.session_state.interview_messages_copy.append({"role": "assistant", "content": new_message})
						break


				last_message = st.session_state.interview_messages[-1]["content"]

				if last_message == '&&':
					with st.chat_message("assistant"):
						st.write("Thank you. The interview is over. Your assessment will be ready in a minute...")

					get_program()
					get_evaluation()
					st.session_state.interview_mode = 3
					st.session_state.chat_disabled = False
					st.rerun()

				with st.chat_message("assistant"):
					st.write(last_message)

		st.session_state.chat_disabled = False


			# 	st.session_state.interview_messages.append({"role": "user", "content": user_input})
			# 	print(f"{st.session_state.interview_messages=}")
			# 	stream = interviewer_client.beta.threads.create_and_run(
			# 	assistant_id=interviewer_assistant.id,
			# 	thread={
			# 		"messages": st.session_state.interview_messages
			# 	},
			# 	stream=True,
			# 	timeout=5
			# )
			# 	with st.chat_message("assistant"):
			# 		st.write_stream(streamed_response_generator(stream))
				
			# 	assistant_response = st.session_state.assistant_response
			# 	print(f"{assistant_response=}")

			# 	if "END" in assistant_response:
			# 		s = assistant_response
			# 		start = s.find('[')
			# 		end = s.rfind(']')
			# 		s = s[start:end+1]
			# 		assistant_response = s

			# 		if assistant_response != "":
			# 			st.session_state.interview_messages.append({"role": "assistant", "content": cleaned_response(assistant_response)})

			# 		get_program(st.session_state.interview_messages)
			# 		get_evaluation(st.session_state.interview_messages)
			# 		st.session_state.interview_mode = 3

			# 		st.rerun()

			# 	if assistant_response != "":
			# 		st.session_state.interview_messages.append({"role": "assistant", "content": cleaned_response(assistant_response)})
						
	# except Exception as e:
	# 	st.session_state.have_error = e

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
			# threads = [Thread(target=generate_response_func(user_input))]

			# if st.session_state.interview_mode % 2 == 0:
			# 	threads.append(Thread(target=suggest_prompt_func(user_input)))

			# for t in threads:
			# 	t.start()

			# for t in threads:
			# 	t.join()

			generate_response_func(user_input)
			if st.session_state.interview_mode % 2 == 0:
				suggest_prompt_func(user_input)

			st.session_state.feedback_flag = True

			if st.session_state.interview_mode % 2 == 0:
				write_row(st.session_state.session_id, st.session_state.conversation_history[-2]['content'], st.session_state.conversation_history[-1]['content'], "#".join(st.session_state.follow_ups))
			else:
				write_row(st.session_state.session_id, st.session_state.interview_messages[-2]['content'], st.session_state.interview_messages[-1]['content'], '-')

	if flag > 0:
		st.session_state.user_input = "" 

def colored_box(text, color):
  return st.container().markdown(
    f"""
    <div style="background-color: {color}; padding: 10px; border-radius: 5px;">
        <p style="color: white;">{text}</p>
    </div>
    """,
    unsafe_allow_html=True
  )

if st.session_state.interview_mode == 0:
	with st.sidebar:
		selected = option_menu(
				"Main Menu", ["About", "Chat", "Interview"],
				icons=['info', 'chat', 'person-lines-fill'],
				menu_icon="cast", default_index=1
		)
elif st.session_state.interview_mode == 1:
	with st.sidebar:
		selected = option_menu(
				"Main Menu", ["About", "Chat", "Interview"],
				icons=['info', 'chat', 'person-lines-fill'],
				menu_icon="cast", default_index=2
		)
elif st.session_state.interview_mode == 2:
	with st.sidebar:
		selected = option_menu(
				"Main Menu", ["About", "Chat", "Assessment"],
				icons=['info', 'chat', 'clipboard-check'],
				menu_icon="cast", default_index=1
		)
else:
	with st.sidebar:
		selected = option_menu(
				"Main Menu", ["About", "Chat", "Assessment"],
				icons=['info', 'chat', 'clipboard-check'],
				menu_icon="cast", default_index=2
		)

if selected == "Chat" and st.session_state.have_error == "":
	if st.session_state.interview_mode % 2:
		st.session_state.interview_mode -= 1
		st.rerun()

	# st.container().markdown(f"""
    #   <div style="background-color: #2E2633; padding: 5px; border-radius: 5px; text-align: center; margin-bottom: 20px;">
    #       <p style="color: #FF8A4B; font-size: 20px; margin: 0;"> I am supposed to respond merely based on the documents provided to me. I'm set to use no outside knowledge. Tough my data is not complete yet, so I might not be able to answer all your questions at the moment.</p>
    #   </div>
    #   """, unsafe_allow_html=True)
	
	# colored_box("**I am supposed to respond merely based on the documents provided to me. I'm set to use no outside knowledge. Tough my data is not complete yet, so I might not be able to answer all your questions at the moment.**", "#FFFFFF")

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
		disabled = st.session_state.chat_disabled
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
						st.session_state.chat_disabled = True

	with col2:
		with st.popover("Report", use_container_width=True):
			if st.session_state.feedback_flag:
				st.container().markdown("Was the answer helpful?")
				feedbacks = ["👍 Accurate", "🤔 Could have been better", "👎 Irrelevant or misinformation"]

				for feedback in feedbacks:
					if st.button(feedback):
							st.session_state.feedback_flag = False
							st.session_state.clicked_button = feedback
							st.session_state.chat_disabled = True

	if st.session_state.clicked_button:
		st.rerun()

if selected == "About":
	st.container().markdown(f"""
		<div style="text-align: center;">
			{st.session_state.gbc_logo}
	""", unsafe_allow_html=True)
	st.container().markdown("This is George Brown College AI assistant. \n\n You can ask any questions regarding the programs and visa requirements. \n\nYou may also be interviewed by the interviewer. You just need to tell the assistant that you want to be interviewed.")
if selected == "Assessment":
	if st.session_state.interview_mode != 3:
		st.session_state.interview_mode = 3
		st.rerun()

	st.write(st.session_state.program_suggestion)

	scores = st.session_state.score

	print(f"{scores=}")

	top_row = st.columns(1)

	top_row[0].markdown("---")

	col1, col2 = st.columns((2, 2))
	columns = [col1, col2, col1, col2, col1]

	for (label, info), col in zip(scores.items(), columns):
		print(f"{label=} --- {info=}")

		if info['score'] < 5:
				info['score'] = 5

		col.markdown(f"### {label.title()}")

		fig = create_gauge(info['score'], label)
		col.plotly_chart(fig, use_container_width=True)
		col.markdown(f"<div style='min-height: 150px;'>{info['reason']}</div>", unsafe_allow_html=True)

		with col.expander("How to improve?"):
			if label == "english":
				improve_message = info['improvements']
				improve_message = "\n\n".join(improve_message)
			else:
				improve_message = info['improvement']
			st.write(improve_message)

if st.session_state.have_error != "":
	st.container().markdown(st.session_state.have_error)

if selected == "Interview" and not st.session_state.interview_started:
	with st.chat_message("assistant"):
		st.container().markdown("**The interview takes around 10 minutes. Are you ready to start?**")

	if st.button("start"):
		st.session_state.interview_started = True
		st.session_state.interview_mode = 1
		st.rerun()

if selected == "Interview" and st.session_state.interview_started:
	if st.session_state.interview_mode % 2 == 0:
		st.session_state.interview_mode += 1
		st.session_state.chat_disabled = False
		st.rerun()
	
	if len(st.session_state.interview_messages) == 0:
		handle_user_input("Hi")
		st.session_state.chat_disabled = False
		st.rerun()

	for message in st.session_state.interview_messages_copy[1:]:
		with st.chat_message(message['role']):
			st.write(message['content'])

	if prompt := st.chat_input(
		"Send message to the interviewer"#, disabled=st.session_state.chat_disabled
	):
		with st.chat_message("user"):
			st.write(prompt)
		handle_user_input(prompt)

	# if prompt := st.chat_input(
	# 	"Ask a question",
	# 	disabled= not (st.session_state.clicked_button is None)
	# ):
	# 	with st.chat_message("user"):
	# 		st.write(prompt)
	# 	handle_user_input(prompt)

	# if st.session_state.clicked_button:
	# 	str = st.session_state.clicked_button
	# 	st.session_state.clicked_button = None

	# 	if str[-1] == '?':
	# 		with st.chat_message("user"):
	# 			st.write(str)
	# 		handle_user_input(str)
	# 	else:
	# 		write_row(st.session_state.session_id, st.session_state.conversation_history[-2]['content'], st.session_state.conversation_history[-1]['content'], "#".join(st.session_state.follow_ups), str)

	# 	st.rerun()

	# c = st.container()
	# col1, col2, col3 = c.columns((1, 1, 3))

	# with col1:
	# 	with st.popover("Report", use_container_width=True):
	# 		if st.session_state.feedback_flag:
	# 			st.container().markdown("Was the answer helpful?")
	# 			feedbacks = ["👍 Accurate", "🤔 Could have been better", "👎 Irrelevant or misinformation"]

	# 			for feedback in feedbacks:
	# 				if st.button(feedback):
	# 					st.session_state.feedback_flag = False
	# 					st.session_state.clicked_button = feedback

	# if st.session_state.clicked_button:
	# 	st.rerun()

if len(st.session_state.conversation_history) > 30:
	st.session_state.conversation_history = st.session_state.conversation_history[-26:]

if len(st.session_state.interview_messages) > 30:
	st.session_state.interview_messages = st.session_state.interview_messages[-26:]

