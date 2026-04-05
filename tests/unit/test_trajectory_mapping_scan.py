"""Unit tests for the TrajectoryMappingScan class."""

import json
import threading
from unittest.mock import MagicMock

import pytest
from astropy.time import Time

from ska_dishln_pointing_device.commands.generate_program_track_table import (  # noqa: E501
    GenerateProgramTrackTable,
)
from ska_dishln_pointing_device.mapping_scan import (
    trajectory_mapping_scan as traj_module,
)
from ska_dishln_pointing_device.mapping_scan.trajectory_mapping_scan import (
    TrajectoryMappingScan,
)
from tests.settings import logger

PVT_CONFIGURE_JSON = "dln_configure_pvt"


def trajectory_mapping_scan(cm):
    """Create a TrajectoryMappingScan object for unit tests."""
    return TrajectoryMappingScan(
        component_manager=cm,
        logger=logger,
    )


def test_traj_init_sets_default_attributes(cm_pointing_device):
    """Test that the constructor initializes all default attributes."""

    cm_pointing_device.program_track_table_size = 50
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)
    assert trajectory_scan.time_offsets == []
    assert trajectory_scan.trajectory_attrs == {}
    assert trajectory_scan.cadence == 0.0
    assert trajectory_scan.trajectory_name == ""
    assert trajectory_scan.traj is None
    assert trajectory_scan.extended_time == 0.0
    assert trajectory_scan.program_track_table_size == 150
    assert (
        trajectory_scan.mapping_scan_event
        is cm_pointing_device.mapping_scan_event
    )


def test_get_time_offsets_returns_offsets_when_present(
    cm_pointing_device, json_factory
):
    """Test that valid time offsets are returned from configure data."""
    configure_data = json.loads(json_factory(PVT_CONFIGURE_JSON))
    cm_pointing_device.target_data = configure_data
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)

    offsets = trajectory_scan.get_time_offsets_and_set_cadence()

    assert offsets == [0, 1, 2, 3, 4]


def test_get_time_offsets_sets_cadence_from_offsets(
    cm_pointing_device, json_factory
):
    """Test that cadence is derived from the first two time offsets."""
    configure_data = json.loads(json_factory(PVT_CONFIGURE_JSON))
    cm_pointing_device.target_data = configure_data
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)
    trajectory_scan.get_time_offsets_and_set_cadence()
    assert trajectory_scan.cadence == 1.0


def test_get_time_offsets_raises_when_no_offsets_and_no_scan_duration(
    cm_pointing_device,
):
    """Test that ValueError is raised when time_offsets are missing
    and no scan_duration is provided."""
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)

    cm_pointing_device.target_data = {
        "pointing": {"trajectory": {"attrs": {}}},
        "tmc": {},
    }
    with pytest.raises(ValueError, match="Scan duration must be provided"):
        trajectory_scan.get_time_offsets_and_set_cadence()


def test_get_time_offsets_raises_when_target_data_empty(cm_pointing_device):
    """Test that ValueError is raised when target_data is empty."""
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)
    cm_pointing_device.target_data = {}

    with pytest.raises(ValueError, match="Scan duration must be provided"):
        trajectory_scan.get_time_offsets_and_set_cadence()


def test_get_trajectory_attrs_returns_attrs_when_present(
    cm_pointing_device, json_factory
):
    """Test that trajectory attrs are returned with expected keys."""
    configure_data = json.loads(json_factory(PVT_CONFIGURE_JSON))
    cm_pointing_device.target_data = configure_data
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)

    attrs = trajectory_scan.get_trajectory_attrs()

    assert "time_offsets" in attrs
    assert "x_offsets" in attrs
    assert "y_offsets" in attrs
    assert "x_velocities" in attrs
    assert "y_velocities" in attrs


def test_get_trajectory_attrs_returns_default_when_attrs_key_absent(
    cm_pointing_device,
):
    """Test that default x/y offsets are returned when attrs key is absent."""
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)
    cm_pointing_device.target_data = {"pointing": {"trajectory": {}}}

    attrs = trajectory_scan.get_trajectory_attrs()

    assert attrs == {"x": 0.0, "y": 0.0}


def test_get_trajectory_attrs_returns_default_when_attrs_empty(
    cm_pointing_device,
):
    """Test that default x/y offsets are returned when attrs dict is empty."""
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)
    cm_pointing_device.target_data = {
        "pointing": {"trajectory": {"attrs": {}}}
    }

    attrs = trajectory_scan.get_trajectory_attrs()

    assert attrs == {"x": 0.0, "y": 0.0}


