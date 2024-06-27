import requests
from datetime import datetime, timezone
import streamlit as st
from notion_client import Client
from pprint import pprint

notion_token = st.secrets["NOTION_TOKEN"]
database_id = st.secrets["DATABASE_ID"]

# Initialize the Notion client
client = Client(auth=notion_token)

# Replace with your database ID
database_id = database_id

def write_row(title, user_prompt, assistant_response, follow_ups):
    client.pages.create(
        **{
            "parent": {
                "database_id": database_id
            },
            "properties": {
                "title": {"title": [{"text": {"content": title}}]},
                "user_prompt": {"rich_text": [{"text": {"content": user_prompt}}]},
                "assistant_response": {"rich_text": [{"text": {"content": assistant_response}}]},
                "follow_ups": {"rich_text": [{"text": {"content": follow_ups}}]}
            }
        }
    )