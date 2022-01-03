"All related to data storage"

import json
from datetime import datetime, timedelta
from logging import getLogger
from pathlib import Path
from typing import Optional

from app.models import EnergyUsage

_logger = getLogger(__name__)


class InMemoryWebCache:
    def __init__(
        self, data_folder: Path, expiration_period: timedelta = timedelta(hours=12)
    ) -> None:
        self._data_folder: Path = data_folder
        self._expiration_period: timedelta = expiration_period
        self._energy_usage: Optional[EnergyUsage] = None
        self._expire_at: datetime = datetime.now()

    def _get_storage_path(self) -> Path:
        return self._data_folder.joinpath("energy_usage.json")

    def restore(self) -> None:
        _logger.info("Loading data from local cache")
        try:
            with self._get_storage_path().open(mode="r", encoding="utf-8") as f:
                data: dict = json.load(fp=f)
            energy_usage: EnergyUsage = EnergyUsage.from_json_dict(data["usage"])
            expire_at: datetime = datetime.fromisoformat(data["expire_at"])
            self._energy_usage = energy_usage
            self._expire_at = expire_at
        except FileNotFoundError:
            pass
        except Exception:  # pylint: disable=broad-except
            _logger.exception("Failed to deserialize cache from dict")

    @property
    def enery_usage(self) -> Optional[EnergyUsage]:
        return self._energy_usage

    @property
    def remaining_till_expiration(self) -> Optional[timedelta]:
        remaining: timedelta = self._expire_at - datetime.now()
        return remaining if remaining.total_seconds() > 0 else None

    def update(self, energy_usage: EnergyUsage) -> None:
        try:
            self._expire_at = datetime.now() + self._expiration_period
            self._energy_usage = energy_usage

            with self._get_storage_path().open(mode="w", encoding="utf-8") as f:
                json.dump(
                    obj={
                        "expire_at": self._expire_at.isoformat(),
                        "usage": energy_usage.to_json_dict(),
                    },
                    fp=f,
                )
            _logger.info(f"Cache is updated with expiration at {self._expire_at}")
        except Exception:  # pylint: disable=broad-except
            _logger.exception("Failed to refresh energy usage")
