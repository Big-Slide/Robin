from generators import recognize_hand_gesture
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
    output_dir = "../../../../../Outputs/HandToTxt/result"
os.makedirs(output_dir, exist_ok=True)


async def process_image(encoded_image):
    logger.info("Starting hand gesture recognition")
    try:
        # Decode base64 image
        image_data = base64.b64decode(encoded_image)
        nparr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            raise ValueError("Invalid image data")

        logger.info("Image successfully decoded")

        # Detect hand gestures
        hand_detections = recognize_hand_gesture(frame)

        if not hand_detections:
            logger.warning("No hand gestures detected in the image")
            return []

        logger.info(f"Detected {len(hand_detections)} hand gestures in the image")

        # Log detected gestures
        for detection in hand_detections:
            logger.info(f"Detected gesture: {detection['gesture']}, bounding box: {detection['bounding_box']}")

        return hand_detections

    except Exception as e:
        logger.exception(f"Error processing image: {e}")
        return []


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
                "Processing hand gesture recognition task", request_id=request_id, priority=priority
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
                routing_key="hand_gesture_result_queue",
            )
            result = {
                "request_id": request_id,
                "status": "in_progress",
            }
            await result_channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(result).encode(), headers={"request_id": request_id}
                ),
                routing_key="hand_gesture_result_queue",
            )
            # Process the image
            hand_detections = await process_image(encoded_image)

            # Optional: save processed image if needed
            # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # output_path = f"{output_dir}/{request_id}_{timestamp}.jpg"
            # Add visualization code here if needed
            # cv2.imwrite(output_path, annotated_frame)

            if hand_detections:
                # Successful processing
                result = {
                    "request_id": request_id,
                    "status": "completed",
                    "results": {"hand_detection": hand_detections},
                }
            else:
                # No hands detected or processing error
                result = {
                    "request_id": request_id,
                    "status": "failed",
                    "error": "No hand gestures detected or processing error"
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
            routing_key="hand_gesture_result_queue",
        )