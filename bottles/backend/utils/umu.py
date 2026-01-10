import csv
import os
from typing import Optional

import requests
from bottles.backend.logger import Logger

logging = Logger()


class UmuDatabase:
    DB_URL = "https://raw.githubusercontent.com/Open-Wine-Components/umu-database/refs/heads/main/umu-database.csv"
    DB_PATH = os.path.expanduser("~/.local/share/bottles/umu-database.csv")

    @staticmethod
    def update_database():
        try:
            logging.info("Updating UMU database...")
            response = requests.get(UmuDatabase.DB_URL, timeout=10)
            if response.status_code == 200:
                os.makedirs(os.path.dirname(UmuDatabase.DB_PATH), exist_ok=True)
                with open(UmuDatabase.DB_PATH, "wb") as f:
                    f.write(response.content)
                logging.info("UMU database updated.")
            else:
                logging.error(f"Failed to update UMU database: {response.status_code}")
        except Exception as e:
            logging.error(f"Failed to update UMU database: {e}")

    @staticmethod
    def get_umu_id(title: str) -> Optional[str]:
        if not os.path.exists(UmuDatabase.DB_PATH):
            UmuDatabase.update_database()

        if not os.path.exists(UmuDatabase.DB_PATH):
            return None

        try:
            with open(UmuDatabase.DB_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                search_title = title.lower().strip()
                for row in reader:
                    # Match Title
                    if row["TITLE"].lower().strip() == search_title:
                        return row["UMU_ID"]
        except Exception as e:
            logging.error(f"Error reading UMU database: {e}")
            return None

        return None
