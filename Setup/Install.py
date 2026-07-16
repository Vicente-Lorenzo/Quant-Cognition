import sys
import subprocess
from argparse import ArgumentParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Auth.Auth import AuthAPI
from Library.Scheduler.Manager import ManagerAPI
from Library.Scheduler.Workflow import Kind
from Library.Scheduler.Task import TaskType
from Library.Database import PostgresDatabaseAPI
from Library.Logging import HandlerLoggingAPI
from Library.Utility.Path import traceback_root
from Setup.Enum import write_all
from Setup.Auth import setup_auth, seed_admin, ADMIN
from Setup.Scheduler import setup_scheduler
from Setup.Universe import populate_universe
from Setup.Market import populate_market
from Setup.Portfolio import populate_portfolio
from Setup.Indicator import setup_indicator

OWNER = ADMIN
ORCHESTRATOR = "Quant Scheduler"
LAUNCHER = str(traceback_root() / "Scripts" / "Scheduler.py")
WORKFLOWS = [
    {
        "uid": "Setup", "name": "Setup", "schedule": None, "kind": Kind.Manual, "tolerates": False,
        "description": "Zero-to-hero provisioning of all Quant database schemas and tables — launched manually",
        "tasks": [
            {"uid": "Setup.Enums", "name": "Setup Enums", "path": "Setup/Enum.py", "kind": Kind.Scheduled, "description": "Generates the C# Connector enum source from the Python enumerations"},
            {"uid": "Setup.Auth", "name": "Setup Auth", "path": "Setup/Auth.py", "kind": Kind.Scheduled, "description": "Creates the Auth schema (Team · Office · User) and seeds the administrator account"},
            {"uid": "Setup.Scheduler", "name": "Setup Scheduler", "path": "Setup/Scheduler.py", "kind": Kind.Scheduled, "description": "Creates the Scheduler schema (Workflow · Task · Dependency · Run)"},
            {"uid": "Setup.Universe", "name": "Setup Universe", "path": "Setup/Universe.py", "kind": Kind.Scheduled, "description": "Creates and populates the Universe schema (categories · providers · tickers · contracts · securities · timeframes)"},
            {"uid": "Setup.Market", "name": "Setup Market", "path": "Setup/Market.py", "kind": Kind.Scheduled, "description": "Creates the Market schema (Tick · Bar)"},
            {"uid": "Setup.Portfolio", "name": "Setup Portfolio", "path": "Setup/Portfolio.py", "kind": Kind.Scheduled, "description": "Creates the Portfolio schema (Session · Account · Order · Position · Trade)"},
            {"uid": "Setup.Indicator", "name": "Setup Indicator", "path": "Setup/Indicator.py", "kind": Kind.Scheduled, "description": "Creates the Indicator schema (Calendar)"}
        ],
        "edges": [
            ("Setup.Auth", "Setup.Scheduler"),
            ("Setup.Universe", "Setup.Market"),
            ("Setup.Universe", "Setup.Portfolio")
        ]
    },
    {
        "uid": "Environment", "name": "Environment", "schedule": "0 4 * * 0", "kind": Kind.Scheduled, "tolerates": True,
        "description": "Weekly maintenance — refreshes the Quant conda environment then relaunches the always-on tunnel and application server",
        "tasks": [
            {"uid": "Environment.Cache", "name": "Cache Cleanup", "path": "Scripts/Cache.py", "kind": Kind.Scheduled, "description": "Removes Python bytecode and tooling caches plus C# build artifacts across the repository"},
            {"uid": "Environment.Update", "name": "Environment Update", "path": "Setup/Environment.py", "kind": Kind.Scheduled, "description": "Syncs the active conda environment to the pinned Quant manifest while the services are suspended"},
            {"uid": "Environment.Tunnel", "name": "Cloudflare Tunnel", "path": "Library/Web/Tunnel.py", "kind": Kind.Service, "description": "Runs the named Cloudflare tunnel exposing the loopback app server to the public edge"},
            {"uid": "Environment.Server", "name": "Application Server", "path": "Library/Web/Tray.py", "kind": Kind.Service, "description": "Serves the Quant Cognition Dash application under waitress with its own system-tray controls"}
        ],
        "edges": [
            ("Environment.Cache", "Environment.Update"),
            ("Environment.Update", "Environment.Tunnel"),
            ("Environment.Tunnel", "Environment.Server")
        ]
    },
    {
        "uid": "Market", "name": "Market Data", "schedule": "0 6 * * *", "kind": Kind.Scheduled, "tolerates": True,
        "description": "Daily download and update of market and fundamental data into the database",
        "tasks": [
            {"uid": "Market.Calendar", "name": "Economic Calendar", "path": "Library/Indicator/Fundamental/Calendar.py", "kind": Kind.Scheduled, "description": "Downloads and updates the Forex Factory economic calendar (previous · current · next week)"}
        ],
        "edges": []
    }
]

