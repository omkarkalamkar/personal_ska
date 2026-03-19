import datetime

import pytest
from astropy.time import Time

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.manager.program_track_table_calculator import (
    ProgramTrackTableCalculator,
)


def test_error_in_apply_refraction_method(cm_without_er_lp):
    az_el_convarter = AzElConverter(cm_without_er_lp)
    with pytest.raises(Exception):
        az_el_convarter.apply_refraction_correction([])


def test_source_error_in_point_to_body_method(cm_without_er_lp):
    az_el_convarter = AzElConverter(cm_without_er_lp)
    with pytest.raises(Exception):
        timestamp: Time = Time(datetime.datetime.utcnow(), scale="utc")
        az_el_convarter.point_to_body("Pluto", str(timestamp))


def test_timestamp_error_in_point_to_body_method(cm_without_er_lp):
    az_el_convarter = AzElConverter(cm_without_er_lp)
    with pytest.raises(Exception):
        cm_without_er_lp.iers_a = ""
        az_el_convarter.point_to_body("Sun", "0")


def test_error_in_azel_to_radec_body_method(cm_without_er_lp):
    az_el_convarter = AzElConverter(cm_without_er_lp)
    with pytest.raises(Exception):
        az_el_convarter.azel_to_radec("0", "0", "0")


def test_error_in_point_method(cm_without_er_lp):
    az_el_convarter = AzElConverter(cm_without_er_lp)
    with pytest.raises(Exception):
        az_el_convarter.point("0", "0", "0")


def test_error_in_calculate_program_track_table(
    cm_without_er_lp, cm_pointig_device
):
    cm = cm_without_er_lp
    az_el_convarter = AzElConverter(cm)
    track_table_calculator = ProgramTrackTableCalculator(
        cm_pointig_device, cm_pointig_device.logger
    )
    with pytest.raises(Exception):
        track_table_calculator.track_table_time_stamp = (
            datetime.datetime.utcnow()
        )
        track_table_calculator.calculate_program_track_table(az_el_convarter)


def test_timestamp_error_in_track_table_point_method(cm_pointig_device):
    cm = cm_pointig_device
    track_table_calculator = ProgramTrackTableCalculator(cm, cm.logger)
    timestamp: Time = Time(datetime.datetime.utcnow(), scale="utc")
    with pytest.raises(Exception):
        track_table_calculator.point(str(timestamp))


def test_error_in_track_table_point_method(tango_context, cm_pointig_device):
    cm = cm_pointig_device
    cm.create_converter_obj_and_antenna_obj()
    non_side_real_objects = [
        "Sun",
        "Moon",
        "Venus",
        "Mars",
        "Jupiter",
        "Saturn",
        "Mercury",
        "Urenus",
        "Neptune",
    ]
    azel_converter = AzElConverter(cm)
    result = None
    for nsr_obj in non_side_real_objects:
        try:
            track_table_calculator = ProgramTrackTableCalculator(cm, cm.logger)
            track_table_calculator.azel_converter = azel_converter
            track_table_calculator.target_name = nsr_obj
            timestamp = Time(datetime.datetime.utcnow(), scale="utc")
            result = track_table_calculator.point(str(timestamp))
            if result:
                break
        except Exception:
            continue

    assert result is not None


def test_error_in_utc_to_tai_method(cm_pointig_device):
    cm = cm_pointig_device
    track_table_calculator = ProgramTrackTableCalculator(cm, cm.logger)
    with pytest.raises(Exception):
        track_table_calculator.convert_utc_to_tai(0.0)


def test_is_elevation_within_limits_method(tango_context, cm_pointig_device):
    cm = cm_pointig_device
    track_table_calculator = ProgramTrackTableCalculator(cm, cm.logger)

    result = track_table_calculator._is_elevation_within_mechanical_limits(
        16.0
    )
    assert result is False
    assert track_table_calculator.elevation_limit is True
