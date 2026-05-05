# app.py script.
from flask import Flask, request, jsonify
import cv2
import numpy as np
import base64
import os
from io import BytesIO
from PIL import Image

app = Flask(__name__)

if not os.path.exists("./api/recognizer.yml"):
    print("🚨 ERROR: ./api/recognizer.yml missing!")
    exit(1)
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("./api/recognizer.yml")
print("✅ Model loaded!")
face_cascade = cv2.CascadeClassifier("./api/haarcascade_frontalface_default.xml")

# Update these to match your training labels
label_map = {
    0: "G2G1g7oykpeDbJ8G1Dpf4t6IMF63",
}

def decode_image(image_data):
    if "," in image_data:
        image_data = image_data.split(",")[1]
    image_bytes = base64.b64decode(image_data)
    img = Image.open(BytesIO(image_bytes)).convert("L")
    return np.array(img, dtype="uint8")

def detect_face(gray):
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
    if len(faces) == 0:
        return None
    x, y, w, h = faces[0]
    return gray[y:y + h, x:x + w]


@app.route("/api/verify-face", methods=["POST"])
def verify_face():
    data = request.get_json(force=True)
    uid = data.get("uid")
    image_data = data.get("image")

    if not image_data:
        return jsonify({"verified": False, "message": "No image received"}), 400

    gray = decode_image(image_data)
    if gray is None or gray.size == 0:  # ← MOVED UP HERE
        return jsonify({"verified": False, "message": "Bad image"}), 400

    face = detect_face(gray)  # Now safe
    if face is None:
        return jsonify({"verified": False, "message": "No face detected"})

    face = cv2.resize(face, (200, 200))
    label, confidence = recognizer.predict(face)

    matched_uid = label_map.get(label)
    threshold = 80

    if matched_uid == uid and confidence < threshold:
        return jsonify({
            "verified": True,
            "label": label,
            "confidence": confidence,
            "message": "Face verified"
        })

    return jsonify({
        "verified": False,
        "label": label,
        "confidence": confidence,
        "message": "Face not recognized"
    })

app = app
