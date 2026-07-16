import sys
from pathlib import Path
from dataclasses import fields
from argparse import ArgumentParser, Namespace, SUPPRESS

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Library.Logging import HandlerLoggingAPI, VerboseLevel
from Library.Utility.Typing import MISSING
from Library.Scheduler.Workflow import Kind, WorkflowAPI
from Library.Scheduler.Task import TaskAPI, TaskType
from Library.Scheduler.Dependency import DependencyAPI
from Library.Scheduler.Cycle import CycleAPI
from Library.Scheduler.Run import RunAPI
from Library.Scheduler.Manager import ManagerAPI
from Library.Scheduler.Scheduler import SchedulerAPI

_WIDE_ = ("Owner", "Description", "Path", "Memory", "PID", "Auditor", "Log", "Heartbeat", "UpdatedAt", "UpdatedBy")

def _dest_(name: str) -> str:
    if name.isupper(): return name.lower()
    return "".join(f"_{char.lower()}" if index and char.isupper() else char.lower() for index, char in enumerate(name))

def _fields_(args: Namespace, model: type) -> dict:
    return {field.name: getattr(args, _dest_(field.name)) for field in fields(model) if hasattr(args, _dest_(field.name))}

def _table_(rows: list, model: type) -> None:
    columns = [field.name for field in fields(model) if field.name not in _WIDE_]
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
    create.add_argument("--kind", default=None, choices=[member.name for member in Kind])
    create.add_argument("--description", default=None)
    create.add_argument("--disabled", action="store_true")
    create.add_argument("--no-waits", action="store_true")
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
    create.add_argument("--kind", default=Kind.Scheduled.name, choices=[member.name for member in Kind])
    create.add_argument("--path", required=True)
    create.add_argument("--schedule", default=None)
    create.add_argument("--workflow", dest="wid", default=None)
    create.add_argument("--description", default=None)
    create.add_argument("--max-retry", type=int, default=0)
    create.add_argument("--retry-delay", type=int, default=0)
    create.add_argument("--approval", action="store_true")
    create.add_argument("--review", action="store_true")
    create.add_argument("--disabled", action="store_true")
    create.add_argument("--no-waits", action="store_true")
    create.add_argument("--no-tolerates", action="store_true")
    update = task.add_parser("update")
    update.add_argument("--uid", required=True)
    update.add_argument("--name", default=SUPPRESS)
    update.add_argument("--owner", default=SUPPRESS)
    update.add_argument("--workflow", dest="wid", default=SUPPRESS)
    update.add_argument("--description", default=SUPPRESS)
    update.add_argument("--type", default=SUPPRESS, choices=[member.name for member in TaskType])
    update.add_argument("--kind", default=SUPPRESS, choices=[member.name for member in Kind])
    update.add_argument("--path", default=SUPPRESS)
    update.add_argument("--schedule", default=SUPPRESS)
    update.add_argument("--max-retry", type=int, default=SUPPRESS)
    update.add_argument("--retry-delay", type=int, default=SUPPRESS)
    for action in ("delete", "show", "enable", "disable"):
        task.add_parser(action).add_argument("--uid", required=True)
    execute = task.add_parser("run")
    execute.add_argument("--uid", required=True)
    execute.add_argument("--wait", action="store_true")
    override = task.add_parser("skip")
    override.add_argument("--uid", required=True)
    override.add_argument("--failure", action="store_true")
    override.add_argument("--by", default=None)
    listing = task.add_parser("list")
    listing.add_argument("--workflow", default=MISSING)
    listing.add_argument("--enabled", action="store_true")

    cycle = resource.add_parser("cycle").add_subparsers(dest="action", required=True)
    cycle.add_parser("show").add_argument("--uid", required=True)
    listing = cycle.add_parser("list")
    listing.add_argument("--workflow", default=MISSING)
    listing.add_argument("--limit", type=int, default=50)

    run = resource.add_parser("run").add_subparsers(dest="action", required=True)
    run.add_parser("show").add_argument("--uid", required=True)
    for action in ("approve", "reject"):
        gate = run.add_parser(action)
        gate.add_argument("--uid", required=True)
        gate.add_argument("--by", default=None)
    halt = run.add_parser("cancel")
    halt.add_argument("--uid", required=True)
    halt.add_argument("--failure", action="store_true")
    halt.add_argument("--by", default=None)
    listing = run.add_parser("list")
    listing.add_argument("--task", default=MISSING)
    listing.add_argument("--cycle", default=MISSING)
    listing.add_argument("--status", default=MISSING)
    listing.add_argument("--limit", type=int, default=50)

    resource.add_parser("serve")
    return parser.parse_args()

