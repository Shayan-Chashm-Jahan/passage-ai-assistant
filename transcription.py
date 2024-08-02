from openai import OpenAI
import streamlit as st
from st_audiorec import st_audiorec

SPEECH_API_KEY = st.secrets["SPEECH_API_KEY"]
client = OpenAI(api_key=SPEECH_API_KEY)

def transcribe(audio_buffer):
    transcription = client.audio.transcriptions.create(
        model="whisper-1", 
        file=audio_buffer
    )
    return transcription.text