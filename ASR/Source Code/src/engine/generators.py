from loguru import logger
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
import torch
import librosa
import os
from typing import Dict


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
        logger.debug(f"Loading {input_path}")
        audio, sr = librosa.load(input_path, sr=16000)
        logger.debug(f"{input_path} loaded")
        input_values = self._processor(
            audio, sampling_rate=sr, return_tensors="pt", padding=True
        ).input_values.to(self._device)
        logger.debug("Input values ready")
        with torch.no_grad():
            logits = self._model(input_values).logits
        logger.debug("Logits ready")
        predicted_ids = torch.argmax(logits, dim=-1)
        logger.debug("predictions ready")
        transcription = self._processor.batch_decode(predicted_ids)[0]
        logger.debug(f"{transcription=}")
        return transcription
