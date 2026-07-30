from Library.Logging import LoggingAPI, VerboseLevel
from Library.Scheduler.Scheduler import SchedulerAPI

def build() -> SchedulerAPI:
    return SchedulerAPI(database="Quant")

def main() -> None:
    log = LoggingAPI()
    log.console.set_level(VerboseLevel.Debug)
    log.file.set_level(VerboseLevel.Debug)
    build().start()

if __name__ == "__main__":
    main()