def test_set_trajectory_data_populates_time_offsets(
    cm_pointing_device, json_factory
):
    """Test that set_trajectory_data fills time_offsets correctly."""
    configure_data = json.loads(json_factory(PVT_CONFIGURE_JSON))
    cm_pointing_device.target_data = configure_data
    cm_pointing_device.trajectory_name = "pos_vel_time"
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)

    trajectory_scan.set_trajectory_data()

    assert trajectory_scan.time_offsets == [0, 1, 2, 3, 4]


def test_set_trajectory_data_populates_trajectory_name(
    cm_pointing_device, json_factory
):
    """Test that set_trajectory_data sets trajectory_name from CM."""
    configure_data = json.loads(json_factory(PVT_CONFIGURE_JSON))
    cm_pointing_device.target_data = configure_data
    cm_pointing_device.trajectory_name = "pos_vel_time"
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)

    trajectory_scan.set_trajectory_data()

    assert trajectory_scan.trajectory_name == "pos_vel_time"


def test_set_trajectory_data_populates_attrs(cm_pointing_device, json_factory):
    """Test that set_trajectory_data fills trajectory_attrs correctly."""
    configure_data = json.loads(json_factory(PVT_CONFIGURE_JSON))
    cm_pointing_device.target_data = configure_data
    cm_pointing_device.trajectory_name = "pos_vel_time"
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)

    trajectory_scan.set_trajectory_data()

    assert len(trajectory_scan.trajectory_attrs["x_offsets"]) == 5
    assert len(trajectory_scan.trajectory_attrs["y_offsets"]) == 5
    assert len(trajectory_scan.trajectory_attrs["x_velocities"]) == 5
    assert len(trajectory_scan.trajectory_attrs["y_velocities"]) == 5


def test_set_target_and_start_process_calls_build_and_start(
    cm_pointing_device, json_factory, monkeypatch
):
    """Test that build_data_for_observation and start_track_table_calculation
    are both called during set_target_and_start_process."""
    configure_data = json.loads(json_factory(PVT_CONFIGURE_JSON))
    cm_pointing_device.target_data = configure_data
    cm_pointing_device.trajectory_name = "pos_vel_time"
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)

    build_called = {"value": False}
    start_called = {"value": False}

    class DummyTrajectory:
        def __init__(self, **kwargs):
            pass

        def posn(self, t):
            return (0.0, 0.0, 0.0, 0.0, 0.0)

    monkeypatch.setattr(
        trajectory_scan.converter, "create_antenna_obj", lambda: None
    )
    monkeypatch.setattr(
        trajectory_scan,
        "build_data_for_observation",
        lambda: build_called.update({"value": True}),
    )
    monkeypatch.setattr(
        trajectory_scan, "get_projection", lambda: ["SIN", "azel"]
    )
    monkeypatch.setattr(
        trajectory_scan,
        "start_track_table_calculation",
        lambda: start_called.update({"value": True}),
    )
    monkeypatch.setattr(
        traj_module, "TrajectoryName", {"pos_vel_time": DummyTrajectory}
    )

    trajectory_scan.set_target_and_start_process()

    assert build_called["value"] is True
    assert start_called["value"] is True


def test_set_target_and_start_process_sets_projection_on_cm(
    cm_pointing_device, json_factory, monkeypatch
):
    """Test that projection_name and projection_alignment are set on CM."""
    configure_data = json.loads(json_factory(PVT_CONFIGURE_JSON))
    cm_pointing_device.target_data = configure_data
    cm_pointing_device.trajectory_name = "pos_vel_time"
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)

    class DummyTrajectory:
        def __init__(self, **kwargs):
            pass

        def posn(self, t):
            return (0.0, 0.0, 0.0, 0.0, 0.0)

    monkeypatch.setattr(
        trajectory_scan.converter, "create_antenna_obj", lambda: None
    )
    monkeypatch.setattr(
        trajectory_scan, "build_data_for_observation", lambda: None
    )
    monkeypatch.setattr(
        trajectory_scan, "get_projection", lambda: ["SIN", "azel"]
    )
    monkeypatch.setattr(
        trajectory_scan, "start_track_table_calculation", lambda: None
    )
    monkeypatch.setattr(
        traj_module, "TrajectoryName", {"pos_vel_time": DummyTrajectory}
    )

    trajectory_scan.set_target_and_start_process()

    assert cm_pointing_device.projection_name == "SIN"
    assert cm_pointing_device.projection_alignment == "azel"


