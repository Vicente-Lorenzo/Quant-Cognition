from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Setup.Universe import populate_universe

def main():
    print("Connecting to database...")
    # By default DatapointAPI uses the "Quant" database, unless overridden.
    db = PostgresDatabaseAPI(database="Quant")
    db.connect()
    
    try:
        print("Populating universe...")
        populate_universe(db)
        print("Population successful.")
    finally:
        db.disconnect()

if __name__ == "__main__":
    main()
