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
edgePath = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" if platform.system() == "Windows" else "/usr/bin/microsoft-edge"

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

# ==== CLOSE EDGE CROSS-PLATFORM ====
def close_edge():
    system = platform.system()
    if system == "Windows":
        os.system("taskkill /im msedge.exe >nul 2>&1")
        time.sleep(3)
        still_running = any("msedge.exe" in (p.name() or "") for p in psutil.process_iter())
        if still_running:
            os.system("taskkill /im msedge.exe /f >nul 2>&1")
    else:
        os.system("pkill -15 msedge")
        time.sleep(3)
        still_running = any("msedge" in (p.name() or "") for p in psutil.process_iter())
        if still_running:
            os.system("pkill -9 msedge")

# ==== Jalankan query ====
def run_queries(user_agent, skipProfiles, waitSeconds, progress_var, progress_offset=0, progress_max=100, show_message=True, on_complete=None, stop_event=None):
    global stop_flag, skip_current_flag
    total_profiles = endProfile - startProfile + 1
    query_count = len(queries)

    for idx, profileNum in enumerate(range(startProfile, endProfile + 1), 1):
        if stop_flag or (stop_event and stop_event.is_set()):
            break
        if profileNum in skipProfiles:
            continue

        query = queries[(profileNum - startProfile) % query_count]
        url = searchEngine + query.replace(" ", "+")

        cmd = [edgePath, f'--profile-directory=Profile {profileNum}',
               f'--user-agent={user_agent}', url]
        subprocess.Popen(cmd)

        for sec in range(waitSeconds):
            if stop_flag or (stop_event and stop_event.is_set()):
                break
            if skip_current_flag:   # kalau tombol Skip ditekan
                skip_current_flag = False
                break
            time.sleep(1)

        close_edge()
        progress_var.set(progress_offset + int((idx / total_profiles) * progress_max))

    progress_var.set(progress_offset + progress_max)
    if show_message and not stop_flag and not (stop_event and stop_event.is_set()):
        messagebox.showinfo("Selesai", "Script selesai atau dihentikan!")
    if on_complete:
        on_complete()

def start_script():
    global stop_flag
    stop_flag = False
    choice = mode_var.get()
    if not choice:
        messagebox.showerror("Error", "Pilih mode Mobile, Desktop, atau Desktop + Mobile!")
        return

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
                t2 = threading.Thread(target=run_queries, args=(ua_mobile, skipProfiles, wait_mobile, progress_var, 50, 50, True))
                t2.start()

        # Run desktop first
        wait_desktop = custom_wait if custom_wait is not None else 1100
        t1 = threading.Thread(target=run_queries, args=(ua_desktop, skipProfiles, wait_desktop, progress_var, 0, 50, False, start_mobile))
        t1.start()
    else:
        ua = ua_mobile if choice == "mobile" else ua_desktop
        waitSeconds = custom_wait if custom_wait is not None else (800 if choice == "mobile" else 1100)
        t = threading.Thread(target=run_queries, args=(ua, skipProfiles, waitSeconds, progress_var))
        t.start()

def stop_script():
    global stop_flag
    stop_flag = True
    close_edge()

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

def scheduler_task(interval_minutes):
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

            if choice == "desktop+mobile":
                def start_mobile():
                    if not scheduler_stop_event.is_set():
                        wait_mobile = custom_wait if custom_wait is not None else 800
                        run_queries(ua_mobile, skipProfiles, wait_mobile, progress_var, 50, 50, False, stop_event=scheduler_stop_event)
                wait_desktop = custom_wait if custom_wait is not None else 1100
                run_queries(ua_desktop, skipProfiles, wait_desktop, progress_var, 0, 50, False, start_mobile, stop_event=scheduler_stop_event)
            else:
                ua = ua_mobile if choice == "mobile" else ua_desktop
                waitSeconds = custom_wait if custom_wait is not None else (800 if choice == "mobile" else 1100)
                run_queries(ua, skipProfiles, waitSeconds, progress_var, show_message=False, stop_event=scheduler_stop_event)

        # Wait for the interval or stop event
        if scheduler_stop_event.wait(interval_minutes * 60):
            break
    logger.info("Scheduler stopped")

def start_scheduler():
    global scheduler_thread, scheduler_stop_event
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
    scheduler_stop_event.clear()
    scheduler_thread = threading.Thread(target=scheduler_task, args=(interval,), daemon=True)
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
root.title("🌐 Edge Query Runner")
root.geometry("900x650")
root.configure(bg="#f0f2f5")

