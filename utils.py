import os
import json
from sklearn.metrics.pairwise import cosine_similarity
import streamlit as st

def load_documents(directory):
    documents = []
    try:
        for file_name in os.listdir(directory):
            file_path = os.path.join(directory, file_name)
            with open(file_path, 'r') as file:
                if file_name.endswith('.json'):
                    data = json.load(file)
                    documents.append(json.dumps(data))
                else:
                    documents.append(file.read())
    except Exception as e:
        print(f"Error loading documents: {e}")
    return documents

def split_text(text, max_tokens=6000, gaps=500):
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0

    last = 0
    i = 0
    while i < len(words):
        word = words[i]
        current_length += len(word) + 1 
        if current_length > max_tokens:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_length = 0
            i = last + gaps
            last = i
        else:
            current_chunk.append(word)
            i += 1

    chunks.append(' '.join(current_chunk))
    return chunks

def get_embeddings(client, text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

def find_relevant_document(client, query, document_embeddings, document_chunks):
    query_embedding = get_embeddings(client, query)
    similarities = cosine_similarity([query_embedding], document_embeddings)
    most_relevant_index = similarities.argmax()
    return document_chunks[most_relevant_index]

def generate_response(client, conversation_history, document_embeddings, document_chunks):
    relevant_document = find_relevant_document(client, conversation_history[-1]["content"], document_embeddings, document_chunks)

    messages=[
        {"role": "system", "content": f"Document: {relevant_document}"},
        {"role": "user", "content": conversation_history[-1]['content']}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return str(e)