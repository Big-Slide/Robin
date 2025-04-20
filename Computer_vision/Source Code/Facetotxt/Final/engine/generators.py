import csv
import itertools
import cv2
import numpy as np
import mediapipe as mp
from keras.models import load_model
from keypoint_classifier import KeyPointClassifier
import os


# =================== Load Gender Classification Model ===================
if os.environ.get("MODE", "dev") == "prod":
    models_dir = "/approot/models"
else:
    models_dir = "../../../../Models/FaceToTxt"
genderModelPath = f'{models_dir}/genderModel_VGG16.hdf5'
genderClassifier = load_model(genderModelPath, compile=False)
genderTargetSize = genderClassifier.input_shape[1:3]

genders = {
    0: {"label": "Female", "color": (245, 215, 130)},
    1: {"label": "Male", "color": (148, 181, 192)},
}

# =================== Load Emotion Classification Model ===================
keypoint_classifier = KeyPointClassifier()
with open(f'{models_dir}/keypoint_classifier/keypoint_classifier_label.csv', encoding='utf-8-sig') as f:
    keypoint_classifier_labels = [row[0] for row in csv.reader(f)]

# =================== Load Face Detection Model (DNN) ===================
modelFile = f'{models_dir}/res10_300x300_ssd_iter_140000.caffemodel'
configFile = f'{models_dir}/deploy.prototxt'
faceNet = cv2.dnn.readNetFromCaffe(configFile, modelFile)

# =================== Initialize Mediapipe for Facial Landmarks ===================
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=5, refine_landmarks=True, min_detection_confidence=0.5, min_tracking_confidence=0.5
)

# =================== Helper Functions ===================
def detect_faces(frame):
    """Detect faces using OpenCV DNN and return bounding boxes."""
    height, width = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 117.0, 123.0))
    faceNet.setInput(blob)
    detections = faceNet.forward()
    faces = []

    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > 0.5:
            box = detections[0, 0, i, 3:7] * np.array([width, height, width, height])
            x, y, x1, y1 = box.astype("int")
            faces.append((x, y, x1, y1))

    return faces


def classify_gender(face):
    """Predict gender using the VGG16-based model."""
    try:
        resized = cv2.resize(face, genderTargetSize).astype("float32") / 255.0
        reshaped = np.reshape(resized, (1, *genderTargetSize, 3))
        prediction = genderClassifier.predict(reshaped)
        gender_label = np.argmax(prediction)
        return genders[gender_label]["label"], genders[gender_label]["color"]
    except:
        return "Unknown", (255, 255, 255)


def extract_facial_landmarks(landmarks, image_shape):
    """Extract and normalize facial landmarks from Mediapipe."""
    image_width, image_height = image_shape[1], image_shape[0]
    landmark_list = []

    for lm in landmarks.landmark:
        x, y = int(lm.x * image_width), int(lm.y * image_height)
        landmark_list.append([x, y])

    # Normalize landmarks relative to the first landmark
    base_x, base_y = landmark_list[0]
    for i in range(len(landmark_list)):
        landmark_list[i][0] -= base_x
        landmark_list[i][1] -= base_y

    # Flatten list for model input
    flattened = list(itertools.chain.from_iterable(landmark_list))

    # Normalize values
    max_value = max(map(abs, flattened)) if max(map(abs, flattened)) > 0 else 1
    normalized = [v / max_value for v in flattened]

    return normalized


def classify_emotion(landmarks, image_shape):
    """Predict facial emotion using the KeyPointClassifier."""
    processed_landmarks = extract_facial_landmarks(landmarks, image_shape)
    emotion_id = keypoint_classifier(processed_landmarks)
    return keypoint_classifier_labels[emotion_id]


