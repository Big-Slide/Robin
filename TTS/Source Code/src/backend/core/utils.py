import aio_pika
import json
from datetime import datetime
from loguru import logger
from typing import AsyncGenerator
from config.config_handler import config
import uuid
from typing import Dict
from core import webhook_handler


def generate_uuid():
    return str(uuid.uuid4())


async def consume_results(connection: aio_pika.RobustConnection, tasks: Dict):
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue("result_queue", durable=True)

        async for message in queue:
            async with message.process():
                try:
                    result = json.loads(message.body.decode())
                    request_id = result["request_id"]
                    if request_id in tasks:
                        tasks[request_id].status = result["status"]
                        tasks[request_id].result_path = result.get("result_path")
                        tasks[request_id].error = result.get("error")
                        tasks[request_id].utime = datetime.now()
                        # TODO: handle failed state
                        webhook_handler.set_completed(request_id=request_id)
                except Exception as e:
                    logger.exception(e)


async def get_rabbitmq_connection() -> AsyncGenerator[aio_pika.RobustConnection, None]:
    """Dependency to get RabbitMQ connection."""
    connection = await aio_pika.connect_robust(config["QUEUE_CONNECTION"])
    try:
        yield connection
    finally:
        await connection.close()
