#!/usr/bin/env python3
import os, sys, time, json, subprocess, signal, psutil
from datetime import datetime

HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, ".rudyrecord")
STATE_FILE = os.path.join(BASE, "state.json")
LOG_FILE = os.path.join(BASE, "ffmpeg.log")
VIDEOS = os.path.join(HOME, "Videos")
FPS_DEFAULT = 60

os.makedirs(BASE, exist_ok=True)
os.makedirs(VIDEOS, exist_ok=True)

def atomic_write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(data)
    os.replace(tmp, path)

def read_state():
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        p = psutil.Process(state["daemon_pid"])
        if p.is_running(): return state
    except: pass
    return None

def write_state(state):
    atomic_write(STATE_FILE, json.dumps(state))

def is_wayland():
    return bool(os.environ.get("WAYLAND_DISPLAY"))

def get_audio():
    try:
        sink = subprocess.check_output(["pactl", "get-default-sink"], text=True).strip()
        return ["-f", "pulse", "-i", sink+".monitor"]
    except: return []

def build_ffmpeg_cmd(fps):
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    outfile = os.path.join(VIDEOS, f"rudy_{ts}.mp4")

    # Video input
    if is_wayland():
        video = ["-f", "pipewire", "-framerate", str(fps), "-i", "0"]
    else:
        display = os.environ.get("DISPLAY", ":0")
        try:
            size = subprocess.check_output(["xdpyinfo"], text=True).split("dimensions:")[1].split()[0]
        except: size = "1920x1080"
        video = ["-f", "x11grab", "-framerate", str(fps), "-video_size", size, "-i", f"{display}.0+0,0"]

    audio = get_audio()
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + video + audio + ["-c:v", "libx264", "-preset", "veryfast",
            "-pix_fmt", "yuv420p", "-r", str(fps), outfile]
    return cmd, outfile

def daemonize():
    if os.fork() > 0: sys.exit(0)
    os.setsid()
    if os.fork() > 0: sys.exit(0)
    for fd in (0,1,2): os.close(fd)

def record(fps):
    daemonize()
    cmd, outfile = build_ffmpeg_cmd(fps)
    with open(LOG_FILE, "a") as log:
        log.write(f"\n=== START {datetime.now()} ===\n")
    proc = subprocess.Popen(cmd, stderr=open(LOG_FILE,"a"))
    state = {
        "daemon_pid": os.getpid(),
        "ffmpeg_pid": proc.pid,
        "start_time": time.time(),
        "output": outfile
    }
    write_state(state)

    def shutdown(sig, frame):
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except: proc.kill()
        os.remove(STATE_FILE)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    proc.wait()
    os.remove(STATE_FILE)

def start():
    if read_state():
        print("Already recording")
        return
    fps = FPS_DEFAULT
    if "--fps" in sys.argv:
        fps = int(sys.argv[sys.argv.index("--fps")+1])
    pid = os.fork()
    if pid==0:
        record(fps)
    else:
        print(f"Recording started ({fps} FPS)")

def stop():
    state = read_state()
    if not state:
        print("Not recording")
        return
    os.kill(state["daemon_pid"], signal.SIGTERM)
    print("Recording stopped")

def status():
    state = read_state()
    if not state:
        print("Not recording")
        return
    print("Recording running")
    print(f"Output: {state['output']}")

def main():
    if len(sys.argv) < 2:
        print("Usage: rudyrecord {start|stop|status} [--fps N]")
        return
    cmd = sys.argv[1]
    if cmd=="start": start()
    elif cmd=="stop": stop()
    elif cmd=="status": status()
    else: print("Unknown command")

if __name__=="__main__":
    main()
