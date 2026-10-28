"""
SimplyMirror — beginner edition (Windows + Android)
Double-click the .exe, follow the 4 pictures/steps. No typing needed.

- Page 1 = Welcome / what you need
- Big green button does everything: fix tools -> find phone -> mirror
- Phone companion: built-in WiFi page so phone gets same steps (scan QR / type address)
"""

import os
import shutil
import socket
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from functools import partial
import urllib.request
import zipfile
import json
import http.server
import socketserver
import sys
import traceback
import datetime
import platform

if getattr(sys, "frozen", False):
    # Running as SimplyMirror.exe: writable folder = folder with the .exe
    APP_DIR = Path(sys.executable).parent
    # companion.html is bundled inside the exe (--add-data), fallback to next to exe
    _bundled = Path(getattr(sys, "_MEIPASS", str(APP_DIR))) / "phone_companion" / "companion.html"
    _external = APP_DIR / "phone_companion" / "companion.html"
    COMPANION_FILE = _bundled if _bundled.is_file() else _external
else:
    APP_DIR = Path(__file__).parent
    COMPANION_FILE = APP_DIR / "phone_companion" / "companion.html"

TOOLS_DIR = APP_DIR / "tools"
SCRCPY_DIR = TOOLS_DIR / "scrcpy-win64"
PLATFORM_TOOLS_DIR = TOOLS_DIR / "platform-tools"
LOG_FILE = APP_DIR / "simplymirror.log"


def log_to_file(msg):
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def excepthook(etype, value, tb):
    err = "".join(traceback.format_exception(etype, value, tb))
    log_to_file("UNCAUGHT EXCEPTION:\n" + err)
    try:
        messagebox.showerror(
            "Something went wrong (saved for debugging)",
            "An error was saved to:\n%s\n\nCopy this and send it for help:\n\n%s"
            % (LOG_FILE, err[-2000:]))
    except Exception:
        pass


sys.excepthook = excepthook
try:
    threading.excepthook = lambda a: excepthook(a.exc_type, a.exc_value, a.exc_traceback)
except Exception:
    pass

SCRCPY_FALLBACK_URL = "https://github.com/Genymobile/scrcpy/releases/download/v3.1/scrcpy-win64-v3.1.zip"
ADB_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"

try:
    import qrcode
    from PIL import Image, ImageTk
    HAS_QR = True
except Exception:
    HAS_QR = False


def find_adb():
    for p in [PLATFORM_TOOLS_DIR / "adb.exe", SCRCPY_DIR / "adb.exe"]:
        if p.is_file():
            return str(p)
    return shutil.which("adb")


def find_scrcpy():
    # Newer releases extract to a versioned folder (scrcpy-win64-vX.Y.Z).
    for p in sorted(TOOLS_DIR.glob("scrcpy-win64*")):
        exe = p / "scrcpy.exe"
        if exe.is_file():
            return str(exe)
    if (SCRCPY_DIR / "scrcpy.exe").is_file():
        return str(SCRCPY_DIR / "scrcpy.exe")
    return shutil.which("scrcpy")


def run_cmd(cmd, timeout=12):
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=flags)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except FileNotFoundError as e:
        return 127, str(e)
    except Exception as e:
        return 1, str(e)


