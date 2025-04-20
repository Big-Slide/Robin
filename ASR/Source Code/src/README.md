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

## Dev
```
cd src
docker run --rm -p 5672:5672 -e RABBITMQ_CONFIG_FILE=/etc/rabbitmq/rabbitmq.conf -v "/$(pwd)/src/rabbitmq/config/rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf" rabbitmq:4.0.6-management

cd src/engine
python3.10 main.py

cd src/backend
python3.10 mainapi.py
```