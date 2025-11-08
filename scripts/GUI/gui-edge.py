import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import platform
import psutil
import os
import time
import logging

# ==== SETUP LOGGER ====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==== SETTINGAN PROFILE ====
startProfile = 1
endProfile = 6
searchEngine = "https://www.google.com/search?q="

system_name = platform.system()

BROWSERS = {
    "edge": {
        "label": "Microsoft Edge",
        "default_path": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" if system_name == "Windows" else "/usr/bin/microsoft-edge",
        "process_names": ["msedge.exe", "msedge"],
        "profile_args": lambda profile_name: [f"--profile-directory={profile_name}"],
        "user_agent_flag": "--user-agent={user_agent}",
        "supports_user_agent": True,
    },
    "chrome": {
        "label": "Google Chrome",
        "default_path": r"C:\Program Files\Google\Chrome\Application\chrome.exe" if system_name == "Windows" else "/usr/bin/google-chrome",
        "process_names": ["chrome.exe", "chrome"],
        "profile_args": lambda profile_name: [f"--profile-directory={profile_name}"],
        "user_agent_flag": "--user-agent={user_agent}",
        "supports_user_agent": True,
    },
    "firefox": {
        "label": "Mozilla Firefox",
        "default_path": r"C:\Program Files\Mozilla Firefox\firefox.exe" if system_name == "Windows" else "/usr/bin/firefox",
        "process_names": ["firefox.exe", "firefox"],
        "profile_args": lambda profile_name: ["-P", profile_name, "-no-remote"],
        "user_agent_flag": None,
        "supports_user_agent": False,
    },
}

BROWSER_LABEL_TO_KEY = {data["label"]: key for key, data in BROWSERS.items()}
DEFAULT_BROWSER_KEY = "edge"
DEFAULT_BROWSER_LABEL = BROWSERS[DEFAULT_BROWSER_KEY]["label"]
custom_browser_paths = {key: data["default_path"] for key, data in BROWSERS.items()}

PROFILE_PATTERN_DEFAULTS = {
    "desktop": "Profile {n}",
    "mobile": "Profile {n}"
}
profile_patterns = PROFILE_PATTERN_DEFAULTS.copy()

# ==== DAFTAR QUERY ====
queries = [
    "cara membuat pancake",
    "destinasi wisata terbaik 2024",
    "rutinitas olahraga di rumah yang mudah",
    "ulasan smartphone terbaru",
    "cara menabung dengan cepat",
    "film terbaik untuk ditonton tahun ini",
    "tips berkebun sederhana",
    "roblox",
    "paul allan",
    "outlook",
    "office 365",
    "cara buat cuka apel",
    "resep kue kering lebaran",
    "tutorial edit video untuk pemula",
    "cara belajar bahasa inggris online",
    "ide bisnis rumahan",
    "tips diet sehat",
    "cara merawat kulit wajah",
    "teknologi terbaru di tahun 2024",
    "tren fashion terkini",
    "cara membuat website gratis",
    "aplikasi edit foto terbaik",
    "cara investasi saham untuk pemula",
    "destinasi liburan murah",
    "cara memasak nasi goreng spesial",
    "tips menulis artikel yang menarik",
]

# ==== USER AGENT ====
ua_desktop = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
ua_mobile = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"

stop_flag = False
skip_current_flag = False
skip_vars = {}
active_browser_key = DEFAULT_BROWSER_KEY
current_browser_selection = {"key": DEFAULT_BROWSER_KEY}


def remember_browser_path(browser_key, path_value):
    """Store the last-used executable path per browser so switching preserves overrides."""
    if path_value:
        custom_browser_paths[browser_key] = path_value


