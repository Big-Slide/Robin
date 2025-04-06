from fastapi import FastAPI, UploadFile
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
import torch
import librosa
import uvicorn
import time
from functools import wraps
import os

# facebook/wav2vec2-large-xlsr-53
# openai/whisper-large-v3-turbo
# openai/whisper-tiny
# m3hrdadfi/wav2vec2-large-xlsr-persian-v3
# SLPL/Sharif-wav2vec2
model_path = '../Models/SLPL/Sharif-wav2vec2'

app = FastAPI()

# Check if GPU is available and set device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f'Device: {device}')

# Load model and processor
processor = Wav2Vec2Processor.from_pretrained(model_path)
model = Wav2Vec2ForCTC.from_pretrained(model_path).to(device)
model.eval()  # Set model to evaluation mode

def timer(argument = None):
    def decorator(function):
        @wraps(function)
        async def wrapper(*args, **kwargs):
            # something_with_argument(argument)
            time_start = time.perf_counter()
            retval = await function(*args, **kwargs)
            print(f"Execution time: {round(time.perf_counter() - time_start, 3)} sec")
            return retval
        return wrapper
    return decorator

@app.post("/transcribe/")
@timer()
async def transcribe(audio_file: UploadFile):
    # Save uploaded file
    audio_path = f"temp_{audio_file.filename}"
    with open(audio_path, "wb") as f:
        f.write(await audio_file.read())

    # Load audio file
    audio, sr = librosa.load(audio_path, sr=16000)
    input_values = processor(audio, sampling_rate=sr, return_tensors="pt", padding=True).input_values.to(device)

    # Perform transcription
    with torch.no_grad():
        logits = model(input_values).logits
    predicted_ids = torch.argmax(logits, dim=-1)
    transcription = processor.batch_decode(predicted_ids)[0]

    if os.path.exists(audio_path):
        os.remove(audio_path)

    print(transcription)
    return {"transcription": transcription}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)