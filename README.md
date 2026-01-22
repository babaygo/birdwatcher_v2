The version 2 of BirdWatcher

A camera trap, who detect by IA with YOLO v8 model and record a video with a high resolution (1080p and 30fps) of the bird. The interface allow to download, delete and visiualize the videos. 
Also check battery and system health in real time. The settings allow to setup videos parameters. 

Components : 
- Raspberry pi zero 2 WH (OS Raspberry Pi Lite 64 bits, Debian Trixie)
- Raspberry Pi Camera Module 3, 12MP high resolution, Auto-Focus, IMX708, 120° FOV and Night Vision (No IR)
- Uninterruptible Power Supply UPS HAT For Raspberry Pi Zero, Stable 5V Power Output + 1000 mA/h battery
- Raspberry Pi Zero V1.3 Camera Cable 15cm
- Raspberry Pi Class A2 SD Card, 32GB
- Capteur PIR HC-SR501 (Movements detector)

Installation :

1. Clone the repository:
```bash
git clone https://github.com/babaygo/birdwatcher_v2.git
cd birdwatcher_v2
```

2. Create a virtual environment with system packages:
```bash
python3 -m venv env --system-site-packages
source env/bin/activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Download the YOLOv8 model:
```bash
# Download yolov8n.onnx and place it in the project root directory
```

5. Run the application:
```bash
# For the Flask web interface:
python3 app.py

# For the detection service:
python3 detect_capture.py
```