def resolve_browser_settings():
    """Return (browser_key, executable_path) while validating the selection."""
    browser_key = get_selected_browser_key()
    selected_path = ""
    if "browser_path_var" in globals():
        selected_path = (browser_path_var.get() or "").strip()
    path_value = selected_path or custom_browser_paths.get(browser_key) or BROWSERS[browser_key]["default_path"]
    if not path_value:
        raise ValueError("Path browser tidak ditemukan.")
    if not os.path.exists(path_value):
        raise FileNotFoundError(path_value)
    remember_browser_path(browser_key, path_value)
    return browser_key, path_value


def update_profile_pattern(kind, new_value):
    default_value = PROFILE_PATTERN_DEFAULTS.get(kind, "Profile {n}")
    value = (new_value or "").strip()
    if not value:
        value = default_value
    if "{n}" not in value:
        value = f"{value} {{n}}"
    profile_patterns[kind] = value
    return value


def get_profile_pattern(kind):
    return profile_patterns.get(kind, PROFILE_PATTERN_DEFAULTS.get(kind, "Profile {n}"))


def format_profile_name(profile_num, profile_type):
    pattern = get_profile_pattern(profile_type)
    return pattern.replace("{n}", str(profile_num))


def build_browser_command(browser_key, browser_path, profile_name, user_agent, url):
    config = BROWSERS.get(browser_key, BROWSERS[DEFAULT_BROWSER_KEY])
    cmd = [browser_path]
    profile_builder = config.get("profile_args")
    if profile_builder:
        cmd.extend(profile_builder(profile_name))

    ua_flag = config.get("user_agent_flag")
    if ua_flag:
        cmd.append(ua_flag.format(user_agent=user_agent))
    elif not config.get("supports_user_agent", True):
        logger.debug("Browser %s tidak mendukung override user agent per-run", config["label"])

    cmd.append(url)
    return cmd


def is_process_running(target_names):
    target_lower = tuple(name.lower() for name in target_names)
    for proc in psutil.process_iter(attrs=["name"]):
        try:
            name = (proc.info.get("name") or "").lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if any(name == target for target in target_lower):
            return True
    return False


def close_browser(browser_key):
    config = BROWSERS.get(browser_key, BROWSERS[DEFAULT_BROWSER_KEY])
    process_names = config["process_names"]
    system = platform.system()

    if system == "Windows":
        for name in process_names:
            os.system(f"taskkill /im {name} >nul 2>&1")
        time.sleep(3)
        if is_process_running(process_names):
            for name in process_names:
                os.system(f"taskkill /im {name} /f >nul 2>&1")
    else:
        for name in process_names:
            os.system(f"pkill -15 {name}")
        time.sleep(3)
        if is_process_running(process_names):
            for name in process_names:
                os.system(f"pkill -9 {name}")


def get_selected_browser_key():
    if "browser_choice_var" in globals():
        label = browser_choice_var.get()
    else:
        label = DEFAULT_BROWSER_LABEL
    return BROWSER_LABEL_TO_KEY.get(label, DEFAULT_BROWSER_KEY)


def on_browser_change(event=None):
    prev_key = current_browser_selection.get("key", DEFAULT_BROWSER_KEY)
    previous_value = ""
    if "browser_path_var" in globals():
        previous_value = (browser_path_var.get() or "").strip()
    remember_browser_path(prev_key, previous_value or custom_browser_paths.get(prev_key) or BROWSERS[prev_key]["default_path"])

    new_key = get_selected_browser_key()
    current_browser_selection["key"] = new_key
    if "browser_path_var" in globals():
        browser_path_var.set(custom_browser_paths.get(new_key) or BROWSERS[new_key]["default_path"])


def persist_browser_path(event=None):
    if "browser_path_var" in globals():
        remember_browser_path(get_selected_browser_key(), (browser_path_var.get() or "").strip())


def persist_profile_pattern(kind, event=None):
    if kind == "desktop" and "desktop_profile_pattern_var" in globals():
        new_value = update_profile_pattern("desktop", desktop_profile_pattern_var.get())
        desktop_profile_pattern_var.set(new_value)
    elif kind == "mobile" and "mobile_profile_pattern_var" in globals():
        new_value = update_profile_pattern("mobile", mobile_profile_pattern_var.get())
        mobile_profile_pattern_var.set(new_value)

