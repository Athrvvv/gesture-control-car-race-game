import os
import signal
import cv2
import mediapipe as mp
import keyboard
import numpy as np
from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)

# MongoDB connection
client = MongoClient("mongodb+srv://Boomer:Boomer2004@cluster0.yp7ed.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client.gesture_controlled_car_racing_game
collection = db.gesture_mapping

# MediaPipe Hand Tracking
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.7)

# Active keys tracker
active_keys = {"right": None, "left": None}

def load_gesture_mappings():
    document = collection.find_one()
    if document:
        document.pop("_id", None)
        return document
    return {}

GESTURE_KEY_MAPPING = load_gesture_mappings()

def recognize_gesture(hand_landmarks):
    landmarks = hand_landmarks.landmark
    fingers = []
    tips = [8, 12, 16, 20]
    for tip in tips:
        fingers.append(1 if landmarks[tip].y < landmarks[tip - 2].y else 0)

    wrist_x = landmarks[0].x
    middle_base_x = landmarks[9].x
    tilt_threshold = 0.05

    if fingers == [1, 1, 0, 0]:
        return "Victory"
    elif fingers == [1, 1, 1, 0]:
        return "Three Fingers Up"
    elif fingers == [1, 1, 1, 1]:
        if wrist_x < middle_base_x - tilt_threshold:
            return "Open Palm Tilted Left"
        elif wrist_x > middle_base_x + tilt_threshold:
            return "Open Palm Tilted Right"
        return "Open Palm"
    elif fingers == [0, 0, 0, 0]:
        return "Fist"

    return None

@app.route("/")
def index():
    gesture_mappings = collection.find_one({}, {"_id": 0}) or {}
    return render_template("index.html", gesture_mappings=gesture_mappings)

@app.route("/update_mappings", methods=["POST"])
def update_mappings():
    try:
        data = request.json
        if data:
            collection.update_one({}, {"$set": data}, upsert=True)
        global GESTURE_KEY_MAPPING
        GESTURE_KEY_MAPPING = load_gesture_mappings()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/run_prototype", methods=["POST"])
def run_prototype():
    cap = cv2.VideoCapture(0)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb_frame)

        detected_keys = {"right": None, "left": None}

        if result.multi_hand_landmarks and result.multi_handedness:
            for hand_landmarks, handedness_info in zip(result.multi_hand_landmarks, result.multi_handedness):
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                handedness = "left" if handedness_info.classification[0].label.lower() == "left" else "right"
                gesture = recognize_gesture(hand_landmarks)

                if gesture and gesture in GESTURE_KEY_MAPPING:
                    detected_keys[handedness] = GESTURE_KEY_MAPPING[gesture][handedness]

        for hand in ["right", "left"]:
            detected_key = detected_keys[hand]
            active_key = active_keys[hand]

            if detected_key and detected_key != active_key:
                if active_key:
                    keyboard.release(active_key)
                keyboard.press(detected_key)
                active_keys[hand] = detected_key

            elif not detected_key and active_key:
                keyboard.release(active_key)
                active_keys[hand] = None

        cv2.imshow("Hand Gesture Game Control", frame)

        if cv2.waitKey(10) & 0xFF == 27:  # Press 'ESC' to exit
            break

    for key in active_keys.values():
        if key:
            keyboard.release(key)

    cap.release()
    cv2.destroyAllWindows()
    return jsonify({"status": "running"})

@app.route("/stop_prototype", methods=["POST"])
def stop_prototype():
    return jsonify({"status": "stopped"})

if __name__ == "__main__":
    app.run(debug=True)
