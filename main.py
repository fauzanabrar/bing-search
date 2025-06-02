from flask import Flask, jsonify
from flask_cors import CORS
import threading
import random

app = Flask(__name__)
CORS(app)
lock = threading.Lock()

# Load keywords into memory from file
with open("keywords.txt", "r") as f:
    keywords = [line.strip() for line in f if line.strip()]

@app.route("/keyword", methods=["GET"])
def get_random_keyword():
    with lock:
        if keywords:
            index = random.randint(0, len(keywords) - 1)
            keyword = keywords.pop(index)
            return jsonify({"keyword": keyword})
        else:
            return jsonify({"keyword": None, "message": "No keywords left"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)