import datetime

import pytest
from astropy.time import Time

from ska_tmc_dishleafnode.az_el_converter import AzElConverter
from ska_tmc_dishleafnode.manager.program_track_table_calculator import (
    ProgramTrackTableCalculator,
)


def test_error_in_apply_refraction_method(tango_context, cm):
    az_el_convarter = AzElConverter(cm)
    with pytest.raises(Exception):
        az_el_convarter.apply_refraction_correction([])


def test_source_error_in_point_to_body_method(tango_context, cm):
    az_el_convarter = AzElConverter(cm)
    with pytest.raises(Exception):
        timestamp: Time = Time(datetime.datetime.utcnow(), scale="utc")
        az_el_convarter.point_to_body("Pluto", str(timestamp))


def test_timestamp_error_in_point_to_body_method(tango_context, cm):
    az_el_convarter = AzElConverter(cm)
    with pytest.raises(Exception):
        cm.iers_a = ""
        az_el_convarter.point_to_body("Sun", "0")


def test_error_in_azel_to_radec_body_method(tango_context, cm):
    az_el_convarter = AzElConverter(cm)
    with pytest.raises(Exception):
        az_el_convarter.azel_to_radec("0", "0", "0")


def test_error_in_point_method(tango_context, cm):
    az_el_convarter = AzElConverter(cm)
    with pytest.raises(Exception):
        az_el_convarter.point("0", "0", "0")


def test_error_in_calculate_program_track_table(tango_context, cm):
    az_el_convarter = AzElConverter(cm)
    track_table_calculator = ProgramTrackTableCalculator(cm, cm.logger)
    with pytest.raises(Exception):
        track_table_calculator.calculate_program_track_table(
            "Pluto", az_el_convarter
        )


def test_error_in_track_table_point_method(tango_context, cm):
    track_table_calculator = ProgramTrackTableCalculator(cm, cm.logger)
    timestamp: Time = Time(datetime.datetime.utcnow(), scale="utc")
    with pytest.raises(Exception):
        track_table_calculator.point(str(timestamp))


def test_error_in_utc_to_tai_method(tango_context, cm):
    track_table_calculator = ProgramTrackTableCalculator(cm, cm.logger)
    with pytest.raises(Exception):
        track_table_calculator.convert_utc_to_tai(0.0)
