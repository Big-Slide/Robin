from generators import IDCardProcessor
import aio_pika
import json
import base64
import numpy as np
import cv2
from loguru import logger
import os
from datetime import datetime

if os.environ.get("MODE", "dev") == "prod":
    output_dir = "/approot/data/result"
else:
    output_dir = "../../../../../Outputs/NcToTxt/result"
os.makedirs(output_dir, exist_ok=True)


async def process_image(encoded_image):
    logger.info("Starting ID card OCR processing")
    try:
        # Decode base64 image
        image_data = base64.b64decode(encoded_image)
        nparr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            raise ValueError("Invalid image data")

        logger.info("Image successfully decoded")

        # Create an instance of IDCardProcessor
        processor = IDCardProcessor()

        # Process ID card using the detect_and_process_id_card method
        _, processed_images, text_data = processor.detect_and_process_id_card(frame)

        # Convert text_data to a more suitable format if needed
        ocr_results = {}

        # If text data exists, process it into a structured format
        if text_data:
            for card_idx, card_data in enumerate(text_data):
                for text_entry in card_data['texts']:
                    field_key = f"field_{text_entry['index']}"
                    ocr_results[field_key] = text_entry['text']

        if not ocr_results:
            logger.warning("No ID card data detected in the image")
            return {}

        logger.info(f"Successfully extracted data from ID card")

        # Log detected fields
        for field, value in ocr_results.items():
            logger.info(f"Extracted field: {field}, value: {value}")

        return ocr_results

    except Exception as e:
        logger.exception(f"Error processing image: {e}")
        return {}


async def process_message(
        message: aio_pika.IncomingMessage,
        result_channel: aio_pika.Channel,
):
    async with message.process():
        try:
            # Parse the message body
            message_body = json.loads(message.body.decode())
            encoded_image = message_body["image"]
            request_id = message_body["request_id"]
            priority = message_body.get("priority", 1)

            logger.info(
                "Processing ID card OCR task", request_id=request_id, priority=priority
            )

            # Publish in-progress status
            await result_channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps({
                        "request_id": request_id,
                        "status": "in_progress"
                    }).encode(),
                    headers={"request_id": request_id}
                ),
                routing_key="nc_ocr_result_queue",
            )
            result = {
                "request_id": request_id,
                "status": "in_progress",
            }
            await result_channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(result).encode(), headers={"request_id": request_id}
                ),
                routing_key="nc_ocr_result_queue",
            )

            # Process the image
            ocr_results = await process_image(encoded_image)

            # Optional: save processed image if needed
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"{output_dir}/{request_id}_{timestamp}.jpg"
            # Uncomment if you want to save the processed image
            # annotated_frame = frame.copy()  # Create annotated frame with bounding boxes
            # cv2.imwrite(output_path, annotated_frame)

            if ocr_results:
                # Successful processing
                result = {
                    "request_id": request_id,
                    "status": "completed",
                    "results": {"ocr_data": ocr_results},
                }
            else:
                # No ID card data detected or processing error
                result = {
                    "request_id": request_id,
                    "status": "failed",
                    "error": "No ID card data detected or processing error"
                }

        except Exception as e:
            logger.exception(e)
            result = {
                "request_id": request_id if 'request_id' in locals() else "unknown",
                "status": "failed",
                "error": str(e)
            }

        # Publish result
        await result_channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(result).encode(),
                headers={"request_id": result["request_id"]}
            ),
            routing_key="nc_ocr_result_queue",
        )