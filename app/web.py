"Web service"

from datetime import datetime
from logging import getLogger
from typing import Optional, Sequence

from quart.json import jsonify
from quart import Quart, Response

from app.models import WebParams, EnergyUsage, UsageValue
from app.storage import InMemoryWebCache

_logger = getLogger(__name__)


def _find_latest_usage(usages: Sequence[UsageValue]) -> Optional[UsageValue]:
    for usage in reversed(usages):
        if usage.is_complete_day:
            return usage
    return None


def _render_status_response(status: str) -> Response:
    return jsonify({"status": status})


def _render_single_response(usage: UsageValue, update_timestamp: datetime) -> Response:
    return jsonify(
        {
            "status": "OK",
            "data": {
                "usage": usage.value,
                "date": usage.date.isoformat(),
                "unit_of_measurement": usage.unit_of_measurement.value,
            },
            "update_timestamp": update_timestamp.isoformat(),
        }
    )


async def start_webservice(cache: InMemoryWebCache, params: WebParams) -> None:
    _logger.info(f"Starting web server {params}")
    app: Quart = Quart(__name__)

    @app.route("/")
    async def default_route() -> Response:
        energy_usage: Optional[EnergyUsage] = cache.enery_usage
        return _render_status_response("OK" if energy_usage else "NOT_AVAILABLE")

    @app.route("/electricity/latest")
    async def electricity_latest_route() -> Response:
        if not (energy_usage := cache.enery_usage):
            return _render_status_response("NOT_AVAILABLE")
        latest: Optional[UsageValue] = _find_latest_usage(energy_usage.electricity)
        if not latest:
            return _render_status_response("NO_DATA")
        return _render_single_response(latest, energy_usage.update_timestamp)

    @app.route("/natural_gas/latest")
    async def natural_gas_latest_route() -> Response:
        if not (energy_usage := cache.enery_usage):
            return _render_status_response("NOT_AVAILABLE")
        latest: Optional[UsageValue] = _find_latest_usage(energy_usage.natural_gas)
        if not latest:
            return _render_status_response("NO_DATA")
        return _render_single_response(latest, energy_usage.update_timestamp)

    await app.run_task(host=params.bind_ip_address, port=params.bind_port)
