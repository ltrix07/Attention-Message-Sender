from dataclasses import dataclass, field
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class Paths:
    """All important filesystem paths used in the project."""
    base_dir: Path = BASE_DIR

    creds_dir: Path = BASE_DIR / "creds"
    db_dir: Path = BASE_DIR / "db"
    cech_dir: Path = BASE_DIR / "cech"

    telegram_creds: Path = creds_dir / "telegram.json"
    google_creds: Path = creds_dir / "google_creds.json"

    staff: Path = db_dir / "staff.json"
    spreadsheets: Path = db_dir / "spreadsheets.json"
    chat_data: Path = db_dir / "chat_data.json"

    sqlite_db: Path = cech_dir / "messages.db"


@dataclass
class Settings:
    """
    Global project settings container.

    For now it only exposes filesystem paths, but you can easily add
    numeric thresholds, API URLs, etc.
    """
    paths: Paths = field(default_factory=Paths)


settings = Settings()
