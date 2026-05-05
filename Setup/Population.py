import argparse
from Setup.Universe import populate
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=str, default="Tests", choices=["Quant", "Tests"])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    env = args.env
    if env == "Quant" and not args.force:
        confirm = input("CRITICAL: You are about to populate the PRODUCTION 'Quant' database. Proceed? (y/n): ")
        if confirm.lower() != 'y':
            return
    db = PostgresDatabaseAPI(database=env)
    db.connect()
    try:
        populate(db)
    finally:
        db.disconnect()
if __name__ == "__main__":
    main()