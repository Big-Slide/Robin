import aio_pika
import json
from loguru import logger
from typing import AsyncGenerator
from config.config_handler import config
from core import webhook_handler
from sqlalchemy.orm import Session
from dbutils import crud
from dbutils.schemas import WebhookStatus


async def consume_results(connection: aio_pika.RobustConnection, db: Session):
    """
    Consume results from the OCR
    """
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue("nc_ocr_result_queue", durable=True)

        async for message in queue:
            async with message.process():
                try:
                    result = json.loads(message.body.decode())
                    status = result["status"]
                    request_id = result["request_id"]

                    # Map status string to enum
                    status_mapping = {
                        "pending": WebhookStatus.pending,
                        "in_progress": WebhookStatus.in_progress,
                        "completed": WebhookStatus.completed,
                        "failed": WebhookStatus.failed
                    }
                    status = status_mapping.get(result["status"], WebhookStatus.failed)

                    logger.info(f"Received result for request {request_id} with status {status}")

                    # Update request in database
                    crud.update_request(
                        db=db,
                        request_id=request_id,
                        status=status,
                        result=result.get("results"),
                        error=result.get("error"),
                    )

                    # Update webhook status
                    if status == "in_progress":
                        webhook_handler.set_inprogress(db=db, request_id=request_id)
                    elif status == "completed":
                        webhook_handler.set_completed(request_id=request_id, db=db)
                    elif status == "failed":
                        webhook_handler.set_failed(db=db, request_id=request_id)

                except Exception as e:
                    logger.exception(f"Error processing result message: {e}")


async def get_rabbitmq_connection() -> AsyncGenerator[aio_pika.RobustConnection, None]:
    """Dependency to get RabbitMQ connection."""
    connection = await aio_pika.connect_robust(config["QUEUE_CONNECTION"])
    try:
        yield connection
    finally:
        await connection.close()