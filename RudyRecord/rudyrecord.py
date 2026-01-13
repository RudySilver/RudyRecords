#!/usr/bin/env python3
import os, sys, time, json, signal, subprocess, psutil
from datetime import datetime

BASE_DIR = os.path.expanduser("~/.rudyrecord")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
VIDEO_DIR = os.path.expanduser("~/Videos")
LOG_FILE = os.path.join(BASE_DIR, "ffmpeg.log")
DEFAULT_FPS = 60

def ensure_dirs():
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(VIDEO_DIR, exist_ok=True)

def atomic_write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(data)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def cleanup():
    try: os.remove(STATE_FILE)
    except: pass

def read_state():
    try:
        with open(STATE_FILE) as f: state=json.load(f)
        p = psutil.Process(state["ffmpeg_pid"])
        if p.is_running(): return state
    except: cleanup()
    return None

def is_wayland(): return bool(os.environ.get("WAYLAND_DISPLAY"))

def has_pulse():
    try: subprocess.check_output(["pactl","info"], stderr=subprocess.DEVNULL)
        return True
    except: return False

def detect_encoder():
    try:
        enc=subprocess.check_output(["ffmpeg","-hide_banner","-encoders"],text=True)
        if "h264_nvenc" in enc: return ["-c:v","h264_nvenc"]
        if "h264_vaapi" in enc and os.path.exists("/dev/dri/renderD128"):
            return ["-vaapi_device","/dev/dri/renderD128","-vf","format=nv12,hwupload","-c:v","h264_vaapi"]
    except: pass
    return ["-c:v","libx264","-preset","veryfast"]

def build_ffmpeg_cmd(output,fps):
    audio=[]
    if has_pulse():
        audio=["-f","pulse","-i","@DEFAULT_SINK@.monitor"]
    if is_wayland():
        video=["-f","pipewire","-framerate",str(fps),"-i","0"]
    else:
        display=os.environ.get("DISPLAY",":0")
        try:
            size_str=subprocess.check_output(["xdpyinfo"],text=True).split("dimensions:")[1].split()[0]
        except: size_str="1920x1080"
        video=["-f","x11grab","-framerate",str(fps),"-video_size",size_str,"-i",f"{display}.0+0,0","-draw_mouse","1"]
    return ["ffmpeg","-y","-loglevel","error",*video,*audio,*detect_encoder(),"-pix_fmt","yuv420p","-r",str(fps),output]

def start_recording(fps):
    ensure_dirs()
    if read_state():
        print("Already recording"); return

    ts=datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output=os.path.join(VIDEO_DIR,f"rudy_{ts}.mp4")

    cmd=build_ffmpeg_cmd(output,fps)
    try:
        proc=subprocess.Popen(cmd,start_new_session=True,stderr=open(LOG_FILE,"a"),stdout=open(LOG_FILE,"a"))
    except Exception as e:
        print("Failed to start ffmpeg:", e)
        return

    time.sleep(0.5)
    if proc.poll() is not None:
        print("ffmpeg failed to start. Check", LOG_FILE)
        return

    state={"ffmpeg_pid":proc.pid,"start_time":time.time(),"output":output,"backend":"wayland" if is_wayland() else "x11"}
    atomic_write(STATE_FILE,json.dumps(state))
    print(f"Recording started ({fps} FPS) -> {output}")

def stop_recording():
    state=read_state()
    if not state:
        print("Not recording")
        return
    try:
        os.kill(state["ffmpeg_pid"],signal.SIGTERM)
        time.sleep(0.5)
        print("Recording stopped")
    except Exception as e:
        print("Failed to stop ffmpeg:", e)
    cleanup()

def status(verbose=False):
    state=read_state()
    if not state:
        print("Not recording")
        return
    print("Recording running")
    if verbose:
        try:
            p=psutil.Process(state["ffmpeg_pid"])
            cpu=p.cpu_percent(interval=0.3)
            uptime=int(time.time()-state["start_time"])
            print(f"Backend: {state['backend']}")
            print(f"CPU: {cpu:.1f}%")
            print(f"Uptime: {uptime}s")
            print(f"Output: {state['output']}")
            print(f"Log: {LOG_FILE}")
        except: print("ffmpeg process not responding")

def main():
    if len(sys.argv)<2:
        print("Usage: rudyrecord {start|stop|status} [--fps N] [--verbose]")
        return
    cmd=sys.argv[1]
    fps=DEFAULT_FPS
    if "--fps" in sys.argv:
        try: fps=int(sys.argv[sys.argv.index("--fps")+1])
        except: pass
    if cmd=="start": start_recording(fps)
    elif cmd=="stop": stop_recording()
    elif cmd=="status": status("--verbose" in sys.argv)
    else: print("Unknown command")

if __name__=="__main__":
    main()
