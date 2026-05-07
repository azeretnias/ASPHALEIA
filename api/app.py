from flask import Flask, request, jsonify
from flask_cors import CORS 
import cv2
import numpy as np
import base64
import os
from io import BytesIO
from PIL import Image
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
CORS(app)
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
# Models (safe load with contrib check)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
recognizer_path = os.path.join(BASE_DIR, "recognizer.yml")
cascade_path = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")

try:
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    if os.path.exists(recognizer_path):
        recognizer.read(recognizer_path)
        print("Recognizer loaded")
except AttributeError:
    recognizer = None
    print("cv2.face missing - using contrib-python-headless")

try:
    face_cascade = cv2.CascadeClassifier(cascade_path)
    print("Cascade loaded")
except:
    face_cascade = None
    print("Cascade failed")

# ... decode_image, detect_face unchanged ...

def decode_image(image_data):
    """Decode base64 to OpenCV grayscale. Returns None on failure."""
    try:
        # Extract base64 (remove 'data:image/...;base64,' prefix if present)
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode bytes
        img_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        
        # PIL for robust decode, then OpenCV grayscale
        pil_img = Image.open(BytesIO(img_bytes)).convert('RGB')
        gray = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2GRAY)
        
        # Validate size (tiny images fail detection)
        if gray.size < 100*100:
            print("Image too small")
            return None
        return gray
    except Exception as e:
        print(f"Decode error: {e}")
        return None

def detect_face(gray):
    """Detect single frontal face ROI. Returns cropped face or None."""
    try:
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        if len(faces) != 1:
            print(f"Found {len(faces)} faces")
            return None
        
        (x, y, w, h) = faces[0]
        if w < 50 or h < 50:  # Too small
            return None
        
        face_roi = gray[y:y+h, x:x+w]
        return face_roi
    except Exception as e:
        print(f"Detect error: {e}")
        return None

@app.route("/api/verify-face", methods=["POST", "OPTIONS"])
def verify_face():
    if request.method == "OPTIONS":
        return "", 200
    
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

    # Resize with validation (your logic fixed)
    face = cv2.resize(face, (200, 200))
    if face.shape[0] == 0 or face.shape[1] == 0:
        return jsonify({"verified": False, "message": "Invalid face"}), 400
    
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