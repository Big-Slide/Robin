# robin-base-asr-api
Automatic Speech Recognition

## How to run
First config virtual environment (.venv).

Run this command:
```
python main.py
```
Test `/transcribe` api in swagger: `http://localhost:8001/docs`

## How to use new model
Download your model to `model` folder.

Example:
```
git lfs install
git clone https://huggingface.co/SLPL/Sharif-wav2vec2
```

Then change model path in `main.py`



### requirements
pip install torch==2.5.1+cu124 --index-url https://download.pytorch.org/whl/cu124