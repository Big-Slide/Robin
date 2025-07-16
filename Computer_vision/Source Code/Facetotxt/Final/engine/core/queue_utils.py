from generators import detect_faces, classify_gender, classify_emotion, face_mesh
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
    output_dir = "../Outputs/result"
os.makedirs(output_dir, exist_ok=True)


async def process_image(encoded_image):
    logger.info("Starting image processing")
    try:
        # Decode base64 image
        image_data = base64.b64decode(encoded_image)
        nparr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            raise ValueError("Invalid image data")

        # Convert to RGB for Mediapipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        logger.info("Image successfully decoded and converted to RGB")

        # Detect faces
        faces = detect_faces(frame)
        if not faces:
            logger.warning("No faces detected in the image")
            return []

        logger.info(f"Detected {len(faces)} faces in the image")

        results = face_mesh.process(rgb_frame)
        if not results.multi_face_landmarks:
            logger.warning("No face landmarks detected")
            return []

        # Process results
        processed_results = []
        for (x, y, x1, y1) in faces:
            face_roi = frame[y:y1, x:x1]
            gender, _ = classify_gender(face_roi)

            emotion = "Unknown"
            if results.multi_face_landmarks:
                for landmarks in results.multi_face_landmarks:
                    emotion = classify_emotion(landmarks, frame.shape)
                    break

            processed_results.append({
                "gender": gender,
                "emotion": emotion,
                "bounding_box": [int(x), int(y), int(x1), int(y1)]
            })
            logger.info(f"Processed face - Gender: {gender}, Emotion: {emotion}")

        return processed_results

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
                "Processing facial expression task", request_id=request_id, priority=priority
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
                routing_key="facial_expression_result_queue",
            )
            result = {
                "request_id": request_id,
                "status": "in_progress",
            }
            await result_channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(result).encode(), headers={"request_id": request_id}
                ),
                routing_key="facial_expression_result_queue",
            )

            # Process the image
            results = await process_image(encoded_image)

            # Optional: save processed image if needed
            # output_path = f"{output_dir}/{request_id}.jpg"

            if results:
                # Successful processing
                result = {
                    "request_id": request_id,
                    "status": "completed",
                    "results": results,
                }
            else:
                # No faces detected or processing error
                result = {
                    "request_id": request_id,
                    "status": "failed",
                    "error": "No faces detected or processing error"
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
            routing_key="facial_expression_result_queue",
        )