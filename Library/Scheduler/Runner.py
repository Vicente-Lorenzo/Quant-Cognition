from argparse import ArgumentParser, Namespace

from Library.Scheduler.Task import TaskAPI
from Library.Scheduler.Executor import ExecutorAPI
from Library.Database import PostgresDatabaseAPI
from Library.Utility.Command import CommandAPI

class RunnerCommandAPI(CommandAPI):

    def __init__(self) -> None:
        super().__init__(name="Runner", refusals=())

    @staticmethod
    def load(database: str, tid: str) -> TaskAPI:
        with PostgresDatabaseAPI(database=database) as db:
            task = TaskAPI(UID=tid, db=db, autoload=True)
        task._db_ = None
        return task

    def arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("tid")
        parser.add_argument("--cycle", default=None)
        parser.add_argument("--retry", type=int, default=0)
        parser.add_argument("--manual", action="store_true")
        parser.add_argument("--arguments", default=None)
        parser.add_argument("--auditor", default=None)
        parser.add_argument("--database", default="Quant")

    def run(self, args: Namespace) -> int:
        task = self.load(args.database, args.tid)
        ExecutorAPI(database=args.database).run(task, cycle=args.cycle, retry=args.retry, manual=args.manual, arguments=args.arguments, auditor=args.auditor)
        return 0

if __name__ == "__main__":
    raise SystemExit(RunnerCommandAPI().main())