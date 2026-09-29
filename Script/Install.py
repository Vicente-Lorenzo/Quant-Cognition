import sys
import subprocess
from argparse import ArgumentParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Auth.Auth import AuthAPI
from Library.Auth.Role import RoleAPI
from Library.Scheduler.Manager import ManagerAPI
from Library.Scheduler.Workflow import Kind
from Library.Scheduler.Task import TaskType
from Library.Scheduler.Tray import TrayAPI
from Library.Database import PostgresDatabaseAPI
from Library.Logging import LoggingAPI
from Library.Utility.Path import traceback_root
from Library.Utility.Runtime import windowless
from Script.Setup.Enum import write_all
from Script.Setup.Auth import setup_auth, seed_admin, ADMIN
from Script.Setup.Credential import setup_credential
from Script.Setup.Scheduler import setup_scheduler
from Script.Setup.Universe import populate_universe
from Script.Setup.Market import populate_market
from Script.Setup.Portfolio import populate_portfolio
from Script.Setup.Indicator import setup_indicator

OWNER = ADMIN
GUARD = RoleAPI.Administrator.name
ORCHESTRATOR = "Quant Scheduler"
LAUNCHER = str(traceback_root() / "Script" / "Scheduler.py")
WORKFLOWS = [
    {
        "uid": "Setup", "name": "Setup", "schedule": None, "kind": Kind.Manual, "tolerates": False,
        "description": "Zero-to-hero provisioning of all Quant database schemas and tables — launched manually",
        "tasks": [
            {"uid": "Setup.Enums", "name": "Setup Enums", "path": "Script/Setup/Enum.py", "kind": Kind.Scheduled, "description": "Generates the C# Connector enum source from the Python enumerations"},
            {"uid": "Setup.Auth", "name": "Setup Auth", "path": "Script/Setup/Auth.py", "kind": Kind.Scheduled, "description": "Creates the Auth schema (Team · Office · User) and seeds the administrator account"},
            {"uid": "Setup.Credential", "name": "Setup Credential", "path": "Script/Setup/Credential.py", "kind": Kind.Scheduled, "description": "Creates the Credential schema holding every external API secret with its View and Edit thresholds"},
            {"uid": "Setup.Logging", "name": "Setup Logging", "path": "Script/Setup/Logging.py", "kind": Kind.Scheduled, "description": "Creates the Logging schema (Log) holding one durable row per captured log"},
            {"uid": "Setup.Scheduler", "name": "Setup Scheduler", "path": "Script/Setup/Scheduler.py", "kind": Kind.Scheduled, "description": "Creates the Scheduler schema (Workflow · Task · Dependency · Run)"},
            {"uid": "Setup.Universe", "name": "Setup Universe", "path": "Script/Setup/Universe.py", "kind": Kind.Scheduled, "description": "Creates the Universe schema (categories · providers · tickers · securities · dated contracts) and seeds the timeframes · the catalog comes from the Universe service"},
            {"uid": "Setup.Market", "name": "Setup Market", "path": "Script/Setup/Market.py", "kind": Kind.Scheduled, "description": "Creates the Market schema (the Tick hypertable and the Download record)"},
            {"uid": "Setup.Portfolio", "name": "Setup Portfolio", "path": "Script/Setup/Portfolio.py", "kind": Kind.Scheduled, "description": "Creates the Portfolio schema (Account · Order · Position · Trade · Cashflow), the mirror of the tracked broker accounts"},
            {"uid": "Setup.Indicator", "name": "Setup Indicator", "path": "Script/Setup/Indicator.py", "kind": Kind.Scheduled, "description": "Creates the Indicator schema (Calendar)"}
        ],
        "edges": [
            ("Setup.Auth", "Setup.Credential"),
            ("Setup.Credential", "Setup.Logging"),
            ("Setup.Logging", "Setup.Scheduler"),
            ("Setup.Scheduler", "Setup.Universe"),
            ("Setup.Universe", "Setup.Portfolio"),
            ("Setup.Universe", "Setup.Market"),
            ("Setup.Portfolio", "Setup.Indicator"),
            ("Setup.Market", "Setup.Indicator"),
            ("Setup.Indicator", "Setup.Enums")
        ]
    },
    {
        "uid": "Environment", "name": "Environment", "schedule": "0 4 * * *", "kind": Kind.Scheduled, "tolerates": True,
        "description": "Daily maintenance — builds and tests the next Quant environment, then clears stale caches and expired logs",
        "tasks": [
            {"uid": "Environment.Update", "name": "Environment Update", "path": "Script/Environment/Update.py", "kind": Kind.Scheduled, "description": "Builds Quant.next from Quant.yml when anything newer exists and validates it with the suite · the launcher applies it at the next logon"},
            {"uid": "Environment.Cache", "name": "Cache Cleanup", "path": "Script/Environment/Cache.py", "kind": Kind.Scheduled, "description": "Removes Python bytecode and tooling caches plus C# build artifacts across the repository"},
            {"uid": "Environment.Retention", "name": "Log Retention", "path": "Script/Environment/Retention.py", "kind": Kind.Scheduled, "description": "Prunes expired log files from the temporary folders and expired log rows from the Logging schema"}
        ],
        "edges": [
            ("Environment.Update", "Environment.Cache"),
            ("Environment.Cache", "Environment.Retention")
        ]
    },
    {
        "uid": "Web", "name": "Web Application", "schedule": "0 4 * * *", "kind": Kind.Scheduled, "tolerates": True,
        "description": "The public web application — checks its frontend library, then runs the Cloudflare tunnel and the application server",
        "tasks": [
            {"uid": "Web.Version", "name": "Version Check", "path": "Script/Web/Version.py", "kind": Kind.Scheduled, "description": "Reports when a vendored frontend library has a newer release upstream — never upgrades automatically"},
            {"uid": "Web.Tunnel", "name": "Cloudflare Tunnel", "path": "Script/Web/Tunnel.py", "kind": Kind.Service, "description": "Runs the named Cloudflare tunnel exposing the loopback app server to the public edge"},
            {"uid": "Web.Server", "name": "Application Server", "path": "Script/Web/Server.py", "kind": Kind.Service, "description": "Serves the Quant Cognition Dash application under waitress with its own system-tray controls"}
        ],
        "edges": [
            ("Web.Version", "Web.Tunnel"),
            ("Web.Tunnel", "Web.Server")
        ]
    },
    {
        "uid": "Data", "name": "Data Intelligence", "schedule": "0 6 * * *", "kind": Kind.Scheduled, "tolerates": True,
        "description": "Everything data — refreshes the credentials the data services use, then downloads market, fundamental and alternative data",
        "tasks": [
            {"uid": "Data.Credential", "name": "Credential Refresh", "path": "Script/Data/Credential.py", "kind": Kind.Scheduled, "description": "Refreshes every stored credential whose expiry falls inside the margin so no service meets an expired token"},
            {"uid": "Data.Universe", "name": "Universe Service", "path": "Script/Data/Universe.py", "kind": Kind.Service, "description": "Mirrors every current symbol of the broker with its dated term sheet into the Universe schema, daily and on every symbol change"},
            {"uid": "Data.Market", "name": "Market Service", "path": "Script/Data/Market.py", "kind": Kind.Service, "description": "Backfills and follows the tick tape of every tracked security, one worker process per security, about a second behind the market"},
            {"uid": "Data.Portfolio", "name": "Portfolio Service", "path": "Script/Data/Portfolio.py", "kind": Kind.Service, "description": "Mirrors every tracked broker account (orders · positions · trades · cash flows) and derives each position's balances and excursions from the tick tape"},
            {"uid": "Data.Calendar", "name": "Economic Calendar", "path": "Script/Data/Calendar.py", "kind": Kind.Service, "description": "Backfills the missing weeks of the Forex Factory economic calendar, then keeps the current and next week fresh and follows each release until its actual lands, keeping every revision"}
        ],
        "edges": [
            ("Data.Credential", "Data.Universe"),
            ("Data.Universe", "Data.Market"),
            ("Data.Market", "Data.Portfolio"),
            ("Data.Credential", "Data.Calendar")
        ]
    }
]

