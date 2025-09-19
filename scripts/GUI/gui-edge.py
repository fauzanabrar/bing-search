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
]

# ==== USER AGENT ====
ua_desktop = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
ua_mobile = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"

stop_flag = False

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
    global stop_flag
    total = len(queries)
    for i, query in enumerate(queries, 1):
        if stop_flag:
            break

        profileNum = startProfile + (i - 1)
        if profileNum in skipProfiles:
            continue
        if profileNum > endProfile:
            break

        url = searchEngine + query.replace(" ", "+")
        cmd = [edgePath, f'--profile-directory=Profile {profileNum}', f'--user-agent={user_agent}', url]
        subprocess.Popen(cmd)

        for sec in range(waitSeconds):
            if stop_flag:
                break
            time.sleep(1)

        close_edge()
        progress_var.set(int((i / total) * 100))

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

# ==== GUI ====
root = tk.Tk()
root.title("🌐 Edge Query Runner")
root.geometry("400x500")
root.configure(bg="#f0f2f5")

style = ttk.Style(root)
style.theme_use("clam")
style.configure("TButton", font=("Segoe UI", 11), padding=6)
style.configure("TLabel", font=("Segoe UI", 10))

# Frame Mode
frame_mode = ttk.LabelFrame(root, text="Pilih Mode", padding=10)
frame_mode.pack(fill="x", padx=10, pady=5)

mode_var = tk.StringVar(value="")
ttk.Radiobutton(frame_mode, text="📱 Mobile", variable=mode_var, value="mobile").pack(anchor="w", pady=2)
ttk.Radiobutton(frame_mode, text="💻 Desktop", variable=mode_var, value="desktop").pack(anchor="w", pady=2)

# Frame Waktu
frame_time = ttk.LabelFrame(root, text="Waktu Tunggu", padding=10)
frame_time.pack(fill="x", padx=10, pady=5)

ttk.Label(frame_time, text="Custom (detik, opsional):").pack(anchor="w")
wait_entry = ttk.Entry(frame_time)
wait_entry.pack(anchor="w", pady=5)

# Frame Skip Profiles
frame_skip = ttk.LabelFrame(root, text="Skip Profile", padding=10)
frame_skip.pack(fill="x", padx=10, pady=5)

skip_vars = {}
for i in range(startProfile, endProfile + 1):
    var = tk.IntVar()
    chk = ttk.Checkbutton(frame_skip, text=f"Profile {i}", variable=var)
    chk.pack(anchor="w")
    skip_vars[i] = var

# Progress bar
progress_var = tk.IntVar()
progress = ttk.Progressbar(root, variable=progress_var, maximum=100)
progress.pack(fill="x", padx=10, pady=15)

# Tombol Start & Stop
frame_btn = tk.Frame(root, bg="#f0f2f5")
frame_btn.pack(pady=10)

ttk.Button(frame_btn, text="▶ Start", command=start_script).pack(side="left", padx=10)
ttk.Button(frame_btn, text="⏹ Stop", command=stop_script).pack(side="left", padx=10)

root.mainloop()
