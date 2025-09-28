from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from contextlib import contextmanager
from threading import RLock
import random
import subprocess
import requests
import os
import time
import json
from pathlib import Path
import logging
import psycopg2

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)
lock = RLock()

# Database Configuration
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError("No DATABASE_URL environment variable found")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_SIZE'] = 10
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 50
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 30  # seconds
app.config['SQLALCHEMY_POOL_RECYCLE'] = 1800  # 30 minutes
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_on_connection_error(max_retries=3, backoff_factor=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except psycopg2.OperationalError as e:
                    if "connection refused" in str(e).lower() or "server running" in str(e).lower():
                        if attempt < max_retries - 1:
                            wait_time = backoff_factor * (2 ** attempt)
                            logger.warning(f"Connection error, retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                        else:
                            raise e
                    else:
                        raise e
        return wrapper
    return decorator

@retry_on_connection_error()
def process_batch(batch):
    # Check existing keywords in batch
    existing_keywords = set(k.keyword for k in
        Keyword.query.filter(Keyword.keyword.in_(batch)).all())

    # Prepare new keywords
    new_records = []
    for keyword_text in batch:
        if keyword_text not in existing_keywords:
            new_records.append(Keyword(keyword=keyword_text))

    # Bulk insert new keywords
    if new_records:
        db.session.bulk_save_objects(new_records)
        db.session.commit()

    return len([k for k in batch if k not in existing_keywords]), len([k for k in batch if k in existing_keywords])

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/add_keywords", methods=["POST"])
def add_keywords():
    new_keywords = request.form.get("keywords", "").strip()
    if not new_keywords:
        return jsonify({"status": "error", "message": "No keywords provided"}), 400

    # Split keywords by newline and filter out empty lines
    keyword_list = [k.strip() for k in new_keywords.split('\n') if k.strip()]

    success_count = 0
    duplicate_count = 0
    batch_size = 10  # Reduced batch size to avoid overwhelming connections

    try:
        # Process keywords in batches
        for i in range(0, len(keyword_list), batch_size):
            batch = keyword_list[i:i + batch_size]
            s, d = process_batch(batch)
            success_count += s
            duplicate_count += d

        # Reload keywords after all batches are processed
        load_keywords()

        message = f"Added {success_count} keywords successfully"
        if duplicate_count > 0:
            message += f" ({duplicate_count} duplicates skipped)"
        return jsonify({"status": "success", "message": message})

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": f"Error adding keywords: {str(e)}"
        }), 500

    return jsonify({"status": "error", "message": "No keywords provided"}), 400

@app.route("/refresh", methods=["POST"])
def refresh():
    try:
        with lock:  # Add lock to prevent race conditions
            # First sync the counts
            sync_called_counts_with_db()
            # Then run refresh script
            subprocess.run(["python", "refresh_keywords.py"], check=True)
            # Finally reload keywords
            load_keywords()
            return jsonify({
                "status": "success", 
                "message": "Refresh completed successfully"
            })
    except subprocess.CalledProcessError:
        return jsonify({
            "status": "error", 
            "message": "Error running refresh script"
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error during refresh: {str(e)}"
        }), 500

@app.route("/reload_keywords", methods=["POST"])
def reload_keywords():
    try:
        with lock:
            # First sync the counts
            sync_called_counts_with_db()
            # Then reload keywords
            load_keywords()
            return jsonify({
                "status": "success",
                "message": "Keywords reloaded successfully"
            })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@contextmanager
def timeout_lock(lock, timeout=5):
    start_time = time.time()
    while True:
        if lock.acquire(blocking=False):
            try:
                yield
            finally:
                lock.release()
            return
        if time.time() - start_time > timeout:
            raise TimeoutError("Failed to acquire lock within timeout")
        time.sleep(0.1)

@app.route("/keyword", methods=["GET"])
def get_random_keyword():
    try:
        with timeout_lock(lock, timeout=5):
            if not keywords:
                return jsonify({"keyword": None, "message": "No keywords left"}), 404
                
            index = random.randint(0, len(keywords) - 1)
            keyword_text = keywords.pop(index)
            
            # Use file-based counting instead of database
            count = increment_keyword_count(keyword_text)
            
            # Immediately sync if count reaches deletion threshold
            if count >= 5:
                sync_called_counts_with_db()
                
            return jsonify({
                "keyword": keyword_text,
                "count": count,
                "deleted": count >= 5
            })
                
    except TimeoutError:
        # Put keyword back if we had timeout
        if 'keyword_text' in locals():
            keywords.append(keyword_text)
        return jsonify({"error": "Request timed out"}), 504
    except Exception as e:
        # Put keyword back if we had an error
        if 'keyword_text' in locals():
            keywords.append(keyword_text)
        return jsonify({"error": str(e)}), 500


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

@app.route('/get_keywords')
def get_keywords():
    try:
        keywords = [k.keyword for k in Keyword.query.all()]
        total_count = len(keywords)
        return jsonify({
            'keywords': keywords,
            'total_count': total_count
        })
    except Exception as e:
        return jsonify({
            'keywords': [], 
            'total_count': 0, 
            'error': str(e)
        }), 500

@app.route('/get_keywords_with_counts')
def get_keywords_with_counts():
    try:
        keywords_with_counts = [
            {
                'keyword': k.keyword,
                'count': k.called_count
            } 
            for k in Keyword.query.all()
        ]
        return jsonify({'keywords': keywords_with_counts})
    except Exception as e:
        return jsonify({'keywords': [], 'error': str(e)}), 500

@app.route("/keywords")
def keywords_page():
    return render_template("keywords.html")

CALLED_COUNTS_FILE = "keywords_called.txt"

def load_called_counts():
    try:
        if Path(CALLED_COUNTS_FILE).exists():
            with open(CALLED_COUNTS_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        return {}
    return {}

def save_called_counts(counts):
    with open(CALLED_COUNTS_FILE, 'w') as f:
        json.dump(counts, f)

def increment_keyword_count(keyword):
    counts = load_called_counts()
    counts[keyword] = counts.get(keyword, 0) + 1
    save_called_counts(counts)
    return counts[keyword]

def sync_called_counts_with_db():
    counts = load_called_counts()
    to_delete = []
    deleted_count = 0
    
    logger.info(f"Starting sync with counts from file: {counts}")
    
    try:
        for keyword_text, count in counts.items():
            keyword = Keyword.query.filter_by(keyword=keyword_text).first()
            if keyword:
                if count >= 1:
                    logger.info(f"Marking for deletion: {keyword_text} with count {count}")
                    db.session.delete(keyword)
                    to_delete.append(keyword_text)
                    deleted_count += 1
                else:
                    keyword.called_count = count
        
        db.session.commit()
        logger.info(f"Deleted {deleted_count} keywords from database")
        
        # Clean up the keywords list
        removed_from_list = 0
        for keyword in to_delete:
            if keyword in keywords:
                logger.info(f"Removing {keyword} from keywords list")
                keywords.remove(keyword)
                removed_from_list += 1
        logger.info(f"Removed {removed_from_list} keywords from memory list")
            
        # Clean up the counts file
        old_count = len(counts)
        new_counts = {k: v for k, v in counts.items() if v < 5}
        save_called_counts(new_counts)
        logger.info(f"Cleaned counts file: removed {old_count - len(new_counts)} entries")
        logger.info(f"Final counts in file: {new_counts}")
        
    except Exception as e:
        logger.error(f"Error in sync: {str(e)}")
        db.session.rollback()
        raise e


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)