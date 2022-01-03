"Entry point for tha app"

import asyncio
import logging
from logging.handlers import RotatingFileHandler
from os import getenv
from pathlib import Path
from typing import Optional

from app.models import ScapingParams, WebParams
from app.storage import InMemoryWebCache
from app.web import start_webservice
from app.scraping import loop_refresh


def _env(key: str) -> str:
    value: Optional[str] = getenv(key)
    if value:
        return value
    raise KeyError(f"Environment variable {key} is not set")


def _start_logging() -> None:
    folder_path: Path = Path(_env("LOGS_FOLDER"))
    folder_path.mkdir(parents=True, exist_ok=True)

    file_path: Path = folder_path.joinpath("pse_scraping_service.log")

    logging.basicConfig(
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(
                filename=str(file_path),
                backupCount=5,
                maxBytes=102400,
                encoding="utf-8",
            ),
        ],
        level=logging.INFO,
        format="%(asctime)s:%(name)s:%(funcName)s:%(levelname)s:%(message)s",
        encoding="utf-8",
    )


def _create_cache() -> InMemoryWebCache:
    return InMemoryWebCache(
        data_folder=Path(_env("DATA_FOLDER")),
    )


async def _run_data_refresh(cache: InMemoryWebCache) -> None:
    await loop_refresh(
        cache=cache,
        scraping_params=ScapingParams(
            pse_username=_env("PSE_USERNAME"),
            pse_password=_env("PSE_PASSWORD"),
        ),
        force_first_refresh=False,
    )


async def _run_web_service(cache: InMemoryWebCache) -> None:
    await start_webservice(
        cache=cache,
        params=WebParams(
            bind_ip_address=_env("BIND_IP_ADDRESS"),
            bind_port=_env("BIND_PORT"),
        ),
    )


async def main() -> None:
    _start_logging()
    cache: InMemoryWebCache = _create_cache()
    cache.restore()
    await asyncio.gather(
        _run_data_refresh(cache),
        _run_web_service(cache),
    )


if __name__ == "__main__":
    asyncio.run(main())
