from Library.Logging import HandlerLoggingAPI, VerboseLevel
from Library.Scheduler.Scheduler import SchedulerAPI

def build() -> SchedulerAPI:
    return SchedulerAPI(database="Quant")

def main() -> None:
    log = HandlerLoggingAPI(Class=SchedulerAPI.__name__, Subclass="Serve")
    log.console.set_verbose_level(VerboseLevel.Debug)
    log.file.set_verbose_level(VerboseLevel.Debug)
    build().start()

if __name__ == "__main__":
    main()