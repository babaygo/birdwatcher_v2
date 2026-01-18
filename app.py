import os
import shutil
import locale
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
os.makedirs(VIDEO_DIR, exist_ok=True)


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
    except:
        return 0.0


@app.route("/")
def index():
    battery_datas = get_battery_datas()
    return render_template("index.html", battery=battery_datas)


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
    selected_days = request.form.getlist("days")  # Récupère les IDs cochés
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
        except:
            continue

    sorted_day_ids = sorted(grouped_videos.keys(), reverse=True)
    return render_template(
        "videos.html", grouped_videos=grouped_videos, sorted_day_ids=sorted_day_ids
    )


@app.route("/settings")
def settings():
    battery_datas = get_battery_datas()
    temp = get_cpu_temp()
    disk = get_disk_info()

    return render_template("settings.html", battery=battery_datas, temp=temp, disk=disk)


@app.route("/videos/<filename>")
def serve_video(filename):
    return send_from_directory(VIDEO_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
