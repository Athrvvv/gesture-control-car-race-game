import os
import signal
import subprocess
from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)

PROCESS_FILE = "prototype1_process.txt"

# MongoDB connection
client = MongoClient("mongodb+srv://Boomer:Boomer2004@cluster0.yp7ed.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client.gesture_controlled_car_racing_game
collection = db.gesture_mapping

# Function to stop any existing process
def stop_existing_process():
    if os.path.exists(PROCESS_FILE):
        try:
            with open(PROCESS_FILE, "r") as f:
                pid = f.read().strip()
            if pid:
                os.kill(int(pid), signal.SIGTERM)
                print(f"Stopped existing process: {pid}")
        except (ProcessLookupError, ValueError) as e:
            print(f"Error stopping process: {e}")
        finally:
            os.remove(PROCESS_FILE)

@app.route("/")
def index():
    gesture_mappings = collection.find_one({}, {"_id": 0}) or {}
    return render_template("index.html", gesture_mappings=gesture_mappings)

@app.route("/update_mappings", methods=["POST"])
def update_mappings():
    try:
        data = request.json
        if data:
            collection.update_one({}, {"$set": data}, upsert=True)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/run_prototype", methods=["POST"])
def run_prototype():
    try:
        stop_existing_process()
        process = subprocess.Popen(["python", "prototype1.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with open(PROCESS_FILE, "w") as f:
            f.write(str(process.pid))
        return jsonify({"status": "running"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/stop_prototype", methods=["POST"])
def stop_prototype():
    try:
        stop_existing_process()
        return jsonify({"status": "stopped"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
