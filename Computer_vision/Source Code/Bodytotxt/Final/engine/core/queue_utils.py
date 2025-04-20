from utils import PoseDetector, FallDetector
import aio_pika
import json
import base64
import numpy as np
import cv2
from loguru import logger
import os
import torch
from datetime import datetime

if os.environ.get("MODE", "dev") == "prod":
    output_dir = "/approot/data/result"
else:
    output_dir = "../../../../../Outputs/result"
os.makedirs(output_dir, exist_ok=True)

# Initialize detectors once
pose_detector = PoseDetector()
fall_detector = FallDetector()

# Set device for PyTorch if available
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
if device.type == 'cuda':
    cv2.cuda.setDevice(0)
    if hasattr(pose_detector, 'model'):
        pose_detector.model = pose_detector.model.to(device)
    if hasattr(fall_detector, 'fall_model'):
        fall_detector.fall_model = fall_detector.fall_model.to(device)
    logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
else:
    logger.info("Using CPU for processing")


async def process_image(encoded_image):
    logger.info("Starting body posture image processing")
    try:
        # Decode base64 image
        image_data = base64.b64decode(encoded_image)

        # Process image with pose detection
        logger.info("Starting pose detection")
        pose_actions, body_detection_dict = pose_detector.process_image(image_data)
        logger.info(f"Pose detection results: {pose_actions}")

        # Decode image for fall detection (needs to be done separately)
        nparr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Invalid image data for fall detection")

        # Process fall detection
        logger.info("Starting fall detection")
        fall_status = fall_detector.detect_fall(frame)
        logger.info(f"Fall detection result: {fall_status}")

        # Convert fall status to boolean for simpler handling
        is_fallen = fall_status == "Fall"

        # Combine results
        results = {
            "pose_actions": pose_actions,
            "fall_status": is_fallen,
            "body_detected": body_detection_dict.get('full_body', False)
        }

        # Optional: Save processed image if needed
        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # output_path = f"{output_dir}/{timestamp}.jpg"
        # cv2.imwrite(output_path, frame)
        # results["image_path"] = output_path

        return results

    except Exception as e:
        logger.exception(f"Error processing image: {e}")
        return None
    finally:
        if device.type == 'cuda':
            torch.cuda.empty_cache()


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
                "Processing body posture task", request_id=request_id, priority=priority
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
                routing_key="body_posture_result_queue",
            )

            # Process the image
            results = await process_image(encoded_image)

            if results:
                # Successful processing
                result = {
                    "request_id": request_id,
                    "status": "completed",
                    "results": results,
                }
            else:
                # No pose detected or processing error
                result = {
                    "request_id": request_id,
                    "status": "failed",
                    "error": "No pose detected or processing error"
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
            routing_key="body_posture_result_queue",)