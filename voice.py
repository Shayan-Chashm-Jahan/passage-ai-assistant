import streamlit as st
import sounddevice as sd
from scipy.io.wavfile import write
import torchaudio
from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
import torch


# Constants
FS = 44100  # Sample rate
SECONDS = 5  # Duration of recording

# Streamlit layout
st.title("Voice Recorder")
st.write("Click the button to start recording.")

# Load the processor and model
processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h")

def record_audio(duration=SECONDS, fs=FS):
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()  # Wait until recording is finished
    write('output.wav', fs, recording)  # Save as WAV file

def load_and_process_audio(file_path):
    # Load audio file
    speech_array, sampling_rate = torchaudio.load(file_path)

    # Resample if necessary
    if sampling_rate != 16000:
        resampler = torchaudio.transforms.Resample(sampling_rate, 16000)
        speech_array = resampler(speech_array)

    # Process audio to get input values
    input_values = processor(speech_array.squeeze().numpy(), return_tensors="pt", sampling_rate=16000).input_values
    return input_values

def transcribe_audio(input_values):
    # Perform inference
    with torch.no_grad():
        logits = model(input_values).logits

    # Get the predicted IDs
    predicted_ids = torch.argmax(logits, dim=-1)

    # Decode the IDs to text
    transcription = processor.decode(predicted_ids[0])
    return transcription


if st.button('Start Recording'):
    with st.spinner(f'Recording for {SECONDS} seconds...'):
        record_audio()
    st.success('Recording finished!')
    
    audio_file_path = "output.wav"

    # Load and process audio
    input_values = load_and_process_audio(audio_file_path)

    # Transcribe audio
    transcription = transcribe_audio(input_values)

    # Print the transcription
    print("Transcription:", transcription)

    st.text_area("Transcript", value=transcription, height=200)