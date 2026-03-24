import math

import katpoint
import pytest

from ska_dishln_pointing_device.mapping_scan import mapping as mapping_module
from ska_dishln_pointing_device.mapping_scan.mapping import BaseScanMapping
from ska_dishln_pointing_device.mapping_scan.utils import (
    InvalidTargetDataError,
)
from tests.settings import logger


def create_mapping_scan(cm_pointing_device):
    """Create a base mapping object for unit tests."""
    return BaseScanMapping("fixed", cm_pointing_device, logger=logger)


@pytest.mark.parametrize(
    ("target_data", "expected_target_name"),
    [
        (
            {
                "pointing": {
                    "target": {
                        "target_name": "Sun",
                        "reference_frame": "special",
                    }
                }
            },
            "Sun",
        ),
        (
            {
                "pointing": {
                    "target": {
                        "target_name": "TestSource",
                        "reference_frame": "radec",
                        "ra": "12:00:00",
                        "dec": "-30:00:00",
                    }
                }
            },
            "TestSource",
        ),
        (
            {
                "pointing": {
                    "field": {
                        "target_name": "ISS (ZARYA)",
                        "reference_frame": "tle",
                        "attrs": {
                            "line1": "1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927",  # noqa: E501
                            "line2": "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537",  # noqa: E501
                        },
                    }
                }
            },
            "ISS (ZARYA)",
        ),
        (
            {
                "pointing": {
                    "field": {
                        "target_name": "Zenith",
                        "reference_frame": "altaz",
                        "attrs": {"c1": "180:00:00", "c2": "45:00:00"},
                    }
                }
            },
            "Zenith",
        ),
    ],
)
def test_build_data_for_observation_with_supported_reference_frames(
    cm_pointing_device, target_data, expected_target_name
):
    """Verify target creation for supported pointing reference frames."""
    mapping_scan = create_mapping_scan(cm_pointing_device)
    cm_pointing_device.target_data = target_data

    mapping_scan.build_data_for_observation()

    assert cm_pointing_device.target == expected_target_name
    assert isinstance(cm_pointing_device.antenna_target, katpoint.Target)
    assert (
        cm_pointing_device.antenna_target.antenna
        == cm_pointing_device.observer
    )


def test_build_data_for_observation_raises_for_missing_target(
    cm_pointing_device,
):
    """Verify missing pointing target data raises the expected error."""
    mapping_scan = create_mapping_scan(cm_pointing_device)
    cm_pointing_device.target_data = {"pointing": {}}

    with pytest.raises(InvalidTargetDataError):
        mapping_scan.build_data_for_observation()


def test_extract_target_from_config_uses_target_name_when_coordinates_missing(
    cm_pointing_device,
):
    """Verify target name is used when RA/Dec values are not provided."""
    mapping_scan = create_mapping_scan(cm_pointing_device)
    cm_pointing_device.target_data = {
        "pointing": {"target": {"target_name": "NamedTarget"}}
    }

    mapping_scan.extract_target_from_config()

    assert cm_pointing_device.target == "NamedTarget"


def test_extract_target_from_config_uses_field_target_name_fallback(
    cm_pointing_device,
):
    """Verify field target name is used as the final fallback."""
    mapping_scan = create_mapping_scan(cm_pointing_device)
    cm_pointing_device.target_data = {
        "pointing": {"field": {"target_name": "FieldTarget", "attrs": {}}}
    }

    mapping_scan.extract_target_from_config()

    assert cm_pointing_device.target == "FieldTarget"


def test_setup_observation_target_accepts_radec_strings(cm_pointing_device):
    """Verify string RA/Dec values create a katpoint target."""
    mapping_scan = create_mapping_scan(cm_pointing_device)
    cm_pointing_device.target = ["12:00:00", "-30:00:00"]

    mapping_scan.setup_observation_target()

    assert isinstance(mapping_scan.ra_dec_target, katpoint.Target)
    assert mapping_scan.ra_dec_target.antenna == cm_pointing_device.observer


def test_get_projection_converts_icrs_alignment_to_radec(cm_pointing_device):
    """Verify ICRS projection alignment is mapped to radec."""
    mapping_scan = create_mapping_scan(cm_pointing_device)
    cm_pointing_device.target_data = {
        "pointing": {"projection": {"name": "arc", "alignment": "ICRS"}}
    }

    projection_name, projection_alignment = mapping_scan.get_projection()

    assert projection_name == "ARC"
    assert projection_alignment == "radec"


def test_get_fixed_trajectory_offsets_uses_default_offsets(cm_pointing_device):
    """Verify missing trajectory attributes fall back to zero offsets."""
    mapping_scan = create_mapping_scan(cm_pointing_device)
    cm_pointing_device.target_data = {
        "pointing": {"trajectory": {"attrs": None}}
    }

    assert mapping_scan.get_fixed_trajectory_offsets() == (0.0, 0.0)


