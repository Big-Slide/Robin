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
    """Consume results from the body posture result queue and update the database."""
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue("body_posture_result_queue", durable=True)

        async for message in queue:
            async with message.process():
                try:
                    result = json.loads(message.body.decode())
                    request_id = result["request_id"]
                    status = result["status"]
                    logger.info(f"Processing result for request_id: {request_id}, status: {result['status']}")

                    # Map status string to WebhookStatus enum
                    status_map = {
                        "pending": WebhookStatus.pending,
                        "in_progress": WebhookStatus.in_progress,
                        "completed": WebhookStatus.completed,
                        "failed": WebhookStatus.failed
                    }

                    status = status_map.get(result["status"], WebhookStatus.failed)

                    # Update database
                    update_success = crud.update_request(
                        db=db,
                        request_id=request_id,
                        status=status,
                        result=result.get("results"),
                        error=result.get("error"),
                    )

                    if not update_success:
                        logger.error(f"Failed to update database for request_id: {request_id}")
                        continue

                    # Call appropriate webhook based on status
                    if status == "in_progress":
                        webhook_handler.set_inprogress(db=db, request_id=request_id)
                    elif status == "completed":
                        webhook_success = webhook_handler.set_completed(request_id=request_id, db=db)
                        logger.info(f"Completed webhook for {request_id}: {'Success' if webhook_success else 'Failed'}")
                    elif status == "failed":
                        webhook_success = webhook_handler.set_failed(request_id=request_id)
                        logger.info(f"Failed webhook for {request_id}: {'Success' if webhook_success else 'Failed'}")

                except Exception as e:
                    logger.exception(f"Error consuming result: {e}")


async def get_rabbitmq_connection() -> AsyncGenerator[aio_pika.RobustConnection, None]:
    """Dependency to get RabbitMQ connection."""
    connection = await aio_pika.connect_robust(config["QUEUE_CONNECTION"])
    try:
        yield connection
    finally:
        await connection.close()