import logging
from typing import override
from openai import AssistantEventHandler, OpenAI
import streamlit as st
import utils 
import json
import load_funcs
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os

# def log_interaction(user_input, bot_response):
#     logging.info(f"User: {user_input}")
#     logging.info(f"Ella: {bot_response}")

# def setup_google_drive():
#     gauth = GoogleAuth()

#     # Load credentials from Streamlit secrets and create a client config
#     client_config = {
#         "web": {
#             "client_id": st.secrets["google"]["client_id"],
#             "client_secret": st.secrets["google"]["client_secret"],
#             "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#             "token_uri": "https://oauth2.googleapis.com/token",
#             "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
#             "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
#         }
#     }

#     # This temporary file is used by pydrive for the OAuth process
#     with open('client_secrets.json', 'w') as outfile:
#         json.dump(client_config, outfile)

#     # Load the client config file created above
#     gauth.LoadClientConfigFile('client_secrets.json')
#     gauth.LocalWebserverAuth()

#     drive = GoogleDrive(gauth)
#     return drive

# def upload_to_google_drive(drive):
#     file1 = drive.CreateFile({'title': 'interaction_log.txt'})
#     file1.SetContentFile('interaction_log.txt')
#     file1.Upload()

# drive = setup_google_drive()

def initialize():
    global document_embeddings, document_chunks

    document_embeddings, document_chunks = load_funcs.load_embeddings("embeddings.pkl")

    global SPLITTER_API_KEY, splitter_client, splitter_instructions

    SPLITTER_API_KEY = st.secrets["SPLITTER_OPENAI_API_KEY"]
    splitter_client = OpenAI(api_key=SPLITTER_API_KEY)
    splitter_instructions = load_funcs.load_instructions("splitter_instructions.txt")

    global tools
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "dummy_function_sentiment",
                "description": "This function always receives the response information from the assistant.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "respond": {
                            "type": "string",
                            "description": "The response to the prompt of the user. All the questions of the user must be answered.",
                        },
                        "follow-ups": {
                            "type": "object",
                            "properties": {
                                "follow-up1": {
                                    "type": "string",
                                    "description": "Ella should suggest three follow-up questions from the user's perspective. This is the first suggested follow-up question",
                                },
                                "follow-up2": {
                                    "type": "string",
                                    "description": "Ella should suggest three follow-up questions from the user's perspective. This is the second suggested follow-up question",
                                },
                                "follow-up3": {
                                    "type": "string",
                                    "description": "Ella should suggest three follow-up questions from the user's perspective. This is the third suggested follow-up question",
                                },
                            },
                            "required": ["follow-up1", "follow-up2", "follow-up3"]
                        }
                    },
                    "required": ["respond", "follow-ups"]
                }
            }
        }
    ]

    global ELLA_API_KEY, ella_client, ella_instructions, ella, ella_thread
    
    ELLA_API_KEY = st.secrets["ELLA_OPENAI_API_KEY"]
    ella_client = OpenAI(api_key=ELLA_API_KEY)
    ella_instructions = load_funcs.load_instructions("ella_ins2.txt")
    ella = ella_client.beta.assistants.create(
        name="Ella",
        instructions=ella_instructions,
        tools=tools,
        model="gpt-3.5-turbo",
        temperature=0.1,
    )
    ella_thread = ella_client.beta.threads.create()

initialize()

# class EventHandler(AssistantEventHandler):    
#   @override
#   def on_text_created(self, text) -> None:
#     print(f"\nassistant > {text}", end="", flush=True)
      
#   @override
#   def on_text_delta(self, delta, snapshot):
#     print(delta.value, end="", flush=True)
      
#   def on_tool_call_created(self, tool_call):
#     print(f"\nassistant > {tool_call.type}\n", flush=True)
  
#   def on_tool_call_delta(self, delta, snapshot):
#     if delta.type == 'code_interpreter':
#       if delta.code_interpreter.input:
#         print(delta.code_interpreter.input, end="", flush=True)
#       if delta.code_interpreter.outputs:
#         print(f"\n\noutput >", flush=True)
#         for output in delta.code_interpreter.outputs:
#           if output.type == "logs":
#             print(f"\n{output.logs}", flush=True)

# ella_run = ella_client.beta.threads.runs.create_and_poll(
#     thread_id=ella_thread.id,
#     assistant_id=ella.id
# )

# directory = "data/"

# for file_name in os.listdir(directory):
#   file_path = os.path.join(directory, file_name)
#   with open(file_path, 'rb') as file:
#       file = ella_client.files.create(file=file, purpose="assistants")

message_body = input("Send your message: ")
message = ella_client.beta.threads.messages.create(
  thread_id=ella_thread.id,
  role="user",
  content=message_body,
)

with ella_client.beta.threads.runs.stream(
  thread_id=ella_thread.id,
  assistant_id=ella.id,
 ) as stream:
  stream.until_done()

messages = ella_client.beta.threads.messages.list(thread_id=ella_thread.id)

new_message = messages.data[0].content[0].text.value
logging.info(f"Ella: {new_message}")
print(f"Ella: {new_message}")

# if ella_run.status == "completed":
#     messages=ella_client.beta.threads.messages.list(
#         thread_id=ella_thread.id
#     )
#     print(messages)
# else:
#     print(ella_run.status)






# if 'ella_conversation_history' not in st.session_state:
#     st.session_state.ella_conversation_history = [{"role": "system", "content": ella_instructions}]

# if 'splitter_conversation_history' not in st.session_state:
#     st.session_state.splitter_conversation_history = [{"role": "system", "content": splitter_instructions}]

# if 'response_dict' not in st.session_state:
#     st.session_state.response_dict = {"response": "", "follow-up": []}

# st.title("Passage AI Assistant")

# def handle_user_input(user_input=None):
#     flag = 0
#     if user_input is None:
#         user_input = st.session_state.user_input
#         flag += 1

#     if user_input:
#         st.session_state.splitter_conversation_history.append({"role": "user", "content": user_input})
#         st.session_state.ella_conversation_history.append({"role": "user", "content": user_input})

#         parts = utils.question_parts(splitter_client, st.session_state.splitter_conversation_history)
#         parts_dict = json.loads(parts)

#         ella_response = utils.generate_response(ella_client, tools, st.session_state.ella_conversation_history, document_embeddings, document_chunks, parts_dict)
        
#         print(f"{ella_response=}")

#         response_text = ella_response.choices[0].message.content.strip()

#         st.session_state.response_dict = json.loads(response_text)

#         st.session_state.ella_conversation_history.append({"role": "assistant", "content": st.session_state.response_dict["response"]})

#         if flag > 0:
#             st.session_state.user_input = ""

#         # # Log the interaction
#         # log_interaction(user_input, json.dumps(st.session_state.response_dict))

#         # # Upload the log to Google Drive after each interaction
#         # upload_to_google_drive(drive)


# query = st.text_input("Enter your query:", key="user_input", on_change=handle_user_input)
# submit_button = st.button("Send", on_click=handle_user_input)

# st.markdown("### Conversation History")
# for message in st.session_state.get('ella_conversation_history', []):
#     if message['role'] == 'assistant':
#         st.markdown(f"**Ella:** {message['content']}")
#     elif message['role'] == 'user':
#         st.markdown(f"**You:** {message['content']}")

# if st.session_state.response_dict["follow-up"]:
#     for question in st.session_state.response_dict["follow-up"]:
#         if st.button(question):
#             handle_user_input(question)
#             st.session_state.clicked_button = question
#             st.rerun()