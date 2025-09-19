import subprocess
import time
import tkinter as tk
from tkinter import messagebox
import threading
import platform
import psutil
import os

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
]

# ==== USER AGENT ====
ua_desktop = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
ua_mobile = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"

# ==== FLAG STOP ====
stop_flag = False


# ==== CLOSE EDGE CROSS-PLATFORM ====
def close_edge():
    system = platform.system()

    if system == "Windows":
        # soft close
        os.system("taskkill /im msedge.exe >nul 2>&1")
        time.sleep(3)
        # cek masih hidup?
        still_running = any("msedge.exe" in (p.name() or "") for p in psutil.process_iter())
        if still_running:
            print("Edge masih hidup → force close")
            os.system("taskkill /im msedge.exe /f >nul 2>&1")

    elif system == "Linux":
        # soft close
        os.system("pkill -15 msedge")
        time.sleep(3)
        # cek masih hidup?
        still_running = any("msedge" in (p.name() or "") for p in psutil.process_iter())
        if still_running:
            print("Edge masih hidup → force kill")
            os.system("pkill -9 msedge")


# ==== Jalankan query ====
def run_queries(user_agent, skipProfiles, waitSeconds):
    global stop_flag
    for i, query in enumerate(queries):
        if stop_flag:
            print("STOP ditekan → keluar loop")
            break

        profileNum = startProfile + i

        if profileNum in skipProfiles:
            print(f"Profile {profileNum} termasuk skip → dilewati")
            continue

        if profileNum > endProfile:
            print("Sudah melewati endProfile → stop")
            break

        print(f"Jalankan Profile {profileNum} | Query: {query}")
        url = searchEngine + query.replace(" ", "+")
        cmd = [
            edgePath,
            f'--profile-directory=Profile {profileNum}',
            f'--user-agent={user_agent}',
            url,
        ]
        subprocess.Popen(cmd)

        print(f"Tunggu {waitSeconds} detik...")
        for _ in range(waitSeconds):
            if stop_flag:
                print("STOP ditekan → keluar saat tunggu")
                break
            time.sleep(1)

        print("Menutup Edge...")
        close_edge()

    messagebox.showinfo("Selesai", "Script selesai atau dihentikan!")


# ==== GUI ACTIONS ====
def start_script():
    global stop_flag
    stop_flag = False

    choice = mode_var.get()
    if choice not in ["mobile", "desktop"]:
        messagebox.showerror("Error", "Pilih mode Mobile atau Desktop dulu!")
        return

    skipProfiles = [i for i, var in skip_vars.items() if var.get() == 1]
    ua = ua_mobile if choice == "mobile" else ua_desktop

    # Ambil custom wait time dari input
    try:
        custom_time = int(wait_entry.get())
        waitSeconds = custom_time
    except ValueError:
        # Kalau kosong → default
        waitSeconds = 800 if choice == "mobile" else 1100

    print(f"Mode: {choice}, Wait: {waitSeconds} detik")

    t = threading.Thread(target=run_queries, args=(ua, skipProfiles, waitSeconds))
    t.start()


def stop_script():
    global stop_flag
    stop_flag = True
    print("Stop button ditekan → flag True")
    close_edge()


# ==== GUI ====
root = tk.Tk()
root.title("Edge Query Runner (Cross-Platform)")

# Pilih mode: Mobile / Desktop
mode_var = tk.StringVar(value="")
tk.Label(root, text="Pilih Mode:").pack(anchor="w")
tk.Radiobutton(root, text="Mobile", variable=mode_var, value="mobile").pack(anchor="w")
tk.Radiobutton(root, text="Desktop", variable=mode_var, value="desktop").pack(anchor="w")

# Input custom wait
tk.Label(root, text="Custom Waktu (detik, opsional):").pack(anchor="w")
wait_entry = tk.Entry(root)
wait_entry.pack(anchor="w")

# Checkbox skip profile
tk.Label(root, text="Pilih Profile yang mau di-skip:").pack(anchor="w")
skip_vars = {}
for i in range(startProfile, endProfile + 1):
    var = tk.IntVar()
    chk = tk.Checkbutton(root, text=f"Profile {i}", variable=var)
    chk.pack(anchor="w")
    skip_vars[i] = var

# Tombol mulai & stop
frame = tk.Frame(root)
frame.pack(pady=10)
tk.Button(frame, text="Start", command=start_script, width=10).pack(side="left", padx=5)
tk.Button(frame, text="Stop", command=stop_script, width=10).pack(side="left", padx=5)

root.mainloop()
