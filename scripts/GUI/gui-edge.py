import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import platform
import psutil
import os
import time

# ==== SETTINGAN PROFILE ====
startProfile = 1
endProfile = 20
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
def run_queries(user_agent, skipProfiles, waitSeconds, progress_var):
    global stop_flag, skip_current_flag
    total_profiles = endProfile - startProfile + 1
    query_count = len(queries)

    for idx, profileNum in enumerate(range(startProfile, endProfile + 1), 1):
        if stop_flag:
            break
        if profileNum in skipProfiles:
            continue

        query = queries[(profileNum - startProfile) % query_count]
        url = searchEngine + query.replace(" ", "+")

        cmd = [edgePath, f'--profile-directory=Profile {profileNum}',
               f'--user-agent={user_agent}', url]
        subprocess.Popen(cmd)

        for sec in range(waitSeconds):
            if stop_flag:
                break
            if skip_current_flag:   # kalau tombol Skip ditekan
                skip_current_flag = False
                break
            time.sleep(1)

        close_edge()
        progress_var.set(int((idx / total_profiles) * 100))

    messagebox.showinfo("Selesai", "Script selesai atau dihentikan!")

def start_script():
    global stop_flag
    stop_flag = False
    choice = mode_var.get()
    if not choice:
        messagebox.showerror("Error", "Pilih mode Mobile atau Desktop!")
        return

    skipProfiles = [i for i, var in skip_vars.items() if var.get() == 1]

    ua = ua_mobile if choice == "mobile" else ua_desktop
    try:
        waitSeconds = int(wait_entry.get())
    except ValueError:
        waitSeconds = 800 if choice == "mobile" else 1100

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


# ==== GUI ====
root = tk.Tk()
root.title("🌐 Edge Query Runner")
root.geometry("900x600")
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

# Frame Waktu
frame_time = ttk.LabelFrame(frame_left, text="Waktu Tunggu", padding=10)
frame_time.pack(fill="x", pady=5)

ttk.Label(frame_time, text="Custom (detik, opsional):").pack(anchor="w")
wait_entry = ttk.Entry(frame_time)
wait_entry.pack(anchor="w", pady=5)

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
