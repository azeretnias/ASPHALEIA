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

# Globals - safe defaults
recognizer = None
face_cascade = None
db = None
label_map = {0: "G2G1g7oykpeDbJ8G1Dpf4t6IMF63"}

# Firebase (graceful)
cred_path = os.environ.get('FIREBASE_JSON_PATH', './asphaleia-project-test-firebase-adminsdk-fbsvc-9e79127123.json')
try:
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
except Exception as e:
    print(f"Firebase failed: {e}")

# Models (safe load)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
recognizer_path = os.path.join(BASE_DIR, "recognizer.yml")
cascade_path = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")

if os.path.exists(recognizer_path):
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(recognizer_path)
if os.path.exists(cascade_path):
    face_cascade = cv2.CascadeClassifier(cascade_path)

# ... decode_image, detect_face unchanged ...

@app.route("/api/verify-face", methods=["POST"])
def verify_face():
    data = request.get_json(force=True)
    uid = data.get("uid")
    image_data = data.get("image")

    if not image_data:
        return jsonify({"verified": False, "message": "No image"}), 400

    gray = decode_image(image_data)
    if gray is None or gray.size == 0:
        return jsonify({"verified": False, "message": "Bad image"}), 400

    if face_cascade is None:
        return jsonify({"verified": False, "message": "No face detector"}), 503

    face = detect_face(gray)
    if face is None:
        return jsonify({"verified": False, "message": "No face"}), 400

    if recognizer is None:
        return jsonify({"verified": False, "message": "No model"}), 503

    face = cv2.resize(face, (200, 200))
    label, confidence = recognizer.predict(face)

    matched_uid = label_map.get(label)
    verified = matched_uid == uid and confidence < 80

    # Firestore (non-blocking)
    if db:
        try:
            doc_ref = db.collection('verifications').document(uid)
            doc_ref.update({
                'faceVerified': verified,
                'confidence': float(confidence),
                'timestamp': firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            print(f"Firestore error: {e}")

    return jsonify({
        "verified": verified,
        "confidence": float(confidence),
        "message": "Verified" if verified else "No match"
    })

# CORS unchanged...

# NO if __name__ !!!