import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Credential import VaultAPI
from Library.Logging import LoggingAPI
from Script.Task import attempt

def refresh_credentials(vault: VaultAPI) -> str:
    due = vault.due()
    refreshed, pending = [], []
    for row in due:
        (refreshed if vault.rotate(row["UID"]) else pending).append(f"{row['Service']} · {row['Name']}")
    detail = f"{len(refreshed)} Refreshed · {len(pending)} Pending"
    return f"{detail} · {' · '.join(pending)}" if pending else detail

def main(database="Quant"):
    with LoggingAPI() as log:
        vault = VaultAPI(database=database)
        return attempt(log, "Credential", lambda: refresh_credentials(vault), detail=f"Margin {vault.Margin // 86400} Days")

if __name__ == "__main__":
    raise SystemExit(main())