import sys
import time
import subprocess
from pathlib import Path
from argparse import ArgumentParser

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import psutil

from Library.Logging import LoggingAPI, VerboseLevel
from Library.Utility.Datetime import utc_now
from Library.Utility.IO import read_json, write_json
from Library.Utility.Path import traceback_root
from Library.Utility.Runtime import terminate, windowless
from Script.Campaign.Campaign import PAIRS, folder, learning, root

GIGABYTE = 2 ** 30

def _launch_(job: dict) -> dict:
    command = [sys.executable, "-m", "Library.System.Main", *learning(job["Pair"], job["Arm"], job["Seed"], job["Seeds"], job["Workers"])]
    job["Process"] = subprocess.Popen(command, cwd=traceback_root(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **windowless())
    job["Began"], job["StartedAt"] = time.perf_counter(), utc_now().isoformat()
    return job

def _record_(job: dict, status: str) -> None:
    fields = ("Pair", "Arm", "Seed", "Seeds", "Workers", "StartedAt")
    write_json(job["Folder"] / "Job.json", {**{key: job[key] for key in fields}, "Status": status, "Exit": job["Process"].returncode, "Seconds": round(time.perf_counter() - job["Began"], 1), "StoppedAt": utc_now().isoformat()}, safe=False)

def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--pairs", nargs="+", default=list(PAIRS), choices=PAIRS)
    parser.add_argument("--arms", nargs="+", default=["A"], choices=["A", "B"])
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--seeds", type=int, default=16)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--floor", type=float, default=6.0)
    parser.add_argument("--reserve", type=float, default=1.2)
    parser.add_argument("--base", type=float, default=5.0)
    parser.add_argument("--evaluators", type=int, default=6)
    args = parser.parse_args()
    log = LoggingAPI("Campaign")
    log.console.set_level(VerboseLevel.Info)
    log.file.set_level(VerboseLevel.Info)
    with log:
        queue = []
        for pair in args.pairs:
            for arm in args.arms:
                target = folder(pair, arm, args.seed, args.seeds)
                done = read_json(target / "Job.json") or {}
                if done.get("Status") == "Completed": log.info(lambda target=target: f"Job Campaign: Skipped · Completed · {target.relative_to(root())}")
                else: queue.append({"Pair": pair, "Arm": arm, "Seed": args.seed, "Seeds": args.seeds, "Workers": min(args.seeds, args.workers), "Folder": target})
        running, waiting = [], False
        while queue or running:
            free = psutil.virtual_memory().available / GIGABYTE
            if free < args.floor and running:
                victim = running.pop()
                terminate(victim["Process"].pid)
                victim["Process"].wait()
                _record_(victim, "Aborted")
                queue.insert(0, victim)
                log.warning(lambda victim=victim, free=free: f"Job Campaign: Aborted · Memory · {free:.1f} GB Free · {victim['Pair']} Arm {victim['Arm']}")
                time.sleep(60)
                continue
            for job in list(running):
                if job["Process"].poll() is None: continue
                running.remove(job)
                status = "Completed" if job["Process"].returncode == 0 else "Failed"
                _record_(job, status)
                log.info(lambda job=job, status=status: f"Job Campaign: {status} · {job['Pair']} Arm {job['Arm']} · Seeds {job['Seed']}-{job['Seed'] + job['Seeds'] - 1} · {time.perf_counter() - job['Began']:.0f}s")
                if status == "Completed" and not running:
                    began = time.perf_counter()
                    code = subprocess.run([sys.executable, "-m", "Script.Campaign.Evaluate", "--pairs", job["Pair"], "--processes", str(args.evaluators)], cwd=traceback_root(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **windowless()).returncode
                    log.info(lambda job=job, code=code, began=began: f"Evaluation Campaign: {'Completed' if code == 0 else 'Failed'} · {job['Pair']} · {time.perf_counter() - began:.0f}s")
            used = sum(job["Workers"] for job in running)
            needed = args.floor + args.base + queue[0]["Workers"] * args.reserve if queue else 0.0
            if queue and used + queue[0]["Workers"] <= args.workers and free < needed and not waiting:
                waiting = True
                log.warning(lambda free=free, needed=needed: f"Job Campaign: Waiting · Memory · {free:.1f} GB Free · {needed:.1f} GB Needed")
            if queue and used + queue[0]["Workers"] <= args.workers and free >= needed:
                waiting = False
                job = _launch_(queue.pop(0))
                running.append(job)
                log.info(lambda job=job: f"Job Campaign: Started · {job['Pair']} Arm {job['Arm']} · Seeds {job['Seed']}-{job['Seed'] + job['Seeds'] - 1} · {job['Workers']} Workers")
                time.sleep(90)
                continue
            time.sleep(5)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())