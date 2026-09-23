import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Credential import CredentialManagerAPI
from Library.Logging import LoggingAPI
from Script.Task import attempt

def refresh_credentials(manager: CredentialManagerAPI) -> str:
    due = manager.due()
    refreshed, pending = [], []
    for row in due:
        (refreshed if manager.rotate(row["UID"]) else pending).append(f"{row['Service']} · {row['Name']}")
    detail = f"{len(refreshed)} Refreshed · {len(pending)} Pending"
    return f"{detail} · {' · '.join(pending)}" if pending else detail

def main(database="Quant"):
    with LoggingAPI() as log:
        manager = CredentialManagerAPI(database=database)
        return attempt(log, "Credential", lambda: refresh_credentials(manager), detail=f"Margin {manager.Margin // 86400} Days")

if __name__ == "__main__":
    raise SystemExit(main())