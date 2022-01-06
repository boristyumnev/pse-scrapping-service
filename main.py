"Entry point for tha app"

import asyncio
from datetime import timedelta
import logging
from asyncio.events import AbstractEventLoop
from asyncio.tasks import Task
from logging.handlers import RotatingFileHandler
from os import getenv
from pathlib import Path
from signal import SIGHUP, SIGINT, SIGTERM
from typing import Optional, Sequence

from app.models import ScapingParams, WebParams
from app.scraping import loop_refresh
from app.storage import InMemoryWebCache
from app.web import start_webservice

_logger = logging.getLogger(__name__)


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


async def _run_server() -> None:
    terminate_event = asyncio.Event()
    try:
        cache: InMemoryWebCache = InMemoryWebCache(
            data_folder=Path(_env("DATA_FOLDER")),
            expiration_period=timedelta(hours=int(_env("CACHE_DURATION_HOURS"))),
        )
        cache.restore()
        refresh_coro = loop_refresh(
            cache=cache,
            scraping_params=ScapingParams(
                pse_username=_env("PSE_USERNAME"),
                pse_password=_env("PSE_PASSWORD"),
            ),
            force_first_refresh=False,
        )
        webservice_coro = start_webservice(
            cache=cache,
            params=WebParams(
                bind_ip_address=_env("BIND_IP_ADDRESS"),
                bind_port=_env("BIND_PORT"),
            ),
            terminate_event=terminate_event,
        )
        await asyncio.gather(refresh_coro, webservice_coro)
    except asyncio.CancelledError:
        pass
    except Exception:  # pylint: disable=broad-except
        _logger.exception("Service execution failure")

    _logger.info("Stopping the loop")
    terminate_event.set()
    asyncio.get_running_loop().stop()


def _shutdown(loop: AbstractEventLoop) -> None:
    tasks: Sequence[Task] = asyncio.all_tasks(loop)
    _logger.info(f"Killing {len(tasks)} tasks")
    for task in tasks:
        task.cancel()


def main() -> None:
    _start_logging()

    loop: AbstractEventLoop = asyncio.new_event_loop()
    loop.create_task(_run_server())
    for signum in [SIGTERM, SIGINT, SIGHUP]:
        loop.add_signal_handler(signum, _shutdown, loop)
    _logger.info("Running")
    loop.run_forever()
    _logger.info("Terminated")


if __name__ == "__main__":
    main()
