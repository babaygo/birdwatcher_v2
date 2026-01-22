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
git clone
cd birdwatcher_v2
python3 venv env --system-site-packages
pip install -r requirements. txt
download yolov8n.onnx