def test_start_process_skips_fixed_offsets_for_non_fixed_trajectory(
    cm_pointing_device, monkeypatch
):
    """Verify fixed offsets are not updated for non-fixed trajectories."""
    mapping_scan = create_mapping_scan(cm_pointing_device)
    cm_pointing_device.fixed_x_offset = "unchanged"
    cm_pointing_device.fixed_y_offset = "unchanged"

    monkeypatch.setattr(
        mapping_scan, "build_data_for_observation", lambda: None
    )
    monkeypatch.setattr(
        mapping_scan, "get_projection", lambda: ["SIN", "azel"]
    )
    monkeypatch.setattr(mapping_scan, "get_trajectory_name", lambda: "spiral")

    callback_state = {"track_table_started": False}

    def dummy_start_track_table_calculation():
        callback_state["track_table_started"] = True

    monkeypatch.setattr(
        cm_pointing_device,
        "start_track_table_calculation",
        dummy_start_track_table_calculation,
    )

    mapping_scan.set_target_and_start_process()

    assert callback_state["track_table_started"] is True
    assert cm_pointing_device.fixed_x_offset == "unchanged"
    assert cm_pointing_device.fixed_y_offset == "unchanged"


def test_set_target_and_start_process_reraises_source_errors(
    cm_pointing_device, monkeypatch
):
    """Verify setup errors are re-raised by the scan start helper."""
    mapping_scan = create_mapping_scan(cm_pointing_device)

    def raise_dummy_error():
        raise RuntimeError("broken")

    monkeypatch.setattr(
        mapping_scan, "build_data_for_observation", raise_dummy_error
    )

    with pytest.raises(RuntimeError, match="broken"):
        mapping_scan.set_target_and_start_process()


def test_set_trajectory_and_duration_uses_default_values(
    cm_pointing_device, monkeypatch
):
    """Verify default trajectory attrs and scan duration are applied."""
    mapping_scan = create_mapping_scan(cm_pointing_device)
    cm_pointing_device.target_data = {
        "pointing": {"trajectory": {"name": "fixed"}}
    }

    class DummyTrajectory:
        """Simple dummy trajectory used to capture constructor values."""

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.scan_duration = None

        def set_scan_duration(self, duration):
            self.scan_duration = duration

    monkeypatch.setattr(
        mapping_module, "TrajectoryName", {"fixed": DummyTrajectory}
    )

    mapping_scan.set_trajectory_and_duration()

    assert isinstance(mapping_scan.traj, DummyTrajectory)
    assert mapping_scan.traj.kwargs == {"x": 0.0, "y": 0.0}
    assert mapping_scan.traj.scan_duration == 1.0


def test_get_offset_in_rad_returns_arcsec_values_in_radians(
    cm_pointing_device,
):
    """Verify arcsecond offsets are converted to radians correctly."""
    mapping_scan = create_mapping_scan(cm_pointing_device)

    x_offset_radians, y_offset_radians = mapping_scan.get_offset_in_rad(
        1.0, -2.0
    )

    assert math.isclose(
        x_offset_radians,
        math.radians(1.0 / 3600.0),
        rel_tol=0,
        abs_tol=1e-12,
    )
    assert math.isclose(
        y_offset_radians,
        math.radians(-2.0 / 3600.0),
        rel_tol=0,
        abs_tol=1e-12,
    )


def test_get_radec_from_plane_to_sphere_returns_updated_coordinates(
    cm_pointing_device, monkeypatch
):
    """Verify plane-to-sphere conversion returns updated RA/Dec values."""
    mapping_scan = create_mapping_scan(cm_pointing_device)

    class DummyTrajectory:
        """Dummy trajectory with a stable starting position."""

        start = 123.0

        def posn(self, _start_time):
            return (1.0, -2.0, None, None, None)

    class DummyTarget:
        """Dummy target that returns predefined sphere coordinates."""

        def plane_to_sphere(
            self, x_offset_radians, y_offset_radians, _timestamp, **kwargs
        ):
            assert x_offset_radians is not None
            assert y_offset_radians is not None
            assert kwargs["projection_type"] == "SIN"
            assert kwargs["coord_system"] == "radec"
            return (0.1, -0.2)

    monkeypatch.setattr(
        mapping_scan, "get_projection", lambda: ["SIN", "radec"]
    )
    monkeypatch.setattr(
        mapping_scan, "set_trajectory_and_duration", lambda: None
    )
    mapping_scan.traj = DummyTrajectory()
    mapping_scan.ra_dec_target = DummyTarget()

    updated_ra, updated_dec = mapping_scan.get_radec_from_plane_to_sphere()

    assert math.isclose(
        updated_ra, math.degrees(0.1), rel_tol=0, abs_tol=1e-12
    )
    assert math.isclose(
        updated_dec, math.degrees(-0.2), rel_tol=0, abs_tol=1e-12
    )


def test_get_radec_from_plane_to_sphere_wraps_internal_exceptions(
    cm_pointing_device, monkeypatch
):
    """Verify conversion errors are wrapped with the mapping-scan message."""
    mapping_scan = create_mapping_scan(cm_pointing_device)
    monkeypatch.setattr(
        mapping_scan, "get_projection", lambda: ["SIN", "azel"]
    )

    def raise_dummy_trajectory_error():
        raise ValueError("trajectory failure")

    monkeypatch.setattr(
        mapping_scan,
        "set_trajectory_and_duration",
        raise_dummy_trajectory_error,
    )

    with pytest.raises(
        Exception, match="Exception while setting Ra and Dec for mapping scan"
    ):
        mapping_scan.get_radec_from_plane_to_sphere()
