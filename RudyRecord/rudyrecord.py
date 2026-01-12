#!/usr/bin/env python3
import os
import sys
import time
import signal
from datetime import datetime

import cv2
import numpy as np
import mss
import psutil

BASE_DIR = os.path.expanduser("~/.rudyrecord")
PID_FILE = os.path.join(BASE_DIR, "pid")
VIDEO_DIR = os.path.expanduser("~/Videos")

DEFAULT_FPS = 65


def get_running_pid():
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        if psutil.pid_exists(pid):
            return pid
    except Exception:
        pass
    return None


def daemonize():
    if os.fork() > 0:
        os._exit(0)
    os.setsid()
    if os.fork() > 0:
        os._exit(0)

    sys.stdin.close()
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")

    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)


def record(fps):
    daemonize()

    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(VIDEO_DIR, exist_ok=True)

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    running = True

    def stop_handler(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop_handler)

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output = os.path.join(VIDEO_DIR, f"rudy_{ts}.mp4")

    frame_time = 1.0 / fps

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        w, h = monitor["width"], monitor["height"]

        writer = cv2.VideoWriter(
            output,
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (w, h),
        )

        while running:
            start = time.time()
            img = sct.grab(monitor)
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            writer.write(frame)

            delay = frame_time - (time.time() - start)
            if delay > 0:
                time.sleep(delay)

        writer.release()

    try:
        os.remove(PID_FILE)
    except FileNotFoundError:
        pass


def start():
    if get_running_pid():
        print("Already recording")
        return

    fps = DEFAULT_FPS
    if "--fps" in sys.argv:
        try:
            fps = int(sys.argv[sys.argv.index("--fps") + 1])
        except Exception:
            print("Invalid FPS value")
            return

    pid = os.fork()
    if pid == 0:
        record(fps)
    else:
        print(f"Recording started ({fps} FPS)")


def stop():
    pid = get_running_pid()
    if not pid:
        print("Not recording")
        return
    os.kill(pid, signal.SIGTERM)
    print("Recording stopped")


def status():
    if get_running_pid():
        print("Recording running")
    else:
        print("Not recording")


def main():
    if len(sys.argv) < 2:
        print("Usage: rudyrecord {start|stop|status} [--fps N]")
        return

    cmd = sys.argv[1]
    if cmd == "start":
        start()
    elif cmd == "stop":
        stop()
    elif cmd == "status":
        status()
    else:
        print("Unknown command")


if __name__ == "__main__":
    main()

