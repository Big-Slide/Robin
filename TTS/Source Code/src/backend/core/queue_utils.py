import aio_pika
import json
from loguru import logger
from typing import AsyncGenerator
from config.config_handler import config
from core import webhook_handler
from sqlalchemy.orm import Session
from dbutils import crud


async def consume_results(connection: aio_pika.RobustConnection, db: Session):
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue("result_queue", durable=True)

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
                        result=result.get("result_path"),
                        error=result.get("error"),
                    )
                    # TODO: handle retry and status_code in db
                    if status == "in_progress":
                        webhook_handler.set_inprogress(db, request_id)
                    elif status == "completed":
                        webhook_handler.set_completed(db, request_id)
                    elif status == "failed":
                        webhook_handler.set_failed(db, request_id)
                except Exception as e:
                    logger.exception(e)


async def get_rabbitmq_connection() -> AsyncGenerator[aio_pika.RobustConnection, None]:
    """Dependency to get RabbitMQ connection."""
    connection = await aio_pika.connect_robust(config["QUEUE_CONNECTION"])
    try:
        yield connection
    finally:
        await connection.close()
