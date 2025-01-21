import cv2
import mediapipe as mp
import numpy as np
from tensorflow.keras.models import load_model, Sequential
from tensorflow.keras.layers import Dense, Conv2D, MaxPooling2D, Flatten
import matplotlib.pyplot as plt

# Initialize MediaPipe solutions
mp_face_mesh = mp.solutions.face_mesh
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# Load pre-trained emotion detection model
try:
    # Try loading the full model (architecture + weights)
    emotion_model = load_model("c:\\Py code\\Models\\emotion_detection_model.h5")
    print("Emotion model loaded successfully!")
except ValueError as e:
    print(f"Error loading full model: {e}")
    print("Attempting to load weights only...")

    # Define the model architecture (replace with your actual architecture)
    emotion_model = Sequential([
        Conv2D(32, (3, 3), activation='relu', input_shape=(48, 48, 1)),
        MaxPooling2D((2, 2)),
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        Flatten(),
        Dense(128, activation='relu'),
        Dense(7, activation='softmax')  # 7 emotions
    ])

    # Load the weights
    try:
        emotion_model.load_weights("c:\\Py code\\Models\\emotion_detection_model.h5")
        print("Weights loaded successfully!")
    except Exception as e:
        print(f"Error loading weights: {e}")
        exit()
except Exception as e:
    print(f"Error: {e}")
    exit()

emotion_labels = ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']

# Constants
VIDEO_PATH = "c:\\Py code\\sample\\interview.mp4"  # Replace with your video path
OUTPUT_VIDEO_PATH = "c:\\Py code\\outputs\\analyzed_interview.mp4"
FRAME_RATE = 15
VIDEO_DURATION = 20  # 1 minute

# Initialize video capture
cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    print(f"Error: Could not open video file {VIDEO_PATH}")
    exit()

frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(OUTPUT_VIDEO_PATH, fourcc, FRAME_RATE, (frame_width, frame_height))

# Initialize MediaPipe models
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, min_detection_confidence=0.5)
pose = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5)

# Behavior analysis variables
speaking_frames = 0
total_frames = 0
gesture_count = 0
emotion_counts = {emotion: 0 for emotion in emotion_labels}

# Process video frames
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    total_frames += 1

    # Convert frame to RGB for MediaPipe
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Face mesh detection
    face_results = face_mesh.process(rgb_frame)
    if face_results.multi_face_landmarks:
        for face_landmarks in face_results.multi_face_landmarks:
            # Draw face landmarks
            mp_drawing.draw_landmarks(frame, face_landmarks, mp_face_mesh.FACEMESH_CONTOURS)

            # Detect if the person is speaking (mouth movement)
            # Use multiple landmarks for better accuracy
            mouth_top = face_landmarks.landmark[13].y  # Upper lip
            mouth_bottom = face_landmarks.landmark[14].y  # Lower lip
            mouth_left = face_landmarks.landmark[308].x  # Left corner of mouth
            mouth_right = face_landmarks.landmark[61].x  # Right corner of mouth

            # Calculate mouth opening and width
            mouth_open = mouth_bottom - mouth_top
            mouth_width = mouth_right - mouth_left

            # Adjust threshold for mouth opening and width
            if mouth_open > 0.02 and mouth_width > 0.05:  # Adjusted thresholds
                speaking_frames += 1
                cv2.putText(frame, "Speaking", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Extract face ROI dynamically using face landmarks
            x_min = int(min([landmark.x for landmark in face_landmarks.landmark]) * frame_width)
            y_min = int(min([landmark.y for landmark in face_landmarks.landmark]) * frame_height)
            x_max = int(max([landmark.x for landmark in face_landmarks.landmark]) * frame_width)
            y_max = int(max([landmark.y for landmark in face_landmarks.landmark]) * frame_height)

            # Ensure the ROI is within the frame boundaries
            x_min, y_min = max(0, x_min), max(0, y_min)
            x_max, y_max = min(frame_width, x_max), min(frame_height, y_max)

            face_roi = frame[y_min:y_max, x_min:x_max]
            if face_roi.size != 0:  # Ensure the ROI is not empty
                face_roi = cv2.resize(face_roi, (48, 48))
                face_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
                face_roi = np.expand_dims(face_roi, axis=0)
                face_roi = np.expand_dims(face_roi, axis=-1)
                emotion_prediction = emotion_model.predict(face_roi)
                emotion_label = emotion_labels[np.argmax(emotion_prediction)]
                emotion_counts[emotion_label] += 1
                cv2.putText(frame, f"Emotion: {emotion_label}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

    # Pose detection
    pose_results = pose.process(rgb_frame)
    if pose_results.pose_landmarks:
        # Draw pose landmarks
        mp_drawing.draw_landmarks(frame, pose_results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # Detect gestures (e.g., hand raising)
        left_hand = pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST]
        right_hand = pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST]
        if left_hand.y < pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER].y or \
           right_hand.y < pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER].y:
            gesture_count += 1
            cv2.putText(frame, "Hand Raised", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Write frame to output video
    out.write(frame)

    # Display frame
    cv2.imshow("HR Behavior Analysis", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    # Stop after 1 minute
    if total_frames >= FRAME_RATE * VIDEO_DURATION:
        break

# Release resources
cap.release()
out.release()
cv2.destroyAllWindows()

# Behavior analysis results
speaking_percentage = (speaking_frames / total_frames) * 100
print(f"Speaking Percentage: {speaking_percentage:.2f}%")
print(f"Gesture Count: {gesture_count}")
print("Emotion Distribution:")
for emotion, count in emotion_counts.items():
    print(f"{emotion}: {count} frames")

# Plotting the results
plt.figure(figsize=(15, 5))

# Plot 1: Speaking Percentage
plt.subplot(1, 3, 1)
plt.bar(['Speaking'], [speaking_percentage], color='blue')
plt.title('Speaking Percentage')
plt.ylabel('Percentage (%)')
plt.ylim(0, 100)

# Plot 2: Gesture Count
plt.subplot(1, 3, 2)
plt.bar(['Gestures'], [gesture_count], color='green')
plt.title('Gesture Count')
plt.ylabel('Count')

# Plot 3: Emotion Distribution
plt.subplot(1, 3, 3)
plt.bar(emotion_counts.keys(), emotion_counts.values(), color='orange')
plt.title('Emotion Distribution')
plt.ylabel('Frame Count')
plt.xticks(rotation=45)

plt.tight_layout()
plt.show()