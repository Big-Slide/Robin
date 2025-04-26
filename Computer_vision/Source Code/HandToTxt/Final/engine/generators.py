import csv
import itertools
import cv2
import numpy as np
import mediapipe as mp
from keypoint_classifier import KeyPointClassifier
import os

# =================== Initialize Mediapipe for Hand Landmarks ===================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=True,
    max_num_hands=2,
    min_detection_confidence=0.7,
)
if os.environ.get("MODE", "dev") == "prod":
    models_dir = "/approot/models"
else:
    models_dir = "../../../../Models/HandToTxt"
# =================== Load Hand Gesture Classification Model ===================
keypoint_classifier = KeyPointClassifier()
with open(f'{models_dir}/keypoint_classifier_label.csv', encoding='utf-8-sig') as f:
    keypoint_classifier_labels = [row[0] for row in csv.reader(f) if row and len(row) > 0]

# =================== Helper Functions ===================
def detect_hands(frame):
    """Process image with MediaPipe Hands and return hand landmarks."""
    # Convert to RGB for processing
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Process the image
    rgb_frame.flags.writeable = False
    results = hands.process(rgb_frame)
    rgb_frame.flags.writeable = True
    
    return results


def calc_bounding_box(landmark_list):
    """Calculate bounding box around hand landmarks."""
    x_coordinates = [point[0] for point in landmark_list]
    y_coordinates = [point[1] for point in landmark_list]
    x_min, x_max = min(x_coordinates), max(x_coordinates)
    y_min, y_max = min(y_coordinates), max(y_coordinates)
    
    return [int(x_min), int(y_min), int(x_max), int(y_max)]


def calc_landmark_list(image, landmarks):
    """Extract landmark points from the MediaPipe hand landmarks."""
    image_width, image_height = image.shape[1], image.shape[0]
    landmark_point = []

    for _, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)
        landmark_point.append([landmark_x, landmark_y])

    return landmark_point


def pre_process_landmark(landmark_list):
    """Convert landmarks to relative coordinates and normalize."""
    temp_landmark_list = landmark_list.copy()

    # Convert to relative coordinates
    base_x, base_y = temp_landmark_list[0]
    for i in range(len(temp_landmark_list)):
        temp_landmark_list[i][0] -= base_x
        temp_landmark_list[i][1] -= base_y

    # Flatten list for model input
    flattened = list(itertools.chain.from_iterable(temp_landmark_list))

    # Normalize values
    max_value = max(map(abs, flattened)) if max(map(abs, flattened)) > 0 else 1
    normalized = [v / max_value for v in flattened]

    return normalized


def recognize_hand_gesture(image):
    """Process an image and detect hand gestures.
    
    Args:
        image: Input image (BGR format from OpenCV)
        
    Returns:
        List of dictionaries containing hand gesture information
    """
    # Detect hands with MediaPipe
    results = detect_hands(image)
    
    # No hands detected
    if results.multi_hand_landmarks is None:
        return []
    
    # Process detected hands
    hand_detection = []
    for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
        # Extract landmark coordinates
        landmark_list = calc_landmark_list(image, hand_landmarks)
        
        # Calculate bounding box
        bounding_box = calc_bounding_box(landmark_list)
        
        # Process landmarks for classification
        processed_landmarks = pre_process_landmark(landmark_list)
        
        # Classify hand gesture
        gesture_id = keypoint_classifier(processed_landmarks)
        gesture = keypoint_classifier_labels[gesture_id]
        
        # Add to results
        hand_detection.append({
            "gesture": gesture,
            "bounding_box": bounding_box
        })
    
    return hand_detection