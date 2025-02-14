import os
from loguru import logger
from version import __version__

if os.environ.get("MODE", "dev") == "prod":
    OUTPUT_DIR = "/approot/data/result"
    log_dir = "/approot/data"
else:
    OUTPUT_DIR = "../Outputs/result"
    log_dir = "../Outputs/result"
os.makedirs(OUTPUT_DIR, exist_ok=True)

logger.add(
    f"{log_dir}/engine.log",
    rotation="50MB",
    format="{time} | {level} | {message} | {extra}",
    level="INFO",
    backtrace=True,
    colorize=True,
    serialize=False,
)

logger.info("Starting service...", version=__version__)

from generators import TTSGenerator
import aio_pika
import asyncio
import json


async def process_message(
    message: aio_pika.IncomingMessage,
    result_channel: aio_pika.Channel,
    tts_generator: TTSGenerator,
):
    async with message.process():
        try:
            # Parse the message body
            message_body = json.loads(message.body.decode())
            text = message_body["text"]
            model = message_body["model"]
            task_id = message_body["task_id"]

            logger.info("Processing task", task_id=task_id, model=model, text=text)
            output_path = f"{OUTPUT_DIR}/{task_id}.wav"
            await tts_generator.do_tts(text=text, model=model, tmp_path=output_path)

            result = {
                "task_id": task_id,
                "status": "completed",
                "result_path": str(output_path),
            }
        except Exception as e:
            logger.exception(e)
            result = {"task_id": task_id, "status": "failed", "error": str(e)}

        await result_channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(result).encode(), headers={"task_id": task_id}
            ),
            routing_key="result_queue",
        )


async def main():
    tts_generator = TTSGenerator()
    connection = await aio_pika.connect_robust("amqp://guest:guest@queue/")

    # Create separate channels for consuming and publishing
    task_channel = await connection.channel()
    result_channel = await connection.channel()

    # Configure task queue
    task_queue = await task_channel.declare_queue("task_queue", durable=True)

    # Start consuming tasks
    await task_queue.consume(
        lambda message: process_message(message, result_channel, tts_generator)
    )

    # Keep connection alive
    try:
        await asyncio.Future()
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
