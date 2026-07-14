import sys
from argparse import ArgumentParser, Namespace, SUPPRESS
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Library.Logging import HandlerLoggingAPI, VerboseLevel
from Library.Scheduler.Manager import ManagerAPI
from Library.Scheduler.Scheduler import SchedulerAPI
from Library.Scheduler.Task import TaskType, TaskKind

_TASK_MAP_ = {"name": "Name", "owner": "Owner", "workflow": "WID", "description": "Description", "type": "Type", "kind": "Kind", "path": "Path", "schedule": "Schedule", "max_attempts": "MaxAttempts", "retry_delay": "RetryDelay"}
_WORKFLOW_MAP_ = {"name": "Name", "owner": "Owner", "description": "Description", "schedule": "Schedule"}
_TASK_COLUMNS_ = ["UID", "Name", "Type", "Kind", "Enabled", "Schedule", "WID"]
_WORKFLOW_COLUMNS_ = ["UID", "Name", "Enabled", "Schedule"]
_RUN_COLUMNS_ = ["UID", "TID", "Status", "Attempt", "StartedAt", "Duration", "ExitCode"]

def _table_(rows: list, columns: list) -> None:
    if not rows:
        print("(none)")
        return
    widths = {column: max(len(column), *(len(str(row.get(column, ""))) for row in rows)) for column in columns}
    print("  ".join(column.ljust(widths[column]) for column in columns))
    for row in rows:
        print("  ".join(str(row.get(column, "")).ljust(widths[column]) for column in columns))

def _detail_(row: dict) -> None:
    if row is None:
        print("(not found)")
        return
    for key, value in row.items():
        if value is not None: print(f"{key}: {value}")

def _fields_(args: Namespace, mapping: dict) -> dict:
    return {name: getattr(args, dest) for dest, name in mapping.items() if hasattr(args, dest)}

