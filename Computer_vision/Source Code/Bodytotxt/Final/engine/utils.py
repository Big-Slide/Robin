from typing import List, Dict, Tuple, Optional
import cv2
import numpy as np
from pydantic import BaseModel
from ultralytics import YOLO
from fastapi import HTTPException
import os

if os.environ.get("MODE", "dev") == "prod":
    models_dir = "/approot/models"
else:
    models_dir = "../../../../Models/BodyToTxt"
PoseModelPath = f'{models_dir}/yolo11n-pose.pt'
bodymodelpath = f'{models_dir}/yolo11s.pt'


class PoseResponse(BaseModel):
    actions: List[str]
    body_detection: Dict[str, bool]


class PoseDetector:
    def __init__(self):
        # Initialize the YOLO model
        self.model = YOLO(PoseModelPath)

        # Define thresholds
        self.up_tresh_hand = 170
        self.down_tresh_hand = 95
        self.up_tresh_leg = 155
        self.down_tresh_leg = 130
        self.arm_up_tresh = 90
        self.upper_body_tresh = 120
        self.dast_tresh = 70
        self.head_tresh_up = 58
        self.head_tresh_down = 36
        self.hip_tresh = 260

        # Define valid identifier
        self.VALID_IDENTIFIER = "AIHIVE-BODYTOTXT"

    def verify_identifier(self, identifier: str) -> bool:
        """
        Verify if the provided identifier matches the valid one
        """
        return identifier == self.VALID_IDENTIFIER

    @staticmethod
    def angle(px1, py1, px2, py2, px3, py3) -> float:
        v1 = np.array([px1, py1]) - ([px2, py2])
        v2 = np.array([px3, py3]) - ([px2, py2])
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 == 0 or norm_v2 == 0:
            return 0
        cos_angle = dot_product / (norm_v1 * norm_v2)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        return np.degrees(np.arccos(cos_angle))

    @staticmethod
    def check_full_body(keypoints) -> Dict[str, bool]:
        """
        Check if all required body parts are visible in the frame
        Returns a dictionary indicating which body parts are detected
        """
        body_parts = {
            'head': [0],  # nose
            'upper_body': [5, 6, 7, 8],  # shoulders and elbows
            'lower_body': [11, 12],  # hips
            'legs': [13, 14, 15, 16]  # knees and ankles
        }

        detection_status = {}
        visible_points = set()
        for i, point in enumerate(keypoints):
            if not (np.isnan(point[0]) or np.isnan(point[1])):
                if point[0] != 0 and point[1] != 0:
                    visible_points.add(i)

        for part, required_points in body_parts.items():
            detection_status[part] = all(point in visible_points for point in required_points)

        detection_status['full_body'] = all(detection_status.values())
        return detection_status

    def process_image(self, image_bytes: bytes) -> Tuple[List[str], Dict[str, bool]]:
        """
        Process image and return pose detection results
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise HTTPException(status_code=400, detail="Invalid image format")

        frame = cv2.resize(frame, (1020, 500))
        result = self.model.track(frame)

        actions = []
        body_status = {'full_body': False}

        if result[0].boxes is not None and result[0].boxes.id is not None:
            keypoints = result[0].keypoints.xy.cpu().numpy()
            for keypoint in keypoints:
                if len(keypoint) > 16:
                    body_status = self.check_full_body(keypoint)

                    if body_status['full_body']:
                        points = []
                        for point in keypoint:
                            cx, cy = int(point[0]), int(point[1])
                            points.append((cx, cy))

                        actions.append("Full body detected")

                        # Calculate angles
                        left_arm_angle = self.angle(points[7][0], points[7][1], points[5][0], points[5][1],
                                                    points[11][0], points[11][1])
                        right_arm_angle = self.angle(points[8][0], points[8][1], points[6][0], points[6][1],
                                                     points[12][0], points[12][1])
                        left_knee_angle = self.angle(points[11][0], points[11][1], points[13][0], points[13][1],
                                                     points[15][0], points[15][1])
                        right_knee_angle = self.angle(points[12][0], points[12][1], points[14][0], points[14][1],
                                                      points[16][0], points[16][1])
                        letf_hand_angle = self.angle(points[5][0], points[5][1], points[8][0], points[8][1],
                                                     points[10][0], points[10][1])
                        right_hand_angle = self.angle(points[6][0], points[6][1], points[7][0], points[7][1],
                                                      points[9][0], points[9][1])
                        head_angle = self.angle(points[0][0], points[0][1], points[5][0], points[5][1],
                                                points[6][0], points[6][1])
                        left_hip_angle = self.angle(points[14][0], points[14][1], points[12][0], points[12][1],
                                                    points[11][0], points[11][1])
                        right_hip_angle = self.angle(points[13][0], points[13][1], points[11][0], points[11][1],
                                                     points[12][0], points[12][1])
                        left_upper_body_angle = self.angle(points[5][0], points[5][1], points[11][0], points[11][1],
                                                           points[13][0], points[13][1])
                        right_upper_body_angle = self.angle(points[6][0], points[6][1], points[12][0], points[12][1],
                                                            points[14][0], points[14][1])

                        # Check conditions and add actions
                        if left_arm_angle >= self.arm_up_tresh:
                            actions.append("left arm up")
                        if right_arm_angle >= self.arm_up_tresh:
                            actions.append("right arm up")
                        if right_arm_angle >= self.arm_up_tresh and left_arm_angle >= self.arm_up_tresh:
                            actions.append("both arms up")

                        if head_angle <= self.head_tresh_down:
                            actions.append("head to left")
                        if head_angle >= self.head_tresh_up:
                            actions.append("head to right")

                        if left_hip_angle + right_hip_angle >= self.hip_tresh:
                            actions.append("legs are wide open")

                        if left_knee_angle <= self.down_tresh_leg:
                            actions.append("left knee bended")
                        if right_knee_angle <= self.down_tresh_leg:
                            actions.append("right knee bended")

                        if right_knee_angle <= self.down_tresh_leg and left_knee_angle <= self.down_tresh_leg:
                            actions.append("both knee bended")

                        if letf_hand_angle <= self.down_tresh_hand and right_hand_angle <= self.down_tresh_hand:
                            actions.append("I am strong")
                        if left_upper_body_angle <= self.upper_body_tresh:
                            actions.append("left leg up")
                        if right_upper_body_angle <= self.upper_body_tresh:
                            actions.append("right leg up")

                    else:
                        actions.append("Full body not detected")

        return actions, body_status

class FallDetector:
    def __init__(self):
        # Initialize the YOLO model for fall detection
        self.fall_model = YOLO(bodymodelpath)

    def detect_fall(self, frame):
        """
        Method to detect falls using YOLO model.
        Returns only the fall status without points.
        """
        # Run YOLO detection
        results = self.fall_model.predict(frame)

        # Initialize default status
        status = "Normal"

        # Check if any object is detected
        if results[0].boxes is not None and len(results[0].boxes) > 0:
            for box in results[0].boxes.xyxy.int().cpu().tolist():
                x1, y1, x2, y2 = box
                h = y2 - y1
                w = x2 - x1
                if h - w <= 0:  # If height is less than or equal to width, it's a fall
                    status = "Fall"
                    break

        return status