# ==== Jalankan query ====
def run_queries(user_agent, skipProfiles, waitSeconds, progress_var, progress_offset=0, progress_max=100, show_message=True, on_complete=None, stop_event=None, browser_key=DEFAULT_BROWSER_KEY, browser_path=None, profile_mode="desktop"):
    global stop_flag, skip_current_flag
    total_profiles = endProfile - startProfile + 1
    query_count = len(queries)
    executable_path = browser_path or custom_browser_paths.get(browser_key) or BROWSERS[browser_key]["default_path"]

    if not executable_path:
        logger.error("Browser path tidak valid untuk %s", browser_key)
        return

    for idx, profileNum in enumerate(range(startProfile, endProfile + 1), 1):
        if stop_flag or (stop_event and stop_event.is_set()):
            break
        if profileNum in skipProfiles:
            continue

        query = queries[(profileNum - startProfile) % query_count]
        url = searchEngine + query.replace(" ", "+")
        profile_name = format_profile_name(profileNum, profile_mode)

        cmd = build_browser_command(browser_key, executable_path, profile_name, user_agent, url)
        try:
            subprocess.Popen(cmd)
        except FileNotFoundError:
            logger.error("Executable %s tidak ditemukan. Hentikan run.", executable_path)
            messagebox.showerror("Browser tidak ditemukan", f"File {executable_path} tidak ditemukan.")
            break

        for sec in range(waitSeconds):
            if stop_flag or (stop_event and stop_event.is_set()):
                break
            if skip_current_flag:   # kalau tombol Skip ditekan
                skip_current_flag = False
                break
            time.sleep(1)

        close_browser(browser_key)
        progress_var.set(progress_offset + int((idx / total_profiles) * progress_max))

    progress_var.set(progress_offset + progress_max)
    if show_message and not stop_flag and not (stop_event and stop_event.is_set()):
        messagebox.showinfo("Selesai", "Script selesai atau dihentikan!")
    if on_complete:
        on_complete()

def start_script():
    global stop_flag, active_browser_key
    stop_flag = False
    choice = mode_var.get()
    if not choice:
        messagebox.showerror("Error", "Pilih mode Mobile, Desktop, atau Desktop + Mobile!")
        return

    persist_profile_pattern("desktop")
    persist_profile_pattern("mobile")

    try:
        browser_key, browser_path = resolve_browser_settings()
    except FileNotFoundError as e:
        messagebox.showerror("Browser tidak ditemukan", f"Path browser tidak valid:\n{e}")
        return
    except ValueError as e:
        messagebox.showerror("Browser error", str(e))
        return

    active_browser_key = browser_key
    if not BROWSERS[browser_key]["supports_user_agent"]:
        messagebox.showinfo(
            "User-Agent default",
            "Mozilla Firefox tidak mendukung override user-agent melalui script ini.\n"
            "Mode Mobile atau Desktop akan menggunakan user-agent bawaan.",
        )

    skipProfiles = [i for i, var in skip_vars.items() if var.get() == 1]

    try:
        custom_wait = int(wait_entry.get())
    except ValueError:
        custom_wait = None

    if choice == "desktop+mobile":
        def start_mobile():
            if not stop_flag:
                # Then run mobile
                wait_mobile = custom_wait if custom_wait is not None else 800
                t2 = threading.Thread(
                    target=run_queries,
                    args=(ua_mobile, skipProfiles, wait_mobile, progress_var, 50, 50, True),
                    kwargs={"browser_key": browser_key, "browser_path": browser_path, "profile_mode": "mobile"}
                )
                t2.start()

        # Run desktop first
        wait_desktop = custom_wait if custom_wait is not None else 1100
        t1 = threading.Thread(
            target=run_queries,
            args=(ua_desktop, skipProfiles, wait_desktop, progress_var, 0, 50, False, start_mobile),
            kwargs={"browser_key": browser_key, "browser_path": browser_path, "profile_mode": "desktop"}
        )
        t1.start()
    else:
        ua = ua_mobile if choice == "mobile" else ua_desktop
        waitSeconds = custom_wait if custom_wait is not None else (800 if choice == "mobile" else 1100)
        t = threading.Thread(
            target=run_queries,
            args=(ua, skipProfiles, waitSeconds, progress_var),
            kwargs={"browser_key": browser_key, "browser_path": browser_path, "profile_mode": "mobile" if choice == "mobile" else "desktop"}
        )
        t.start()

