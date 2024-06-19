import pickle

def load_instructions(file_path):
    with open(file_path, 'r') as file:
        return file.read()
    
def load_embeddings(file_path):
    with open(file_path, 'rb') as file:
        return pickle.load(file)