style = ttk.Style(root)
style.theme_use("clam")
style.configure("TButton", font=("Segoe UI", 11), padding=6)
style.configure("TLabel", font=("Segoe UI", 10))
style.configure("Vertical.TScrollbar", gripcount=0,
                background="#d9d9d9", troughcolor="#f0f2f5",
                bordercolor="#f0f2f5", arrowcolor="#333")

# Paned Window (bagi kiri & kanan)
paned = ttk.PanedWindow(root, orient="horizontal")
paned.pack(fill="both", expand=True, padx=10, pady=10)

# ========== KIRI ==========
frame_left = ttk.Frame(paned, padding=10)
paned.add(frame_left, weight=1)

# Frame Mode
frame_mode = ttk.LabelFrame(frame_left, text="Pilih Mode", padding=10)
frame_mode.pack(fill="x", pady=5)

mode_var = tk.StringVar(value="")
ttk.Radiobutton(frame_mode, text="📱 Mobile", variable=mode_var, value="mobile").pack(anchor="w", pady=2)
ttk.Radiobutton(frame_mode, text="💻 Desktop", variable=mode_var, value="desktop").pack(anchor="w", pady=2)
ttk.Radiobutton(frame_mode, text="💻📱 Desktop + Mobile", variable=mode_var, value="desktop+mobile").pack(anchor="w", pady=2)

# Frame Waktu
frame_time = ttk.LabelFrame(frame_left, text="Waktu Tunggu", padding=10)
frame_time.pack(fill="x", pady=5)

ttk.Label(frame_time, text="Custom (detik, opsional):").pack(anchor="w")
wait_entry = ttk.Entry(frame_time)
wait_entry.pack(anchor="w", pady=5)

# Frame Scheduler
frame_scheduler = ttk.LabelFrame(frame_left, text="Scheduler", padding=10)
frame_scheduler.pack(fill="x", pady=5)

ttk.Label(frame_scheduler, text="Interval (minutes):").pack(anchor="w")
scheduler_interval_entry = ttk.Entry(frame_scheduler)
scheduler_interval_entry.pack(anchor="w", pady=5)
scheduler_interval_entry.insert(0, "10")

scheduler_status_var = tk.StringVar(value="Scheduler stopped")
scheduler_status_label = ttk.Label(frame_scheduler, textvariable=scheduler_status_var)
scheduler_status_label.pack(anchor="w", pady=5)

scheduler_btn_frame = ttk.Frame(frame_scheduler)
scheduler_btn_frame.pack(anchor="w", pady=5)

ttk.Button(scheduler_btn_frame, text="▶ Start Scheduler", command=start_scheduler).pack(side="left", padx=5)
ttk.Button(scheduler_btn_frame, text="⏹ Stop Scheduler", command=stop_scheduler).pack(side="left", padx=5)

# Tombol Start, Stop, Skip
frame_btn = tk.Frame(frame_left, bg="#f0f2f5")
frame_btn.pack(pady=20)

ttk.Button(frame_btn, text="▶ Start", command=start_script).pack(side="left", padx=10)
ttk.Button(frame_btn, text="⏹ Stop", command=stop_script).pack(side="left", padx=10)
ttk.Button(frame_btn, text="⏭ Skip", command=skip_current).pack(side="left", padx=10)

# ========== KANAN ==========
frame_right = ttk.Frame(paned, padding=10)
paned.add(frame_right, weight=2)

# Frame Profile Range
frame_range = ttk.LabelFrame(frame_right, text="Range Profile", padding=10)
frame_range.pack(fill="x", pady=5)

ttk.Label(frame_range, text="Start:").pack(side="left", padx=5)
start_entry = ttk.Entry(frame_range, width=5)
start_entry.insert(0, str(startProfile))
start_entry.pack(side="left")

ttk.Label(frame_range, text="End:").pack(side="left", padx=5)
end_entry = ttk.Entry(frame_range, width=5)
end_entry.insert(0, str(endProfile))
end_entry.pack(side="left")

ttk.Button(frame_range, text="Update", command=update_profiles).pack(side="left", padx=10)

# Frame Skip Profiles (checkbox manual)
frame_skip = ttk.LabelFrame(frame_right, text="Skip Profiles (Checkbox)", padding=5)
frame_skip.pack(fill="both", expand=True, pady=5)

canvas = tk.Canvas(frame_skip, bg="#ffffff", highlightthickness=0)
scrollbar = ttk.Scrollbar(frame_skip, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar")

scrollable_frame = ttk.Frame(canvas)

def resize_canvas(event):
    canvas.itemconfig(frame_window, width=event.width)

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

frame_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.bind("<Configure>", resize_canvas)

canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# Progress bar
progress_var = tk.IntVar()
progress = ttk.Progressbar(frame_right, variable=progress_var, maximum=100)
progress.pack(fill="x", pady=15)

update_profiles()
root.mainloop()
