#!/usr/bin/env python3
import os, sys, json, signal, subprocess, time

BASE = os.path.expanduser("~/.rudyrecord")
PID_FILE = os.path.join(BASE, "ffmpeg.pid")
INFO_FILE = os.path.join(BASE, "info.json")
VIDEO_DIR = os.path.expanduser("~/Videos")
FPS = 60

def ensure():
    os.makedirs(BASE, exist_ok=True)
    os.makedirs(VIDEO_DIR, exist_ok=True)

def pid_alive(pid):
    return os.path.exists(f"/proc/{pid}")

def load_pid():
    try:
        pid = int(open(PID_FILE).read().strip())
        return pid if pid_alive(pid) else None
    except:
        return None

def clear():
    for f in (PID_FILE, INFO_FILE):
        try: os.remove(f)
        except: pass

def backend():
    return "wayland" if os.environ.get("WAYLAND_DISPLAY") else "x11"

def audio():
    try:
        return subprocess.check_output(
            ["pactl","get-default-sink"], text=True
        ).strip() + ".monitor"
    except:
        return None

def ffmpeg_cmd(outfile):
    v = (
        ["-f","pipewire","-i","0"]
        if backend() == "wayland"
        else ["-f","x11grab","-i",":0.0"]
    )

    a = ["-f","pulse","-i",audio()] if audio() else []

    return [
        "ffmpeg",
        "-y",
        "-nostdin",
        "-loglevel","error",
        *v,*a,
        "-c:v","libx264",
        "-preset","veryfast",
        "-pix_fmt","yuv420p",
        outfile
    ]

def start():
    ensure()
    if load_pid():
        print("Already recording")
        return

    name = time.strftime("rudy_%Y-%m-%d_%H-%M-%S.mp4")
    out = os.path.join(VIDEO_DIR, name)

    proc = subprocess.Popen(
        ffmpeg_cmd(out),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(0.5)

    if not pid_alive(proc.pid):
        print("ffmpeg failed to start")
        return

    open(PID_FILE,"w").write(str(proc.pid))
    json.dump({"file":out}, open(INFO_FILE,"w"))

    print("Recording started")

def stop():
    pid = load_pid()
    if not pid:
        print("Not recording")
        return

    os.kill(pid, signal.SIGTERM)

    for _ in range(10):
        if not pid_alive(pid):
            break
        time.sleep(0.2)

    clear()
    print("Recording stopped")

def status():
    pid = load_pid()
    if not pid:
        print("Not recording")
        return

    info = json.load(open(INFO_FILE))
    print("Recording running")
    print("PID:", pid)
    print("File:", info["file"])

def main():
    if len(sys.argv) < 2:
        print("Usage: rudyrecord {start|stop|status}")
        return
    {"start":start,"stop":stop,"status":status}.get(sys.argv[1],lambda:None)()

if __name__ == "__main__":
    main()
