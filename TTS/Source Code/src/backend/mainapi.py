import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
import aio_pika
import uuid
import json
from typing import Dict
import asyncio
from messages import Message
from datetime import datetime
from fastapi.responses import FileResponse
from loguru import logger
import os
from version import __version__
from config.config_handler import config
from core.utils import consume_results, get_rabbitmq_connection
from dbutils import schemas

if os.environ.get("MODE", "dev") == "prod":
    log_dir = "/approot/data"
else:
    log_dir = "../Outputs/result"
os.makedirs(log_dir, exist_ok=True)

logger.add(
    f"{log_dir}/backend.log",
    rotation="50MB",
    format="{time} | {level} | {message} | {extra}",
    level="INFO",
    backtrace=True,
    colorize=True,
    serialize=False,
)

logger.info("Starting service", version=__version__)


tasks: Dict[str, schemas.TaskStatus] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan to start the result consumer."""
    connection = await aio_pika.connect_robust(config["QUEUE_CONNECTION"])
    asyncio.create_task(consume_results(connection, tasks))
    yield
    await connection.close()


app = FastAPI(lifespan=lifespan)


@app.post("/aihive-txttosp/api/v1/text-to-speech-offline")
async def generate_sound(
    request: schemas.GenerateRequest,
    connection: aio_pika.RobustConnection = Depends(get_rabbitmq_connection),
):
    logger.info("/tts/text-to-speech-offline", request=request)
    request_id = request.request_id
    if request_id is None:
        request_id = str(uuid.uuid4())
    tasks[request_id] = schemas.TaskStatus(
        request_id=request_id, status="pending", itime=datetime.now()
    )

    channel = await connection.channel()

    # Prepare message with text, model, and request_id
    message_body = {
        "text": request.text,
        "model": request.model,
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


@app.get("/aihive-txttosp/api/v1/status/{request_id}")
async def get_status(request_id: str):
    logger.info("/tts/status", request_id=request_id)
    task = tasks.get(request_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    msg = Message("fa").INF_SUCCESS()
    msg["data"] = task
    return msg


@app.get("/aihive-txttosp/api/v1/file/{request_id}")
async def get_file(request_id: str):
    logger.info("/tts/file", request_id=request_id)
    task = tasks.get(request_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status == "completed" and task.result_path is not None:
        return FileResponse(path=task.result_path, media_type="audio/wav")
    else:
        raise HTTPException(status_code=404, detail="Task pending or failed")


if __name__ == "__main__":
    uvicorn.run(app="mainapi:app", host="0.0.0.0", port=8001, reload=False)
