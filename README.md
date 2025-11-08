# Bing Search Automation Suite

Tools for managing long keyword lists, distributing them to automation clients, and driving Microsoft Edge profiles to keep search activity fresh.

- **Flask API (`main.py`)** – stores keywords in PostgreSQL, exposes endpoints and a small UI for loading, sampling, deleting, and monitoring keywords.
- **Maintenance scripts** – e.g., `refresh_keywords.py` for pruning exhausted keywords or converting legacy text files to SQL.
- **Browser automation GUI (`scripts/GUI/gui-edge.py`)** – Tkinter desktop app that opens Edge/Chrome/Firefox profiles with rotating queries (mobile, desktop, or both) and ships with scheduling controls. It can be converted to an `.exe` via PyInstaller.

---

## Repository Layout

| Path | Purpose |
| --- | --- |
| `main.py`, `templates/` | Flask keyword service + HTML UI (port `3000`). |
| `keywords.txt` | Optional seed list (newline-delimited). |
| `keywords_called.txt` | Tracks how often a keyword was issued; when a keyword exceeds the threshold it will be deleted from PostgreSQL. |
| `refresh_keywords.py` | Cleans both keyword files by dropping entries that were called ≥6 times (legacy workflow). |
| `scripts/convert-sql.py`, `scripts/keyword.txt` | Converts a plain text list into `insert.sql` statements for bulk loading into PostgreSQL. |
| `scripts/GUI/gui-edge.py` | Tkinter automation GUI (Edge/Chrome/Firefox); `scripts/GUI/dist/` holds PyInstaller artifacts. |

---

## Requirements

- **Python** 3.10+ (Tkinter bundled on Windows/macOS; on some Linux distros install `python3-tk` separately).
- **PostgreSQL** database reachable via a SQLAlchemy URL.
- **Microsoft Edge**, **Google Chrome**, or **Mozilla Firefox** installed (the GUI ships with default paths for each, and you can override them per browser).
- **pip** + virtual environment tooling (`python -m venv .venv` recommended).
- Optional: **PyInstaller** 6.x for packaging the GUI.

> ℹ️ `requirements.txt` is encoded in UTF-16 LE (Windows default). If `pip install -r requirements.txt` errors with an encoding message, re-save the file as UTF-8 or run `python -m pip install -r <(iconv -f utf-16 -t utf-8 requirements.txt)` on Bash.

---

## Setup

```bash
# create and activate a virtual environment
python -m venv .venv
source .venv/Scripts/activate    # Windows PowerShell: .venv\Scripts\Activate.ps1

# install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

1. Create a PostgreSQL database (for example `bing_search`).
2. Export `DATABASE_URL` before starting the Flask app:

   ```bash
   set DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/bing_search   # Windows (cmd)
   $env:DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/bing_search" # PowerShell
   export DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/bing_search # Linux/macOS
   ```

3. (Optional) Populate initial keywords:
   - Put raw keywords (one per line) into `keywords.txt` or `scripts/keyword.txt`.
   - Run `python scripts/convert-sql.py` to generate `scripts/insert.sql`, then execute it against PostgreSQL (`psql -f scripts/insert.sql`).

---

## Running the Flask Keyword Service

```bash
python main.py
# Server listens on http://0.0.0.0:3000
```

During startup SQLAlchemy will call `db.create_all()` to build the `keyword` table if it does not exist and load all keywords into memory.

### Web UI

- Visit `http://localhost:3000/` to open **Keyword Manager**.
- Paste newline-delimited keywords and click **Submit Keywords**.
- Buttons:
  - **Refresh Keywords** – runs `refresh_keywords.py` (legacy pruning script) through a subprocess.
  - **Reload Keywords** – reloads from the database after syncing call counts/deletions.
  - **View All Keywords** – opens `/keywords` with a read-only textarea and total count.

### REST Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/add_keywords` | Accepts form field `keywords`; stores unique entries in PostgreSQL (batch size 10). |
| `POST` | `/refresh` | Syncs usage counts, executes `refresh_keywords.py`, reloads keywords. |
| `POST` | `/reload_keywords` | Syncs usage counts then reloads keywords without touching files. |
| `GET` | `/keyword` | Pops a random keyword from in-memory list, increments count, deletes at threshold (default 5). |
| `GET` | `/get_keywords` | Returns `{keywords: [], total_count: N}`. |
| `GET` | `/get_keywords_with_counts` | Includes each keyword’s `called_count`. |
| `GET` | `/search?q=foo` | Renders `templates/search.html` showing an iframe that proxies Bing. |
| `GET` | `/proxy_search?q=foo` | Lightweight proxy that forwards headers to `https://bing.com`. |

### Keyword Call Tracking

