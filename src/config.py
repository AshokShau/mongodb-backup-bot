from os import getenv
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def get_env_int(name: str, default: Optional[int] = None) -> Optional[int]:
    value = getenv(name)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


API_ID: Optional[int] = get_env_int("API_ID")
API_HASH: Optional[str] = getenv("API_HASH")
TOKEN: Optional[str] = getenv("TOKEN")
OWNER_ID: int = get_env_int("OWNER_ID", 5938660179)
DATABASES_PER_PAGE = get_env_int('MONGODB_BACKUP_PAGE_SIZE', 8)
