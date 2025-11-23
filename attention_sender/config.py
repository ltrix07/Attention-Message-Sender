from dataclasses import dataclass
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class Paths:
    creds_dir: Path = BASE_DIR / "creds"
    db_dir: Path = BASE_DIR / "db"
    cech_dir: Path = BASE_DIR / "cech"

    telegram_creds: Path = BASE_DIR / "creds" / "telegram.json"
    google_creds: Path = BASE_DIR / "creds" / "google_creds.json"
    staff: Path = BASE_DIR / "db" / "staff.json"
    spreadsheets: Path = BASE_DIR / "db" / "spreadsheets.json"
    chat_data: Path = BASE_DIR / "db" / "chat_data.json"
    sqlite_db: Path = BASE_DIR / "cech" / "messages.db"


@dataclass
class Settings:
    paths: Paths = Paths()


settings = Settings()
