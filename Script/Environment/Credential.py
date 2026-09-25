import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Credential import VaultAPI
from Library.Logging import LoggingAPI
from Library.Spotware.Token import TokenAPI
from Script.Task import attempt

def refresh_credentials(vault: VaultAPI) -> str:
    refreshed, pending, failed = [], [], []
    with vault.scope():
        for row in vault.due():
            label = f"{row['Service']} · {row['Name']}"
            try: (refreshed if vault.rotate(row["UID"]) else pending).append(label)
            except Exception as error: failed.append(f"{label} ({type(error).__name__})")
    detail = " · ".join([f"{len(refreshed)} Refreshed · {len(pending)} Pending · {len(failed)} Failed", *pending, *failed])
    if failed: raise RuntimeError(detail)
    return detail

def main(database="Quant"):
    with LoggingAPI() as log:
        return attempt(log, "Credential", lambda: refresh_credentials(VaultAPI(database=database, refreshers={"Spotware": TokenAPI.refresh})))

if __name__ == "__main__":
    raise SystemExit(main())