- `keywords_called.txt` stores JSON containing how many times each keyword was served.
- `increment_keyword_count` bumps the counter whenever `/keyword` serves a record.
- When a keyword reaches the deletion threshold (currently `>=5` inside `sync_called_counts_with_db`), the row is removed from PostgreSQL and the in-memory cache. Edit `CALLED_COUNTS_FILE` and the `>= 5` checks if you need different behavior.
- `refresh_keywords.py` is still available for environments that rely solely on `keywords.txt`/`keywords_called.txt`. It expects the legacy `keyword:count` format. If your file has been rewritten as JSON, convert it back (or keep using the Flask-based cleanup instead of this script).

---

## Browser Automation GUI (`scripts/GUI/gui-edge.py`)

Run from source:

```bash
python scripts/GUI/gui-edge.py
```

Features:

- Choose **Edge**, **Chrome**, or **Firefox**, and override the executable path if it lives somewhere else. Paths are remembered per browser so you can switch back and forth quickly (Firefox will always use its built-in user agent).
- Choose **Mobile**, **Desktop**, or **Desktop + Mobile** user-agents (Edge is launched with `--user-agent`).
- Specify **Start/End profile numbers** (`Profile 1` … `Profile N`), regenerate checkbox list, and skip specific profiles.
- **Wait time** field (seconds) overrides default dwell durations (1100 seconds desktop, 800 seconds mobile).
- Toolbar buttons:
  - **Start** spawns threads per selection and rotates through `queries` defined near the top of the file.
  - **Stop** sets `stop_flag` and kills any Edge instances via `psutil`.
  - **Skip** fast-forwards the current profile iteration.
- Built-in **Scheduler** can rerun the current mode every _N_ minutes (runs on a daemon thread and shares the same start/stop flags).
- Progress bar gives per-run progress (0–50 Desktop, 50–100 Mobile when both modes are enabled).

> ⚠️ Firefox does not expose a command-line flag for overriding the user-agent, so both Mobile and Desktop modes use Firefox’s default UA. Edge/Chrome runs still honor the per-mode overrides.

Customizing:

- Update the `queries` list, `startProfile/endProfile`, or `searchEngine` constants in the script to match your workflow. Executable paths can be changed directly from the GUI (and are remembered per browser).
- The GUI uses standard Tkinter themes; feel free to adjust fonts or colors for your display.

---

## Packaging the GUI with PyInstaller

1. Install PyInstaller in your virtual environment (or globally):

   ```bash
   pip install pyinstaller
   ```

2. From the project root, run one of the following:

   ```bash
   # Windowed, folder-based build (keeps supporting files separate)
   pyinstaller --noconfirm --clean --windowed --name gui-edge scripts/GUI/gui-edge.py

   # Single-file executable (takes longer to start but copies only gui-edge.exe)
   pyinstaller --noconfirm --clean --windowed --onefile --name gui-edge scripts/GUI/gui-edge.py
   ```

   Tips:
   - Add `--icon path/to/icon.ico` if you have a custom icon.
   - Tkinter is part of the standard library, but on some Linux builds you may need to pass `--hidden-import tkinter`.

3. Outputs:
   - `dist/gui-edge/` – contains the run-ready folder build.
   - `dist/gui-edge.exe` – produced when `--onefile` is used (already tracked in this repo).
   - `build/gui-edge/` – intermediate PyInstaller cache (`scripts/GUI/gui-edge/` currently stores these artifacts).

4. Ship `dist/gui-edge.exe` (or the whole `dist/gui-edge/` directory) to end users. They do **not** need Python installed.

To regenerate a clean build, delete `build/` and `dist/` (or the folders under `scripts/GUI/`) before running PyInstaller again.

---

## Troubleshooting & Tips

- **psycopg2 OperationalError / connection refused** – ensure your `DATABASE_URL` points to a reachable PostgreSQL instance. The built-in `retry_on_connection_error` decorator retries with exponential backoff; persistent failures will bubble up in the server logs.
- **`keywords_called.txt` not updating** – confirm the Flask app has write permissions inside the project directory. The file is rewritten after every `/keyword` call.
- **Browser path differs** – update the GUI’s executable path field per browser (defaults cover standard install locations on Windows/Linux). The script remembers your overrides.
- **Tkinter missing on Linux** – install the OS package (`sudo apt install python3-tk`) before running the GUI or PyInstaller.
- **Encoding errors installing requirements** – re-save `requirements.txt` as UTF-8 in your editor, or feed it through `iconv` as mentioned earlier.
- **Testing** – run the Flask app and visit `/keywords` to make sure counts move as you trigger `/keyword`. For the GUI, use short wait times (e.g., 5–10 seconds) when testing so that Edge sessions close quickly.

---

Happy hacking! Let me know if you need schema migrations, Dockerization, or automation hooks added to this workflow.