def stop_script():
    global stop_flag
    stop_flag = True
    close_browser(active_browser_key if active_browser_key else get_selected_browser_key())

def skip_current():
    global skip_current_flag
    skip_current_flag = True

def update_profiles():
    """Regenerate checkbox berdasarkan start & end profile"""
    global skip_vars, startProfile, endProfile

    try:
        startProfile = int(start_entry.get())
        endProfile = int(end_entry.get())
    except ValueError:
        messagebox.showerror("Error", "Start dan End harus angka!")
        return

    if startProfile > endProfile:
        messagebox.showerror("Error", "Start Profile harus <= End Profile!")
        return

    # Clear frame lama
    for widget in scrollable_frame.winfo_children():
        widget.destroy()

    # Buat ulang checkbox
    skip_vars = {}
    for i in range(startProfile, endProfile + 1):
        var = tk.IntVar()
        chk = ttk.Checkbutton(scrollable_frame, text=f"Profile {i}", variable=var)
        chk.pack(anchor="w", padx=5, pady=2)
        skip_vars[i] = var


# ==== SCHEDULER IMPLEMENTATION ====
scheduler_thread = None
scheduler_stop_event = threading.Event()

def scheduler_task(interval_minutes, browser_key, browser_path):
    logger.info(f"Scheduler started with interval {interval_minutes} minutes")
    while not scheduler_stop_event.is_set():
        logger.info("Scheduler running queries")
        # Run queries with current mode and wait time
        choice = mode_var.get()
        if not choice:
            logger.warning("No mode selected, skipping scheduled run")
        else:
            skipProfiles = [i for i, var in skip_vars.items() if var.get() == 1]
            try:
                custom_wait = int(wait_entry.get())
            except ValueError:
                custom_wait = None

            desktop_kwargs = {
                "browser_key": browser_key,
                "browser_path": browser_path,
                "stop_event": scheduler_stop_event,
                "profile_mode": "desktop"
            }
            mobile_kwargs = {
                "browser_key": browser_key,
                "browser_path": browser_path,
                "stop_event": scheduler_stop_event,
                "profile_mode": "mobile"
            }

            if choice == "desktop+mobile":
                def start_mobile():
                    if not scheduler_stop_event.is_set():
                        wait_mobile = custom_wait if custom_wait is not None else 800
                        run_queries(ua_mobile, skipProfiles, wait_mobile, progress_var, 50, 50, False, stop_event=scheduler_stop_event, **mobile_kwargs)
                wait_desktop = custom_wait if custom_wait is not None else 1100
                run_queries(ua_desktop, skipProfiles, wait_desktop, progress_var, 0, 50, False, start_mobile, stop_event=scheduler_stop_event, **desktop_kwargs)
            else:
                ua = ua_mobile if choice == "mobile" else ua_desktop
                waitSeconds = custom_wait if custom_wait is not None else (800 if choice == "mobile" else 1100)
                run_queries(ua, skipProfiles, waitSeconds, progress_var, show_message=False, stop_event=scheduler_stop_event, **(mobile_kwargs if choice == "mobile" else desktop_kwargs))

        # Wait for the interval or stop event
        if scheduler_stop_event.wait(interval_minutes * 60):
            break
    logger.info("Scheduler stopped")

