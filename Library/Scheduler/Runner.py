from __future__ import annotations

import argparse

from Library.Scheduler.Task import TaskAPI
from Library.Scheduler.Executor import ExecutorAPI
from Library.Database import PostgresDatabaseAPI

def load(database: str, tid: str) -> TaskAPI:
    with PostgresDatabaseAPI(database=database) as db:
        task = TaskAPI(UID=tid, db=db, autoload=True)
    task._db_ = None
    return task

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tid")
    parser.add_argument("--workflow-run", default=None)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--database", default="Quant")
    arguments = parser.parse_args()
    task = load(arguments.database, arguments.tid)
    ExecutorAPI(database=arguments.database).run(task, workflow_run=arguments.workflow_run, attempt=arguments.attempt)

if __name__ == "__main__":
    main()