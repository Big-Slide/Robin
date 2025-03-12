import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from sqlalchemy.orm import Session
import aio_pika
import uuid
import json
import asyncio
import base64
from datetime import datetime
from fastapi.responses import FileResponse
from loguru import logger
import os
from starlette.middleware.cors import CORSMiddleware
from core import base
from dbutils.database import SessionLocal
from dbutils import schemas, crud
from core.queue_utils import consume_results, get_rabbitmq_connection
import sys
from config.config_handler import config

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

logger.info("Starting Body Posture Detection Service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan to start the result consumer."""
    try:
        connection = await aio_pika.connect_robust(config["QUEUE_CONNECTION"])
        db = SessionLocal()
        asyncio.create_task(consume_results(connection, db))
        yield
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        response = schemas.ApiResponse.error("ERR_FAILED_TO_CONNECT_TO_SERVER", "RabbitMQ")
        raise HTTPException(status_code=503, detail=response.message)
    finally:
        try:
            db.close()
            await connection.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
base_mdl = base.Base()


@app.post("/aihive-bodytotxt/api/v1/image-to-txt-offline")
async def process_image(
        image: UploadFile = File(...),
        request_id: str = Form(None),
        priority: int = Form(1),
        connection: aio_pika.RobustConnection = Depends(get_rabbitmq_connection),
        db: Session = Depends(base.get_db),
):
    logger.info("/bodytotxt/image-to-txt-offline", image=image.filename, request_id=request_id)

    # Generate request_id if not provided
    if request_id is None:
        request_id = str(uuid.uuid4())

    try:
        # Read the image
        image_data = await image.read()
    except Exception as e:
        logger.error(f"Failed to read image: {e}")
        return schemas.ApiResponse.error("ERR_INVALID_INPUT")

    # Add request to database
    response = crud.add_request(
        db=db,
        request_id=request_id,
        status=schemas.WebhookStatus.pending,
        itime=datetime.now(tz=None),
    )

    if not response["status"]:
        return schemas.ApiResponse.error("ERR_FAILED_TO_ADD_TO_DB")

    try:
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
            routing_key="body_posture_queue",
        )
        await channel.close()

        # Return success response
        return schemas.ApiResponse.success(data={"request_id": request_id})
    except Exception as e:
        logger.error(f"Failed to publish message to queue: {e}")
        return schemas.ApiResponse.error("ERR_FAILED_TO_CONNECT_TO_SERVER", "RabbitMQ")


@app.get("/aihive-bodytotxt/api/v1/status/{request_id}")
async def get_status(request_id: str, db: Session = Depends(base.get_db)):
    logger.info("/bodytotxt/status", request_id=request_id)
    task = crud.get_request(db=db, request_id=request_id)
    if not task:
        response = schemas.ApiResponse.error("ERR_NOT_FOUND", request_id)
        raise HTTPException(status_code=404, detail=response.message)

    return schemas.ApiResponse.success(data=task)


@app.get("/aihive-bodytotxt/api/v1/image/{request_id}")
async def get_image(request_id: str, db: Session = Depends(base.get_db)):
    logger.info("/bodytotxt/image", request_id=request_id)
    task = crud.get_request(db=db, request_id=request_id)
    if not task:
        response = schemas.ApiResponse.error("ERR_NOT_FOUND", request_id)
        raise HTTPException(status_code=404, detail=response.message)

    if task.status == schemas.WebhookStatus.completed and task.result:
        # Assuming result contains a path to the image
        image_path = task.result.get("image_path")
        if image_path and os.path.exists(image_path):
            return FileResponse(path=image_path, media_type="image/jpeg")

        response = schemas.ApiResponse.custom_error("Image file not found")
        raise HTTPException(status_code=404, detail=response.message)
    else:
        if task.status == schemas.WebhookStatus.pending:
            response = schemas.ApiResponse.custom_error("Task is still pending")
        elif task.status == schemas.WebhookStatus.in_progress:
            response = schemas.ApiResponse.custom_error("Task is being processed")
        else:
            response = schemas.ApiResponse.error("ERR_FAILED")

        raise HTTPException(status_code=404, detail=response.message)


@app.post("/aihive-bodytotxt/webhook")
async def webhook(
        request_id: str = Form(...),
        db: Session = Depends(base.get_db)
):
    """
    Webhook endpoint for checking body posture analysis status

    Args:
        request_id: The ID of the request to check
        db: Database session

    Returns:
        dict: Status and results of the body posture analysis
    """
    logger.info(f"Webhook request for {request_id}")

    # Get the task from the database
    task = crud.get_request(db=db, request_id=request_id)

    # Log the task for debugging
    logger.info(f"Task retrieved: {task}")

    if not task:
        logger.warning(f"Task not found for request_id: {request_id}")
        return schemas.WebhookResponse.failed(f"Request {request_id} not found")

    # Return appropriate response based on task status
    return schemas.WebhookResponse.from_status(task.status, task.result)


if __name__ == "__main__":
    uvicorn.run(app="mainapi:app", host="0.0.0.0", port=8000, reload=False)