STANDALONE = [
    {"uid": "Research.Backtesting", "name": "Backtesting", "path": "Library/System/Main.py", "description": "Runs the Python trading engine over a historical period and writes its report export and plot", "run": RoleAPI.Editor.name},
    {"uid": "Research.Optimization", "name": "Optimization", "path": "Library/System/Main.py", "description": "Sweeps a parameter space over walk-forward folds and re-runs the elected candidate", "run": RoleAPI.Editor.name},
    {"uid": "Research.Learning", "name": "Learning", "path": "Library/System/Main.py", "description": "Trains a deep reinforcement learning agent and promotes its weights", "run": RoleAPI.Editor.name},
]

def bootstrap(database="Quant"):
    with PostgresDatabaseAPI(database=database) as db:
        setup_auth(db)
        setup_credential(db)
        setup_scheduler(db)
    seed_admin(AuthAPI(database=database))

def provision(database="Quant"):
    write_all()
    with PostgresDatabaseAPI(database=database) as db:
        setup_auth(db)
        setup_credential(db)
        setup_scheduler(db)
        populate_universe(db)
        populate_market(db)
        populate_portfolio(db)
        setup_indicator(db)
    seed_admin(AuthAPI(database=database))

def register(manager):
    for workflow in WORKFLOWS:
        manager.create_workflow(UID=workflow["uid"], Name=workflow["name"], Owner=OWNER, RunRole=GUARD, EditRole=GUARD, Kind=workflow["kind"], Description=workflow["description"], Schedule=workflow["schedule"], Enabled=True, Waits=True)
        for task in workflow["tasks"]:
            service = task["kind"] is Kind.Service
            manager.create_task(UID=task["uid"], Name=task["name"], Owner=OWNER, RunRole=GUARD, EditRole=GUARD, WID=workflow["uid"], Type=TaskType.Python, Kind=task["kind"], Path=task["path"], Description=task["description"], Enabled=True, MaxRetry=0, RetryDelay=15 if service else 0, RequiresApproval=False, RequiresReview=False, Waits=True, Tolerates=workflow["tolerates"])
        wanted = {(predecessor, successor) for predecessor, successor in workflow["edges"]}
        for predecessor, successor in wanted:
            manager.link(workflow["uid"], predecessor, successor)
        for row in manager.dependencies(workflow["uid"]):
            edge = (row["Predecessor"], row["Successor"])
            if edge not in wanted: manager.unlink(workflow["uid"], *edge)

