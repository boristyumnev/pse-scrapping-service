from datetime import date
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from os.path import dirname
from app.models import UnitOfMeasurement

from app.scraping import UsageValue, _extract_usage_from_zip


class ScappingTest(IsolatedAsyncioTestCase):
    maxDiff = None

    async def test_extract_usage_from_zip(self) -> None:
        # given
        path = Path(dirname(__file__)).joinpath("TestData.zip")

        # when
        data = await _extract_usage_from_zip(
            path, "Electric usage", UnitOfMeasurement.KILOWATT_HOUR
        )

        # then
        self.assertEqual(
            data,
            [
                UsageValue(
                    date=date(2021, 12, 5),
                    value=2.99,
                    minutes_included=180,
                    unit_of_measurement=UnitOfMeasurement.KILOWATT_HOUR,
                ),
                UsageValue(
                    date=date(2021, 12, 6),
                    value=1.31,
                    minutes_included=150,
                    unit_of_measurement=UnitOfMeasurement.KILOWATT_HOUR,
                ),
            ],
        )
