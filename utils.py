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

def load_instructions(name):
    try:
        with open(name, 'r') as file:
            return file.read()
    except Exception as e:
        print(e)

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

def question_parts(client, conversation_history):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[conversation_history[0], conversation_history[-1]],
            temperature=0.05
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return str(e)

def find_matching_program(client, document_embeddings, document_chunks, interests):
    matching_program_doc = find_relevant_document(client, interests, document_embeddings, document_chunks)

    result = {
        "interests": interests,
        "response": f"The document of the matching program: {matching_program_doc}"
    }
    return json.dumps(result)

def generate_response(client, tools, conversation_history, document_embeddings, document_chunks, prompt_parts_dict):
    non_suggestion_relevant_documents = [find_relevant_document(client, prompt_part, document_embeddings, document_chunks) for prompt_part in prompt_parts_dict["non-suggestions"]]

    messages = conversation_history[:-1]

    try:
        user_prompt = ""

        if len(prompt_parts_dict["suggestion-based"]) > 0:
            messages.append({"role": "user", "content": prompt_parts_dict["suggestion-based"][0]})

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.1
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            if tool_calls:
                messages.append(response_message)

                available_functions = {
                    "find_matching_program": find_matching_program,
                }

                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_to_call = available_functions[function_name]
                    function_args = json.loads(tool_call.function.arguments)

                    function_response = function_to_call(
                        client,
                        document_embeddings,
                        document_chunks,
                        interests=function_args.get("interests"),
                    )

                    messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response,
                        }
                    )

                    matched_program_document = find_relevant_document(client, function_response, document_embeddings, document_chunks)
                
                    messages.append({"role": "system", "content": f"For the program suggestion part of your response, just use the information provided in the following document: {matched_program_document}"})
                    user_prompt += prompt_parts_dict["suggestion-based"][0]
                    # messages.append({"role": "system", "content": "About the suggestion part, do not forget to suggest based on the document I sent you above."})
        
        if len(prompt_parts_dict["non-suggestions"]) > 0:
            for relevant_document in non_suggestion_relevant_documents:
                    messages.append({"role": "system", "content": f"Document: {relevant_document}"})

            messages.append({"role": "system", "content": "If the user asks several questions or suggestions, make sure to answer all of them using the information I sent you above the questions and statements."})
            
            non_suggestions = ' '.join(prompt_parts_dict["non-suggestions"])
            user_prompt = non_suggestions + " " + user_prompt

        messages.append({"role": "system", "content": "Make sure to answer all of the user questions and statements. Do not ignore any of the questions. Answer in JSON format."})
        messages.append({"role": "user", "content": f"Please provide a response in JSON format. Prompt: {user_prompt}"})

        second_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.1,
        )

        return second_response

    except Exception as e:
        print(f"{str(e)}")
        return str(e)
    
def change_page(new_page):
    st.session_state.selected_option = new_page
    st.experimental_rerun()