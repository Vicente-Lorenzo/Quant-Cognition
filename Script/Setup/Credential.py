import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Credential import CredentialAPI
from Library.Database import QueryAPI
from Library.Logging import LoggingAPI
from Script.Task import migrate, provision

def setup_credential(db):
    db.create(schema=CredentialAPI.Schema)
    migrate(db, CredentialAPI)
    db.executeone(QueryAPI(f'CREATE UNIQUE INDEX IF NOT EXISTS "Credential_Service_Name_idx" ON "{CredentialAPI.Schema}"."{CredentialAPI.Table}" ("Service", "Name")'))

def main(database="Quant"):
    with LoggingAPI() as log:
        return provision(log, "Credential", setup_credential, database=database, detail="Schema + 1 Table + 1 Index")

if __name__ == "__main__":
    raise SystemExit(main())