def bootstrap(database="Quant"):
    with PostgresDatabaseAPI(database=database) as db:
        setup_auth(db)
        setup_scheduler(db)
    seed_admin(AuthAPI(database=database))

def provision(database="Quant"):
    write_all()
    with PostgresDatabaseAPI(database=database) as db:
        setup_auth(db)
        setup_scheduler(db)
        populate_universe(db)
        populate_market(db)
        populate_portfolio(db)
        setup_indicator(db)
    seed_admin(AuthAPI(database=database))

def register(manager):
    for workflow in WORKFLOWS:
        manager.create_workflow(UID=workflow["uid"], Name=workflow["name"], Owner=OWNER, Kind=workflow["kind"], Description=workflow["description"], Schedule=workflow["schedule"], Enabled=True, Waits=True)
        for task in workflow["tasks"]:
            service = task["kind"] is Kind.Service
            manager.create_task(UID=task["uid"], Name=task["name"], Owner=OWNER, WID=workflow["uid"], Type=TaskType.Python, Kind=task["kind"], Path=task["path"], Description=task["description"], Enabled=True, MaxRetry=0, RetryDelay=15 if service else 0, RequiresApproval=False, RequiresReview=False, Waits=True, Tolerates=workflow["tolerates"])
        for predecessor, successor in workflow["edges"]:
            manager.link(workflow["uid"], predecessor, successor)

def schedule_orchestrator():
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    interpreter = pythonw if pythonw.exists() else Path(sys.executable)
    command = f'"{interpreter}" "{LAUNCHER}"'
    subprocess.run(["schtasks", "/Create", "/TN", ORCHESTRATOR, "/TR", command, "/SC", "ONLOGON", "/F"], check=True)

def main(database="Quant", boot=False):
    with HandlerLoggingAPI(Class="Setup", Subclass="Install") as log:
        try:
            provision(database)
            register(ManagerAPI(database=database))
        except Exception as error:
            log.exception(lambda: f"Install Setup: Failed · Due to {error}")
            return 1
        if boot:
            try:
                schedule_orchestrator()
                log.info(lambda: f"Install Setup: Scheduled ({ORCHESTRATOR}) · {LAUNCHER}")
            except Exception as error:
                log.warning(lambda: f"Install Setup: Boot Task Skipped · Due to {error} · Register {ORCHESTRATOR} manually")
        log.info(lambda: f"Install Setup: Completed · {database} Database · {len(WORKFLOWS)} Workflows · {sum(len(workflow['tasks']) for workflow in WORKFLOWS)} Tasks")
        return 0

def _cli_():
    parser = ArgumentParser(prog="Install")
    parser.add_argument("--database", default="Quant", choices=["Quant", "Tests"])
    parser.add_argument("--boot", action="store_true")
    args = parser.parse_args()
    return main(args.database, args.boot)

if __name__ == "__main__":
    raise SystemExit(_cli_())