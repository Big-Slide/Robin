from loguru import logger
import edge_tts
import os
from typing import List, Dict
from config.config_handler import config
import torch
import soundfile as sf

logger.info("Loading synthesizer...")
os.environ["NUMBA_CACHE_DIR"] = "/tmp/numba_cache"
from TTS.utils.synthesizer import Synthesizer
from kokoro import KPipeline


if os.environ.get("MODE", "dev") == "prod":
    models_dir = "/approot/models"
else:
    models_dir = "../../../Models"

models = {
    "1": {  # ~Bad
        "model_path": f"{models_dir}/karim23657/persian-tts-female-GPTInformal-Persian-vits/best_model_98066.pth",
        "config_path": f"{models_dir}/karim23657/persian-tts-female-GPTInformal-Persian-vits/config.json",
        "lang": "fa",
        "type": "TTS",
    },
    "2": {  # Afghanistan
        "model_path": f"{models_dir}/Kamtera/persian-tts-female-glow_tts/best_model.pth",
        "config_path": f"{models_dir}/Kamtera/persian-tts-female-glow_tts/config.json",
        "lang": "fa",
        "type": "TTS",
    },
    "3": {  # Afghanistan
        "model_path": f"{models_dir}/Kamtera/persian-tts-female-vits/best_model_30824.pth",
        "config_path": f"{models_dir}/Kamtera/persian-tts-female-vits/config.json",
        "lang": "fa",
        "type": "TTS",
    },
    "female1-fa": {  # Good
        "model_path": f"{models_dir}/Kamtera/persian-tts-female1-vits/best_model_97741.pth",
        "config_path": f"{models_dir}/Kamtera/persian-tts-female1-vits/config.json",
        "lang": "fa",
        "type": "TTS",
    },
    "male1-fa": {  # Mid
        "model_path": f"{models_dir}/Kamtera/persian-tts-male1-vits/best_model_199921.pth",
        "config_path": f"{models_dir}/Kamtera/persian-tts-male1-vits/config.json",
        "lang": "fa",
        "type": "TTS",
    },
    "6": {  # Bad
        "model_path": f"{models_dir}/Kamtera/persian-tts-female-tacotron2/best_model_305416.pth",
        "config_path": f"{models_dir}/Kamtera/persian-tts-female-tacotron2/config.json",
        "lang": "fa",
        "type": "TTS",
    },
    "female1-en": {"type": "kokoro"},
}


class TTSGenerator:
    def __init__(self):
        self.load_models(config.MODEL_IDs.split(","))
        self._default_model_ids = {"fa": "male1-online-fa", "en": "female1-en"}

    def delete_file_after_response(self, file_path: str):
        if os.path.exists(file_path):
            os.remove(file_path)

    # async def get_temp_file(self, background_tasks: BackgroundTasks):
    #     tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    #     try:
    #         yield tmp.name
    #     finally:
    #         background_tasks.add_task(self.delete_file_after_response, tmp.name)

    def load_models(self, model_ids: List[str]) -> Dict:
        logger.info(f"Loading {len(model_ids)} model(s)")
        self._synthesizers = {}
        for model_id in model_ids:
            if models[model_id]["type"] == "TTS":
                config_path = models[model_id]["config_path"]
                model_path = models[model_id]["model_path"]
                if os.path.exists(config_path) and os.path.exists(model_path):
                    logger.info("Loading model...", model_id=model_id)
                    self._synthesizers[model_id] = Synthesizer(model_path, config_path)
                    logger.info(
                        "Model loaded", model_id=model_id, model_path=model_path
                    )
                else:
                    logger.warning(
                        "Config or model not found",
                        config_path=config_path,
                        model_path=model_path,
                    )
            elif models[model_id]["type"] == "kokoro":
                a = KPipeline(lang_code="a")
                a()
                self._synthesizers[model_id] = KPipeline(lang_code="a")
                self._synthesizers[model_id].load_voice("af_heart")
                self._kokoro_voice_tensor = torch.load(
                    f"{models_dir}/kokoro/voices/af_heart.pt", weights_only=True
                )

    async def do_tts(
        self, text: str, tmp_path: str, model: str = None, lang: str = "fa"
    ):
        if lang is None:
            lang = "fa"
        if model is None:
            model = self._default_model_ids[lang]
        if model == "male1-online-fa":
            voice = "fa-IR-FaridNeural"
            communicate = edge_tts.Communicate(text, voice)
            communicate.save_sync(tmp_path)
            # return FileResponse(path=tmp_path, media_type="audio/wav")
        elif model in ["female1-fa", "male1-fa"]:
            wavs = self._synthesizers[model].tts(text)
            self._synthesizers[model].save_wav(wavs, tmp_path)
            # return FileResponse(path=tmp_path, media_type="audio/wav")
        elif model == "female1-en":
            generator = self._synthesizers[model](
                text, voice=self._kokoro_voice_tensor, speed=1, split_pattern=None
            )
            gs, ps, audio = generator[0]
            logger.debug("TTS output", graphemes=gs, phonemes=ps)
            sf.write(tmp_path, audio, 24000)  # save each audio file
        else:
            raise AssertionError("Model not found")
            # return JSONResponse(
            #     status_code=status_code.HTTP_412_PRECONDITION_FAILED,
            #     content={"details": "Model not found"},
            # )
