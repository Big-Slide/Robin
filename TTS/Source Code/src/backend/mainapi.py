import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import aio_pika
import uuid
import json
from typing import Dict, Optional
import asyncio
from messages import Message
from datetime import datetime
from fastapi.responses import FileResponse

app = FastAPI()


class GenerateRequest(BaseModel):
    text: str
    model: str = None
    task_id: str = None
    priority: int = 1


class TaskStatus(BaseModel):
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    itime: datetime
    utime: Optional[datetime] = None
    result_path: Optional[str] = None
    error: Optional[str] = None


tasks: Dict[str, TaskStatus] = {}


async def consume_results(connection: aio_pika.RobustConnection):
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue("result_queue", durable=True)

        async for message in queue:
            async with message.process():
                try:
                    result = json.loads(message.body.decode())
                    task_id = result["task_id"]
                    if task_id in tasks:
                        tasks[task_id].status = result["status"]
                        tasks[task_id].result_path = result.get("result_path")
                        tasks[task_id].error = result.get("error")
                        tasks[task_id].utime = datetime.now()
                except Exception as e:
                    print(f"Error processing result: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to RabbitMQ
    connection = await aio_pika.connect_robust("amqp://guest:guest@queue/")
    app.state.rabbitmq_connection = connection

    # Start result consumer
    asyncio.create_task(consume_results(connection))

    yield

    await connection.close()


@app.post("/tts/generate")
async def generate_sound(request: GenerateRequest):
    task_id = request.task_id
    if task_id is None:
        task_id = str(uuid.uuid4())
    tasks[task_id] = TaskStatus(task_id=task_id, status="pending", itime=datetime.now())

    connection = app.state.rabbitmq_connection
    channel = await connection.channel()

    # Prepare message with text, model, and task_id
    message_body = {"text": request.text, "model": request.model, "task_id": task_id}

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message_body).encode(),
            headers={"task_id": task_id},
        ),
        routing_key="task_queue",
    )
    await channel.close()

    msg = Message("fa").INF_SUCCESS()
    msg["data"] = {"task_id": task_id}
    return msg


@app.get("/tts/status/{task_id}")
async def get_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    msg = Message("fa").INF_SUCCESS()
    msg["data"] = task
    return msg


@app.get("/tts/file/{task_id}")
async def get_file(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status == "completed" and task.result_path is not None:
        return FileResponse(path=task.result_path, media_type="audio/wav")
    else:
        raise HTTPException(status_code=404, detail="Task pending or failed")


if __name__ == "__main__":
    uvicorn.run(app="mainapi:app", host="0.0.0.0", port=8001, reload=False)