def enlist(manager):
    for task in STANDALONE:
        manager.create_task(
            UID=task["uid"],
            Name=task["name"],
            Owner=OWNER,
            RunRole=task["run"],
            EditRole=GUARD,
            WID=None,
            Type=TaskType.Python,
            Kind=Kind.Manual,
            Path=task["path"],
            Description=task["description"],
            Enabled=True,
            MaxRetry=0,
            RetryDelay=0,
            RequiresApproval=False,
            RequiresReview=False,
            Waits=True,
            Tolerates=True
        )

def schedule_orchestrator():
    interpreter = Path(TrayAPI.launcher()[0]).with_name("pythonw.exe")
    command = f'"{interpreter}" "{LAUNCHER}"'
    subprocess.run(["schtasks", "/Create", "/TN", ORCHESTRATOR, "/TR", command, "/SC", "ONLOGON", "/RL", "HIGHEST", "/F"], check=True, **windowless())

def main(database="Quant", boot=False, registration=False):
    with LoggingAPI() as log:
        try:
            if not registration: provision(database)
            manager = ManagerAPI(database=database)
            with manager.scope():
                register(manager)
                enlist(manager)
        except Exception as error:
            log.exception(lambda error=error: f"Install Setup: Failed · Due to {error}")
            return 1
        if boot:
            try:
                schedule_orchestrator()
                log.info(lambda: f"Install Setup: Scheduled ({ORCHESTRATOR}) · {LAUNCHER}")
            except Exception as error:
                log.warning(lambda error=error: f"Install Setup: Boot Task Skipped · Due to {error} · Register {ORCHESTRATOR} manually")
        log.info(lambda: f"Install Setup: Completed · {database} Database · {len(WORKFLOWS)} Workflows · {sum(len(workflow['tasks']) for workflow in WORKFLOWS)} Tasks")
        return 0

def _cli_():
    parser = ArgumentParser(prog="Install")
    parser.add_argument("--database", default="Quant", choices=["Quant", "Tests"])
    parser.add_argument("--boot", action="store_true")
    parser.add_argument("--register", action="store_true")
    args = parser.parse_args()
    return main(args.database, args.boot, args.register)

if __name__ == "__main__":
    raise SystemExit(_cli_())