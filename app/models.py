"All models of the app"

from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Sequence
from enum import Enum


class UnitOfMeasurement(Enum):
    KILOWATT_HOUR = "kWh"
    CUBIC_FEET = "CCF"
    CUBIC_METERS = "m³"


@dataclass
class UsageValue:
    date: date
    minutes_included: int
    value: float
    unit_of_measurement: UnitOfMeasurement

    @property
    def is_complete_day(self) -> bool:
        return self.minutes_included == 24 * 60

    def change_self_to_si(self) -> None:
        if self.unit_of_measurement == UnitOfMeasurement.CUBIC_FEET:
            self.unit_of_measurement = UnitOfMeasurement.CUBIC_METERS
            self.value = round(self.value * 2.83168, 2)

    def to_json_dict(self) -> Mapping[str, Any]:
        return {
            "date": self.date.isoformat(),
            "minutes_included": self.minutes_included,
            "value": self.value,
            "unit_of_measurement": self.unit_of_measurement.value,
        }

    @classmethod
    def from_json_dict(cls, data: Mapping[str, Any]) -> UsageValue:
        return UsageValue(
            date=date.fromisoformat(data["date"]),
            minutes_included=data["minutes_included"],
            value=data["value"],
            unit_of_measurement=UnitOfMeasurement(data["unit_of_measurement"]),
        )


@dataclass
class EnergyUsage:
    update_timestamp: datetime
    electricity: Sequence[UsageValue]
    natural_gas: Sequence[UsageValue]

    def to_json_dict(self) -> Mapping[str, Any]:
        return {
            "update_timestamp": self.update_timestamp.isoformat(),
            "electricity": [item.to_json_dict() for item in self.electricity],
            "natural_gas": [item.to_json_dict() for item in self.natural_gas],
        }

    @classmethod
    def from_json_dict(cls, data: Mapping[str, Any]) -> EnergyUsage:
        return EnergyUsage(
            update_timestamp=datetime.fromisoformat(data["update_timestamp"]),
            electricity=[
                UsageValue.from_json_dict(item) for item in data["electricity"]
            ],
            natural_gas=[
                UsageValue.from_json_dict(item) for item in data["natural_gas"]
            ],
        )


@dataclass
class ScapingParams:
    pse_username: str
    pse_password: str


@dataclass
class WebParams:
    bind_ip_address: str = "0.0.0.0"
    bind_port: int = 5000