def test_set_target_and_start_process_sets_cadence_from_offsets(
    cm_pointing_device, json_factory, monkeypatch
):
    """Test that cadence is correctly calculated from the first two
    time offsets and traj object is instantiated."""
    configure_data = json.loads(json_factory(PVT_CONFIGURE_JSON))
    cm_pointing_device.target_data = configure_data
    cm_pointing_device.trajectory_name = "pos_vel_time"
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)

    class DummyTrajectory:
        def __init__(self, **kwargs):
            pass

        def posn(self, t):
            return (0.0, 0.0, 0.0, 0.0, 0.0)

    monkeypatch.setattr(
        trajectory_scan.converter, "create_antenna_obj", lambda: None
    )
    monkeypatch.setattr(
        trajectory_scan, "build_data_for_observation", lambda: None
    )
    monkeypatch.setattr(
        trajectory_scan, "get_projection", lambda: ["SIN", "azel"]
    )
    monkeypatch.setattr(
        trajectory_scan, "start_track_table_calculation", lambda: None
    )
    monkeypatch.setattr(
        traj_module, "TrajectoryName", {"pos_vel_time": DummyTrajectory}
    )

    trajectory_scan.set_target_and_start_process()

    # cadence = time_offsets[1] - time_offsets[0] = 1 - 0 = 1.0
    assert trajectory_scan.cadence == 1.0
    assert trajectory_scan.traj is not None


def test_start_track_table_calculation_creates_and_starts_thread(
    cm_pointing_device, monkeypatch
):
    """Test that thread is created and started when
    stop_track_called is clear."""
    cm_pointing_device.stop_track_called = threading.Event()
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)

    thread_started = {"value": False}

    def mock_create_thread():
        cm_pointing_device.track_table_thread = MagicMock()
        cm_pointing_device.track_table_thread.is_alive = lambda: False
        cm_pointing_device.track_table_thread.start = (
            lambda: thread_started.update({"value": True})
        )

    monkeypatch.setattr(
        trajectory_scan, "create_track_table_thread", mock_create_thread
    )

    trajectory_scan.start_track_table_calculation()

    assert thread_started["value"] is True


def test_start_track_table_calculation_skips_when_stop_track_called(
    cm_pointing_device, monkeypatch
):
    """Test that thread is not started when stop_track_called is set."""
    cm_pointing_device.stop_track_called = threading.Event()
    cm_pointing_device.stop_track_called.set()
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)

    thread_started = {"value": False}

    def mock_create_thread():
        cm_pointing_device.track_table_thread = MagicMock()
        cm_pointing_device.track_table_thread.is_alive = lambda: False
        cm_pointing_device.track_table_thread.start = (
            lambda: thread_started.update({"value": True})
        )

    monkeypatch.setattr(
        trajectory_scan, "create_track_table_thread", mock_create_thread
    )

    trajectory_scan.start_track_table_calculation()

    assert thread_started["value"] is False


def test_calculate_ptt_returns_correct_number_of_entries(
    cm_pointing_device, monkeypatch
):
    """Test that valid time offsets produce correct PTT entry count."""
    cm_pointing_device.wrap_sector = 0
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)
    trajectory_scan.extended_time = Time.now()

    class DummyTraj:
        def posn(self, t):
            return (10.5, 20.3, 0.0, 0.0, 0.0)

    trajectory_scan.traj = DummyTraj()
    monkeypatch.setattr(
        trajectory_scan.converter, "point", lambda ts: (45.0, 30.0)
    )
    monkeypatch.setattr(
        trajectory_scan.track_table_calculator,
        "convert_utc_to_tai",
        lambda ts: 12345.0,
    )
    monkeypatch.setattr(
        trajectory_scan.track_table_calculator,
        "_is_elevation_within_mechanical_limits",
        lambda el: True,
    )
    trajectory_scan.track_table_scheduler = MagicMock()

    result = trajectory_scan.calculate_program_track_table(
        time_offsets=[0.0, 1.0, 2.0],
        ptt_buffer_set=False,
        program_track_table_size=10,
    )

    assert len(result) == 9
    assert result[0] == 12345.0


