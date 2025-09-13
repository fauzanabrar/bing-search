from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import threading
import random
import subprocess
import requests
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)
lock = threading.Lock()

# Database Configuration
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError("No DATABASE_URL environment variable found")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(200), unique=True, nullable=False)
    called_count = db.Column(db.Integer, default=0)

# Initialize keywords list
keywords = []

# Modified load_keywords function to use database
def load_keywords():
    global keywords
    with app.app_context():
        keywords = [k.keyword for k in Keyword.query.all()]

# Create tables and load initial keywords
with app.app_context():
    db.create_all()
    load_keywords()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/add_keywords", methods=["POST"])
def add_keywords():
    new_keywords = request.form.get("keywords", "").strip()
    if new_keywords:
        # Check if keyword already exists
        if Keyword.query.filter_by(keyword=new_keywords).first():
            return jsonify({"status": "error", "message": "Keyword already exists"}), 400
        
        # Add new keyword to database
        keyword = Keyword(keyword=new_keywords)
        db.session.add(keyword)
        try:
            db.session.commit()
            load_keywords()
            return jsonify({"status": "success", "message": "Keywords added successfully"})
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)}), 500
            
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
            keyword_text = keywords.pop(index)
            
            # Update count in database
            keyword = Keyword.query.filter_by(keyword=keyword_text).first()
            if keyword:
                keyword.called_count += 1
                db.session.commit()

            return jsonify({"keyword": keyword_text})
        else:
            return jsonify({"keyword": None, "message": "No keywords left"}), 404


########## Search Functionality ##########
@app.route("/search")
def search():
    keyword = request.args.get('q', '')
    return render_template("search.html", keyword=keyword)

@app.route("/proxy_search")
def proxy_search():
    keyword = request.args.get('q', '')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(f'https://bing.com/',
                          headers=headers)
    
    return response.text


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)