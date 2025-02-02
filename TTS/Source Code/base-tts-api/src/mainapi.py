from fastapi import FastAPI
import uvicorn
import time
from functools import wraps
from generators import TTSGenerator
from fastapi import Depends


app = FastAPI()
tts_generator = TTSGenerator()


def timer(argument=None):
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


@app.get("/text-to-speech/")
@timer()
async def text_to_speech(
    text: str, model: str = None, tmp_file=Depends(tts_generator.get_temp_file)
):
    response = await tts_generator.do_tts(text=text, model=model, tmp_file=tmp_file)
    return response


if __name__ == "__main__":
    uvicorn.run(app="mainapi:app", host="0.0.0.0", port=8002, reload=False)