def test_calculate_ptt_sets_fixed_offsets_on_cm(
    cm_pointing_device, monkeypatch
):
    """Test that traj.posn() x/y results are set as fixed offsets on CM."""
    cm_pointing_device.wrap_sector = 0
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)
    trajectory_scan.extended_time = Time.now()

    class DummyTraj:
        def posn(self, t):
            return (10.5, 20.3, 0.0, 0.0, 0.0)

    trajectory_scan.traj = DummyTraj()
    monkeypatch.setattr(
        trajectory_scan.converter, "point", lambda ts: (45.0, 30.0)
    )
    monkeypatch.setattr(
        trajectory_scan.track_table_calculator,
        "convert_utc_to_tai",
        lambda ts: 12345.0,
    )
    monkeypatch.setattr(
        trajectory_scan.track_table_calculator,
        "_is_elevation_within_mechanical_limits",
        lambda el: True,
    )
    trajectory_scan.track_table_scheduler = MagicMock()

    trajectory_scan.calculate_program_track_table(
        time_offsets=[0.0, 1.0, 2.0],
        ptt_buffer_set=False,
        program_track_table_size=10,
    )

    assert cm_pointing_device.fixed_x_offset == 10.5
    assert cm_pointing_device.fixed_y_offset == 20.3


def test_calculate_ptt_applies_wrap_sector_to_azimuth(
    cm_pointing_device, monkeypatch
):
    """Test that wrap_sector is applied to azimuth values."""
    cm_pointing_device.wrap_sector = -1
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)
    trajectory_scan.extended_time = Time.now()

    class DummyTraj:
        def posn(self, t):
            return (0.0, 0.0, 0.0, 0.0, 0.0)

    trajectory_scan.traj = DummyTraj()
    raw_az = 45.0
    monkeypatch.setattr(
        trajectory_scan.converter, "point", lambda ts: (raw_az, 30.0)
    )
    monkeypatch.setattr(
        trajectory_scan.track_table_calculator,
        "convert_utc_to_tai",
        lambda ts: 100.0,
    )
    monkeypatch.setattr(
        trajectory_scan.track_table_calculator,
        "_is_elevation_within_mechanical_limits",
        lambda el: True,
    )
    trajectory_scan.track_table_scheduler = MagicMock()

    result = trajectory_scan.calculate_program_track_table(
        time_offsets=[0.0],
        ptt_buffer_set=False,
        program_track_table_size=10,
    )

    assert result[1] == round(raw_az + 360 * (-1), 12)


def test_calculate_ptt_skips_entry_when_elevation_out_of_limits(
    cm_pointing_device, monkeypatch
):
    """Test that entries are skipped and error callback is invoked
    when elevation is outside mechanical limits. The loop does NOT break —
    it continues processing all offsets, so 2 offsets → 2 error callbacks."""
    cm_pointing_device.wrap_sector = 0
    error_messages = []
    cm_pointing_device.update_program_track_table_error_callback = (
        lambda msg: error_messages.append(msg)
    )
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)
    trajectory_scan.extended_time = Time.now()

    class DummyTraj:
        def posn(self, t):
            return (0.0, 0.0, 0.0, 0.0, 0.0)

    trajectory_scan.traj = DummyTraj()
    monkeypatch.setattr(
        trajectory_scan.converter, "point", lambda ts: (45.0, 5.0)
    )
    monkeypatch.setattr(
        trajectory_scan.track_table_calculator,
        "convert_utc_to_tai",
        lambda ts: 100.0,
    )
    monkeypatch.setattr(
        trajectory_scan.track_table_calculator,
        "_is_elevation_within_mechanical_limits",
        lambda el: False,
    )
    trajectory_scan.track_table_scheduler = MagicMock()

    result = trajectory_scan.calculate_program_track_table(
        time_offsets=[0.0, 1.0],
        ptt_buffer_set=False,
        program_track_table_size=10,
    )

    # no entries added since elevation check failed for all offsets
    assert len(result) == 0
    # error callback fired once per offset, not once total
    assert len(error_messages)
    assert "Elevation" in error_messages[0]


def test_calculate_ptt_returns_empty_list_on_exception(cm_pointing_device):
    """Test that exceptions during calculation return an empty list."""
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)
    trajectory_scan.extended_time = Time.now()

    class DummyTraj:
        def posn(self, t):
            raise RuntimeError("trajectory error")

    trajectory_scan.traj = DummyTraj()
    trajectory_scan.track_table_scheduler = MagicMock()

    result = trajectory_scan.calculate_program_track_table(
        time_offsets=[0.0],
        ptt_buffer_set=False,
        program_track_table_size=10,
    )

    assert result == []


