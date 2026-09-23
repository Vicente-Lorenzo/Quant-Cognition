import sys
import time
import shlex
import random
import subprocess

import psutil
import pytest

from Library.Utility.Path import traceback_root
from Library.Utility.Runtime import is_windows, join_arguments, release, split_arguments, tether

def reference(arguments):
    tokens = shlex.split(arguments, posix=False) if arguments else []
    return [token[1:-1] if len(token) > 1 and token[0] == token[-1] and token[0] in "\"'" else token for token in tokens]

def outcome(function, arguments):
    try: return function(arguments)
    except ValueError: return ValueError

def test_split_arguments_unquotes_and_keeps_windows_paths():
    assert split_arguments('--run "C:\\Users\\Admin\\Runs\\a b" --plot') == ["--run", "C:\\Users\\Admin\\Runs\\a b", "--plot"]
    assert split_arguments("") == [] and split_arguments(None) == []

def test_split_arguments_refuses_an_unclosed_quote():
    with pytest.raises(ValueError):
        split_arguments('--ticker "EURUSD')

def test_split_arguments_round_trips_join_arguments():
    parts = ["--strategy", "Trend", "--run", "C:\\Temp\\Runs\\a b", "--label", ""]
    assert split_arguments(join_arguments(parts)) == parts

def test_split_arguments_agrees_with_non_posix_shlex():
    generator = random.Random(7)
    alphabet = ["a", "b", " ", " ", "\"", "'", "\t", "-", "=", "\n", "\r", "\\", "#", "\x0b", "\u00e9", "\u00a0"]
    for _ in range(20000):
        text = "".join(generator.choice(alphabet) for _ in range(generator.randint(0, 14)))
        assert outcome(split_arguments, text) == outcome(reference, text), ascii(text)

def _gone_(pid: int, seconds: float = 10.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not psutil.pid_exists(pid) or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE: return True
        time.sleep(0.1)
    return False

@pytest.mark.skipif(not is_windows(), reason="Job objects are a Windows mechanism")
def test_a_tethered_child_dies_with_a_hard_killed_parent():
    code = "; ".join(["import subprocess, sys, time", "from Library.Utility.Runtime import tether",
                      "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])", "job = tether(child)",
                      "print(child.pid if job else -1, flush=True)", "time.sleep(120)"])
    parent = subprocess.Popen([sys.executable, "-c", code], cwd=str(traceback_root()), stdout=subprocess.PIPE, text=True)
    child = int(parent.stdout.readline())
    assert child > 0 and psutil.pid_exists(child)
    psutil.Process(parent.pid).kill()
    parent.wait(timeout=10)
    assert _gone_(child)

@pytest.mark.skipif(not is_windows(), reason="Job objects are a Windows mechanism")
def test_releasing_a_job_ends_what_is_left_in_it():
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    job = tether(child)
    assert job is not None
    release(job)
    child.wait(timeout=10)
    assert child.returncode is not None

def test_release_accepts_no_job():
    release(None)