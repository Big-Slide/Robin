import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from sqlalchemy.orm import Session
import aio_pika
import uuid
import json
import asyncio
import base64
from core.messages import Message
from datetime import datetime
from loguru import logger
import os
from version import __version__
from config.config_handler import config
from core.queue_utils import consume_results, get_rabbitmq_connection
from dbutils import schemas, crud
import sys
from starlette.middleware.cors import CORSMiddleware
from core import base
from dbutils.database import SessionLocal
from typing import Optional

if os.environ.get("MODE", "dev") == "prod":
    log_dir = "/approot/data"
else:
    log_dir = "../../../../Outputs/GENERALOCR/result"
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
    colorize=False,
    serialize=False,
    enqueue=True,
)

logger.info("Starting OCR Service with Skew Correction", version=__version__)


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


app = FastAPI(
    title="OCR Service API",
    description="API for OCR processing with skew correction",
    version=__version__,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base_mdl = base.Base()


@app.post("/aihive-ocr/api/v1/image-to-txt-offline")
async def process_image(
        image: UploadFile = File(..., description="Image file to process for OCR"),
        request_id: Optional[str] = Form(None, description="Optional request ID"),
        priority: int = Form(1, description="Processing priority (1-10)"),
        connection: aio_pika.RobustConnection = Depends(get_rabbitmq_connection),
        db: Session = Depends(base.get_db),
):
    """
    Process an image for OCR text extraction with skew correction.

    - **image**: Upload an image file (JPEG, PNG, etc.)
    - **request_id**: Optional custom request ID (will be generated if not provided)
    - **priority**: Processing priority from 1-10 (higher number = higher priority)
    """
    logger.info("/api/v1/image-to-txt-offline", image=image.filename, request_id=request_id)

    # Validate file type
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Generate request_id if not provided
    if request_id is None:
        request_id = str(uuid.uuid4())

    # Read the image data
    image_data = await image.read()

    # Add request to database
    response = crud.add_request(
        db=db,
        request_id=request_id,
        status=schemas.WebhookStatus.pending,
        itime=datetime.now(tz=None),
    )

    if not response["status"]:
        return response

    # Create channel
    channel = await connection.channel()

    # Convert image to base64
    base64_image = base64.b64encode(image_data).decode('utf-8')

    # Prepare message
    message_body = {
        "image": base64_image,
        "request_id": request_id,
        "priority": priority,
    }

    # Publish to queue
    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message_body).encode(),
            headers={"request_id": request_id},
        ),
        routing_key="ocr_queue",
    )
    await channel.close()

    # Return success response
    msg = Message("fa").INF_SUCCESS()
    msg["data"] = {"request_id": request_id}
    return msg


@app.get("/aihive-ocr/api/v1/status/{request_id}")
async def get_status(
        request_id: str,
        db: Session = Depends(base.get_db)
):
    """
    Get the status of an OCR processing request.

    - **request_id**: The request ID returned from the process_image endpoint
    """
    logger.info("/api/v1/status", request_id=request_id)
    task = crud.get_request(db=db, request_id=request_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    msg = Message("fa").INF_SUCCESS()
    msg["data"] = task
    return msg


if __name__ == "__main__":
    uvicorn.run(app="mainapi:app", host="0.0.0.0", port=8000, reload=False)