import pyaudio
import wave
from pydub import AudioSegment
from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
import torch
import torchaudio

# Constants
FS = 44100  # Sample rate
SECONDS = 20  # Duration of recording

# Load the processor and model
processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h")

def record_audio(file_path="output.wav", duration=SECONDS, fs=FS):
    p = pyaudio.PyAudio()

    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=fs,
                    input=True,
                    frames_per_buffer=1024)

    frames = []

    for _ in range(0, int(fs / 1024 * duration)):
        data = stream.read(1024)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(file_path, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(fs)
    wf.writeframes(b''.join(frames))
    wf.close()

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