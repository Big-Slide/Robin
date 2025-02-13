import edge_tts
import os
from typing import List, Dict
# import tempfile
# from fastapi.responses import FileResponse, JSONResponse
# from fastapi import BackgroundTasks
# from starlette import status as status_code

os.environ["NUMBA_CACHE_DIR"] = "/tmp/numba_cache"
from TTS.utils.synthesizer import Synthesizer


if os.environ.get("MODE", "dev") == "prod":
    models_dir = "/approot/models"
else:
    models_dir = "../../Models"

models = {
    "1": {  # ~Bad
        "model_path": f"{models_dir}/karim23657/persian-tts-female-GPTInformal-Persian-vits/best_model_98066.pth",
        "config_path": f"{models_dir}/karim23657/persian-tts-female-GPTInformal-Persian-vits/config.json",
    },
    "2": {  # Afghanistan
        "model_path": f"{models_dir}/Kamtera/persian-tts-female-glow_tts/best_model.pth",
        "config_path": f"{models_dir}/Kamtera/persian-tts-female-glow_tts/config.json",
    },
    "3": {  # Afghanistan
        "model_path": f"{models_dir}/Kamtera/persian-tts-female-vits/best_model_30824.pth",
        "config_path": f"{models_dir}/Kamtera/persian-tts-female-vits/config.json",
    },
    "female1": {  # Good
        "model_path": f"{models_dir}/Kamtera/persian-tts-female1-vits/best_model_97741.pth",
        "config_path": f"{models_dir}/Kamtera/persian-tts-female1-vits/config.json",
    },
    "male1": {  # Mid
        "model_path": f"{models_dir}/Kamtera/persian-tts-male1-vits/best_model_199921.pth",
        "config_path": f"{models_dir}/Kamtera/persian-tts-male1-vits/config.json",
    },
    "6": {  # Bad
        "model_path": f"{models_dir}/Kamtera/persian-tts-female-tacotron2/best_model_305416.pth",
        "config_path": f"{models_dir}/Kamtera/persian-tts-female-tacotron2/config.json",
    },
}


class TTSGenerator:
    def __init__(self):
        self.synthesizers = self.load_models(["female1", "male1"])

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
        synthesizers = {}
        for model_id in model_ids:
            config_path = models[model_id]["config_path"]
            model_path = models[model_id]["model_path"]
            if os.path.exists(config_path) and os.path.exists(model_path):
                print(f"Loading model ({model_id}) ...")
                synthesizers[model_id] = Synthesizer(model_path, config_path)
                print(f"Model {model_id} loaded from {model_path}")
            else:
                print(
                    f"Warning: config or model not found. {config_path=}, {model_path=}"
                )
        return synthesizers

    async def do_tts(self, text: str, tmp_path: str, model: str = None):
        if model is None:
            model = "male1-online"
        if model == "male1-online":
            voice = "fa-IR-FaridNeural"
            communicate = edge_tts.Communicate(text, voice)
            communicate.save_sync(tmp_path)
            # return FileResponse(path=tmp_path, media_type="audio/wav")
        elif model == "female1":
            wavs = self.synthesizers["female1"].tts(text)
            self.synthesizers["female1"].save_wav(wavs, tmp_path)
            # return FileResponse(path=tmp_path, media_type="audio/wav")
        elif model == "male1":
            wavs = self.synthesizers["male1"].tts(text)
            self.synthesizers["male1"].save_wav(wavs, tmp_path)
            # return FileResponse(path=tmp_path, media_type="audio/wav")
        else:
            raise AssertionError("Model not found")
            # return JSONResponse(
            #     status_code=status_code.HTTP_412_PRECONDITION_FAILED,
            #     content={"details": "Model not found"},
            # )
