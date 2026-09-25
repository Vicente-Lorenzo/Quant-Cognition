import re
import subprocess

from pathlib import Path

from Library.Utility.Path import traceback_root

ROOT = traceback_root()

SECRET = re.compile(r"""(password|passwd|passphrase|secret|api_?key|access_?token|refresh_?token|client_?secret)["']?\s*(?::\s*\w+\s*)?[=:]\s*["']([^"']{8,})["']""", re.IGNORECASE)

FIXTURES = ("Tests/", "Library/Database/Postgres/Postgres.py", "Library/Database/Oracle/Oracle.py", "Library/Database/Microsoft/Microsoft.py")

def tracked() -> list:
    listing = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [line for line in listing.stdout.splitlines() if line.endswith((".py", ".cs", ".js", ".yml", ".yaml", ".json", ".sql", ".md"))]

def exempt(path: str) -> bool:
    return any(path.startswith(allowed) or path == allowed for allowed in FIXTURES)

def test_no_tracked_file_holds_a_secret_literal():
    offenders = []
    for name in tracked():
        if exempt(name): continue
        path = ROOT / name
        if not path.is_file(): continue
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            match = SECRET.search(line)
            if match and "<" not in match.group(2) and "..." not in match.group(2): offenders.append(f"{name}:{number} {match.group(1)}")
    assert not offenders, "secret-shaped literals found: " + " · ".join(offenders)

def test_the_guard_recognises_a_secret_literal():
    for line in ('client_secret = "8f3c2a9d7e1b4f60"', 'AccessToken="8f3c2a9d7e1b4f60"', '{"Secret": "8f3c2a9d7e1b4f60"}', "RefreshToken: '8f3c2a9d7e1b4f60'"):
        assert SECRET.search(line) is not None, line

def test_the_database_drivers_are_the_only_exempt_library_files():
    assert [name for name in FIXTURES if name.startswith("Library/")] == [
        "Library/Database/Postgres/Postgres.py",
        "Library/Database/Oracle/Oracle.py",
        "Library/Database/Microsoft/Microsoft.py"
    ]