def start_scheduler():
    global scheduler_thread, scheduler_stop_event, active_browser_key
    if scheduler_thread and scheduler_thread.is_alive():
        messagebox.showinfo("Scheduler", "Scheduler is already running")
        return
    try:
        interval = int(scheduler_interval_entry.get())
        if interval <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid positive integer for interval")
        return

    persist_profile_pattern("desktop")
    persist_profile_pattern("mobile")

    try:
        browser_key, browser_path = resolve_browser_settings()
    except FileNotFoundError as e:
        messagebox.showerror("Browser tidak ditemukan", f"Path browser tidak valid:\n{e}")
        return
    except ValueError as e:
        messagebox.showerror("Browser error", str(e))
        return

    active_browser_key = browser_key
    scheduler_stop_event.clear()
    scheduler_thread = threading.Thread(target=scheduler_task, args=(interval, browser_key, browser_path), daemon=True)
    scheduler_thread.start()
    scheduler_status_var.set(f"Scheduler running every {interval} minutes")
    logger.info(f"Scheduler started with interval {interval} minutes")

def stop_scheduler():
    global scheduler_stop_event, scheduler_thread
    if not scheduler_thread or not scheduler_thread.is_alive():
        messagebox.showinfo("Scheduler", "Scheduler is not running")
        return
    scheduler_stop_event.set()
    scheduler_thread.join(timeout=5)  # Wait for thread to finish
    scheduler_status_var.set("Scheduler stopped")
    logger.info("Scheduler stopped")

# ==== GUI ====
root = tk.Tk()
root.title("🌐 Browser Query Runner")
root.geometry("960x640")
root.minsize(900, 700)
root.configure(bg="#f6f8fb")

style = ttk.Style(root)
style.theme_use("clam")
style.configure("TButton", font=("Segoe UI", 11), padding=6)
style.configure("TLabel", font=("Segoe UI", 10), background="#f6f8fb")
style.configure("Main.TFrame", background="#f6f8fb")
style.configure("Card.TLabelframe", background="#ffffff", relief="ridge", borderwidth=1)
style.configure("Card.TLabelframe.Label", background="#ffffff", font=("Segoe UI", 11, "bold"))
style.configure("Card.TFrame", background="#ffffff")
style.configure("Vertical.TScrollbar", gripcount=0,
                background="#cfd8e3", troughcolor="#ecf0f7",
                bordercolor="#ecf0f7", arrowcolor="#4b5874")

header = ttk.Frame(root, padding=(16, 14), style="Main.TFrame")
header.pack(fill="x")
ttk.Label(header, text="Browser Query Runner", font=("Segoe UI Semibold", 18), background="#f6f8fb").pack(anchor="w")
ttk.Label(
    header,
    text="Semua pengaturan run dan profil kini dikelompokkan supaya mudah terlihat.",
    font=("Segoe UI", 10),
    background="#f6f8fb"
).pack(anchor="w", pady=(4, 0))

content = ttk.Frame(root, padding=(16, 0, 16, 16), style="Main.TFrame")
content.pack(fill="both", expand=True)
content.columnconfigure(0, weight=1)
content.columnconfigure(1, weight=1)

# ========== KIRI ==========
left_column = ttk.Frame(content, style="Main.TFrame")
left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

mode_browser = ttk.LabelFrame(left_column, text="Mode & Browser", padding=12, style="Card.TLabelframe")
mode_browser.pack(fill="x", pady=(0, 12))
mode_browser.columnconfigure(0, weight=1)
mode_browser.columnconfigure(1, weight=1)

mode_container = ttk.Frame(mode_browser, style="Card.TFrame")
mode_container.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

