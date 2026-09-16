def migrate(db, *datapoints) -> None:
    for datapoint in datapoints: datapoint(db=db, migrate=True, autosave=False, autoload=False)

def attempt(log, name: str, work, *, detail: str = "") -> int:
    try:
        outcome = work()
        log.info(lambda: f"{name} Setup: Completed · {outcome if isinstance(outcome, str) else detail}")
        return 0
    except Exception as error:
        log.exception(lambda error=error: f"{name} Setup: Failed · Due to {error}")
        return 1

def provision(log, name: str, work, *, database: str = "Quant", detail: str = "") -> int:
    def connected():
        from Library.Database import PostgresDatabaseAPI
        with PostgresDatabaseAPI(database=database) as db: return work(db)
    return attempt(log, name, connected, detail=detail)