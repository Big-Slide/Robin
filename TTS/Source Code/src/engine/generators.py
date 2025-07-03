from loguru import logger
import edge_tts
import os
from typing import List, Dict
from config.config_handler import config
import torch
import soundfile as sf
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan

logger.info("Loading synthesizer...")
os.environ["NUMBA_CACHE_DIR"] = "/tmp/numba_cache"
from TTS.utils.synthesizer import Synthesizer
from kokoro import KPipeline


if os.environ.get("MODE", "dev") == "prod":
    models_dir = "/approot/models"
else:
    models_dir = "../../../Models"

models = {
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
    "female1-en": {"lang": "en", "type": "kokoro"},
    "male1-ar": {
        "model_dir": f"{models_dir}/MBZUAI/speecht5_tts_clartts_ar",
        "vocoder_dir": f"{models_dir}/microsoft/speecht5_hifigan",
        "lang": "ar",
        "type": "transformers",
        "speaker_embedding": torch.tensor([[-0.060953, 0.011393, 0.021317, 0.034482, -0.041738, -0.047594, -0.076155, 0.030272, 0.036947, 0.019681, -0.096886, -0.10144, 0.052221, 0.031387, 0.023239, 0.044667, 0.022445, 0.042147, 0.011137, 0.0068737, 0.036914, 0.018001, -0.015255, -0.063905, -0.054215, -0.0058751, -0.081165, 0.023229, 0.047986, 0.03899, -0.0033311, 0.042164, 0.037297, -0.0067525, 0.02166, -0.085262, 0.0317, 0.04245, 0.0017618, -0.058694, 0.040141, 0.020342, 0.042358, 0.037335, 0.0029816, -0.1161, -0.020504, 0.015386, -0.080145, 0.035499, 0.029252, 0.037858, 0.028225, 0.028238, -0.10738, -0.040188, 0.0081922, 0.01522, 0.038353, 0.014901, 0.0206, -0.0090125, -0.012125, 0.019219, 0.051554, 0.051783, 0.03371, -0.055953, -0.06614, -0.050663, 0.019378, 0.010127, 0.025047, 0.0092762, 0.063343, 0.043151, 0.0080534, 0.023047, -0.05806, -0.081426, -0.06319, -0.058764, -0.081307, -0.045667, -0.033335, -0.060165, -0.070624, 0.020454, 0.011427, -0.025894, 0.030859, -0.078426, 0.012313, -0.076215, 0.033594, -0.036764, 0.028681, 0.037867, -0.045463, -0.093065, 0.011355, -0.076891, -0.083498, 0.061721, 0.020459, 0.050605, 0.05034, 0.056154, 0.0107, 0.027665, -0.08587, 0.016364, 0.086115, 0.013601, 0.014244, 0.053044, -0.064748, 0.045687, -0.062912, 0.029984, 0.023844, -0.058679, 0.02338, 0.059065, -0.053872, 0.0039795, -0.07757, 0.024048, 0.047804, 0.032243, 0.048718, 0.022941, 0.016898, 0.03531, 0.02973, -0.067357, -0.068301, 0.018325, -0.054641, -0.0053395, 0.026019, 0.0039472, 0.0046661, 0.027077, -0.075463, -0.0019879, -0.017942, -0.0033377, 0.024551, -0.10593, 0.035829, -0.033172, -0.075471, 0.035059, -0.037617, 0.045408, 0.0062747, -0.056948, -0.099708, 0.021961, 0.046098, 0.0095151, 0.014834, 0.023781, 0.021634, 0.0057199, 0.025415, 0.043959, 0.035511, 0.047049, -0.019793, -0.072582, 0.025922, -0.044946, 0.0026978, 0.026134, -0.049715, 0.014787, 0.041698, -0.061493, 0.028508, -0.049958, 0.022493, 0.0015875, -0.069054, -0.01176, 0.04712, 0.030965, -0.069384, -0.067083, -0.012681, 0.042851, -0.065355, 0.044498, 0.025549, 0.026663, 0.021235, 0.040546, 0.035647, -0.0063575, 0.051012, 0.046262, -0.094101, 0.013949, 0.016531, 0.016108, 0.04689, 0.0044695, 0.021537, 0.026579, 0.0034872, -0.080498, -0.049073, 0.041845, -0.044627, 0.02857, 0.040985, -0.058557, 0.061979, 0.049644, -0.044761, 0.032579, -0.093305, -0.0242, -0.03988, 0.031115, 0.053844, 0.045628, 0.040595, 0.023324, 0.019325, 0.028053, 0.0090704, -0.01155, 0.036839, -0.027254, 0.032294, 0.027014, 0.0023589, 0.05046, -0.062414, 0.02079, -0.083619, 0.0086655, -0.05323, 0.020566, 0.046759, 0.018634, 0.012443, 0.023193, 0.028824, 0.011507, 0.0067171, -0.075471, -0.0044045, 0.02767, 0.025556, 0.034208, -0.054128, 0.052806, 0.034801, -0.09024, 0.025306, 0.037913, 0.00060479, 0.016681, 0.048816, 0.030664, 0.018899, -0.018023, 0.06485, -0.028146, -0.05376, 0.0025131, -0.074593, 0.04556, 0.040048, 0.030187, -0.083365, -0.053243, -0.018631, 0.047354, 0.023803, -0.091919, 0.01402, 0.042322, 0.024808, 0.052457, -0.10511, 0.0047798, 0.016413, 0.017174, 0.0037029, -0.01543, 0.020848, 0.032155, 0.017094, 0.01957, 0.029525, 0.048286, -0.045783, 0.028181, 0.022114, -0.083942, 0.024172, 0.062461, 0.030156, 0.018219, 0.026092, 0.042475, 0.041367, 0.012337, 0.012288, 0.033295, -0.072627, -0.070949, -0.022519, 0.016354, -0.045556, 0.050319, -0.043233, 0.043916, -0.05357, 0.010184, 0.053347, -0.090895, 0.054007, 0.072932, -0.054383, -0.082377, -0.074783, 0.011541, 0.017254, 0.053634, -0.064085, 0.040574, 0.024547, -0.039297, 0.0046599, 0.027823, 0.015105, -0.035607, 0.02473, 0.025918, -0.075153, 0.014867, 0.026748, 0.04089, -0.049498, -0.074685, -0.080423, 0.022272, -0.05143, 0.1315, 0.02361, -0.044485, -0.0051101, 0.031829, -0.045783, -0.039129, -0.098745, 0.011365, 0.025807, 0.033528, 0.033617, -0.042267, -0.04242, 0.045201, 0.027885, 0.055616, 0.0043782, 0.025951, -0.060031, 0.023383, -0.014222, -0.0022961, 0.02946, 0.021252, 0.057002, 0.025116, -0.063082, -0.10453, 0.037316, -0.0019759, 0.054568, 0.0091359, 0.021566, -0.078754, 0.036626, 0.049466, 0.033124, 0.0014198, -0.048457, 0.043503, 0.042824, 0.013626, 0.001734, -0.0808, 0.023578, 0.037011, -0.030384, -0.04637, 0.065932, 0.050391, 0.02032, 0.010928, 0.0017605, -0.064198, -0.053785, -0.050661, 0.021888, 0.024806, 0.0092742, -0.013214, 0.051849, -0.058198, -0.025241, -0.08427, -0.11335, -0.066253, -0.05115, 0.020138, 0.043081, 0.0077078, -0.061379, 0.020171, 0.035282, 0.050911, 0.010767, -0.057514, -0.039988, -0.012018, -0.022638, 0.025245, 0.011085, 0.0021424, 0.035175, 0.020605, 0.0088105, -0.061632, 0.016829, 0.025681, 0.027587, -0.0016571, -0.044312, 0.038529, 0.028854, 0.0076286, 0.011122, -0.0037352, 0.033357, 0.032568, 0.026509, 0.014394, 0.0091987, 0.020114, 0.050142, -0.067922, -0.062906, 0.032516, -0.010765, -0.007347, 0.033498, 0.020313, -0.069176, 0.042928, 0.032016, 0.0058412, 0.028358, 0.0095166, -0.0028116, 0.018711, 0.029872, 0.0050382, 0.0057486, -0.090134, -3.3951e-05, -0.0053928, 0.030402, 0.043504, -0.058045, -0.04669, 0.022087, 0.0097785, 0.044239, 0.054929, -0.068051, 0.021117, -0.018138, -0.01201, -0.064778, 0.0059865, -0.031096, 0.019363, -0.040012, 0.032286, -0.041819, -0.018622, -0.071067, -0.050765, 0.0083951, 0.03234, -0.060739, 0.040116, 0.022749, -0.015233, -0.0048315, 0.051734, 0.036158, -0.011246, 0.031979, -0.063811]]),
    },
}


