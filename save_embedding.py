import os
import json
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
import streamlit as st
import pickle
import utils

api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

directory = "data/"

documents = utils.load_documents(directory)

print("Documents loaded successfully")

document_chunks = []
for doc in documents:
    chunks = utils.split_text(doc)
    document_chunks.extend(chunks)

print("Documents splitted successfully")

document_embeddings = [utils.get_embeddings(client, chunk) for chunk in document_chunks]

try:
    with open('embeddings.pkl', 'wb') as f:
        pickle.dump((document_embeddings, document_chunks), f)
    print("Saved the embeddings")
except Exception as e:
    print(str(e))