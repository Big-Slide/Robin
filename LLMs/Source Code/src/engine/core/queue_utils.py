from generators import LLMGenerator
import aio_pika
import json
from loguru import logger


async def process_message(
    message: aio_pika.IncomingMessage,
    result_channel: aio_pika.Channel,
    llm_generator: LLMGenerator,
):
    async with message.process():
        try:
            # Parse the message body
            message_body = json.loads(message.body.decode())
            task = message_body["task"]
            input1_path = message_body["input1_path"]
            input2_path = message_body["input2_path"]
            request_id = message_body["request_id"]

            logger.info(
                "Processing task",
                request_id=request_id,
                task=task,
                input1_path=input1_path,
                input2_path=input2_path,
            )
            # TODO: mark task as in progress
            result_details = await llm_generator.process_task(task, input1_path, input2_path)

            result = {
                "request_id": request_id,
                "status": "completed",
                "data": result_details,
            }
            logger.debug(f"{result=}")
        except Exception as e:
            logger.exception(e)
            result = {"request_id": request_id, "status": "failed", "error": str(e)}

        await result_channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(result).encode(), headers={"request_id": request_id}
            ),
            routing_key="result_queue",
        )
