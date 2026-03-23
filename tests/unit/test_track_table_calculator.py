import datetime
import sched
import time

import pytest

from ska_tmc_dishleafnode.constants import PROGRAM_TRACK_TABLE_SIZE
from ska_tmc_dishleafnode.manager.program_track_table_calculator import (
    ProgramTrackTableCalculator,
)
from tests.settings import logger


def test_calculate_time_stamp_array(cm_pointing_device):
    cm = cm_pointing_device
    track_table_calculator = ProgramTrackTableCalculator(cm, logger=logger)
    track_table_calculator.track_table_time_stamp = datetime.datetime.utcnow()
    (
        time_stamp_array,
        tai_timestamp_array,
    ) = track_table_calculator.calculate_time_stamp_list()
    assert len(time_stamp_array) == PROGRAM_TRACK_TABLE_SIZE
    assert len(tai_timestamp_array) == PROGRAM_TRACK_TABLE_SIZE


def test_calculate_program_track_table(cm_pointing_device):
    from katpoint import Target

    from ska_tmc_dishleafnode.az_el_converter import AzElConverter_v2

    cm = cm_pointing_device
    wait_for_iers_data_available(cm)

    target = Target("Polaris Australis, radec, 21:08:47.92, -88:57:22.9")
    target.antenna = cm.observer
    cm.antenna_target = target
    cm.projection_and_fixed_trajectory_data = ["SIN", "azel", 0.0, 0.0]

    azel_converter = AzElConverter_v2(cm)
    track_table_calculator = ProgramTrackTableCalculator(cm, logger=logger)
    track_table_calculator.track_table_time_stamp = datetime.datetime.utcnow()
    track_table_calculator.track_table_scheduler = sched.scheduler(
        time.time, time.sleep
    )

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

    program_track_table = track_table_calculator.calculate_program_track_table(
        azel_converter
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


def test_azimuth_range(cm_pointing_device):
    track_table_calculator = ProgramTrackTableCalculator(
        cm_pointing_device, logger=logger
    )
    assert (
        cm_pointing_device.azimuth_min_limit
        < track_table_calculator.fit_azimuth_in_observable_range(500.0)
        < cm_pointing_device.azimuth_max_limit
    )
    assert (
        cm_pointing_device.azimuth_min_limit
        < track_table_calculator.fit_azimuth_in_observable_range(-500.0)
        < cm_pointing_device.azimuth_max_limit
    )


def test_azimuth_range_exception(cm_pointing_device):
    track_table_calculator = ProgramTrackTableCalculator(
        cm_pointing_device, logger=logger
    )
    with pytest.raises(Exception):
        track_table_calculator.fit_azimuth_in_observable_range()
