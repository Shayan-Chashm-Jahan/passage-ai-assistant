import requests
from datetime import datetime, timezone
import streamlit as st
from notion_client import Client
from pprint import pprint
from datetime import datetime

notion_token = st.secrets["NOTION_TOKEN"]
database_id = st.secrets["DATABASE_ID"]

# Initialize the Notion client
client = Client(auth=notion_token)

# Replace with your database ID
database_id = database_id

def fix_length(str):
    if len(str) > 2000 - 10:
        return str[:2000 - 10]
    return str

def write_row(title, user_prompt, assistant_response, follow_ups, feedback=""):
    user_prompt = fix_length(user_prompt)
    assistant_response = fix_length(assistant_response)
    follow_ups = fix_length(follow_ups)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    client.pages.create(
        **{
            "parent": {
                "database_id": database_id
            },
            "properties": {
                "title": {"title": [{"text": {"content": f"Message at {current_time}"}}]},
                "user_prompt": {"rich_text": [{"text": {"content": user_prompt}}]},
                "assistant_response": {"rich_text": [{"text": {"content": assistant_response}}]},
                "follow_ups": {"rich_text": [{"text": {"content": follow_ups}}]},
                "feedback": {"rich_text": [{"text": {"content": feedback}}]}
            }
        }
    )