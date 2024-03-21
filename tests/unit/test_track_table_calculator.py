import datetime
import time

import pytest

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.manager.program_track_table_calculator import ProgramTrackTableCalculator
from tests.settings import logger


def test_calculate_time_stamp_array(cm):
    track_table_calculator = ProgramTrackTableCalculator(cm, logger=logger)
    cm.extended_time = datetime.datetime.utcnow()
    time_stamp_array, tai_timestamp_array = track_table_calculator.calculate_time_stamp_array()
    assert len(time_stamp_array) == cm.track_table_entries
    assert len(tai_timestamp_array) == cm.track_table_entries


def test_calculate_program_track_table(cm):
    cm.extended_time = datetime.datetime.utcnow()
    wait_for_iers_data_available(cm)
    azel_converter = AzElConverter(cm)
    track_table_calculator = ProgramTrackTableCalculator(cm, logger=logger)

    retry = 0
    while retry <= 3:
        try:
            azel_converter.create_antenna_obj()
            break
        except Exception as e:
            logger.exception("Exception occurred while creating antenna object: %s", e)
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
    elapsed_time = 0
    timeout = 45
    while cm.iers_a is not None and elapsed_time <= timeout:
        elapsed_time = elapsed_time + 1
        time.sleep(1)
