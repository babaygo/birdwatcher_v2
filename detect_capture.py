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

# Variables globales
PIR_PIN = 14
MODEL_PATH = "yolov8n.onnx"
CONFIG_FILE = "config.json"
VIDEO_DIR = "videos"
CONF_THRESHOLD = 0.40
TARGET_CLASSES = [0, 14]  # Personne, Oiseau

# État global de la résolution actuelle
current_res = (1280, 720)

# Initialisation dossiers
os.makedirs(VIDEO_DIR, exist_ok=True)

# Initialisation GPIO PIR
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Initialisation Model Yolov8n
net = cv2.dnn.readNetFromONNX(MODEL_PATH)
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

# Initialisation objet caméra
picam2 = Picamera2()


def get_full_config():
    """Récupère la durée ET la résolution depuis config.json"""
    config = {"duration": 30, "res_video": (1280, 720)}
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                config["duration"] = int(data.get("time_clip", 30))

                res_list = data.get("res_video", [1280, 720])
                if isinstance(res_list, list) and len(res_list) == 2:
                    config["res_video"] = (res_list[0], res_list[1])
    except Exception as e:
        print(f"Erreur lecture config : {e}")
    return config


def setup_camera(width, height):
    """Configure ou Re-configure la caméra avec une nouvelle résolution"""
    global current_res
    config = picam2.create_video_configuration(
        main={"size": (width, height), "format": "YUV420"},
        lores={"size": (640, 480), "format": "YUV420"},
    )
    picam2.configure(config)
    picam2.start()

    picam2.set_controls({"FrameRate": 25, "AfMode": 2})

    current_res = (width, height)


initial_conf = get_full_config()
setup_camera(initial_conf["res_video"][0], initial_conf["res_video"][1])


def is_bird_detected():
    """Détection sur flux LORES (léger)"""
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
            if np.max(scores) > CONF_THRESHOLD:
                if np.argmax(scores) in TARGET_CLASSES:
                    return True
        return False
    except Exception as e:
        print(f"Erreur IA : {e}")
        time.sleep(1)
        return False


def recording(duration):
    """Enregistrement"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    h264_path = os.path.join(VIDEO_DIR, f"{timestamp}.h264")

    print(f"REC ({current_res[0]}x{current_res[1]} - {duration}s)...")

    if current_res[0] >= 1920:
        bitrate = 12000000
    elif current_res[0] >= 1280:
        bitrate = 8000000
    else:
        bitrate = 4000000

    encoder = H264Encoder(bitrate=bitrate)
    picam2.start_recording(encoder, h264_path)
    time.sleep(duration)
    picam2.stop_recording()
    print("Fin REC")

    process_video(h264_path)


def process_video(raw_h264):
    """Conversion MP4"""
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
                live_config = get_full_config()
                recording(live_config["duration"])

                print("Reset Pipeline (Vérification config)...")

                picam2.stop()
                time.sleep(1.5)

                next_config = get_full_config()
                next_res = next_config["res_video"]

                if next_res != current_res:
                    setup_camera(next_res[0], next_res[1])
                else:
                    picam2.start()
                    picam2.set_controls({"FrameRate": 25, "AfMode": 2})

                time.sleep(3)
            else:
                time.sleep(0.5)

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nArrêt...")
finally:
    picam2.stop()
    GPIO.cleanup()
