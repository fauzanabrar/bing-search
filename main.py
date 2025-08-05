from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import threading
import random
import subprocess

app = Flask(__name__)
CORS(app)
lock = threading.Lock()

# Load keywords into memory from file
def load_keywords():
    global keywords
    with open("keywords.txt", "r") as f:
        keywords = [line.strip() for line in f if line.strip()]

load_keywords()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/add_keywords", methods=["POST"])
def add_keywords():
    new_keywords = request.form.get("keywords", "").strip()
    if new_keywords:
        with open("keywords.txt", "a") as f:
            f.write("\n" + new_keywords)
        load_keywords()
        return jsonify({"status": "success", "message": "Keywords added successfully"})
    return jsonify({"status": "error", "message": "No keywords provided"}), 400

@app.route("/refresh", methods=["POST"])
def refresh():
    try:
        subprocess.run(["python", "refresh_keywords.py"], check=True)
        load_keywords()
        return jsonify({"status": "success", "message": "Refresh completed successfully"})
    except subprocess.CalledProcessError:
        return jsonify({"status": "error", "message": "Error running refresh script"}), 500

@app.route("/reload_keywords", methods=["POST"])
def reload_keywords():
    with lock:
        try:
            load_keywords()
            return jsonify({"status": "success", "message": "Keywords reloaded successfully"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/keyword", methods=["GET"])
def get_random_keyword():
    with lock:
        if keywords:
            index = random.randint(0, len(keywords) - 1)
            keyword = keywords.pop(index)

            # Read current counts
            counts = {}
            try:
                with open("keywords_called.txt", "r") as f:
                    for line in f:
                        if ":" in line:
                            k, v = line.strip().split(":", 1)
                            counts[k] = int(v)
            except FileNotFoundError:
                pass

            # Update count
            counts[keyword] = counts.get(keyword, 0) + 1

            # Write back counts
            with open("keywords_called.txt", "w") as f:
                for k, v in counts.items():
                    f.write(f"{k}:{v}\n")

            return jsonify({"keyword": keyword})
        else:
            return jsonify({"keyword": None, "message": "No keywords left"}), 404


########## Search Functionality ##########
@app.route("/search")
def search():
    keyword = request.args.get('q', '')
    return render_template("search.html", keyword=keyword)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)