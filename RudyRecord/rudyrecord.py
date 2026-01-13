#!/usr/bin/env python3
import os, sys, time, json, signal, subprocess, psutil
from datetime import datetime

BASE_DIR = os.path.expanduser("~/.rudyrecord")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
LOG_FILE = os.path.join(BASE_DIR, "ffmpeg.log")
VIDEO_DIR = os.path.expanduser("~/Videos")
DEFAULT_FPS = 60
LOCK_FILE = os.path.join(BASE_DIR, "lock")

# ------------------------
# filesystem
# ------------------------
def ensure_dirs():
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(VIDEO_DIR, exist_ok=True)

def atomic_write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def cleanup():
    for f in (STATE_FILE, LOCK_FILE):
        try: os.remove(f)
        except: pass

# ------------------------
# env detection
# ------------------------
def is_wayland(): 
    return bool(os.environ.get("WAYLAND_DISPLAY"))

def pulse_sink():
    try:
        sinks = subprocess.check_output(["pactl", "list", "short", "sinks"], text=True)
        default = subprocess.check_output(["pactl", "get-default-sink"], text=True).strip()
        monitor = default + ".monitor"
        return monitor if monitor in sinks else None
    except:
        return None

# ------------------------
# daemon
# ------------------------
def daemonize():
    pid = os.fork()
    if pid > 0: sys.exit(0)
    os.setsid()
    pid2 = os.fork()
    if pid2 > 0: sys.exit(0)
    sys.stdin.close()
    sys.stdout.close()
    sys.stderr.close()

# ------------------------
# state
# ------------------------
def read_state():
    try:
        with open(STATE_FILE) as f: state=json.load(f)
        p = psutil.Process(state["daemon_pid"])
        if abs(p.create_time()-state["daemon_start"])<1: return state
    except: cleanup()
    return None

# ------------------------
# ffmpeg
# ------------------------
def detect_encoder():
    try:
        enc = subprocess.check_output(["ffmpeg","-hide_banner","-encoders"],text=True)
        if "h264_nvenc" in enc: return ["-c:v","h264_nvenc"]
        if "h264_vaapi" in enc and os.path.exists("/dev/dri/renderD128"):
            return ["-vaapi_device","/dev/dri/renderD128","-vf","format=nv12,hwupload","-c:v","h264_vaapi"]
    except: pass
    return ["-c:v","libx264","-preset","veryfast"]

def build_ffmpeg_cmd(output,fps):
    # Video input
    if is_wayland():
        video = ["-f","pipewire","-i","0"]
    else:
        display=os.environ.get("DISPLAY",":0")
        try:
            size_str=subprocess.check_output(["xdpyinfo"],text=True).split("dimensions:")[1].split()[0]
        except: size_str="1920x1080"
        video=["-f","x11grab","-framerate",str(fps),"-video_size",size_str,"-i",f"{display}.0+0,0"]

    # Audio input (optional)
    audio = []
    sink = pulse_sink()
    if sink:
        audio=["-f","pulse","-i",sink]

    return ["ffmpeg","-y","-loglevel","error",*video,*audio,*detect_encoder(),"-pix_fmt","yuv420p","-r",str(fps),output]

# ------------------------
# recording
# ------------------------
def record(fps):
    daemonize()
    ensure_dirs()
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output = os.path.join(VIDEO_DIR,f"rudy_{ts}.mp4")
    with open(LOG_FILE,"a") as log: log.write(f"\n=== START {datetime.now()} ===\n")

    cmd = build_ffmpeg_cmd(output,fps)
    try:
        proc = subprocess.Popen(cmd, stderr=open(LOG_FILE,"a"))
        time.sleep(1)
        if proc.poll() is not None:
            cleanup(); sys.exit(1)
    except:
        cleanup(); sys.exit(1)

    state={"daemon_pid":os.getpid(),"daemon_start":psutil.Process(os.getpid()).create_time(),
           "ffmpeg_pid":proc.pid,"backend":"wayland" if is_wayland() else "x11",
           "output":output,"start_time":time.time(),"last_error":None}
    atomic_write(STATE_FILE,json.dumps(state))
    try: os.remove(LOCK_FILE)
    except: pass

    def shutdown(sig,frame):
        try: proc.terminate(); proc.wait(timeout=5)
        except: proc.kill()
        cleanup(); sys.exit(0)

    signal.signal(signal.SIGTERM,shutdown)
    signal.signal(signal.SIGINT,shutdown)

    while True:
        if proc.poll() is not None:
            state["last_error"]="ffmpeg exited"
            atomic_write(STATE_FILE,json.dumps(state))
            cleanup(); sys.exit(1)
        time.sleep(1)

# ------------------------
# CLI
# ------------------------
def start():
    ensure_dirs()
    if read_state() or os.path.exists(LOCK_FILE):
        print("Already recording or starting"); return
    fps=DEFAULT_FPS
    if "--fps" in sys.argv:
        fps=int(sys.argv[sys.argv.index("--fps")+1])
    atomic_write(LOCK_FILE,str(time.time()))
    pid=os.fork()
    if pid==0: record(fps)
    else: print(f"Recording started ({fps} FPS)")

def stop():
    state=read_state()
    if not state: print("Not recording"); return
    os.kill(state["daemon_pid"],signal.SIGTERM)
    print("Recording stopped")

def status(verbose=False):
    state=read_state()
    if not state: print("Not recording"); return
    print("Recording running")
    if verbose:
        try:
            ff=psutil.Process(state["ffmpeg_pid"])
            cpu=ff.cpu_percent(interval=0.3)
            uptime=int(time.time()-state["start_time"])
            print(f"Backend: {state['backend']}")
            print(f"CPU: {cpu:.1f}%")
            print(f"Uptime: {uptime}s")
            print(f"Output: {state['output']}")
            print(f"Log: {LOG_FILE}")
            if state.get("last_error"): print(f"Last error: {state['last_error']}")
        except: print("ffmpeg process not responding")

def main():
    if len(sys.argv)<2:
        print("Usage: rudyrecord {start|stop|status} [--fps N] [--verbose]")
        return
    cmd=sys.argv[1]
    if cmd=="start": start()
    elif cmd=="stop": stop()
    elif cmd=="status": status("--verbose" in sys.argv)
    else: print("Unknown command")

if __name__=="__main__":
    main()
