from loguru import logger
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
import torch
import librosa
import os
from typing import Dict

# os.environ["NUMBA_CACHE_DIR"] = "/tmp/numba_cache"


if os.environ.get("MODE", "dev") == "prod":
    models_dir = "/approot/models"
else:
    models_dir = "../../Models"

models = {"1": {"model_path": f"{models_dir}/SLPL/Sharif-wav2vec2"}}


class ASRGenerator:
    def __init__(self):
        model_id = "1"
        # Check if GPU is available and set device
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Device: {self._device}")
        self._load_model(model_id)

    def _load_model(self, model_id: str = "1") -> Dict:
        # Load model and processor
        model_path = models[model_id]["model_path"]
        if os.path.exists(model_path):
            logger.info("Loading model...", model_id=model_id)
            self._processor = Wav2Vec2Processor.from_pretrained(model_path)
            self._model = Wav2Vec2ForCTC.from_pretrained(model_path).to(self._device)
            self._model.eval()  # Set model to evaluation mode
            logger.info("Model loaded", model_id=model_id, model_path=model_path)
        else:
            logger.warning(
                "Model not found",
                model_path=model_path,
            )

    async def do_asr(self, input_path: str):
        # Load audio file
        audio, sr = librosa.load(input_path, sr=16000)
        input_values = self._processor(
            audio, sampling_rate=sr, return_tensors="pt", padding=True
        ).input_values.to(self._device)
        with torch.no_grad():
            logits = self._model(input_values).logits
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = self._processor.batch_decode(predicted_ids)[0]
        return transcription