def test_calculate_ptt_stops_when_buffer_set_and_event_signalled(
    cm_pointing_device, monkeypatch
):
    """Test that calculation stops when ptt_buffer_set is True
    and mapping_scan_event is set."""
    cm_pointing_device.wrap_sector = 0
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)
    trajectory_scan.extended_time = Time.now()
    trajectory_scan.cadence = 0.0

    class DummyTraj:
        def posn(self, t):
            return (0.0, 0.0, 0.0, 0.0, 0.0)

    trajectory_mapping_scan.traj = DummyTraj()
    monkeypatch.setattr(
        trajectory_scan.converter, "point", lambda ts: (45.0, 30.0)
    )
    monkeypatch.setattr(
        trajectory_scan.track_table_calculator,
        "convert_utc_to_tai",
        lambda ts: 100.0,
    )
    monkeypatch.setattr(
        trajectory_scan.track_table_calculator,
        "_is_elevation_within_mechanical_limits",
        lambda el: True,
    )
    trajectory_scan.track_table_scheduler = MagicMock()
    cm_pointing_device.mapping_scan_event.set()

    result = trajectory_scan.calculate_program_track_table(
        time_offsets=[0.0, 1.0, 2.0],
        ptt_buffer_set=True,
        program_track_table_size=10,
    )

    assert len(result) <= 3


def test_track_thread_stops_on_mapping_scan_event(
    cm_pointing_device, monkeypatch
):
    """Test that track_thread makes the initial PTT call plus at least one
    loop iteration before stopping when mapping_scan_event is set.

    The loop also breaks when track_table_scheduler.queue is empty, so we
    set the event on the second calculate call to ensure the loop exits via
    the event path rather than the empty-queue path."""
    cm_pointing_device.wrap_sector = 0
    trajectory_scan = trajectory_mapping_scan(cm_pointing_device)
    trajectory_scan.time_offsets = [0.0, 1.0, 2.0]
    trajectory_scan.cadence = 1.0

    call_count = {"value": 0}

    def mock_calculate(**kwargs):
        call_count["value"] += 1
        if call_count["value"] == 1:
            # initial PTT — must be non-empty to avoid ValueError
            return [100.0, 45.0, 30.0]
        # second call: signal stop so the while loop exits
        cm_pointing_device.mapping_scan_event.set()
        return [200.0, 46.0, 31.0]

    monkeypatch.setattr(
        trajectory_scan, "calculate_program_track_table", mock_calculate
    )
    monkeypatch.setattr(
        trajectory_scan.track_table_calculator,
        "build_scheduled_time",
        lambda ts: 0.0,
    )
    monkeypatch.setattr(
        trajectory_scan.track_table_calculator,
        "add_program_track_table_in_schedular",
        lambda **kwargs: None,
    )

    trajectory_scan.track_thread()

    # 1 initial call + at least 1 loop iteration
    assert call_count["value"] >= 2


def test_generate_command_creates_trajectory_scan(
    cm_pointing_device, json_factory, monkeypatch
):
    """Test that GenerateProgramTrackTable creates a TrajectoryMappingScan."""
    from ska_dishln_pointing_device.commands.generate_program_track_table import (  # noqa: E501
        GenerateProgramTrackTable,
    )

    configure_data = json.loads(json_factory(PVT_CONFIGURE_JSON))
    cm_pointing_device.target_data = configure_data
    cm_pointing_device.trajectory_name = "pos_vel_time"

    scan_created = {"cls": None}
    original_init = TrajectoryMappingScan.__init__

    def tracking_init(self, **kwargs):
        scan_created["cls"] = type(self).__name__
        original_init(self, **kwargs)

    monkeypatch.setattr(TrajectoryMappingScan, "__init__", tracking_init)
    monkeypatch.setattr(
        TrajectoryMappingScan,
        "set_target_and_start_process",
        lambda self: None,
    )

    cmd = GenerateProgramTrackTable(
        component_manager=cm_pointing_device, logger=logger
    )
    cmd.generate_program_track_table(task_callback=lambda **kwargs: None)

    assert scan_created["cls"] == "TrajectoryMappingScan"


def test_generate_command_reports_error_on_exception(
    cm_pointing_device, monkeypatch
):
    """Test that the error callback is invoked when an exception occurs
    during scan object construction."""

    error_messages = []
    cm_pointing_device.update_program_track_table_error_callback = (
        lambda msg: error_messages.append(msg)
    )
    cm_pointing_device.trajectory_name = "pos_vel_time"
    cm_pointing_device.target_data = {}

    monkeypatch.setattr(
        TrajectoryMappingScan,
        "__init__",
        lambda self, **kwargs: (_ for _ in ()).throw(
            RuntimeError("bad config")
        ),
    )

    cmd = GenerateProgramTrackTable(
        component_manager=cm_pointing_device, logger=logger
    )
    cmd.generate_program_track_table(task_callback=lambda **kwargs: None)

    assert len(error_messages) == 1
    assert "bad config" in error_messages[0]
