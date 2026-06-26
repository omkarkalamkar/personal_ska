"""conftest module for CSP Subarray Leaf Node."""
import logging

import pytest
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import WEATHER_STATION_DEVICE, WEATHER_STATION_DEVICE2


@pytest.fixture(autouse=True, scope="session")
def set_weather_station_admin_mode(request):
    """Ensure DishLN and DishMaster start with matching KValue."""
    if not request.config.getoption("--true-context"):
        return
    try:
        dev_factory = DevFactory()
        for device in [WEATHER_STATION_DEVICE, WEATHER_STATION_DEVICE2]:
            proxy = dev_factory.get_device(device)
            proxy.adminMode = 0

    except Exception as e:
        logging.exception("Failed to set admin mode %s", e)
