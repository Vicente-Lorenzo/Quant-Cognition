from Library.Utility.Progress import Phase, ProgressAPI

def migrate(db, *datapoints) -> None:
    for datapoint in datapoints: datapoint(db=db, migrate=True, autoload=False)

def attempt(log, name: str, work, *, detail: str = "", operation: str = "Setup") -> int:
    ProgressAPI.phase(Phase.Running)
    try:
        outcome = work()
        log.info(lambda: f"{name} {operation}: Completed · {outcome if isinstance(outcome, str) else detail}")
        return 0
    except Exception as error:
        log.exception(lambda error=error: f"{name} {operation}: Failed · Due to {error}")
        return 1
    finally:
        ProgressAPI.phase(Phase.Terminating)

def provision(log, name: str, work, *, database: str = "Quant", detail: str = "") -> int:
    def connected():
        from Library.Database import PostgresDatabaseAPI
        with PostgresDatabaseAPI(database=database) as db: return work(db)
    return attempt(log, name, connected, detail=detail)