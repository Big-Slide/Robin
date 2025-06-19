from generators import LLMGenerator
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
    llm_generator: LLMGenerator,
):
    async with message.process():
        try:
            # Parse the message body
            message_body = json.loads(message.body.decode())
            task = message_body["task"]
            request_id = message_body["request_id"]
            input1_path = message_body.get("input1_path", None)
            input2_path = message_body.get("input2_path", None)
            input_params = message_body.get("input_params", None)
            model = message_body.get("model", None)

            logger.info(
                "Processing task",
                request_id=request_id,
                task=task,
                input1_path=input1_path,
                input2_path=input2_path,
                input_params=input_params,
                model=model,
            )
            # Mark task as in progress
            result = {"request_id": request_id, "status": "in_progress"}
            await result_channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(result).encode(), headers={"request_id": request_id}
                ),
                routing_key="result_queue",
            )

            # TODO: handle this based on new added tasks
            output_path = None
            if input_params:
                output_path = f"{output_dir}/{request_id}.pdf"

            result_data, result_path = await llm_generator.process_task(
                task, input1_path, input2_path, input_params, output_path, model=model
            )

            result = {
                "request_id": request_id,
                "status": "completed",
                "result_data": result_data,
                "result_path": result_path,
            }
            logger.debug(f"{result=}")
        except Exception as e:
            if output_path and os.path.exists(output_path):
                os.remove(output_path)
            logger.exception(e)
            result = {"request_id": request_id, "status": "failed", "error": str(e)}

        await result_channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(result).encode(), headers={"request_id": request_id}
            ),
            routing_key="result_queue",
        )
