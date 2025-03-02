from generators import ASRGenerator
import aio_pika
import json
from loguru import logger
import os

if os.environ.get("MODE", "dev") == "prod":
    output_dir = "/approot/data/result"
else:
    output_dir = "../Outputs/result"
os.makedirs(output_dir, exist_ok=True)


async def process_message(
    message: aio_pika.IncomingMessage,
    result_channel: aio_pika.Channel,
    asr_generator: ASRGenerator,
):
    async with message.process():
        try:
            # Parse the message body
            message_body = json.loads(message.body.decode())
            input_path = message_body["input_path"]
            request_id = message_body["request_id"]

            logger.info(
                "Processing task",
                request_id=request_id,
                input_path=input_path,
            )
            text = await asr_generator.do_asr(input_path)

            result = {
                "request_id": request_id,
                "status": "completed",
                "text": text,
            }
        except Exception as e:
            logger.exception(e)
            result = {"request_id": request_id, "status": "failed", "error": str(e)}

        await result_channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(result).encode(), headers={"request_id": request_id}
            ),
            routing_key="result_queue",
        )
