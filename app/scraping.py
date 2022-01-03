"All about scraping PSE website for usage"

import logging
import os
import asyncio
from datetime import date, datetime, time, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import AsyncGenerator, Dict, Iterable, List, Optional, Sequence
from zipfile import ZipFile
from contextlib import asynccontextmanager

from playwright.async_api import Browser, Download, Page, async_playwright

from app.storage import InMemoryWebCache
from app.models import EnergyUsage, ScapingParams, UnitOfMeasurement, UsageValue

_logger = logging.getLogger(__name__)


async def _login(page: Page, username: str, password: str) -> None:
    _logger.info("Logging into the website")
    await page.goto("https://www.pse.com/")
    await page.type("#Username", username)
    await page.type("#Password", password)
    await page.click("#signin-btn")
    await page.wait_for_load_state(state="networkidle")


async def _download_usage_zipped_csv(page: Page) -> str:
    _logger.info("Downloading usage file")
    await page.goto("https://www.pse.com/account-and-billing/my-usage/view-my-usage")
    await page.click(".green-button")
    await page.click("#period-bill-radio-container")
    async with page.expect_download() as download_info:
        await page.click(".usage-export-submit-container button.primary")
    download: Download = await download_info.value
    return await download.path()


@asynccontextmanager
async def download_usage_zipped_csv(
    username: str, password: str
) -> AsyncGenerator[Path, None]:
    async with async_playwright() as playwright:
        browser: Browser = await playwright.firefox.launch(headless=True)
        page: Page = await browser.new_page(accept_downloads=True)
        await _login(page, username, password=password)
        file_path: Path = await _download_usage_zipped_csv(page)
        yield file_path


async def _parse_usage_file(
    file_path: str, usage_filter: str, default_units: UnitOfMeasurement
) -> Iterable[UsageValue]:
    mode: str = "HEADER"
    name_index: int = -1
    date_index: int = -1
    start_time_index: Optional[int] = None
    end_time_index: Optional[int] = None
    usage_index: int = -1
    units_index: int = -1
    result: Dict[date, UsageValue] = {}
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file.readlines():
            line = line.strip("\n")
            if mode == "HEADER":
                if line == "":
                    mode = "TITLE"
                continue
            elif mode == "TITLE":
                parts: Sequence[str] = line.split(",")
                name_index = parts.index("TYPE")
                date_index = parts.index("DATE")
                try:
                    start_time_index = parts.index("START TIME")
                    end_time_index = parts.index("END TIME")
                except ValueError:
                    start_time_index = None
                    end_time_index = None
                usage_index = parts.index("USAGE")
                units_index = parts.index("UNITS")
                mode = "DATA"
                continue

            parts: List[str] = line.split(",")
            name_value: str = parts[name_index]
            date_value: date = date.fromisoformat(parts[date_index])
            usage_value: str = float(parts[usage_index])
            units_value: str = parts[units_index]
            minute_count: int = 24 * 60
            if start_time_index is not None and end_time_index is not None:
                start_time: time = time.fromisoformat(parts[start_time_index])
                end_time: time = time.fromisoformat(parts[end_time_index])
                minute_count: int = (
                    (end_time.hour - start_time.hour) * 24
                    + end_time.minute
                    - start_time.minute
                    + 1
                )

            if name_value != usage_filter:
                continue

            try:
                if date_value in result:
                    item = result[date_value]
                    item.value = round(item.value + usage_value, 2)
                    item.minutes_included += minute_count
                else:
                    usage: UsageValue = UsageValue(
                        date=date_value,
                        minutes_included=minute_count,
                        value=round(usage_value, 2),
                        unit_of_measurement=UnitOfMeasurement(units_value)
                        if units_value
                        else default_units,
                    )
                    result[date_value] = usage
            except Exception:  # pylint: disable=broad-except
                _logger.exception("Failed processing line %s", line)

    return result.values()


async def _extract_usage_from_zip(
    zip_file_path: Path, usage_filter: str, default_units: UnitOfMeasurement
) -> Sequence[UsageValue]:
    _logger.info(f"Reading usage file for {usage_filter}")
    result: List[UsageValue] = []
    with TemporaryDirectory() as tmp_dir:
        with ZipFile(str(zip_file_path), "r") as zip_ref:
            zip_ref.extractall(tmp_dir)

        files = os.listdir(tmp_dir)
        csv_file_names = [file_name for file_name in files if file_name.endswith("csv")]
        if len(csv_file_names) == 0:
            return []

        for file_name in csv_file_names:
            csv_file_path: str = os.path.join(tmp_dir, file_name)
            result += sorted(
                await _parse_usage_file(
                    file_path=csv_file_path,
                    usage_filter=usage_filter,
                    default_units=default_units,
                ),
                key=lambda item: item.date,
            )

    for item in result:
        item.change_self_to_si()

    return result


async def _get_latest_usage_data(scraping_params: ScapingParams) -> EnergyUsage:
    "Loads current usage since last bill  from PSE website."

    async with download_usage_zipped_csv(
        username=scraping_params.pse_username, password=scraping_params.pse_password
    ) as zip_file_path:
        usage: EnergyUsage = EnergyUsage(
            update_timestamp=datetime.now(),
            electricity=await _extract_usage_from_zip(
                zip_file_path=zip_file_path,
                usage_filter="Electric usage",
                default_units=UnitOfMeasurement.KILOWATT_HOUR,
            ),
            natural_gas=await _extract_usage_from_zip(
                zip_file_path=zip_file_path,
                usage_filter="Natural gas usage",
                default_units=UnitOfMeasurement.CUBIC_FEET,
            ),
        )
        return usage


async def _refresh_cache_data(
    cache: InMemoryWebCache, scraping_params: ScapingParams
) -> None:
    try:
        data: EnergyUsage = await _get_latest_usage_data(scraping_params)
        cache.update(data)
    except Exception:
        _logger.exception("Failed to scrape data from the website")


async def loop_refresh(
    cache: InMemoryWebCache,
    scraping_params: ScapingParams,
    period: timedelta = timedelta(minutes=60),
    force_first_refresh: bool = False,
) -> None:
    period_sec: float = round(period.total_seconds())
    if force_first_refresh:
        await _refresh_cache_data(cache=cache, scraping_params=scraping_params)

    while True:
        remaining: Optional[timedelta] = cache.remaining_till_expiration
        if not remaining:
            await _refresh_cache_data(cache=cache, scraping_params=scraping_params)
        else:
            _logger.info(f"{remaining} remains till next refresh")

        _logger.info(f"Data checker is sleeping for {period_sec} seconds")
        await asyncio.sleep(period_sec)
