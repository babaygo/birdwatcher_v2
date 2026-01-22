import os
import time
import json
import cv2
import numpy as np
import subprocess
import RPi.GPIO as GPIO
from datetime import datetime
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder

# Variables globales de config
PIR_PIN = 14
MODEL_PATH = "yolov8n.onnx"
CONFIG_FILE = "config.json"
VIDEO_DIR = "videos"
CONF_THRESHOLD = 0.40
TARGET_CLASSES = [0, 14]  # Personne, Oiseau

# Initialisation dossiers
os.makedirs(VIDEO_DIR, exist_ok=True)

# Initialisation GPIO PIR
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Initialisation Model Yolov8n
net = cv2.dnn.readNetFromONNX(MODEL_PATH)
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

# Initialisation pi caméra 2
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (1920, 1080), "format": "YUV420", "fps": 25},
    lores={"size": (640, 480), "format": "YUV420", "fps": 25},
)
picam2.configure(config)
picam2.start()
picam2.set_controls({"AfMode": 2})


def get_config():
    """Charge la durée depuis config.json ou 30s par défaut"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return int(data.get("time_clip", 30))
    except Exception as e:
        print(f"Erreur pour récupérer le fichier config.json : {e}")
        pass
    return 30


def is_bird_detected():
    """Détecte si un oiseau est présent en utilisant le flux LORES (léger)"""
    try:
        frame_yuv = picam2.capture_array("lores")

        if frame_yuv is None:
            return False

        frame = cv2.cvtColor(frame_yuv, cv2.COLOR_YUV2BGR_I420)
        blob = cv2.dnn.blobFromImage(
            frame, 1 / 255.0, (640, 640), swapRB=True, crop=False
        )
        net.setInput(blob)
        output = net.forward()

        predictions = np.squeeze(output).T

        for row in predictions:
            scores = row[4:]
            confidence = np.max(scores)
            if confidence > CONF_THRESHOLD:
                class_id = np.argmax(scores)
                if class_id in TARGET_CLASSES:
                    label = "OISEAU" if class_id == 14 else "PERSONNE"
                    print(f"IA : {label} détecté ({confidence:.2f})")
                    return True
        return False
    except Exception as e:
        print(f"Erreur IA : {e}")
        time.sleep(1)
        return False


def recording():
    """Enregistrement optimisé avec bitrate limité"""
    duration = get_config()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    h264_path = os.path.join(VIDEO_DIR, f"{timestamp}.h264")

    print(f"REC ({duration}s)...")

    encoder = H264Encoder(bitrate=12000000)

    picam2.start_recording(encoder, h264_path)
    time.sleep(duration)
    picam2.stop_recording()
    print("Fin REC")

    process_video(h264_path)


def process_video(raw_h264):
    """Convertit en MP4 avec priorité basse pour ne pas bloquer la Pi"""
    final_mp4 = raw_h264.replace(".h264", ".mp4")

    cmd = f"nice -n 19 ionice -c 3 ffmpeg -y -i {raw_h264} -c copy {final_mp4} && rm {raw_h264}"
    subprocess.Popen(
        cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


try:
    print("BirdWatcher Activé !")
    while True:
        if GPIO.input(PIR_PIN) == GPIO.HIGH:
            print("\nMouvement PIR détecté...")

            if is_bird_detected():
                recording()

                print("Reset Pipeline (Anti-Timeout)...")
                picam2.stop()
                time.sleep(1.5)
                picam2.start()
                picam2.set_controls({"AfMode": 2})

                time.sleep(3)
            else:
                time.sleep(0.5)

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nArrêt...")
finally:
    picam2.stop()
    GPIO.cleanup()
