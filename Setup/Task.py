from Library.Database import PostgresDatabaseAPI

def migrate(db, *datapoints) -> None:
    for datapoint in datapoints: datapoint(db=db, migrate=True, autosave=False, autoload=False)

def provision(log, name: str, work, *, database: str = "Quant", detail: str = "") -> int:
    try:
        with PostgresDatabaseAPI(database=database) as db:
            outcome = work(db)
        log.info(lambda: f"{name} Setup: Completed · {outcome if isinstance(outcome, str) else detail}")
        return 0
    except Exception as error:
        log.exception(lambda: f"{name} Setup: Failed · Due to {error}")
        return 1