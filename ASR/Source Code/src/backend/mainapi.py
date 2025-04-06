import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, UploadFile
from sqlalchemy.orm import Session
import aio_pika
import uuid
import json
import asyncio
from core.messages import Message
from datetime import datetime
from loguru import logger
import os
from version import __version__
from config.config_handler import config
from core.queue_utils import consume_results, get_rabbitmq_connection
from dbutils import crud
import sys
from starlette.middleware.cors import CORSMiddleware
from core import base
from dbutils.database import SessionLocal


if os.environ.get("MODE", "dev") == "prod":
    log_dir = "/approot/data"
else:
    log_dir = "../Outputs/result"
os.makedirs(log_dir, exist_ok=True)

logger.remove()
logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message} | {extra}",
    level=config["CONSOLE_LOG_LEVEL"],
    backtrace=True,
    diagnose=True,
    colorize=True,
    serialize=False,
    enqueue=True,
)
logger.add(
    f"{log_dir}/backend.log",
    rotation="50MB",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message} | {extra}",
    level=config["FILE_LOG_LEVEL"],
    backtrace=True,
    diagnose=False,
    colorize=True,
    serialize=False,
    enqueue=True,
)

logger.info("Starting service", version=__version__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan to start the result consumer."""
    try:
        connection = await aio_pika.connect_robust(config["QUEUE_CONNECTION"])
        db = SessionLocal()
        asyncio.create_task(consume_results(connection, db))
        yield
    finally:
        db.close()
        await connection.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
base_mdl = base.Base()


@app.post("/aihive-sptotxt/api/v1/speech-to-text-offline")
async def generate_sound(
    audio_file: UploadFile,
    request_id: str = None,
    priority: int = 1,
    connection: aio_pika.RobustConnection = Depends(get_rabbitmq_connection),
    db: Session = Depends(base.get_db),
):
    logger.info("/asr/speech-to-text-offline")
    if request_id is None:
        request_id = str(uuid.uuid4())

    # Save uploaded file
    audio_path = f"temp_{audio_file.filename}"
    with open(audio_path, "wb") as f:
        f.write(await audio_file.read())

    response = crud.add_request(
        db=db,
        request_id=request_id,
        input_path=audio_path,
        itime=datetime.now(tz=None),
    )
    if not response["status"]:
        return response

    channel = await connection.channel()

    # Prepare message with text, model, and request_id
    # TODO: change input_path to binary data
    message_body = {
        "input_path": audio_path,
        "request_id": request_id,
    }

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message_body).encode(),
            headers={"request_id": request_id},
        ),
        routing_key="task_queue",
    )
    await channel.close()

    msg = Message("fa").INF_SUCCESS()
    msg["data"] = {"request_id": request_id}
    return msg


@app.get("/aihive-sptotxt/api/v1/status/{request_id}")
async def get_status(request_id: str, db: Session = Depends(base.get_db)):
    logger.info("/asr/status", request_id=request_id)
    task = crud.get_request(db=db, request_id=request_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    msg = Message("fa").INF_SUCCESS()
    msg["data"] = task
    return msg


if __name__ == "__main__":
    uvicorn.run(app="mainapi:app", host="0.0.0.0", port=8001, reload=False)