def _workflow_(manager: ManagerAPI, args: Namespace) -> None:
    match args.action:
        case "create":
            settings = _fields_(args, WorkflowAPI)
            settings["Kind"] = args.kind or (Kind.Scheduled.name if args.schedule else Kind.Manual.name)
            print(f"Workflow '{manager.create_workflow(Enabled=not args.disabled, Waits=not args.no_waits, **settings).UID}' created")
        case "update": print(f"Workflow '{args.uid}' updated" if manager.update_workflow(args.uid, **_fields_(args, WorkflowAPI)) else f"Workflow '{args.uid}' not found")
        case "delete": print(f"Workflow '{args.uid}' deleted" if manager.delete_workflow(args.uid) else f"Workflow '{args.uid}' not found")
        case "enable": print(f"Workflow '{args.uid}' enabled" if manager.enable_workflow(args.uid) else f"Workflow '{args.uid}' not found")
        case "disable": print(f"Workflow '{args.uid}' disabled" if manager.disable_workflow(args.uid) else f"Workflow '{args.uid}' not found")
        case "run": print(f"Workflow '{args.uid}' dispatched · {manager.run_workflow(args.uid)}" if manager.workflow(args.uid) else f"Workflow '{args.uid}' not found")
        case "link": print("Linked" if manager.link(args.uid, args.predecessor, args.successor) else "Rejected · Would create a cycle")
        case "unlink": print("Unlinked" if manager.unlink(args.uid, args.predecessor, args.successor) else f"Workflow '{args.uid}' not found")
        case "show":
            _detail_(manager.workflow(args.uid))
            _table_(manager.tasks(workflow=args.uid), TaskAPI)
            _table_(manager.dependencies(args.uid), DependencyAPI)
            _table_(manager.cycles(workflow=args.uid, limit=10), CycleAPI)
        case "list": _table_(manager.workflows(enabled=True if args.enabled else MISSING), WorkflowAPI)

def _task_(manager: ManagerAPI, args: Namespace) -> None:
    match args.action:
        case "create": print(f"Task '{manager.create_task(Enabled=not args.disabled, RequiresApproval=args.approval, RequiresReview=args.review, Waits=not args.no_waits, Tolerates=not args.no_tolerates, **_fields_(args, TaskAPI)).UID}' created")
        case "update": print(f"Task '{args.uid}' updated" if manager.update_task(args.uid, **_fields_(args, TaskAPI)) else f"Task '{args.uid}' not found")
        case "delete": print(f"Task '{args.uid}' deleted" if manager.delete_task(args.uid) else f"Task '{args.uid}' not found")
        case "enable": print(f"Task '{args.uid}' enabled" if manager.enable_task(args.uid) else f"Task '{args.uid}' not found")
        case "disable": print(f"Task '{args.uid}' disabled" if manager.disable_task(args.uid) else f"Task '{args.uid}' not found")
        case "run":
            if manager.task(args.uid) is None: print(f"Task '{args.uid}' not found")
            else:
                result = manager.run_task(args.uid, wait=args.wait)
                print(f"Run '{result.UID}' finished · {result.Status}" if result else f"Task '{args.uid}' dispatched")
        case "skip":
            run = manager.skip(args.uid, failure=args.failure, by=args.by)
            print(f"Task '{args.uid}' skipped · {run.Status}" if run else f"Task '{args.uid}' not skippable · No open cycle")
        case "show": _detail_(manager.task(args.uid))
        case "list": _table_(manager.tasks(workflow=args.workflow, enabled=True if args.enabled else MISSING), TaskAPI)

def _cycle_(manager: ManagerAPI, args: Namespace) -> None:
    match args.action:
        case "show":
            _detail_(manager.cycle(args.uid))
            _table_(manager.runs(cycle=args.uid), RunAPI)
        case "list": _table_(manager.cycles(workflow=args.workflow, limit=args.limit), CycleAPI)

def _run_(manager: ManagerAPI, args: Namespace) -> None:
    match args.action:
        case "show": _detail_(manager.run(args.uid))
        case "approve": print(f"Run '{args.uid}' approved" if manager.approve(args.uid, args.by) else f"Run '{args.uid}' not awaiting approval")
        case "reject": print(f"Run '{args.uid}' rejected" if manager.reject(args.uid, args.by) else f"Run '{args.uid}' not awaiting review")
        case "cancel": print(f"Run '{args.uid}' cancelled" if manager.cancel(args.uid, failure=args.failure, by=args.by) else f"Run '{args.uid}' not live")
        case "list": _table_(manager.runs(task=args.task, cycle=args.cycle, status=args.status, limit=args.limit), RunAPI)

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
    try:
        match args.resource:
            case "workflow": _workflow_(manager, args)
            case "task": _task_(manager, args)
            case "cycle": _cycle_(manager, args)
            case "run": _run_(manager, args)
    except ValueError as error:
        print(f"Rejected · {error}")

if __name__ == "__main__":
    main()