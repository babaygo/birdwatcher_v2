import os
import shutil
import locale
import time
import json
from datetime import datetime
from power import get_battery_datas
from flask import (
    Flask,
    render_template,
    send_from_directory,
    request,
    redirect,
    url_for,
)

locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")

app = Flask(__name__)

VIDEO_DIR = os.path.join(os.path.dirname(__file__), "videos")
DEFAULT_CLEANUP_DAYS = 7
DEFAULT_TIMECLIP = 60
DEFAULT_CONFIG = {"cleanup_days": DEFAULT_CLEANUP_DAYS, "time_clip": DEFAULT_TIMECLIP}
CONFIG_FILE = "config.json"

os.makedirs(VIDEO_DIR, exist_ok=True)


def get_video_count_today():
    if not os.path.exists(VIDEO_DIR):
        return 0

    today_str = datetime.now().strftime("%Y%m%d")

    count = len(
        [
            f
            for f in os.listdir(VIDEO_DIR)
            if f.startswith(f"cap_{today_str}") and f.endswith(".mp4")
        ]
    )
    return count


def get_disk_info():
    total, used, free = shutil.disk_usage("/")

    percent = round((used / total) * 100, 1)

    used_gb = round(used / (2**30), 1)
    total_gb = round(total / (2**30), 1)

    return {"percent": percent, "used_gb": used_gb, "total_gb": total_gb}


def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = float(f.read()) / 1000.0
            return round(temp, 1)
    except Exception as e:
        print(f"Erreur get temp CPU : {e}")
        return 0.0


def get_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Erreur ouverture config.json : {e}")
        return DEFAULT_CONFIG


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)


def auto_cleanup_files():
    config = get_config()
    days = config.get("cleanup_days", DEFAULT_CLEANUP_DAYS)

    if days <= 0:
        return

    now = time.time()
    cutoff = now - (days * 86400)

    if os.path.exists(VIDEO_DIR):
        for filename in os.listdir(VIDEO_DIR):
            if filename.endswith(".mp4"):
                file_path = os.path.join(VIDEO_DIR, filename)
                if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff:
                    os.remove(file_path)


@app.route("/")
def index():
    battery_datas = get_battery_datas()
    temp = get_cpu_temp()
    disk = get_disk_info()

    return render_template("index.html", battery=battery_datas, temp=temp, disk=disk)


@app.route("/video/view/<filename>")
def view_video(filename):
    return send_from_directory(VIDEO_DIR, filename)


@app.route("/video/download/<filename>")
def download_video(filename):
    return send_from_directory(VIDEO_DIR, filename, as_attachment=True)


@app.route("/video/delete/<filename>")
def delete_video(filename):
    file_path = os.path.join(VIDEO_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect(url_for("list_videos"))


@app.route("/video/delete-all")
def delete_all():
    video_dir = os.path.join(os.path.dirname(__file__), "videos")
    try:
        files = os.listdir(video_dir)
        for f in files:
            if f.endswith(".mp4"):
                os.remove(os.path.join(video_dir, f))
    except Exception as e:
        print(f"Erreur suppression : {e}")

    return redirect(url_for("list_videos"))


@app.route("/video/delete-days", methods=["POST"])
def delete_selected_days():
    selected_days = request.form.getlist("days")
    video_dir = os.path.join(os.path.dirname(__file__), "videos")

    for day_id in selected_days:
        for f in os.listdir(video_dir):
            if f.startswith(day_id) and f.endswith(".mp4"):
                os.remove(os.path.join(video_dir, f))

    return redirect(url_for("list_videos"))


@app.route("/videos")
def list_videos():
    video_dir = os.path.join(os.path.dirname(__file__), "videos")
    all_files = [f for f in os.listdir(video_dir) if f.endswith(".mp4")]

    grouped_videos = {}
    for f in all_files:
        try:
            day_id = f.split("_")[0]
            date_obj = datetime.strptime(day_id, "%Y%m%d")
            date_readable = date_obj.strftime("%d %B %Y")

            if day_id not in grouped_videos:
                grouped_videos[day_id] = {"label": date_readable, "files": []}
            grouped_videos[day_id]["files"].append(f)
        except Exception as e:
            print(f"Erreur groupements des vidéos par jour : {e}")
            continue

    sorted_day_ids = sorted(grouped_videos.keys(), reverse=True)
    return render_template(
        "videos.html", grouped_videos=grouped_videos, sorted_day_ids=sorted_day_ids
    )


@app.route("/api/config/cleanup", methods=["POST"])
def set_cleanup_config():
    try:
        data = request.get_json()
        if not data:
            return {"status": "error", "message": "No data received"}, 400

        config = get_config()
        days = int(data.get("cleanup_days", DEFAULT_CLEANUP_DAYS))
        config["cleanup_days"] = max(1, min(99, days))
        print("La config ", config)

        save_config(config)
        return {"status": "success", "cleanup_days": config["cleanup_days"]}
    except Exception as e:
        return {"status": "error", "message": f"Erreur update cleanup_days : {e}"}, 500


@app.route("/api/config/timeclip", methods=["POST"])
def set_timeclip_config():
    try:
        data = request.get_json()
        if not data:
            return {"status": "error", "message": "No data received"}, 400

        config = get_config()
        seconds = int(data.get("time_clip", DEFAULT_TIMECLIP))
        config["time_clip"] = max(1, min(120, seconds))
        print("La config ", config)

        save_config(config)
        return {"status": "success", "time_clip": config["time_clip"]}
    except Exception as e:
        return {"status": "error", "message": f"Erreur update time_clip : {e}"}, 500


@app.route("/api/system_stats")
def system_stats():
    return {
        "battery": get_battery_datas(),
        "temp": get_cpu_temp(),
        "disk": get_disk_info(),
        "video_count": get_video_count_today()
    }


@app.route("/settings")
def settings():
    config = get_config()
    battery_datas = get_battery_datas()
    temp = get_cpu_temp()
    disk = get_disk_info()

    return render_template(
        "settings.html", config=config, battery=battery_datas, temp=temp, disk=disk
    )


@app.route("/videos/<filename>")
def serve_video(filename):
    return send_from_directory(VIDEO_DIR, filename)


if __name__ == "__main__":
    auto_cleanup_files()
    app.run(host="0.0.0.0", port=5000, debug=True)
