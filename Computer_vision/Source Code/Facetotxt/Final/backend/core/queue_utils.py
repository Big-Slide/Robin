import aio_pika
import json
from loguru import logger
from typing import AsyncGenerator
from config.config_handler import Config  # Import the class
from core import webhook_handler
from sqlalchemy.orm import Session
from dbutils import crud

# Create an instance of Config
config = Config()

async def consume_results(connection: aio_pika.RobustConnection, db: Session):
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue("facial_expression_result_queue", durable=True)

        async for message in queue:
            async with message.process():
                try:
                    result = json.loads(message.body.decode())
                    request_id = result["request_id"]
                    status = result["status"]
                    crud.update_request(
                        db=db,
                        request_id=request_id,
                        status=status,
                        result=result.get("results"),
                        error=result.get("error"),
                    )

                    if status == "in_progress":
                        webhook_handler.set_inprogress(db=db, request_id=request_id)
                    elif status == "completed":
                        webhook_handler.set_completed(db=db, request_id=request_id)
                    elif status == "failed":
                        webhook_handler.set_failed(db=db, request_id=request_id)
                except Exception as e:
                    logger.exception(e)


async def get_rabbitmq_connection() -> AsyncGenerator[aio_pika.RobustConnection, None]:
    """Dependency to get RabbitMQ connection."""
    connection = await aio_pika.connect_robust(config["QUEUE_CONNECTION"])
    try:
        yield connection
    finally:
        await connection.close()