mode_var = tk.StringVar(value="")
ttk.Label(mode_container, text="Mode pencarian:", background="#ffffff").pack(anchor="w", pady=(0, 4))
ttk.Radiobutton(mode_container, text="📱 Mobile", variable=mode_var, value="mobile").pack(anchor="w", pady=2)
ttk.Radiobutton(mode_container, text="💻 Desktop", variable=mode_var, value="desktop").pack(anchor="w", pady=2)
ttk.Radiobutton(mode_container, text="💻📱 Desktop + Mobile", variable=mode_var, value="desktop+mobile").pack(anchor="w", pady=2)

browser_container = ttk.Frame(mode_browser, style="Card.TFrame")
browser_container.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

browser_choice_var = tk.StringVar(value=DEFAULT_BROWSER_LABEL)
browser_path_var = tk.StringVar(value=BROWSERS[DEFAULT_BROWSER_KEY]["default_path"])
browser_labels = [data["label"] for data in BROWSERS.values()]

ttk.Label(browser_container, text="Browser:", background="#ffffff").pack(anchor="w")
browser_combo = ttk.Combobox(
    browser_container,
    textvariable=browser_choice_var,
    state="readonly",
    values=browser_labels
)
browser_combo.pack(fill="x", pady=4)
if DEFAULT_BROWSER_LABEL in browser_labels:
    browser_combo.current(browser_labels.index(DEFAULT_BROWSER_LABEL))
browser_combo.bind("<<ComboboxSelected>>", on_browser_change)

ttk.Label(browser_container, text="Path executable:", background="#ffffff").pack(anchor="w", pady=(6, 0))
browser_path_entry = ttk.Entry(browser_container, textvariable=browser_path_var)
browser_path_entry.pack(fill="x", pady=4)
browser_path_entry.bind("<FocusOut>", persist_browser_path)
browser_path_entry.bind("<Return>", persist_browser_path)

profile_naming = ttk.LabelFrame(left_column, text="Penamaan Profil", padding=12, style="Card.TLabelframe")
profile_naming.pack(fill="x", pady=(0, 12))
profile_naming.columnconfigure(0, weight=1)
profile_naming.columnconfigure(1, weight=1)

desktop_profile_pattern_var = tk.StringVar(value=profile_patterns["desktop"])
mobile_profile_pattern_var = tk.StringVar(value=profile_patterns["mobile"])

ttk.Label(profile_naming, text="Gunakan {n} sebagai placeholder nomor profil.", background="#ffffff").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

ttk.Label(profile_naming, text="Desktop:", background="#ffffff").grid(row=1, column=0, sticky="w")
desktop_profile_entry = ttk.Entry(profile_naming, textvariable=desktop_profile_pattern_var)
desktop_profile_entry.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(2, 6))
desktop_profile_entry.bind("<FocusOut>", lambda e: persist_profile_pattern("desktop", e))
desktop_profile_entry.bind("<Return>", lambda e: persist_profile_pattern("desktop", e))

ttk.Label(profile_naming, text="Mobile:", background="#ffffff").grid(row=1, column=1, sticky="w")
mobile_profile_entry = ttk.Entry(profile_naming, textvariable=mobile_profile_pattern_var)
mobile_profile_entry.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(2, 6))
mobile_profile_entry.bind("<FocusOut>", lambda e: persist_profile_pattern("mobile", e))
mobile_profile_entry.bind("<Return>", lambda e: persist_profile_pattern("mobile", e))

timing_controls = ttk.LabelFrame(left_column, text="Timing & Kontrol", padding=12, style="Card.TLabelframe")
timing_controls.pack(fill="x", pady=(0, 12))

ttk.Label(timing_controls, text="Custom wait (detik, opsional):", background="#ffffff").pack(anchor="w")
wait_entry = ttk.Entry(timing_controls)
wait_entry.pack(anchor="w", pady=4)
ttk.Label(
    timing_controls,
    text="Kosongkan untuk pakai default (1100s Desktop / 800s Mobile).",
    background="#ffffff"
).pack(anchor="w", pady=(0, 8))

