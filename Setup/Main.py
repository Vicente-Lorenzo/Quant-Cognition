import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Setup.Universe import populate
from Setup.Strategy import generate_csharp_enum as generate_strategy_enum
from Setup.Logging import generate_csharp_enum as generate_logging_enum
from Library.Database.Postgres.Postgres import PostgresAPI
from Library.Logging import HandlerLoggingAPI

def main():
    with HandlerLoggingAPI() as logger:
        parser = argparse.ArgumentParser(description="Setup workspace and populate database.")
        parser.add_argument("--env", type=str, default="Tests", choices=["Quant", "Tests"], help="Target database environment")
        parser.add_argument("--force", action="store_true", help="Bypass confirmation prompt for production database")
        parser.add_argument("--universe", action="store_true", help="Populate Universe tables")
        parser.add_argument("--enums", action="store_true", help="Generate C# enums for Connector")
        parser.add_argument("--all", action="store_true", help="Perform all setup tasks")
        args = parser.parse_args()
        if args.enums or args.all:
            logger.info("Generating C# Enums...")
            strategy_path = generate_strategy_enum()
            logging_path = generate_logging_enum()
            logger.info(f"Generated: {strategy_path}")
            logger.info(f"Generated: {logging_path}")
        if args.universe or args.all:
            env = args.env
            if env == "Quant" and not args.force:
                logger.warning("CRITICAL: You are about to populate the PRODUCTION 'Quant' database.")
                confirm = input("Proceed? (y/n): ")
                if confirm.lower() != 'y':
                    logger.info("Population cancelled by user.")
                    return
            logger.info(f"Connecting to database: {env}")
            db = PostgresAPI(database=env)
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