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
from fastapi.responses import FileResponse
from loguru import logger
import os
from version import __version__
from config.config_handler import config  # Import the config instance
from core.queue_utils import consume_results, get_rabbitmq_connection
from dbutils import schemas, crud
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
    level=config["CONSOLE_LOG_LEVEL"],  # Use config instance
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
    level=config["FILE_LOG_LEVEL"],  # Use config instance
    backtrace=True,
    diagnose=False,
    colorize=False,
    serialize=False,
    enqueue=True,
)

logger.info("Starting service", version=__version__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan to start the result consumer."""
    try:
        connection = await aio_pika.connect_robust(config["QUEUE_CONNECTION"])  # Use config instance
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


@app.post("/aihive-facetotxt/api/v1/image-to-txt-offline")
async def process_image(
        image: UploadFile = File(...),
        request_id: str = Form(None),
        priority: int = Form(1),
        connection: aio_pika.RobustConnection = Depends(get_rabbitmq_connection),
        db: Session = Depends(base.get_db),
):
    logger.info("/facetotxt/image-to-txt-offline", image=image.filename, request_id=request_id)

    # Generate request_id if not provided
    if request_id is None:
        request_id = str(uuid.uuid4())

    # Save the image to a temporary file if needed
    # For now, we'll skip this step and just process the image directly
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
        routing_key="facial_expression_queue",
    )
    await channel.close()

    # Return success response
    msg = Message("fa").INF_SUCCESS()
    msg["data"] = {"request_id": request_id}
    return msg


@app.get("/aihive-facetotxt/api/v1/status/{request_id}")
async def get_status(request_id: str, db: Session = Depends(base.get_db)):
    logger.info("/facetotxt/status", request_id=request_id)
    task = crud.get_request(db=db, request_id=request_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    msg = Message("fa").INF_SUCCESS()
    msg["data"] = task
    return msg


@app.get("/aihive-facetotxt/api/v1/image/{request_id}")
async def get_image(request_id: str, db: Session = Depends(base.get_db)):
    logger.info("/facetotxt/image", request_id=request_id)
    task = crud.get_request(db=db, request_id=request_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # In a real implementation, you would store the path to the image
    # and return it here. For now, we'll return an error since we're not saving images.
    if task.status == schemas.WebhookStatus.completed and task.result:
        # Assuming result contains a path to the image
        image_path = task.result.get("image_path")
        if image_path and os.path.exists(image_path):
            return FileResponse(path=image_path, media_type="image/jpeg")

    raise HTTPException(status_code=404, detail="Image not available or task pending/failed")


@app.post("/system-name/api/v1/aihive-facetotxt/webhook")
async def webhook(
        request_id: str = Form(...),
        db: Session = Depends(base.get_db)
):
    """
    Webhook endpoint for checking facial expression analysis status

    Args:
        request_id: The ID of the request to check
        db: Database session

    Returns:
        dict: Status and results of the facial expression analysis
    """
    logger.info(f"Webhook request for {request_id}")

    # Get the task from the database
    task = crud.get_request(db=db, request_id=request_id)

    # Log the task for debugging
    logger.info(f"Task retrieved: {task}")

    if not task:
        logger.warning(f"Task not found for request_id: {request_id}")
        return {
            "status": False,
            "message": "Request not found",
            "code": "3"
        }

    # Determine the status code
    try:
        # Convert status to integer if it's an enum
        status_value = task.status.value if hasattr(task.status, 'value') else task.status

        # Map status to code string
        status_codes = {
            0: "0",
            1: "1",
            2: "2",
            3: "3"
        }

        # Get status code
        status_code = status_codes.get(status_value, "3")
        logger.info(f"Determined status_code: {status_code} from status: {task.status}")

        # Map status code to message
        status_messages = {
            "0": "Pending",
            "1": "In Processing",
            "2": "Completed",
            "3": "Failed"
        }

        # Prepare webhook response
        response = {
            "status": status_code != "3",  # True if not failed
            "message": status_messages.get(status_code, "Failed"),
            "code": status_code
        }

        # Add results if completed
        if status_code == "2" and task.result:
            response["results"] = task.result

        logger.info(f"Webhook response: {response}")
        return response
    except Exception as e:
        logger.exception(f"Error processing webhook: {e}")
        return {
            "status": False,
            "message": f"Error processing webhook: {str(e)}",
            "code": "3"
        }


if __name__ == "__main__":
    uvicorn.run(app="mainapi:app", host="0.0.0.0", port=9000, reload=False)