button_row = ttk.Frame(timing_controls, style="Card.TFrame")
button_row.pack(fill="x", pady=(0, 10))
ttk.Button(button_row, text="▶ Start", command=start_script).pack(side="left", expand=True, padx=4)
ttk.Button(button_row, text="⏹ Stop", command=stop_script).pack(side="left", expand=True, padx=4)
ttk.Button(button_row, text="⏭ Skip", command=skip_current).pack(side="left", expand=True, padx=4)

progress_var = tk.IntVar()
progress = ttk.Progressbar(timing_controls, variable=progress_var, maximum=100)
progress.pack(fill="x")
ttk.Label(timing_controls, text="Progress run tampil di sini.", background="#ffffff").pack(anchor="w", pady=(6, 0))

# Scheduler
scheduler_frame = ttk.LabelFrame(left_column, text="Scheduler", padding=12, style="Card.TLabelframe")
scheduler_frame.pack(fill="x")

ttk.Label(scheduler_frame, text="Interval (menit):", background="#ffffff").pack(anchor="w")
scheduler_interval_entry = ttk.Entry(scheduler_frame)
scheduler_interval_entry.pack(anchor="w", pady=4)
scheduler_interval_entry.insert(0, "10")

scheduler_status_var = tk.StringVar(value="Scheduler stopped")
scheduler_status_label = ttk.Label(scheduler_frame, textvariable=scheduler_status_var, background="#ffffff")
scheduler_status_label.pack(anchor="w", pady=4)

scheduler_buttons = ttk.Frame(scheduler_frame, style="Card.TFrame")
scheduler_buttons.pack(anchor="w", pady=(4, 0))
ttk.Button(scheduler_buttons, text="▶ Start Scheduler", command=start_scheduler).pack(side="left", padx=4)
ttk.Button(scheduler_buttons, text="⏹ Stop Scheduler", command=stop_scheduler).pack(side="left", padx=4)

# ========== KANAN ==========
right_column = ttk.Frame(content, style="Main.TFrame")
right_column.grid(row=0, column=1, sticky="nsew")
right_column.rowconfigure(1, weight=1)

profiles_panel = ttk.LabelFrame(right_column, text="Profil & Skip List", padding=12, style="Card.TLabelframe")
profiles_panel.grid(row=0, column=0, sticky="nsew")

frame_range = ttk.Frame(profiles_panel, style="Card.TFrame")
frame_range.pack(fill="x", pady=(0, 10))

ttk.Label(frame_range, text="Start:", background="#ffffff").pack(side="left", padx=5)
start_entry = ttk.Entry(frame_range, width=6)
start_entry.insert(0, str(startProfile))
start_entry.pack(side="left")

ttk.Label(frame_range, text="End:", background="#ffffff").pack(side="left", padx=5)
end_entry = ttk.Entry(frame_range, width=6)
end_entry.insert(0, str(endProfile))
end_entry.pack(side="left")

ttk.Button(frame_range, text="Update", command=update_profiles).pack(side="left", padx=10)
ttk.Label(
    profiles_panel,
    text="Centang profil yang ingin dilewati ketika script berjalan.",
    background="#ffffff"
).pack(anchor="w", pady=(0, 6))

frame_skip = ttk.Frame(profiles_panel, style="Card.TFrame")
frame_skip.pack(fill="both", expand=True)

canvas = tk.Canvas(frame_skip, bg="#fdfdfd", highlightthickness=0)
scrollbar = ttk.Scrollbar(frame_skip, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar")
scrollable_frame = ttk.Frame(canvas, padding=6)

def resize_canvas(event):
    canvas.itemconfig(frame_window, width=event.width)

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

frame_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.bind("<Configure>", resize_canvas)
canvas.configure(yscrollcommand=scrollbar.set)

def bind_scroll(widget, target_canvas):
    def _on_mousewheel(event):
        target_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"
    widget.bind_all("<MouseWheel>", _on_mousewheel)

bind_scroll(scrollable_frame, canvas)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

update_profiles()
root.mainloop()
