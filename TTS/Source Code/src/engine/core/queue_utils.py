from generators import TTSGenerator
import aio_pika
import json
from loguru import logger
import os

if os.environ.get("MODE", "dev") == "prod":
    output_dir = "/approot/data/result"
else:
    output_dir = "../../../Outputs/result"
os.makedirs(output_dir, exist_ok=True)


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
            model = message_body.get("model", None)
            request_id = message_body["request_id"]
            lang = message_body.get("lang", None)

            logger.info("Processing task", request_id=request_id)
            result = {
                "request_id": request_id,
                "status": "in_progress",
            }
            await result_channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(result).encode(), headers={"request_id": request_id}
                ),
                routing_key="result_queue",
            )

            output_path = f"{output_dir}/{request_id}.wav"
            await tts_generator.do_tts(
                text=text, model_id=model, tmp_path=output_path, lang=lang
            )

            result = {
                "request_id": request_id,
                "status": "completed",
                "result_path": str(output_path),
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