class TTSGenerator:
    def __init__(self):
        self.load_models(config.MODEL_IDs.split(","))
        self._default_model_ids = {
            "fa": "male1-online-fa",
            "en": "female1-en",
            "ar": "male1-ar",
        }

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
                        model_id=model_id,
                        config_path=config_path,
                        model_path=model_path,
                    )
            elif models[model_id]["type"] == "kokoro":
                self._synthesizers[model_id] = KPipeline(lang_code="a")
                self._synthesizers[model_id].load_voice("af_heart")
                self._kokoro_voice_tensor = torch.load(
                    f"{models_dir}/kokoro/voices/af_heart.pt", weights_only=True
                )
                logger.info("Model loaded", model_id=model_id)
            elif models[model_id]["type"] == "transformers":
                # https://huggingface.co/MBZUAI/speecht5_tts_clartts_ar
                self._synthesizers[model_id] = {}
                self._synthesizers[model_id]["speaker_embedding"] = models[model_id][
                    "speaker_embedding"
                ]
                self._synthesizers[model_id]["processor"] = (
                    SpeechT5Processor.from_pretrained(models[model_id]["model_dir"])
                )
                self._synthesizers[model_id]["model"] = (
                    SpeechT5ForTextToSpeech.from_pretrained(
                        models[model_id]["model_dir"]
                    )
                )
                self._synthesizers[model_id]["vocoder"] = (
                    SpeechT5HifiGan.from_pretrained(models[model_id]["vocoder_dir"])
                )
                logger.info("Model loaded", model_id=model_id)

    async def do_tts(
        self, text: str, tmp_path: str, model_id: str = None, lang: str = "fa"
    ):
        if lang is None:
            lang = "fa"
        if model_id is None:
            model_id = self._default_model_ids[lang]
        if model_id == "male1-online-fa":
            try:
                voice = "fa-IR-FaridNeural"
                communicate = edge_tts.Communicate(text, voice)
                communicate.save_sync(tmp_path)
                return
            except Exception:
                logger.opt(exception=True).warning(
                    "male1-online-fa not worked: using female1-fa instead"
                )
                model_id = "female1-fa"
            # return FileResponse(path=tmp_path, media_type="audio/wav")
        if model_id in ["female1-fa", "male1-fa"]:
            wavs = self._synthesizers[model_id].tts(text)
            self._synthesizers[model_id].save_wav(wavs, tmp_path)
            # return FileResponse(path=tmp_path, media_type="audio/wav")
        elif model_id == "female1-en":
            generator = self._synthesizers[model_id](
                text, voice=self._kokoro_voice_tensor, speed=1, split_pattern=None
            )
            gs, ps, audio = next(generator)
            logger.debug("TTS output", graphemes=gs, phonemes=ps)
            sf.write(tmp_path, audio, 24000)  # save each audio file
        elif model_id == "male1-ar":
            inputs = self._synthesizers[model_id]["processor"](
                text=text, return_tensors="pt"
            )
            speech = self._synthesizers[model_id]["model"].generate_speech(
                inputs["input_ids"],
                self._synthesizers[model_id]["speaker_embedding"],
                vocoder=self._synthesizers[model_id]["vocoder"],
            )
            sf.write(tmp_path, speech.numpy(), samplerate=16000)
        else:
            raise ValueError(f"Model {model_id} not found")
            # return JSONResponse(
            #     status_code=status_code.HTTP_412_PRECONDITION_FAILED,
            #     content={"details": "Model not found"},
            # )
