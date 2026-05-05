import sys
import argparse

from Setup.Universe import populate
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Logging import HandlerLoggingAPI

def main():
    with HandlerLoggingAPI() as logger:
        parser = argparse.ArgumentParser(description="Populate the database with universe data.")
        parser.add_argument("--env", type=str, default="Tests", choices=["Quant", "Tests"], help="Target database environment")
        parser.add_argument("--force", action="store_true", help="Bypass confirmation prompt for production database")
        args = parser.parse_args()
        env = args.env
        if env == "Quant" and not args.force:
            logger.warning("CRITICAL: You are about to populate the PRODUCTION 'Quant' database.")
            confirm = input("Proceed? (y/n): ")
            if confirm.lower() != 'y':
                logger.info("Population cancelled by user.")
                sys.exit(0)
        logger.info(f"Connecting to database: {env}")
        db = PostgresDatabaseAPI(database=env)
        db.connect()
        try:
            logger.info("Populating universe...")
            populate(db)
            logger.info("Population completed successfully.")
        except Exception as e:
            logger.exception(f"An error occurred during population: {e}")
            sys.exit(1)
        finally:
            logger.info("Disconnecting from database.")
            db.disconnect()
if __name__ == "__main__":
    main()