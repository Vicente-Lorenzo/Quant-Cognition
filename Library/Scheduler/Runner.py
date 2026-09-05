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
    parser.add_argument("--cycle", default=None)
    parser.add_argument("--retry", type=int, default=0)
    parser.add_argument("--manual", action="store_true")
    parser.add_argument("--arguments", default=None)
    parser.add_argument("--database", default="Quant")
    arguments = parser.parse_args()
    task = load(arguments.database, arguments.tid)
    ExecutorAPI(database=arguments.database).run(task, cycle=arguments.cycle, retry=arguments.retry, manual=arguments.manual, arguments=arguments.arguments)

if __name__ == "__main__":
    main()