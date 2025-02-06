# Text To Speech
## Requirements
```
apt install espeak-ng
```

Download models from [this link](https://drive.google.com/drive/folders/1PoeQZwbaQeyuzr-qU0fspJx4PfWBlAAs?usp=sharing) to `Models` folder.


## How to run
### DEV
First config virtual environment (.venv)

Run this command:
```
python main.py
```

Test `/text-to-speech` api in swagger: `http://localhost:8002/docs`

### PROD
- Copy `.env` from `template` to root directory where docker-compose.yml is.

- `docker-compose up -d`

- Test `/text-to-speech` api in swagger: `http://localhost:8002/docs`

## Model Parameter in API
- male1-online
- male1
- female1

## Add new model
Download your model to `Models` folder.

Add new models to `models` dict in `generators.py` and update `do_tts` method.

