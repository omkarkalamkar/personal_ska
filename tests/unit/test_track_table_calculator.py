import datetime
import time

import pytest

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.manager.program_track_table_calculator import (
    ProgramTrackTableCalculator,
)
from tests.settings import logger


def test_calculate_time_stamp_array(cm):
    track_table_calculator = ProgramTrackTableCalculator(cm, logger=logger)
    track_table_calculator.track_table_time_stamp = datetime.datetime.utcnow()
    (
        time_stamp_array,
        tai_timestamp_array,
    ) = track_table_calculator.calculate_time_stamp_list()
    assert len(time_stamp_array) == cm.track_table_entries
    assert len(tai_timestamp_array) == cm.track_table_entries


def test_calculate_program_track_table(cm):
    wait_for_iers_data_available(cm)
    azel_converter = AzElConverter(cm)
    track_table_calculator = ProgramTrackTableCalculator(cm, logger=logger)
    track_table_calculator.track_table_time_stamp = datetime.datetime.utcnow()

    retry = 0
    while retry <= 3:
        try:
            azel_converter.create_antenna_obj()
            break
        except Exception as e:
            logger.exception(
                "Exception occurred while creating antenna object: %s", e
            )
            if retry == 2:
                pytest.fail(f"{e}")
            retry += 1
        time.sleep(0.1)

    # Given Ra and Dec are of polaris australis
    program_track_table = track_table_calculator.calculate_program_track_table(
        "21:27:51.5", "-88:51:08.8", azel_converter
    )

    TIMEOUT = 10
    start_time = time.time()
    while (time.time() - start_time) < TIMEOUT:
        if len(program_track_table) != 0:
            break
        time.sleep(0.5)

    logger.info(f"ProgramTrackTable: {program_track_table}")

    assert len(program_track_table) > 0 and len(program_track_table) % 3 == 0

    for item in program_track_table:
        assert isinstance(item, float)


def wait_for_iers_data_available(cm):
    """Function which waits for the IERS data to be available."""
    TIMEOUT = 45
    start_time = time.time()
    while cm.iers_a is not None and (time.time() - start_time) < TIMEOUT:
        time.sleep(0.5)
