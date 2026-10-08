import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def database_url():
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError(
            "Configure DATABASE_URL no .env ou use o iniciador iniciar.ps1."
        )
    return value
