from loguru import logger
from transformers import (
    Wav2Vec2ForCTC,
    Wav2Vec2Processor,
    WhisperProcessor,
    WhisperForConditionalGeneration,
)
import torch
import librosa
import os
from typing import Dict
from config.config_handler import config
import numpy as np
from speechbrain.inference.ASR import WhisperASR

if os.environ.get("MODE", "dev") == "prod":
    models_dir = "/approot/models"
else:
    models_dir = "../../../Models"

models = {
    "SLPL/Sharif-wav2vec2": {
        "model_path": f"{models_dir}/SLPL/Sharif-wav2vec2",
        "lang": "fa",
        "type": "wav2vec2",
    },
    "facebook/wav2vec2-base-960h": {
        "model_path": f"{models_dir}/facebook/wav2vec2-base-960h",
        "lang": "en",
        "type": "wav2vec2",
    },
    "jonatasgrosman/wav2vec2-large-xlsr-53-english": {
        "model_path": f"{models_dir}/jonatasgrosman/wav2vec2-large-xlsr-53-english",
        "lang": "en",
        "type": "wav2vec2",
    },
    "facebook/wav2vec2-large-robust-ft-libri-960h": {
        "model_path": f"{models_dir}/facebook/wav2vec2-large-robust-ft-libri-960h",
        "lang": "en",
        "type": "wav2vec2",
    },
    "jonatasgrosman/wav2vec2-large-xlsr-53-arabic": {
        "model_path": f"{models_dir}/jonatasgrosman/wav2vec2-large-xlsr-53-arabic",
        "lang": "ar",
        "type": "wav2vec2",
    },
    "speechbrain/asr-whisper-medium-commonvoice-ar": {
        "model_path": f"{models_dir}/speechbrain/asr-whisper-medium-commonvoice-ar",
        "lang": "ar",
        "type": "speechbrain_whisper",
    },
}


class ASRGenerator:
    def __init__(self):
        model_ids = config.MODEL_IDs
        # Check if GPU is available and set device
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Device: {self._device}")
        self._processor = {}
        self._model = {}
        self._model_type = {}
        for model_id in model_ids.split(","):
            self._load_model(model_id)

    def _load_model(self, model_id: str) -> Dict:
        # Load model and processor
        model_path = models[model_id]["model_path"]
        model_lang = models[model_id]["lang"]
        model_type = models[model_id]["type"]
        self._model_type[model_lang] = model_type
        if os.path.exists(model_path):
            logger.info("Loading model...", model_id=model_id)
            if model_type == "wav2vec2":
                self._processor[model_lang] = Wav2Vec2Processor.from_pretrained(
                    model_path
                )
                self._model[model_lang] = Wav2Vec2ForCTC.from_pretrained(model_path).to(
                    self._device
                )
                self._model[model_lang].eval()  # Set model to evaluation mode
            elif model_type == "whisper":
                self._processor[model_lang] = WhisperProcessor.from_pretrained(
                    model_path
                )
                self._model[model_lang] = (
                    WhisperForConditionalGeneration.from_pretrained(model_path).to(
                        self._device
                    )
                )
                self._model[model_lang].eval()  # Set model to evaluation mode
            elif model_type == "speechbrain_whisper":
                self._model[model_lang] = WhisperASR.from_hparams(
                    source=model_path, run_opts={"device": self._device}
                )
                self._model[model_lang].eval()
            logger.info("Model loaded", model_id=model_id, model_path=model_path)
        else:
            logger.warning(
                "Model not found",
                model_path=model_path,
            )

    async def do_asr(self, input_path: str, lang: str):
        if self._model_type[lang] == "wav2vec2":
            audio, sr = librosa.load(input_path, sr=16000)
            input_values = self._processor[lang](
                audio, sampling_rate=sr, return_tensors="pt", padding=True
            ).input_values.to(self._device)
            with torch.no_grad():
                logits = self._model[lang](input_values).logits
            predicted_ids = torch.argmax(logits, dim=-1)
            transcription = self._processor[lang].batch_decode(predicted_ids)[0]
        elif self._model_type[lang] == "whisper":
            audio, sr = librosa.load(input_path, sr=16000)
            audio = np.array(audio).astype(np.float32)
            # Process with Whisper processor
            input_features = self._processor[lang](
                audio, sampling_rate=16000, return_tensors="pt"
            ).input_features
            input_features = input_features.to(self._device)
            # Generate token ids
            predicted_ids = self._model[lang].generate(input_features)
            # Decode token ids to text
            transcription = self._processor[lang].batch_decode(
                predicted_ids, skip_special_tokens=True
            )[0]
        elif self._model_type[lang] == "speechbrain_whisper":
            transcription = self._model[lang].transcribe_file(input_path)
        logger.debug(f"{transcription=}")
        return transcription