def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "YOUR-PC-IP"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SimplyMirror — Show my phone on my PC")
        self.geometry("720x780")
        self.scrcpy_proc = None
        self.phone_server = None
        self.phone_url = ""

        self.sound_on = tk.BooleanVar(value=True)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        self._build_welcome()
        self._build_steps()
        self._build_actions()
        self._build_phone()
        self._build_log()
        self.after(400, self.auto_check_silent)

    # ---------- UI sections ----------
    def _build_welcome(self):
        box = ttk.Frame(self)
        box.pack(fill="x", padx=14, pady=(12, 4))

        ttk.Label(box, text="👋 Welcome! This shows your phone on your computer, with sound.",
                  font=("Segoe UI", 13, "bold"), wraplength=680, justify="center").pack()
        ttk.Label(box,
                  text="First time takes about 5 minutes. After that it is 1 click.\n"
                       "You need: your Android phone + the USB cable that came with it.\n"
                       "(Some cheap cables only charge — they will NOT work. Use the original.)",
                  font=("Segoe UI", 10), foreground="#333",
                  justify="center").pack(pady=6)

        # magic button
        self.magic_btn = tk.Button(box, text="✨  DO EVERYTHING FOR ME  ✨\n(click here and follow what it says)",
                                   font=("Segoe UI", 12, "bold"), bg="#16a34a", fg="white",
                                   relief="raised", bd=3, padx=12, pady=10,
                                   command=self.do_everything_thread)
        self.magic_btn.pack(fill="x", pady=6)

    def _build_steps(self):
        frame = ttk.LabelFrame(self, text="Follow these 4 steps — tick off as you go")
        frame.pack(fill="x", padx=14, pady=4)

        self.step_vars = [tk.BooleanVar(value=False) for _ in range(4)]
        texts = [
            ("Step 1 — Program is ready",
             "I click FIX and wait until it says Ready. You do this once."),
            ("Step 2 — Prepare my phone (tap 7 times)",
             "On phone: Settings → About phone → tap Build number 7 times → Developer options → USB debugging ON."),
            ("Step 3 — Plug in + tap Allow",
             "Plug USB cable. On phone choose File Transfer. Tap Allow when it asks."),
            ("Step 4 — Show it!",
             "Click the big green SHOW button below. Done!"),
        ]
        for i, (title, desc) in enumerate(texts):
            row = ttk.Frame(frame)
            row.pack(fill="x", padx=10, pady=3)
            ttk.Checkbutton(row, variable=self.step_vars[i]).pack(side="left")
            ttk.Label(row, text=title, font=("Segoe UI", 10, "bold")).pack(anchor="w")
            ttk.Label(row, text=desc, font=("Segoe UI", 9), foreground="#444",
                      wraplength=620, justify="left").pack(anchor="w", padx=(26, 0))

        btnrow = ttk.Frame(frame)
        btnrow.pack(fill="x", padx=10, pady=6)
        ttk.Button(btnrow, text="1. FIX program for me", command=self.download_tools_thread).pack(side="left", padx=3)
        ttk.Button(btnrow, text="2. Show me exactly what to tap on phone", command=self.show_phone_taps).pack(side="left", padx=3)
        ttk.Button(btnrow, text="3. Check if phone is connected", command=self.check_phone_plain).pack(side="left", padx=3)

        self.status_label = ttk.Label(frame, text="Status: starting…",
                                      font=("Segoe UI", 10, "bold"), foreground="#555",
                                      wraplength=640)
        self.status_label.pack(padx=10, pady=(0, 6))

    def _build_actions(self):
        frame = ttk.LabelFrame(self, text="Mirror (screen + sound)")
        frame.pack(fill="x", padx=14, pady=4)
        row = ttk.Frame(frame)
        row.pack(fill="x", padx=10, pady=8)

        self.show_btn = tk.Button(row, text="▶  SHOW MY PHONE ON PC NOW",
                                  font=("Segoe UI", 13, "bold"), bg="#16a34a", fg="white",
                                  padx=14, pady=10, command=self.start_mirror)
        self.show_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))
        tk.Button(row, text="■  Stop", font=("Segoe UI", 11),
                  padx=14, pady=10, command=self.stop_mirror).pack(side="left")

        row2 = ttk.Frame(frame)
        row2.pack(fill="x", padx=10, pady=(0, 8))
        ttk.Checkbutton(row2, text="🔊 Sound on computer (leave ON)", variable=self.sound_on).pack(side="left")
        ttk.Label(row2, text="  Mouse + keyboard control your phone automatically.",
                  font=("Segoe UI", 9), foreground="gray").pack(side="left")

    def _build_phone(self):
        frame = ttk.LabelFrame(self, text="Helper for your phone (optional, same steps on phone screen)")
        frame.pack(fill="x", padx=14, pady=4)
        ttk.Label(frame, wraplength=640, justify="left", font=("Segoe UI", 9),
                  text="If reading on PC is hard: get the steps ON your phone. "
                       "Connect phone to the SAME WiFi as this computer, then scan / type the address.").pack(padx=10, pady=2)
        row = ttk.Frame(frame)
        row.pack(fill="x", padx=10, pady=4)
        ttk.Button(row, text="Start phone helper", command=self.start_phone_server).pack(side="left", padx=3)
        ttk.Button(row, text="Stop phone helper", command=self.stop_phone_server).pack(side="left", padx=3)
        self.phone_label = ttk.Label(frame, text="Phone helper is OFF. Click Start phone helper.",
                                     font=("Segoe UI", 10, "bold"), wraplength=640)
        self.phone_label.pack(padx=10, pady=2)
        self.qr_label = ttk.Label(frame)
        self.qr_label.pack(pady=2)

    def _build_log(self):
        frame = ttk.LabelFrame(self, text="What is happening (you can ignore this)")
        frame.pack(fill="both", expand=True, padx=14, pady=4)
        self.logbox = tk.Text(frame, height=6, font=("Consolas", 8), wrap="word", fg="#333")
        self.logbox.pack(fill="both", expand=True, padx=8, pady=6)
        self.logbox.config(state="disabled")
        btnrow = ttk.Frame(frame)
        btnrow.pack(fill="x", padx=8, pady=(0, 6))
        ttk.Button(btnrow, text="📋 Copy error report for help", command=self.export_diagnostics).pack(side="left")
        ttk.Label(btnrow, text="If anything fails, click that button and paste the text back for debugging.",
                  font=("Segoe UI", 8), foreground="gray").pack(side="left", padx=8)

    def log(self, msg):
        log_to_file(msg)
        self.logbox.config(state="normal")
        self.logbox.insert("end", msg + "\n")
        self.logbox.see("end")
        self.logbox.config(state="disabled")

    def set_status(self, msg, color="#111"):
        self.status_label.config(text="Status: " + msg, foreground=color)

    # ---------- logic ----------
    def auto_check_silent(self):
        adb, scrcpy = find_adb(), find_scrcpy()
        if adb and scrcpy:
            self.set_status("Program looks Ready. Now do Step 2 on your phone. ✅", "#16a34a")
            self.step_vars[0].set(True)
        else:
            self.set_status("First time? Click ✨ DO EVERYTHING FOR ME ✨ above. It will download what is missing.", "#b45309")
        self.log(f"auto-check: adb={adb or 'missing'} scrcpy={scrcpy or 'missing'}")

    def do_everything_thread(self):
        threading.Thread(target=self.do_everything, daemon=True).start()

    def do_everything(self):
        self.set_status("Working… downloading helper files if needed (1-2 min). Please wait…", "#2563eb")
        self.log("Magic button pressed.")
        self.download_tools(block=True)
        adb, scrcpy = find_adb(), find_scrcpy()
        if not (adb and scrcpy):
            self.set_status("Download had a problem. See popup. Try FIX button again.", "red")
            return
        self.step_vars[0].set(True)
        self.after(0, self.show_phone_taps)
        self.set_status("Program is Ready ✅. Now follow the phone window, then plug in + Allow, then press SHOW.", "#16a34a")
        self.log("Ready. Waiting for phone…")
        # auto-poll for device 3 times
        import time
        for _ in range(6):
            state = self._device_state()
            if state == "ready":
                self.set_status("Phone found! ✅ Press SHOW MY PHONE ON PC NOW. 🎉", "#16a34a")
                self.step_vars[2].set(True)
                self.after(0, self.start_mirror)
                return
            time.sleep(5)
        self.set_status("I still don't see your phone. Click 'Check if phone is connected' — it will tell you exactly what is wrong.", "#b45309")

    def _device_state(self):
        adb = find_adb()
        if not adb:
            return "no-adb"
        run_cmd([adb, "start-server"])
        _, out = run_cmd([adb, "devices"])
        lines = [l.strip() for l in out.strip().splitlines()[1:] if l.strip()]
        if not lines:
            return "none"
        for ln in lines:
            if "unauthorized" in ln:
                return "unauthorized"
            if "device" in ln and "offline" not in ln:
                return "ready"
        return "other"

    def check_phone_plain(self):
        state = self._device_state()
        if state == "ready":
            self.set_status("Great! Your phone IS connected ✅. Press SHOW MY PHONE ON PC NOW.", "#16a34a")
            self.step_vars[2].set(True)
            self.log("Phone: ready.")
        elif state == "unauthorized":
            self.set_status("Almost! Look at your PHONE — tap 'Allow USB debugging' (tick Always allow), then check again.", "#b45309")
            messagebox.showinfo("One tap left on your phone",
                                "Your computer can see your phone, but your phone has not said YES yet.\n\n"
                                "Look at your PHONE screen now.\nTap 'Always allow' + 'Allow'.\nThen click 'Check if phone is connected' again.")
        elif state == "none":
            self.set_status("I don't see any phone. Is the cable plugged in? Is USB = File Transfer (not Charging only)? Try another cable/port.", "red")
            messagebox.showinfo("No phone found",
                                "I cannot see your phone yet. Most common fixes:\n\n"
                                "1. Use a DATA cable (the one from the box). Cheap charge-only cables do not work.\n"
                                "2. On phone: swipe down → tap USB → choose File Transfer.\n"
                                "3. USB debugging must be ON (Step 2).\n"
                                "4. Try a different USB hole on the computer.")
        else:
            self.set_status(f"Phone state: {state}. Unplug, plug again, tap Allow, check again.", "#b45309")
        self.log(f"phone check: {state}")

    def download_tools_thread(self):
        threading.Thread(target=partial(self.download_tools, block=False), daemon=True).start()

    def download_tools(self, block=True):
        def _ui(msg, color="#2563eb"):
            self.set_status(msg, color)
            self.log(msg)
        try:
            TOOLS_DIR.mkdir(exist_ok=True)
            if not find_adb():
                _ui("Downloading connection helper (adb)… please wait…")
                z = TOOLS_DIR / "_pt.zip"
                urllib.request.urlretrieve(ADB_URL, z)
                with zipfile.ZipFile(z) as zf:
                    zf.extractall(TOOLS_DIR)
                z.unlink(missing_ok=True)
                self.log("adb done.")
            if not find_scrcpy():
                _ui("Downloading screen helper (scrcpy)… please wait…")
                url = self._latest_scrcpy_url() or SCRCPY_FALLBACK_URL
                self.log(f"scrcpy url: {url}")
                z = TOOLS_DIR / "_sc.zip"
                urllib.request.urlretrieve(url, z)
                with zipfile.ZipFile(z) as zf:
                    zf.extractall(TOOLS_DIR)
                z.unlink(missing_ok=True)
                self.log("scrcpy done.")
            _ui("Program is Ready ✅. Go to Step 2.", "#16a34a")
            self.step_vars[0].set(True)
        except Exception as e:
            self.log(f"download failed: {e}")
            self.after(0, lambda: messagebox.showerror(
                "Internet needed once",
                f"I could not download automatically:\n{e}\n\n"
                "Connect to internet and try FIX again.\n"
                "Or ask someone to install 'scrcpy' + 'platform-tools' for you."))

    def _latest_scrcpy_url(self):
        try:
            req = urllib.request.Request(
                "https://api.github.com/repos/Genymobile/scrcpy/releases/latest",
                headers={"User-Agent": "mirror-helper"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode())
            for a in data.get("assets", []):
                n = a.get("name", "")
                if "win64" in n and n.endswith(".zip"):
                    return a.get("browser_download_url")
        except Exception as e:
            self.log(f"latest lookup failed, using backup ({e})")
        return None

    def start_mirror(self):
        if self.scrcpy_proc and self.scrcpy_proc.poll() is None:
            messagebox.showinfo("Already showing", "Your phone is already on the screen.")
            return
        scrcpy = find_scrcpy()
        if not scrcpy:
            messagebox.showwarning("Not ready yet", "Click ✨ DO EVERYTHING FOR ME ✨ first.")
            return
        if self._device_state() != "ready":
            self.check_phone_plain()
            if self._device_state() != "ready":
                return
        cmd = [scrcpy]
        if not self.sound_on.get():
            cmd.append("--no-audio")
        if "--stay-awake" not in cmd:
            cmd.append("--stay-awake")
        self.log("$ " + " ".join(cmd))
        self.set_status("Opening your phone on PC… look for a new window! 🎉", "#16a34a")
        try:
            self.scrcpy_proc = subprocess.Popen(cmd)
            self.step_vars[3].set(True)
            # Mobile-first handshake: tell the phone app we made it.
            # Phone listens for: com.mirrorhelper.PC_CONNECTED
            self.after(2000, self.notify_phone_connected)
        except Exception as e:
            messagebox.showerror("Could not open", str(e))

    def notify_phone_connected(self):
        adb = find_adb()
        if not adb:
            return
        _, out = run_cmd([adb, "shell", "am", "broadcast",
                          "-a", "com.mirrorhelper.PC_CONNECTED"])
        self.log("Handshake → phone: com.mirrorhelper.PC_CONNECTED")
        self.log(out.strip()[:500])

    def export_diagnostics(self):
        """Build a paste-ready error report + save full log file."""
        try:
            lines = []
            lines.append("=== SimplyMirror error report ===")
            lines.append(f"Time: {datetime.datetime.now()}")
            lines.append(f"OS: {platform.system()} {platform.release()} ({platform.version()})")
            lines.append(f"Frozen exe: {bool(getattr(sys, 'frozen', False))} | Python: {sys.version.split()[0]}")
            lines.append(f"App dir: {APP_DIR}")
            lines.append(f"Log file: {LOG_FILE} (exists={LOG_FILE.is_file()})")
            adb, scrcpy = find_adb(), find_scrcpy()
            lines.append(f"adb: {adb or 'MISSING'}")
            lines.append(f"scrcpy: {scrcpy or 'MISSING'}")
            if adb:
                _, v = run_cmd([adb, "version"])
                lines.append("--- adb version ---")
                lines.append(v.strip()[:1000] or "(no output)")
                _, d = run_cmd([adb, "devices", "-l"])
                lines.append("--- adb devices -l ---")
                lines.append(d.strip()[:2000] or "(no devices)")
            if scrcpy:
                _, v = run_cmd([scrcpy, "--version"])
                lines.append("--- scrcpy --version ---")
                lines.append(v.strip()[:1000] or "(no output)")
            lines.append(f"--- tools dir ({TOOLS_DIR.exists()}) ---")
            try:
                names = [p.name for p in TOOLS_DIR.iterdir()] if TOOLS_DIR.exists() else ["(no tools dir)"]
                lines.append(", ".join(names)[:1000])
            except Exception as e:
                lines.append(f"(list failed: {e})")
            lines.append("--- last log (from file tail) ---")
            try:
                if LOG_FILE.is_file():
                    tail = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
                    lines.extend(tail)
                else:
                    lines.append("(no log file yet)")
            except Exception as e:
                lines.append(f"(log read failed: {e})")
            lines.append("=== end report: paste everything above back for help ===")
            report = "\n".join(lines)
            # save copy next to exe + try clipboard
            out = APP_DIR / "diagnostics-report.txt"
            out.write_text(report, encoding="utf-8")
            try:
                self.clipboard_clear()
                self.clipboard_append(report[-12000:])  # clipboard size guard
            except Exception:
                pass
            self.log(f"Diagnostics saved to {out} (also copied to clipboard).")
            messagebox.showinfo(
                "Error report ready",
                f"Saved to:\n{out}\n\nIt is also copied to your clipboard.\n\n"
                "Paste it back here so I can debug.\n"
                f"Full history is in:\n{LOG_FILE}")
        except Exception as e:
            messagebox.showerror("Report failed", f"{e}\n\nLog file location:\n{LOG_FILE}")

    def stop_mirror(self):
        if self.scrcpy_proc and self.scrcpy_proc.poll() is None:
            self.scrcpy_proc.terminate()
            self.set_status("Stopped. Press SHOW to start again.", "#555")
        else:
            self.set_status("Nothing is showing right now.", "#555")

    # ---------- popups ----------
    def show_phone_taps(self):
        messagebox.showinfo("On your PHONE — tap exactly this (2 min)",
            "Grab your PHONE. Tap exactly this:\n\n"
            "1. Open Settings (gear icon)\n"
            "2. Tap 'About phone'\n"
            "3. Find 'Build number' → TAP IT 7 TIMES fast\n"
            "   (It says 'You are now a developer!' — that is good!)\n"
            "4. Go back → tap 'System' → 'Developer options'\n"
            "5. Turn ON 'USB debugging' → tap OK\n"
            "6. Plug cable phone → computer\n"
            "7. On phone: swipe down → tap USB → 'File Transfer'\n"
            "8. On phone popup: tick 'Always allow' → 'Allow'\n\n"
            "Then on computer click 'Check if phone is connected'.")

    # ---------- phone web server ----------
    def start_phone_server(self):
        if self.phone_server:
            messagebox.showinfo("Already on", f"Phone helper already at:\n{self.phone_url}")
            return
        if not COMPANION_FILE.is_file():
            messagebox.showwarning("Missing file", "phone_companion/companion.html not found.")
            return
        serve_dir = str(COMPANION_FILE.parent)
        handler = partial(http.server.SimpleHTTPRequestHandler, directory=serve_dir)
        try:
            self.phone_server = socketserver.TCPServer(("0.0.0.0", 0), handler)
            port = self.phone_server.server_address[1]
            threading.Thread(target=self.phone_server.serve_forever, daemon=True).start()
            ip = get_lan_ip()
            self.phone_url = f"http://{ip}:{port}/companion.html"
            self.phone_label.config(text=f"On your PHONE (same WiFi!): open Camera → scan QR, or type:\n{self.phone_url}")
            self.log(f"phone server: {self.phone_url}")
            if HAS_QR:
                qr = qrcode.make(self.phone_url)
                qr = qr.resize((180, 180))
                self._qr_img = ImageTk.PhotoImage(qr)
                self.qr_label.config(image=self._qr_img)
            else:
                self.qr_label.config(text="(Tip: pip install qrcode pillow for a scannable QR code)")
            messagebox.showinfo("Phone helper is ON",
                f"On your PHONE:\n1. Connect to the SAME WiFi as this computer\n"
                f"2. Open Camera, point at the QR — or type:\n{self.phone_url}\n"
                f"3. In browser tap ⋮ → Add to Home screen (now it is an app!)")
        except Exception as e:
            messagebox.showerror("Could not start", str(e))

    def stop_phone_server(self):
        if self.phone_server:
            self.phone_server.shutdown()
            self.phone_server.server_close()
            self.phone_server = None
            self.phone_label.config(text="Phone helper is OFF.")
            self.qr_label.config(image="", text="")
            self.log("phone server stopped.")


if __name__ == "__main__":
    app = App()
    app.mainloop()
