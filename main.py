from flask import Flask, jsonify, render_template, request, Response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from contextlib import contextmanager
from threading import RLock, local
import random
import subprocess
import requests
import os
import time
import json
import gzip
import io
from pathlib import Path
import logging

try:
    import psycopg2
except ImportError:
    psycopg2 = None

# Load environment variables from .env file
load_dotenv()

# Configure logging early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
lock = RLock()

def gzip_response(data_dict):
    json_str = json.dumps(data_dict)
    content = json_str.encode('utf-8')
    
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode='w', compresslevel=6) as f:
        f.write(content)
    
    compressed_content = out.getvalue()
    
    response = Response(compressed_content)
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Length'] = len(compressed_content)
    return response

# Database Configuration
use_database_str = os.getenv('USE_DATABASE', '').lower()
database_url = os.getenv('DATABASE_URL')

if use_database_str == 'true':
    if not database_url:
        raise ValueError("No DATABASE_URL environment variable found but USE_DATABASE is set to True")
    USE_DATABASE = True
elif use_database_str == 'false':
    USE_DATABASE = False
else:
    # Default behavior: use database if DATABASE_URL is present, otherwise use txt file
    USE_DATABASE = bool(database_url)

db = None
class Keyword(object):
    pass

if USE_DATABASE:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_POOL_SIZE'] = 10  # Healthy size for concurrent operations
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = 5  # Allow overflow for concurrent actions
    app.config['SQLALCHEMY_POOL_TIMEOUT'] = 30  # seconds
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 1800  # Recycle after 30 minutes to stay fresh
    db = SQLAlchemy(app, engine_options={"pool_pre_ping": True})

    # Database Models
    class Keyword(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        keyword = db.Column(db.String(200), unique=True, nullable=False)
        called_count = db.Column(db.Integer, default=0)

SETTINGS_FILE = "settings.json"
DEFAULT_SETTINGS = {
    "deletion_threshold": 5,
    "batch_size": 10,
    "lock_timeout": 5
}

def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving settings: {e}")

# Initialize keywords list
keywords = []

def load_keywords():
    global keywords
    if USE_DATABASE:
        with app.app_context():
            results = db.session.query(Keyword.keyword).all()
            keywords = [r[0] for r in results if r[0] is not None]
    else:
        if os.path.exists('keywords.txt'):
            with open('keywords.txt', 'r', encoding='utf-8') as f:
                keywords = [line.strip() for line in f if line.strip()]
        else:
            keywords = []

# Create tables and load initial keywords
with app.app_context():
    if USE_DATABASE:
        db.create_all()
    load_keywords()


def retry_on_connection_error(max_retries=3, backoff_factor=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if psycopg2 and isinstance(e, psycopg2.OperationalError):
                        if ("connection refused" in str(e).lower() or
                            "server running" in str(e).lower() or
                            "max clients" in str(e).lower()):
                            if attempt < max_retries - 1:
                                wait_time = backoff_factor * (2 ** attempt)
                                logger.warning(f"Connection error, retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                                time.sleep(wait_time)
                            else:
                                raise e
                        else:
                            raise e
                    else:
                        raise e
        return wrapper
    return decorator

@retry_on_connection_error()
def process_batch(batch):
    if not USE_DATABASE:
        return 0, 0
    # Check existing keywords in batch
    existing_keywords = set(k.keyword for k in
        Keyword.query.filter(Keyword.keyword.in_(batch)).all())

    # Prepare new keywords
    new_records = []
    for keyword_text in batch:
        if keyword_text not in existing_keywords:
            new_records.append(Keyword(keyword=keyword_text))

    # Insert new keywords letting PostgreSQL auto-generate IDs
    if new_records:
        db.session.add_all(new_records)
        db.session.commit()

    return len([k for k in batch if k not in existing_keywords]), len([k for k in batch if k in existing_keywords])

CALLED_COUNTS_FILE = "keywords_called.txt"

def load_called_counts():
    counts = {}
    try:
        if Path(CALLED_COUNTS_FILE).exists():
            with open(CALLED_COUNTS_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return {}
                # Try loading as JSON first
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # Fallback to key:val lines
                    lines = content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        if ':' in line:
                            parts = line.rsplit(':', 1)
                            if len(parts) == 2 and parts[1].strip().isdigit():
                                counts[parts[0].strip()] = int(parts[1].strip())
    except Exception as e:
        logger.error(f"Error loading called counts: {e}")
        return {}
    return counts

def save_called_counts(counts):
    try:
        with open(CALLED_COUNTS_FILE, 'w', encoding='utf-8') as f:
            for keyword, count in counts.items():
                f.write(f"{keyword}:{count}\n")
    except Exception as e:
        logger.error(f"Error saving called counts: {e}")

def increment_keyword_count(keyword):
    counts = load_called_counts()
    counts[keyword] = counts.get(keyword, 0) + 1
    save_called_counts(counts)
    return counts[keyword]

def sync_called_counts_with_db():
    counts = load_called_counts()
    if not counts:
        return
        
    to_delete = []
    deleted_count = 0
    
    settings = load_settings()
    threshold = settings.get("deletion_threshold", 5)
    
    logger.info(f"Starting sync with counts from file: {counts}")
    
    try:
        # Fetch ALL matching keywords in a SINGLE query to eliminate the N+1 network overhead!
        keyword_list = list(counts.keys())
        db_keywords = Keyword.query.filter(Keyword.keyword.in_(keyword_list)).all()
        db_keywords_map = {k.keyword: k for k in db_keywords}
        
        for keyword_text, count in counts.items():
            keyword = db_keywords_map.get(keyword_text)
            if keyword:
                if count >= threshold:
                    logger.info(f"Marking for deletion: {keyword_text} with count {count}")
                    db.session.delete(keyword)
                    to_delete.append(keyword_text)
                    deleted_count += 1
                else:
                    keyword.called_count = count
        
        db.session.commit()
        logger.info(f"Deleted {deleted_count} keywords from database")
        
        # Clean up the keywords list in memory
        global keywords
        keywords = [kw for kw in keywords if kw not in to_delete]
            
        # Clean up the counts file
        old_count = len(counts)
        new_counts = {k: v for k, v in counts.items() if v < threshold}
        save_called_counts(new_counts)
        logger.info(f"Cleaned counts file: removed {old_count - len(new_counts)} entries")
        logger.info(f"Final counts in file: {new_counts}")
        
    except Exception as e:
        logger.error(f"Error in sync: {str(e)}")
        db.session.rollback()
        raise e

def sync_called_counts_file_only():
    counts = load_called_counts()
    to_delete = []
    
    settings = load_settings()
    threshold = settings.get("deletion_threshold", 5)
    
    logger.info(f"Starting file-only sync with counts: {counts}")
    
    try:
        for keyword_text, count in counts.items():
            if count >= threshold:
                logger.info(f"Marking for deletion in txt: {keyword_text} with count {count}")
                to_delete.append(keyword_text)
        
        if to_delete:
            # Remove from keywords.txt
            if os.path.exists('keywords.txt'):
                with open('keywords.txt', 'r', encoding='utf-8') as f:
                    kws = [line.strip() for line in f if line.strip()]
                
                updated_kws = [kw for kw in kws if kw not in to_delete]
                
                with open('keywords.txt', 'w', encoding='utf-8') as f:
                    for kw in updated_kws:
                        f.write(kw + '\n')
            
            # Clean up the memory list
            global keywords
            removed_from_list = 0
            for keyword in to_delete:
                if keyword in keywords:
                    keywords.remove(keyword)
                    removed_from_list += 1
            logger.info(f"Removed {removed_from_list} keywords from memory list")
            
        # Clean up the counts file
        old_count = len(counts)
        new_counts = {k: v for k, v in counts.items() if v < threshold}
        save_called_counts(new_counts)
        logger.info(f"Cleaned counts file: removed {old_count - len(new_counts)} entries")
        logger.info(f"Final counts in file: {new_counts}")
        
    except Exception as e:
        logger.error(f"Error in sync: {str(e)}")
        raise e

def sync_called_counts():
    if USE_DATABASE:
        sync_called_counts_with_db()
    else:
        sync_called_counts_file_only()

@app.route("/")
def home():
    return render_template("index.html", use_database=USE_DATABASE)

@app.route("/add_keywords", methods=["POST"])
def add_keywords():
    new_keywords = request.form.get("keywords", "").strip()
    if not new_keywords:
        return jsonify({"status": "error", "message": "No keywords provided"}), 400

    # Split keywords by newline and filter out empty lines
    keyword_list = [k.strip() for k in new_keywords.split('\n') if k.strip()]

    success_count = 0
    duplicate_count = 0
    settings = load_settings()
    batch_size = settings.get("batch_size", 10)

    try:
        if USE_DATABASE:
            # Process keywords in batches
            for i in range(0, len(keyword_list), batch_size):
                batch = keyword_list[i:i + batch_size]
                s, d = process_batch(batch)
                success_count += s
                duplicate_count += d
        else:
            # File-based insertion
            existing_keywords = set()
            if os.path.exists('keywords.txt'):
                with open('keywords.txt', 'r', encoding='utf-8') as f:
                    existing_keywords = set(line.strip() for line in f if line.strip())
            
            new_to_append = []
            for k in keyword_list:
                if k not in existing_keywords:
                    new_to_append.append(k)
                    existing_keywords.add(k)
                    success_count += 1
                else:
                    duplicate_count += 1
            
            if new_to_append:
                with open('keywords.txt', 'a', encoding='utf-8') as f:
                    for k in new_to_append:
                        f.write(k + '\n')

        # Reload keywords after all batches are processed
        load_keywords()

        message = f"Added {success_count} keywords successfully"
        if duplicate_count > 0:
            message += f" ({duplicate_count} duplicates skipped)"
        return jsonify({"status": "success", "message": message})

    except Exception as e:
        if USE_DATABASE:
            db.session.rollback()
        return jsonify({
            "status": "error",
            "message": f"Error adding keywords: {str(e)}"
        }), 500

@app.route("/refresh", methods=["POST"])
def refresh():
    try:
        with lock:  # Add lock to prevent race conditions
            # First sync the counts
            sync_called_counts()
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
            sync_called_counts()
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
        settings = load_settings()
        lock_timeout = settings.get("lock_timeout", 5)
        threshold = settings.get("deletion_threshold", 5)
        
        with timeout_lock(lock, timeout=lock_timeout):
            if not keywords:
                return jsonify({"keyword": None, "message": "No keywords left"}), 404
                
            index = random.randint(0, len(keywords) - 1)
            keyword_text = keywords.pop(index)
            
            # Use file-based counting instead of database
            count = increment_keyword_count(keyword_text)
            
            # Immediately sync if count reaches deletion threshold
            if count >= threshold:
                sync_called_counts()
                
            return jsonify({
                "keyword": keyword_text,
                "count": count,
                "deleted": count >= threshold
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
        if USE_DATABASE:
            kws = [k.keyword for k in Keyword.query.all()]
        else:
            if os.path.exists('keywords.txt'):
                with open('keywords.txt', 'r', encoding='utf-8') as f:
                    kws = [line.strip() for line in f if line.strip()]
            else:
                kws = []
        total_count = len(kws)
        return jsonify({
            'keywords': kws,
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
        if USE_DATABASE:
            results = db.session.query(Keyword.keyword, Keyword.called_count).all()
            keywords_with_counts = [
                {
                    'keyword': r[0],
                    'count': r[1] or 0
                } 
                for r in results if r[0] is not None
            ]
        else:
            counts = load_called_counts()
            if os.path.exists('keywords.txt'):
                with open('keywords.txt', 'r', encoding='utf-8') as f:
                    kws = [line.strip() for line in f if line.strip()]
            else:
                kws = []
            keywords_with_counts = [
                {
                    'keyword': kw,
                    'count': counts.get(kw, 0) or 0
                }
                for kw in kws if kw is not None
            ]
        # Compress the response using native Gzip to prevent Render/browser truncation!
        return gzip_response({'keywords': keywords_with_counts})
    except Exception as e:
        return jsonify({'keywords': [], 'error': str(e)}), 500

@app.route("/keywords")
def keywords_page():
    return render_template("keywords.html")

@app.route("/export")
def export_keywords():
    try:
        source = request.args.get("source", "active")
        export_format = request.args.get("format", "plain")
        
        # 1. Fetch the data based on source
        kws_data = []
        
        if source == "database":
            if not USE_DATABASE:
                return jsonify({"status": "error", "message": "PostgreSQL database is disabled or not configured in environment"}), 400
            results = db.session.query(Keyword.keyword, Keyword.called_count).all()
            kws_data = [{'keyword': r[0], 'count': r[1] or 0} for r in results if r[0] is not None]
            
        elif source == "file":
            if not os.path.exists('keywords.txt'):
                return jsonify({"status": "error", "message": "Local keywords.txt file not found"}), 404
            
            with open('keywords.txt', 'r', encoding='utf-8') as f:
                file_kws = [line.strip() for line in f if line.strip()]
                
            counts = load_called_counts()
            kws_data = [{'keyword': kw, 'count': counts.get(kw, 0) or 0} for kw in file_kws if kw is not None]
            
        else: # "active"
            if USE_DATABASE:
                results = db.session.query(Keyword.keyword, Keyword.called_count).all()
                kws_data = [{'keyword': r[0], 'count': r[1] or 0} for r in results if r[0] is not None]
            else:
                if os.path.exists('keywords.txt'):
                    with open('keywords.txt', 'r', encoding='utf-8') as f:
                        file_kws = [line.strip() for line in f if line.strip()]
                else:
                    file_kws = []
                counts = load_called_counts()
                kws_data = [{'keyword': kw, 'count': counts.get(kw, 0) or 0} for kw in file_kws if kw is not None]
        
        # 2. Format the response
        if export_format == "json":
            content = json.dumps(kws_data, indent=4)
            filename = f"keywords_export_{source}.json"
            mimetype = "application/json"
            
        elif export_format == "counts":
            lines = [f"{item['keyword']}:{item['count']}" for item in kws_data]
            content = "\n".join(lines)
            filename = f"keywords_export_{source}_counts.txt"
            mimetype = "text/plain"
            
        else: # "plain"
            lines = [item['keyword'] for item in kws_data]
            content = "\n".join(lines)
            filename = f"keywords_export_{source}.txt"
            mimetype = "text/plain"
            
        return Response(
            content,
            mimetype=mimetype,
            headers={"Content-disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/import", methods=["POST"])
def import_keywords():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400
    
    try:
        # Read file content and decode to string
        content = file.read().decode('utf-8', errors='ignore')
        keyword_list = [k.strip() for k in content.split('\n') if k.strip()]
        
        if not keyword_list:
            return jsonify({"status": "error", "message": "Uploaded file is empty"}), 400
        
        success_count = 0
        duplicate_count = 0
        settings = load_settings()
        batch_size = settings.get("batch_size", 10)
        
        if USE_DATABASE:
            # Process in batches to avoid overwhelming connections
            for i in range(0, len(keyword_list), batch_size):
                batch = keyword_list[i:i + batch_size]
                s, d = process_batch(batch)
                success_count += s
                duplicate_count += d
        else:
            # File-based insertion
            existing_keywords = set()
            if os.path.exists('keywords.txt'):
                with open('keywords.txt', 'r', encoding='utf-8') as f:
                    existing_keywords = set(line.strip() for line in f if line.strip())
            
            new_to_append = []
            for k in keyword_list:
                if k not in existing_keywords:
                    new_to_append.append(k)
                    existing_keywords.add(k)
                    success_count += 1
                else:
                    duplicate_count += 1
            
            if new_to_append:
                with open('keywords.txt', 'a', encoding='utf-8') as f:
                    for k in new_to_append:
                        f.write(k + '\n')
        
        # Reload keywords after all batches are processed
        load_keywords()
        
        message = f"Imported {success_count} keywords successfully"
        if duplicate_count > 0:
            message += f" ({duplicate_count} duplicates skipped)"
        return jsonify({"status": "success", "message": message})
        
    except Exception as e:
        if USE_DATABASE:
            db.session.rollback()
        return jsonify({
            "status": "error",
            "message": f"Error importing keywords: {str(e)}"
        }), 500

@app.route("/export_to_file", methods=["POST"])
def export_to_file():
    try:
        if not USE_DATABASE:
            return jsonify({"status": "error", "message": "Cannot export from database because database mode is disabled"}), 400
        
        kws = [k.keyword for k in Keyword.query.all()]
        with open('keywords.txt', 'w', encoding='utf-8') as f:
            for kw in kws:
                f.write(kw + '\n')
                
        return jsonify({
            "status": "success",
            "message": f"Successfully exported {len(kws)} keywords from PostgreSQL database to local keywords.txt"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/import_from_file", methods=["POST"])
def import_from_file():
    try:
        if not USE_DATABASE:
            return jsonify({"status": "error", "message": "Cannot import to database because database mode is disabled"}), 400
        
        if not os.path.exists('keywords.txt'):
            return jsonify({"status": "error", "message": "Local keywords.txt file not found"}), 404
            
        with open('keywords.txt', 'r', encoding='utf-8') as f:
            keyword_list = [line.strip() for line in f if line.strip()]
            
        if not keyword_list:
            return jsonify({"status": "error", "message": "Local keywords.txt file is empty"}), 400
            
        success_count = 0
        duplicate_count = 0
        settings = load_settings()
        batch_size = settings.get("batch_size", 10)
        
        for i in range(0, len(keyword_list), batch_size):
            batch = keyword_list[i:i + batch_size]
            s, d = process_batch(batch)
            success_count += s
            duplicate_count += d
            
        # Reload keywords in memory
        load_keywords()
        
        message = f"Successfully loaded {success_count} keywords from keywords.txt into PostgreSQL database"
        if duplicate_count > 0:
            message += f" ({duplicate_count} duplicates skipped)"
        return jsonify({"status": "success", "message": message})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/settings")
def settings_page():
    return render_template("settings.html", use_database=USE_DATABASE)

@app.route("/api/settings", methods=["GET"])
def get_settings():
    try:
        current_settings = load_settings()
        # Add server stats/metadata
        current_settings["use_database"] = USE_DATABASE
        current_settings["total_keywords"] = len(keywords)
        current_settings["database_status"] = "Connected" if USE_DATABASE else "Disabled"
        return jsonify(current_settings)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/settings", methods=["POST"])
def update_settings():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        # Validation
        deletion_threshold = data.get("deletion_threshold")
        batch_size = data.get("batch_size")
        lock_timeout = data.get("lock_timeout")
        
        if deletion_threshold is not None:
            try:
                deletion_threshold = int(deletion_threshold)
                if deletion_threshold < 1:
                    raise ValueError
            except (ValueError, TypeError):
                return jsonify({"status": "error", "message": "Deletion threshold must be a positive integer"}), 400
        
        if batch_size is not None:
            try:
                batch_size = int(batch_size)
                if batch_size < 1:
                    raise ValueError
            except (ValueError, TypeError):
                return jsonify({"status": "error", "message": "Batch size must be a positive integer"}), 400
                
        if lock_timeout is not None:
            try:
                lock_timeout = int(lock_timeout)
                if lock_timeout < 1:
                    raise ValueError
            except (ValueError, TypeError):
                return jsonify({"status": "error", "message": "Lock timeout must be a positive integer"}), 400

        # Save settings
        current_settings = load_settings()
        if deletion_threshold is not None:
            current_settings["deletion_threshold"] = deletion_threshold
        if batch_size is not None:
            current_settings["batch_size"] = batch_size
        if lock_timeout is not None:
            current_settings["lock_timeout"] = lock_timeout
            
        save_settings(current_settings)
        return jsonify({"status": "success", "message": "Settings updated successfully", "settings": current_settings})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/clear_data", methods=["POST"])
def clear_all_data():
    try:
        with lock:
            # 1. Clear database keywords if database is active
            if USE_DATABASE:
                try:
                    db.session.query(Keyword).delete()
                    db.session.commit()
                except Exception as db_err:
                    db.session.rollback()
                    logger.error(f"Database clear failed: {db_err}")
                    raise db_err
            
            # 2. Clear local keywords file
            if os.path.exists('keywords.txt'):
                with open('keywords.txt', 'w', encoding='utf-8') as f:
                    f.write("")
            
            # 3. Clear local called counts tracker file
            if os.path.exists('keywords_called.txt'):
                with open('keywords_called.txt', 'w', encoding='utf-8') as f:
                    f.write("")
            
            # 4. Clear memory list
            global keywords
            keywords = []
            
            logger.info("Successfully wiped all keyword data.")
            return jsonify({
                "status": "success",
                "message": "Successfully wiped all keyword data from the system (database, local files, and memory cache)."
            })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to clear data: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
