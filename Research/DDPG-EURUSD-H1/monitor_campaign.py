import os, sys, time, glob
from datetime import datetime

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")
import psutil

SCRATCH = os.path.dirname(os.path.abspath(__file__))
SEEN = os.path.join(SCRATCH, "_monitor_seen.txt")

def seen():
    if not os.path.exists(SEEN): return set()
    with open(SEEN, encoding="utf-8") as handle: return {line.strip() for line in handle if line.strip()}

def remember(name):
    with open(SEEN, "a", encoding="utf-8") as handle: handle.write(name + "\n")

def sweep_processes():
    parents, workers, orphans = [], [], []
    for proc in psutil.process_iter(["pid", "ppid", "cmdline", "memory_info"]):
        try:
            cmd = proc.info.get("cmdline") or []
            if any(str(a).endswith("sweep_campaign.py") for a in cmd):
                parents.append(proc); continue
            if "spawn_main" not in " ".join(str(a) for a in cmd): continue
            if proc.info["memory_info"].rss < 5e8: continue
            try:
                parent = psutil.Process(proc.info["ppid"])
                alive = parent.is_running() and any(str(a).endswith("sweep_campaign.py") for a in parent.cmdline())
            except Exception:
                alive = False
            (workers if alive else orphans).append(proc)
        except Exception: pass
    return parents, workers, orphans

def cpu_of(procs):
    for proc in procs:
        try: proc.cpu_percent(None)
        except Exception: pass
    time.sleep(5)
    total = 0.0
    for proc in procs:
        try: total += proc.cpu_percent(None)
        except Exception: pass
    return total

while True:
    stamp = datetime.now().strftime("%d/%m/%Y at %H:%M")
    known = seen()
    for log in sorted(glob.glob(os.path.join(SCRATCH, "r_*.log"))):
        name = os.path.splitext(os.path.basename(log))[0]
        if name in known: continue
        try: text = open(log, encoding="utf-8", errors="replace").read()
        except Exception: continue
        if "[DONE]" in text:
            row = [l for l in text.splitlines() if "[DONE]" in l]
            remember(name); print(f"DONE {name} :: {row[-1][:260]}", flush=True)
    parents, workers, orphans = sweep_processes()
    free = psutil.virtual_memory().available / 1e9
    alarm = ""
    if orphans:
        held = sum(p.memory_info().rss for p in orphans) / 1e9
        alarm += f"  !! ORPHANS {len(orphans)} workers holding {held:.1f}G with dead parents — kill children before parents"
    if parents:
        load = cpu_of(parents + workers)
        state = "healthy" if load > 50 else "STUCK"
        if load <= 50: alarm += f"  !! STALL: {len(parents)} parent(s) at {load:.0f}% CPU — not training"
        print(f"Monitor for {stamp} :: {len(parents)} arm(s) · {len(workers)} workers · CPU {load:.0f}% {state} · RAM {free:.1f}G{alarm}", flush=True)
    else:
        print(f"Monitor for {stamp} :: IDLE — no arms running · RAM {free:.1f}G{alarm}", flush=True)
    time.sleep(3600)