def _parse_() -> Namespace:
    parser = ArgumentParser(prog="Scheduler")
    parser.add_argument("--database", default="Quant", choices=["Quant", "Tests"])
    parser.add_argument("--console", default=VerboseLevel.Info.name, choices=[level.name for level in VerboseLevel])
    parser.add_argument("--file", default=VerboseLevel.Debug.name, choices=[level.name for level in VerboseLevel])
    resource = parser.add_subparsers(dest="resource", required=True)

    workflow = resource.add_parser("workflow").add_subparsers(dest="action", required=True)
    create = workflow.add_parser("create")
    create.add_argument("--uid", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--owner", required=True)
    create.add_argument("--schedule", default=None)
    create.add_argument("--description", default=None)
    create.add_argument("--disabled", action="store_true")
    update = workflow.add_parser("update")
    update.add_argument("--uid", required=True)
    update.add_argument("--name", default=SUPPRESS)
    update.add_argument("--owner", default=SUPPRESS)
    update.add_argument("--description", default=SUPPRESS)
    update.add_argument("--schedule", default=SUPPRESS)
    for action in ("delete", "show", "enable", "disable", "run"):
        workflow.add_parser(action).add_argument("--uid", required=True)
    workflow.add_parser("list").add_argument("--enabled", action="store_true")
    for action in ("link", "unlink"):
        edge = workflow.add_parser(action)
        edge.add_argument("--uid", required=True)
        edge.add_argument("--predecessor", required=True)
        edge.add_argument("--successor", required=True)

    task = resource.add_parser("task").add_subparsers(dest="action", required=True)
    create = task.add_parser("create")
    create.add_argument("--uid", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--owner", required=True)
    create.add_argument("--type", required=True, choices=[member.name for member in TaskType])
    create.add_argument("--kind", default=TaskKind.Scheduled.name, choices=[member.name for member in TaskKind])
    create.add_argument("--path", required=True)
    create.add_argument("--schedule", default=None)
    create.add_argument("--workflow", default=None)
    create.add_argument("--description", default=None)
    create.add_argument("--max-attempts", type=int, default=1)
    create.add_argument("--retry-delay", type=int, default=0)
    create.add_argument("--approval", action="store_true")
    create.add_argument("--review", action="store_true")
    create.add_argument("--disabled", action="store_true")
    update = task.add_parser("update")
    update.add_argument("--uid", required=True)
    update.add_argument("--name", default=SUPPRESS)
    update.add_argument("--owner", default=SUPPRESS)
    update.add_argument("--workflow", default=SUPPRESS)
    update.add_argument("--description", default=SUPPRESS)
    update.add_argument("--type", default=SUPPRESS, choices=[member.name for member in TaskType])
    update.add_argument("--kind", default=SUPPRESS, choices=[member.name for member in TaskKind])
    update.add_argument("--path", default=SUPPRESS)
    update.add_argument("--schedule", default=SUPPRESS)
    update.add_argument("--max-attempts", type=int, default=SUPPRESS)
    update.add_argument("--retry-delay", type=int, default=SUPPRESS)
    for action in ("delete", "show", "enable", "disable"):
        task.add_parser(action).add_argument("--uid", required=True)
    execute = task.add_parser("run")
    execute.add_argument("--uid", required=True)
    execute.add_argument("--wait", action="store_true")
    listing = task.add_parser("list")
    listing.add_argument("--workflow", default=None)
    listing.add_argument("--enabled", action="store_true")

    run = resource.add_parser("run").add_subparsers(dest="action", required=True)
    run.add_parser("show").add_argument("--uid", required=True)
    for action in ("approve", "reject"):
        gate = run.add_parser(action)
        gate.add_argument("--uid", required=True)
        gate.add_argument("--by", default="CLI")
    listing = run.add_parser("list")
    listing.add_argument("--task", default=None)
    listing.add_argument("--workflow-run", default=None)
    listing.add_argument("--status", default=None)
    listing.add_argument("--limit", type=int, default=50)

    resource.add_parser("serve")
    return parser.parse_args()

def _workflow_(manager: ManagerAPI, args: Namespace) -> None:
    match args.action:
        case "create": print(f"Workflow '{manager.create_workflow(UID=args.uid, Enabled=not args.disabled, **_fields_(args, _WORKFLOW_MAP_)).UID}' created")
        case "update": print(f"Workflow '{args.uid}' updated" if manager.update_workflow(args.uid, **_fields_(args, _WORKFLOW_MAP_)) else f"Workflow '{args.uid}' not found")
        case "delete": print(f"Workflow '{args.uid}' deleted" if manager.delete_workflow(args.uid) else f"Workflow '{args.uid}' not found")
        case "enable": print(f"Workflow '{args.uid}' enabled" if manager.enable_workflow(args.uid) else f"Workflow '{args.uid}' not found")
        case "disable": print(f"Workflow '{args.uid}' disabled" if manager.disable_workflow(args.uid) else f"Workflow '{args.uid}' not found")
        case "run": print(f"Workflow '{args.uid}' dispatched · {manager.run_workflow(args.uid)}" if manager.workflow(args.uid) else f"Workflow '{args.uid}' not found")
        case "link": print("Linked" if manager.link(args.uid, args.predecessor, args.successor) else "Rejected · Would create a cycle")
        case "unlink": print("Unlinked" if manager.unlink(args.uid, args.predecessor, args.successor) else f"Workflow '{args.uid}' not found")
        case "show":
            _detail_(manager.workflow(args.uid))
            _table_(manager.tasks(workflow=args.uid), _TASK_COLUMNS_)
            _table_(manager.dependencies(args.uid), ["Predecessor", "Successor"])
        case "list": _table_(manager.workflows(enabled=True if args.enabled else None), _WORKFLOW_COLUMNS_)

def _task_(manager: ManagerAPI, args: Namespace) -> None:
    match args.action:
        case "create": print(f"Task '{manager.create_task(UID=args.uid, Enabled=not args.disabled, RequiresApproval=args.approval, RequiresReview=args.review, **_fields_(args, _TASK_MAP_)).UID}' created")
        case "update": print(f"Task '{args.uid}' updated" if manager.update_task(args.uid, **_fields_(args, _TASK_MAP_)) else f"Task '{args.uid}' not found")
        case "delete": print(f"Task '{args.uid}' deleted" if manager.delete_task(args.uid) else f"Task '{args.uid}' not found")
        case "enable": print(f"Task '{args.uid}' enabled" if manager.enable_task(args.uid) else f"Task '{args.uid}' not found")
        case "disable": print(f"Task '{args.uid}' disabled" if manager.disable_task(args.uid) else f"Task '{args.uid}' not found")
        case "run":
            if manager.task(args.uid) is None: print(f"Task '{args.uid}' not found")
            else:
                result = manager.run_task(args.uid, wait=args.wait)
                print(f"Run '{result.UID}' finished · {result.Status}" if result else f"Task '{args.uid}' dispatched")
        case "show": _detail_(manager.task(args.uid))
        case "list": _table_(manager.tasks(workflow=args.workflow, enabled=True if args.enabled else None), _TASK_COLUMNS_)

def _run_(manager: ManagerAPI, args: Namespace) -> None:
    match args.action:
        case "show": _detail_(manager.run(args.uid))
        case "approve": print(f"Run '{args.uid}' approved" if manager.approve(args.uid, args.by) else f"Run '{args.uid}' not awaiting approval")
        case "reject": print(f"Run '{args.uid}' rejected" if manager.reject(args.uid, args.by) else f"Run '{args.uid}' not awaiting review")
        case "list": _table_(manager.runs(task=args.task, workflow_run=args.workflow_run, status=args.status, limit=args.limit), _RUN_COLUMNS_)

def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")
    args = _parse_()
    log = HandlerLoggingAPI(Class=ManagerAPI.__name__, Subclass="Management")
    log.console.set_verbose_level(VerboseLevel[args.console])
    log.file.set_verbose_level(VerboseLevel[args.file])
    if args.resource == "serve":
        SchedulerAPI(database=args.database).start()
        return
    manager = ManagerAPI(database=args.database)
    match args.resource:
        case "workflow": _workflow_(manager, args)
        case "task": _task_(manager, args)
        case "run": _run_(manager, args)

if __name__ == "__main__":
    main()