# app.py - Production Ready
from flask import Flask, request, jsonify
import cv2
import numpy as np
import base64
import os
from io import BytesIO
from PIL import Image
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# 🔥 FIRESTORE ADMIN SDK (bypasses rules)
if not firebase_admin._apps:
    # REPLACE with your actual JSON filename
    cred = credentials.Certificate('./asphaleia-project-test-firebase-adminsdk-fbsvc-9e79127123.json')  # Upload file to Vercel
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Model paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
recognizer_path = os.path.join(BASE_DIR, "recognizer.yml")
cascade_path = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")

# Load models
if not os.path.exists(recognizer_path):
    print(f"🚨 ERROR: {recognizer_path} missing!")
else:
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(recognizer_path)
    print("✅ Model loaded!")

if not os.path.exists(cascade_path):
    print(f"🚨 ERROR: {cascade_path} missing!")
    face_cascade = None
else:
    face_cascade = cv2.CascadeClassifier(cascade_path)

label_map = {0: "G2G1g7oykpeDbJ8G1Dpf4t6IMF63"}

def decode_image(image_data):
    if "," in image_data:
        image_data = image_data.split(",")[1]
    image_bytes = base64.b64decode(image_data)
    img = Image.open(BytesIO(image_bytes)).convert("L")
    return np.array(img, dtype="uint8")

def detect_face(gray):
    if face_cascade is None:
        return None
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
    if len(faces) == 0:
        return None
    x, y, w, h = faces[0]
    return gray[y:y + h, x:x + w]

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route("/", methods=["OPTIONS"])
def preflight():
    return "", 200

@app.route("/api/verify-face", methods=["POST"])
def verify_face():
    data = request.get_json(force=True)
    uid = data.get("uid")
    image_data = data.get("image")

    if not image_data:
        return jsonify({"verified": False, "message": "No image received"}), 400

    gray = decode_image(image_data)
    if gray is None or gray.size == 0:
        return jsonify({"verified": False, "message": "Bad image"}), 400

    face = detect_face(gray)
    if face is None:
        return jsonify({"verified": False, "message": "No face detected"}), 400

    face = cv2.resize(face, (200, 200))
    label, confidence = recognizer.predict(face)

    matched_uid = label_map.get(label)
    threshold = 80
    verified = matched_uid == uid and confidence < threshold

    # 🔥 UPDATE FIRESTORE (Admin SDK bypasses rules)
    try:
        doc_ref = db.collection('verifications').document(uid)
        doc_ref.update({
            'faceVerified': verified,
            'confidence': float(confidence),
            'timestamp': firestore.SERVER_TIMESTAMP,
            'status': 'both' if verified else 'face_fail'
        })
        print(f"✅ Firestore updated for {uid}: {verified}")
    except Exception as e:
        print(f"⚠️ Firestore update failed: {e}")

    return jsonify({
        "verified": verified,
        "label": label,
        "confidence": confidence,
        "message": "Face verified" if verified else "Face not recognized"
    })

if __name__ == "__main__":
    app.run(debug=True)