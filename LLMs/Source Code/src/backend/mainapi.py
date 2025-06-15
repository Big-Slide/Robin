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
from dbutils import crud, schemas
import sys
from starlette.middleware.cors import CORSMiddleware
from core import base
from dbutils.database import SessionLocal
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz


if os.environ.get("MODE", "dev") == "prod":
    log_dir = "/approot/data"
    temp_dir = "/approot/data/temp"
else:
    log_dir = "../../../Outputs"
    temp_dir = "../../../Outputs/temp"
os.makedirs(log_dir, exist_ok=True)
os.makedirs(temp_dir, exist_ok=True)

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

logger.info("Starting service", version=__version__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan to start the result consumer."""
    try:
        # Result queue
        connection = await aio_pika.connect_robust(config["QUEUE_CONNECTION"])
        db = SessionLocal()
        asyncio.create_task(consume_results(connection, db))
        # Delete unused temp files everyday at 2 AM
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            crud.clean_unused_temp_files,
            trigger=CronTrigger(
                hour=2, minute=0, timezone=pytz.timezone("Asia/Tehran")
            ),
            args=(db,),
        )
        scheduler.start()
        yield
    finally:
        scheduler.shutdown()
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


@app.post("/aihive-llm/api/v1/hrpdfanl/pdf-to-json-offline", tags=["HR"])
async def hr_pdf_analysis(
    file: UploadFile,
    request_id: str = None,
    priority: int = 1,
    model: str = None,
    connection: aio_pika.RobustConnection = Depends(get_rabbitmq_connection),
    db: Session = Depends(base.get_db),
):
    logger.info("request hr_pdf_analysis", request_id=request_id, model=model)
    if request_id is None:
        request_id = str(uuid.uuid4())

    # Save uploaded file
    current_day = datetime.now().strftime("%Y-%m/%d")
    os.makedirs(f"{temp_dir}/{current_day}", exist_ok=True)
    input1_path = f"{temp_dir}/{current_day}/{request_id}_{file.filename}"
    with open(input1_path, "wb") as f:
        f.write(await file.read())

    response = crud.add_request(
        db=db,
        request_id=request_id,
        model=model,
        task="hr_pdf_analysis",
        input1_path=input1_path,
        itime=datetime.now(tz=None),
    )
    if not response["status"]:
        if os.path.exists(input1_path):
            os.remove(input1_path)
        return response

    channel = await connection.channel()

    # TODO: change input_path to binary data
    message_body = {
        "task": "hr_pdf_analysis",
        "input1_path": input1_path,
        "input2_path": None,
        "request_id": request_id,
        "model": model,
    }

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message_body).encode(),
            headers={"request_id": request_id},
        ),
        routing_key="task_queue",
    )
    await channel.close()

    msg = Message("en").INF_SUCCESS()
    msg["data"] = {"request_id": request_id}
    return msg


@app.post("/aihive-llm/api/v1/pdfanl/pdf-to-txt-offline", tags=["General"])
async def pdf_analysis(
    file: UploadFile,
    request_id: str = None,
    priority: int = 1,
    model: str = None,
    connection: aio_pika.RobustConnection = Depends(get_rabbitmq_connection),
    db: Session = Depends(base.get_db),
):
    logger.info("request pdf_analysis", request_id=request_id, model=model)
    if request_id is None:
        request_id = str(uuid.uuid4())

    # Save uploaded file
    current_day = datetime.now().strftime("%Y-%m/%d")
    os.makedirs(f"{temp_dir}/{current_day}", exist_ok=True)
    input1_path = f"{temp_dir}/{current_day}/{request_id}_{file.filename}"
    with open(input1_path, "wb") as f:
        f.write(await file.read())

    response = crud.add_request(
        db=db,
        request_id=request_id,
        model=model,
        task="pdf_analysis",
        input1_path=input1_path,
        itime=datetime.now(tz=None),
    )
    if not response["status"]:
        if os.path.exists(input1_path):
            os.remove(input1_path)
        return response

    channel = await connection.channel()

    # TODO: change input_path to binary data
    message_body = {
        "task": "pdf_analysis",
        "input1_path": input1_path,
        "input2_path": None,
        "request_id": request_id,
        "model": model,
    }

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message_body).encode(),
            headers={"request_id": request_id},
        ),
        routing_key="task_queue",
    )
    await channel.close()

    msg = Message("en").INF_SUCCESS()
    msg["data"] = {"request_id": request_id}
    return msg


@app.post("/aihive-llm/api/v1/hrpdfcmp/pdf-to-txt-offline", tags=["HR"])
async def hr_pdf_comparison(
    file1: UploadFile,
    file2: UploadFile,
    request_id: str = None,
    priority: int = 1,
    model: str = None,
    connection: aio_pika.RobustConnection = Depends(get_rabbitmq_connection),
    db: Session = Depends(base.get_db),
):
    logger.info("request hr_pdf_comparison", request_id=request_id, model=model)
    if request_id is None:
        request_id = str(uuid.uuid4())

    # Save uploaded file
    current_day = datetime.now().strftime("%Y-%m/%d")
    os.makedirs(f"{temp_dir}/{current_day}", exist_ok=True)
    input1_path = f"{temp_dir}/{current_day}/{request_id}_1_{file1.filename}"
    input2_path = f"{temp_dir}/{current_day}/{request_id}_2_{file2.filename}"
    with open(input1_path, "wb") as f:
        f.write(await file1.read())
    with open(input2_path, "wb") as f:
        f.write(await file2.read())

    response = crud.add_request(
        db=db,
        request_id=request_id,
        task="hr_pdf_comparison",
        input1_path=input1_path,
        input2_path=input2_path,
        itime=datetime.now(tz=None),
    )
    if not response["status"]:
        if os.path.exists(input1_path):
            os.remove(input1_path)
        return response

    channel = await connection.channel()

    # TODO: change input_path to binary data
    message_body = {
        "task": "hr_pdf_comparison",
        "input1_path": input1_path,
        "input2_path": input2_path,
        "request_id": request_id,
        "model": model,
    }

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message_body).encode(),
            headers={"request_id": request_id},
        ),
        routing_key="task_queue",
    )
    await channel.close()

    msg = Message("en").INF_SUCCESS()
    msg["data"] = {"request_id": request_id}
    return msg


@app.post("/aihive-llm/api/v1/hrpdfcmp/zip-to-txt-offline", tags=["HR"])
async def hr_pdf_zip_comparison(
    file: UploadFile,
    request_id: str = None,
    priority: int = 1,
    model: str = None,
    connection: aio_pika.RobustConnection = Depends(get_rabbitmq_connection),
    db: Session = Depends(base.get_db),
):
    logger.info("request hr_pdf_comparison", request_id=request_id, model=model)
    if request_id is None:
        request_id = str(uuid.uuid4())

    # Save uploaded file
    current_day = datetime.now().strftime("%Y-%m/%d")
    os.makedirs(f"{temp_dir}/{current_day}", exist_ok=True)
    input1_path = f"{temp_dir}/{current_day}/{request_id}_{file.filename}"
    with open(input1_path, "wb") as f:
        f.write(await file.read())

    response = crud.add_request(
        db=db,
        request_id=request_id,
        task="hr_pdf_zip_comparison",
        input1_path=input1_path,
        itime=datetime.now(tz=None),
    )
    if not response["status"]:
        if os.path.exists(input1_path):
            os.remove(input1_path)
        return response

    channel = await connection.channel()

    # TODO: change input_path to binary data
    message_body = {
        "task": "hr_pdf_zip_comparison",
        "input1_path": input1_path,
        "request_id": request_id,
        "model": model,
    }

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message_body).encode(),
            headers={"request_id": request_id},
        ),
        routing_key="task_queue",
    )
    await channel.close()

    msg = Message("en").INF_SUCCESS()
    msg["data"] = {"request_id": request_id}
    return msg


@app.post("/aihive-llm/api/v1/hrpdfmatch/zip-to-txt-offline", tags=["HR"])
async def hr_pdf_zip_compare_and_match(
    file: UploadFile,
    job_description: str,
    request_id: str = None,
    priority: int = 1,
    model: str = None,
    connection: aio_pika.RobustConnection = Depends(get_rabbitmq_connection),
    db: Session = Depends(base.get_db),
):
    """
    file:            [File] Zip file consist of CV pdfs
    job_description: [str]  Description of job to find best candidate from CVs
    """
    logger.info(
        "request hr_pdf_zip_compare_and_match", request_id=request_id, model=model
    )
    if request_id is None:
        request_id = str(uuid.uuid4())

    # Save uploaded file
    current_day = datetime.now().strftime("%Y-%m/%d")
    os.makedirs(f"{temp_dir}/{current_day}", exist_ok=True)
    input1_path = f"{temp_dir}/{current_day}/{request_id}_{file.filename}"
    with open(input1_path, "wb") as f:
        f.write(await file.read())

    response = crud.add_request(
        db=db,
        request_id=request_id,
        task="hr_pdf_zip_compare_and_match",
        input1_path=input1_path,
        itime=datetime.now(tz=None),
    )
    if not response["status"]:
        if os.path.exists(input1_path):
            os.remove(input1_path)
        return response

    channel = await connection.channel()

    # TODO: change input_path to binary data
    message_body = {
        "task": "hr_pdf_zip_compare_and_match",
        "input1_path": input1_path,
        "input_params": {"job_description": job_description},
        "request_id": request_id,
        "model": model,
    }

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message_body).encode(),
            headers={"request_id": request_id},
        ),
        routing_key="task_queue",
    )
    await channel.close()

    msg = Message("en").INF_SUCCESS()
    msg["data"] = {"request_id": request_id}
    return msg


@app.post("/aihive-llm/api/v1/hranlqus/txt-to-json-offline", tags=["HR"])
async def hr_analysis_question(
    items: schemas.vm_request_hr_analysis_question,
    connection: aio_pika.RobustConnection = Depends(get_rabbitmq_connection),
    db: Session = Depends(base.get_db),
):
    logger.info(
        "request hr_analysis_question", request_id=items.request_id, model=items.model
    )
    if items.request_id is None:
        request_id = str(uuid.uuid4())
    else:
        request_id = items.request_id

    response = crud.add_request(
        db=db,
        request_id=request_id,
        task="hr_analysis_question",
        input_params=json.dumps(
            items.model_dump(exclude={"request_id", "priority", "model"})
        ).encode(),
        itime=datetime.now(tz=None),
    )
    if not response["status"]:
        return response

    channel = await connection.channel()

    # TODO: change input_path to binary data
    message_body = {
        "task": "hr_analysis_question",
        "input_params": items.model_dump(exclude={"request_id", "priority", "model"}),
        "request_id": request_id,
        "model": items.model,
    }

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message_body).encode(),
            headers={"request_id": request_id},
        ),
        routing_key="task_queue",
    )
    await channel.close()

    msg = Message("en").INF_SUCCESS()
    msg["data"] = {"request_id": request_id}
    return msg


@app.post("/aihive-llm/api/v1/cvgenerate/txt-to-pdf-offline", tags=["CV"])
async def cv_generate_offline(
    items: schemas.vm_request_cv_generator,
    connection: aio_pika.RobustConnection = Depends(get_rabbitmq_connection),
    db: Session = Depends(base.get_db),
):
    logger.info(
        "request cv_generate_offline", request_id=items.request_id, model=items.model
    )
    if items.request_id is None:
        request_id = str(uuid.uuid4())
    else:
        request_id = items.request_id

    response = crud.add_request(
        db=db,
        request_id=request_id,
        task="cv_generate",
        input_params=json.dumps(
            items.model_dump(exclude={"request_id", "priority", "model"})
        ).encode(),
        itime=datetime.now(tz=None),
    )
    if not response["status"]:
        return response

    channel = await connection.channel()

    message_body = {
        "task": "cv_generate",
        "input_params": items.model_dump(exclude={"request_id", "priority", "model"}),
        "request_id": request_id,
        "model": items.model,
    }

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message_body).encode(),
            headers={"request_id": request_id},
        ),
        routing_key="task_queue",
    )
    await channel.close()

    msg = Message("en").INF_SUCCESS()
    msg["data"] = {"request_id": request_id}
    return msg


@app.post("/aihive-llm/api/v1/chat/txt-to-txt-offline", tags=["Chat"])
async def chat(
    items: schemas.vm_request_chat,
    connection: aio_pika.RobustConnection = Depends(get_rabbitmq_connection),
    db: Session = Depends(base.get_db),
):
    logger.info("request chat", request_id=items.request_id)
    if items.request_id is None:
        request_id = str(uuid.uuid4())
    else:
        request_id = items.request_id

    response = crud.add_request(
        db=db,
        request_id=request_id,
        task="cv_generate",
        input_params=json.dumps(
            items.model_dump(exclude={"request_id", "priority", "model"})
        ).encode(),
        itime=datetime.now(tz=None),
    )
    if not response["status"]:
        return response

    channel = await connection.channel()

    message_body = {
        "task": "chat",
        "input_params": items.model_dump(exclude={"request_id", "priority", "model"}),
        "request_id": request_id,
        "model": items.model,
    }

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message_body).encode(),
            headers={"request_id": request_id},
        ),
        routing_key="task_queue",
    )
    await channel.close()

    msg = Message("en").INF_SUCCESS()
    msg["data"] = {"request_id": request_id}
    return msg


@app.post(
    "/aihive-llm/api/v1/painting-analysis/zip-to-txt-offline", tags=["Psychology"]
)
async def painting_analysis(
    file: UploadFile,
    request_id: str = None,
    priority: int = 1,
    lang: str = "en",
    model: str = None,
    connection: aio_pika.RobustConnection = Depends(get_rabbitmq_connection),
    db: Session = Depends(base.get_db),
):
    logger.info("request painting_analysis", request_id=request_id, model=model)
    if request_id is None:
        request_id = str(uuid.uuid4())

    # Save uploaded file
    current_day = datetime.now().strftime("%Y-%m/%d")
    os.makedirs(f"{temp_dir}/{current_day}", exist_ok=True)
    input1_path = f"{temp_dir}/{current_day}/{request_id}_{file.filename}"
    with open(input1_path, "wb") as f:
        f.write(await file.read())

    response = crud.add_request(
        db=db,
        request_id=request_id,
        task="painting_analysis",
        input1_path=input1_path,
        itime=datetime.now(tz=None),
    )
    if not response["status"]:
        if os.path.exists(input1_path):
            os.remove(input1_path)
        return response

    channel = await connection.channel()

    # TODO: change input_path to binary data
    message_body = {
        "task": "painting_analysis",
        "input1_path": input1_path,
        "input_params": {"lang": lang},
        "request_id": request_id,
        "model": model,
    }

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message_body).encode(),
            headers={"request_id": request_id},
        ),
        routing_key="task_queue",
    )
    await channel.close()

    msg = Message("en").INF_SUCCESS()
    msg["data"] = {"request_id": request_id}
    return msg


@app.post("/aihive-llm/api/v1/ocr/any-to-txt-offline", tags=["OCR"])
async def ocr(
    file: UploadFile,
    request_id: str = None,
    priority: int = 1,
    model: str = None,
    connection: aio_pika.RobustConnection = Depends(get_rabbitmq_connection),
    db: Session = Depends(base.get_db),
):
    logger.info("request ocr", request_id=request_id, model=model)
    if request_id is None:
        request_id = str(uuid.uuid4())

    # Save uploaded file
    current_day = datetime.now().strftime("%Y-%m/%d")
    os.makedirs(f"{temp_dir}/{current_day}", exist_ok=True)
    input1_path = f"{temp_dir}/{current_day}/{request_id}_{file.filename}"
    with open(input1_path, "wb") as f:
        f.write(await file.read())

    response = crud.add_request(
        db=db,
        request_id=request_id,
        model=model,
        task="ocr",
        input1_path=input1_path,
        itime=datetime.now(tz=None),
    )
    if not response["status"]:
        if os.path.exists(input1_path):
            os.remove(input1_path)
        return response

    channel = await connection.channel()

    # TODO: change input_path to binary data
    message_body = {
        "task": "ocr",
        "input1_path": input1_path,
        "input2_path": None,
        "request_id": request_id,
        "model": model,
    }

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message_body).encode(),
            headers={"request_id": request_id},
        ),
        routing_key="task_queue",
    )
    await channel.close()

    msg = Message("en").INF_SUCCESS()
    msg["data"] = {"request_id": request_id}
    return msg


@app.post("/aihive-llm/api/v1/ocr/any-to-json-offline", tags=["OCR"])
async def ocr_json(
    file: UploadFile,
    request_id: str = None,
    priority: int = 1,
    model: str = None,
    connection: aio_pika.RobustConnection = Depends(get_rabbitmq_connection),
    db: Session = Depends(base.get_db),
):
    """
    Extracting text as json format from any filetype. Now supporting images only.

    {
        "detected_languages": ["language1", "language2"],
        "extracted_text": "The complete extracted text maintaining original structure and formatting",
        "confidence_score": 0.95,
        "text_blocks": [
            {
            "text": "Individual text block content",
            "language": "detected_language",
            "position": "top-left|center|bottom-right",
            "confidence": 0.98
            }
        ],
        "formatting_notes": "Any relevant observations about text structure, tables, or special formatting",
        "extraction_challenges": "Notes about unclear text, image quality issues, or recognition difficulties"
    }
    """
    logger.info("request ocr_json", request_id=request_id, model=model)
    if request_id is None:
        request_id = str(uuid.uuid4())

    # Save uploaded file
    current_day = datetime.now().strftime("%Y-%m/%d")
    os.makedirs(f"{temp_dir}/{current_day}", exist_ok=True)
    input1_path = f"{temp_dir}/{current_day}/{request_id}_{file.filename}"
    with open(input1_path, "wb") as f:
        f.write(await file.read())

    response = crud.add_request(
        db=db,
        request_id=request_id,
        model=model,
        task="ocr_json",
        input1_path=input1_path,
        itime=datetime.now(tz=None),
    )
    if not response["status"]:
        if os.path.exists(input1_path):
            os.remove(input1_path)
        return response

    channel = await connection.channel()

    # TODO: change input_path to binary data
    message_body = {
        "task": "ocr_json",
        "input1_path": input1_path,
        "input2_path": None,
        "request_id": request_id,
        "model": model,
    }

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message_body).encode(),
            headers={"request_id": request_id},
        ),
        routing_key="task_queue",
    )
    await channel.close()

    msg = Message("en").INF_SUCCESS()
    msg["data"] = {"request_id": request_id}
    return msg


@app.get("/aihive-llm/api/v1/status/{request_id}")
async def get_status(request_id: str, db: Session = Depends(base.get_db)):
    logger.info("/llm/status", request_id=request_id)
    task = crud.get_request(db=db, request_id=request_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    msg = Message("en").INF_SUCCESS()
    msg["data"] = task
    return msg


if __name__ == "__main__":
    uvicorn.run(app="mainapi:app", host="0.0.0.0", port=8000, reload=False)
