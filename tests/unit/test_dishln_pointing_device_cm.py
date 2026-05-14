import json
import time
from unittest.mock import patch

import pytest

from ska_dishln_pointing_device.commands.generate_program_track_table import (
    GenerateProgramTrackTable,
)
from ska_dishln_pointing_device.commands.stop_program_track_table import (
    StopProgramTrackTable,
)
from tests.settings import (
    NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES,
    TIMEOUT,
    logger,
)


def test_dish_pointing_device_cm(cm_pointing_device):
    """Test dish pointing device component manager"""
    assert cm_pointing_device.pointing_program_track_table == []
    assert cm_pointing_device.target_data == {}
    cm_pointing_device.target_data = [1, 2]
    assert cm_pointing_device.target_data == [1, 2]


@pytest.mark.parametrize(
    "json_input,wait_time",
    [("dishleafnode_configure", 5), ("dishleafnode_configure_tle_adr63", 15)],
)
def test_dish_pointing_device_generate_program_track_table_command(
    cm_pointing_device, json_factory, json_input, wait_time
):
    """Test to check programTrackTable generation on dish leaf
    node pointing device"""
    timeout = 0
    cm = cm_pointing_device
    configure_data = json_factory(json_input)
    configure_data = json.loads(configure_data)
    del configure_data["dish"]
    cm.target_data = configure_data
    generate_program_track_table = GenerateProgramTrackTable(
        logger=logger, component_manager=cm
    )
    generate_program_track_table.do()
    while not cm.pointing_program_track_table and timeout < wait_time:
        time.sleep(1)
        timeout += 1

    assert (
        len(cm.pointing_program_track_table)
        == NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES
    )


def test_trajectory_name_set_from_target_data(
    cm_pointing_device, json_factory
):
    """Tests that trajectory_name is set correctly based on target data."""
    cm = cm_pointing_device
    configure_data = json_factory("delta_configure")
    configure_data = json.loads(configure_data)
    cm.target_data = configure_data
    assert cm.trajectory_name == "fixed"
    configure_data = json_factory("partial_configure")
    cm.target_data = json.loads(configure_data)
    assert cm.trajectory_name == "fixed"


@pytest.mark.parametrize(
    "json_input,wait_time",
    [
        ("dishleafnode_configure", 5),
        ("dishleafnode_configure_tle_adr63", 10),
    ],
)
def test_dish_pointing_device_stop_program_track_table_command(
    cm_pointing_device, json_factory, json_input, wait_time
):
    """Test to check stop programTrackTable generation on dish leaf
    node pointing device"""
    timeout = 0
    cm = cm_pointing_device
    configure_data = json_factory(json_input)
    configure_data = json.loads(configure_data)
    del configure_data["dish"]
    cm.target_data = configure_data
    generate_program_track_table = GenerateProgramTrackTable(
        logger=logger, component_manager=cm
    )
    stop_program_track_table = StopProgramTrackTable(
        logger=logger, component_manager=cm
    )

    generate_program_track_table.do()
    while not cm.pointing_program_track_table and timeout < wait_time:
        time.sleep(1)
        timeout += 1

    stop_program_track_table.do()
    while cm.pointing_program_track_table and timeout < wait_time:
        time.sleep(1)
        timeout += 1
    assert len(cm.pointing_program_track_table) == 0


def test_dish_pointing_device_program_track_table_error(
    cm_pointing_device, json_factory
):
    """Test to check program track table error"""
    timeout = 0
    cm = cm_pointing_device
    configure_data = json_factory("non_sidereal_tracking")
    configure_data = json.loads(configure_data)
    del configure_data["dish"]
    configure_data["pointing"]["target"]["target_name"] = "Urenus"
    cm.target_data = configure_data
    generate_program_track_table = GenerateProgramTrackTable(
        logger=logger, component_manager=cm
    )
    generate_program_track_table.do()
    while not cm.current_track_table_error and timeout < 5:
        time.sleep(1)
        timeout += 1
    assert "unknown *special* body 'Urenus'" in cm.current_track_table_error


@pytest.mark.parametrize(
    "json_input",
    [
        "dishleafnode_configure",
        "dishleafnode_configure_tle_adr63",
    ],
)
def test_dish_pointing_device_multi_command_scenarios(
    cm_pointing_device, json_factory, json_input
):
    """
    This test tests following scenarios:
    1. Ensure same thread is not used for tracktable calculation
    in following command sequence:
    GenerateProgramTrackTable -> GenerateProgramTrackTable

    2. Ensure same thread is not are used in following command sequence:
    GenerateProgramTrackTable -> StopProgramTrackTable ->
    GenerateProgramTrackTable

    """
    cm = cm_pointing_device
    configure_data = json_factory(json_input)
    configure_data = json.loads(configure_data)
    del configure_data["dish"]
    cm.target_data = configure_data
    generate_program_track_table = GenerateProgramTrackTable(
        logger=logger, component_manager=cm
    )
    generate_program_track_table.do()
    start_time = time.time()
    while (
        not cm.pointing_program_track_table
        and (time.time() - start_time) < TIMEOUT
    ):
        time.sleep(1)

    assert (
        len(cm.pointing_program_track_table)
        == NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES
    )
    track_table_thread1 = (
        cm.current_mapping_scan_obj.component_manager.track_table_thread
    )
    generate_program_track_table.do()

    start_time = time.time()
    while (
        not cm.pointing_program_track_table
        and (time.time() - start_time) < TIMEOUT
    ):
        time.sleep(1)

    assert (
        len(cm.pointing_program_track_table)
        == NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES
    )
    track_table_thread2 = (
        cm.current_mapping_scan_obj.component_manager.track_table_thread
    )

    assert track_table_thread1 is not track_table_thread2

    stop_program_track_table = StopProgramTrackTable(
        logger=logger, component_manager=cm
    )

    stop_program_track_table.do()
    start_time = time.time()
    while (
        cm.pointing_program_track_table
        and (time.time() - start_time) < TIMEOUT
    ):
        time.sleep(1)
    assert len(cm.pointing_program_track_table) == 0

    generate_program_track_table.do()
    start_time = time.time()
    while (
        not cm.pointing_program_track_table
        and (time.time() - start_time) < TIMEOUT
    ):
        time.sleep(1)

    assert (
        len(cm.pointing_program_track_table)
        == NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES
    )

    track_table_thread3 = (
        cm.current_mapping_scan_obj.component_manager.track_table_thread
    )
    assert track_table_thread3 is not track_table_thread1
    assert track_table_thread3 is not track_table_thread2

    stop_program_track_table.do()
    start_time = time.time()
    while (
        cm.pointing_program_track_table
        and (time.time() - start_time) < TIMEOUT
    ):
        time.sleep(1)
    assert len(cm.pointing_program_track_table) == 0


def test_track_table_min_frequency(cm_pointing_device, json_factory):
    """Test that PTT entries are generated with expected cadence.

    With TrajectoryMappingScan, the cadence between PTT entries is
    derived from the trajectory time offsets (1s for fixed trajectory),
    not from track_table_update_rate.
    """
    timeout = 0
    cm = cm_pointing_device
    configure_data = json_factory("dishleafnode_configure")
    configure_data = json.loads(configure_data)
    del configure_data["dish"]
    cm.target_data = configure_data
    generate_program_track_table = GenerateProgramTrackTable(
        logger=logger, component_manager=cm
    )
    generate_program_track_table.do()
    while not cm.pointing_program_track_table and timeout < 5:
        time.sleep(1)
        timeout += 1
    assert (
        len(cm.pointing_program_track_table)
        == NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES
    )

    tai_first = cm.pointing_program_track_table[0]
    tai_second = cm.pointing_program_track_table[3]
    cadence = round(tai_second - tai_first, 1)
    assert cadence == 1.0


def test_track_table_max_frequency(cm_pointing_device, json_factory):
    """Test to check max track table frequency"""
    timeout = 0
    cm = cm_pointing_device
    configure_data = json_factory("dishleafnode_configure")
    configure_data = json.loads(configure_data)
    del configure_data["dish"]
    cm.target_data = configure_data
    cm.track_table_update_rate = 50
    generate_program_track_table = GenerateProgramTrackTable(
        logger=logger, component_manager=cm
    )
    generate_program_track_table.do()
    while not cm.pointing_program_track_table and timeout < 5:
        time.sleep(1)
        timeout += 1
    tracktable1_time = cm.pointing_program_track_table[0]
    time.sleep(51)
    tracktable2_time = cm.pointing_program_track_table[0]
    assert (tracktable2_time - tracktable1_time) == cm.track_table_update_rate


def test_dish_pointing_schedular_length(cm_pointing_device, json_factory):
    """Test to check programTrackTable generation and scheduler queue length
    on dish leaf node pointing device."""
    timeout = 0
    cm = cm_pointing_device
    configure_data = json_factory("dishleafnode_configure")
    configure_data = json.loads(configure_data)
    del configure_data["dish"]
    cm.target_data = configure_data

    class TestScheduler:
        def __init__(self):
            self.queue = []

        def enterabs(self, scheduled_time, event_priority, func, argument=()):
            self.queue.append((scheduled_time, event_priority, func, argument))

        def run(self, blocking=False):
            # Execute any due events (scheduled_time <= now) and remove them
            now = time.time()
            remaining = []
            for item in self.queue:
                scheduled_time, event_priority, func, argument = item
                if scheduled_time <= now:
                    try:
                        func(*argument)
                    except Exception:
                        # Ignore callback exceptions in test scheduler
                        pass
                else:
                    remaining.append(item)
            self.queue = remaining

    real_scheduler = TestScheduler()
    with patch(
        "ska_dishln_pointing_device.dishlnpd_component_manager."
        "component_manager.sched.scheduler",
        return_value=real_scheduler,
    ):
        generate_program_track_table = GenerateProgramTrackTable(
            logger=logger, component_manager=cm
        )
        generate_program_track_table.do()
        cm.pointing_program_track_table = []
        while not cm.pointing_program_track_table and timeout < 50:
            time.sleep(1)
            timeout += 1
        assert cm.pointing_program_track_table
        time.sleep(3)
        sched_len = len(real_scheduler.queue)
        assert sched_len <= 6
        assert sched_len > 0
        # Assert entries in the PTT
        assert (
            len(cm.pointing_program_track_table)
            == NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES
        )


def test_array_layout_set_with_dict_updates_and_calls_converter(
    cm_pointing_device, monkeypatch
):
    cm = cm_pointing_device
    calls = {"n": 0}

    def _fake_create_antenna_obj():
        calls["n"] += 1

    monkeypatch.setattr(
        cm.converter, "create_antenna_obj", _fake_create_antenna_obj
    )
    layout = {"stations": {"SKA001": {"lat": 1.0, "lon": 2.0, "elev": 3.0}}}
    cm.array_layout = layout
    assert cm.array_layout == layout
    assert calls["n"] == 1


def test_array_layout_set_with_json_string_parses_and_updates(
    cm_pointing_device, monkeypatch
):
    cm = cm_pointing_device
    calls = {"n": 0}

    def _fake_create_antenna_obj():
        calls["n"] += 1

    monkeypatch.setattr(
        cm.converter, "create_antenna_obj", _fake_create_antenna_obj
    )
    layout_dict = {
        "stations": {"SKA002": {"lat": -10.5, "lon": 45.0, "elev": 1000}}
    }
    layout_json = json.dumps(layout_dict)
    cm.array_layout = layout_json
    assert cm.array_layout == layout_dict
    assert calls["n"] == 1


def test_array_layout_idempotent_when_setting_same_value(
    cm_pointing_device, monkeypatch
):
    cm = cm_pointing_device

    calls = {"n": 0}

    def _fake_create_antenna_obj():
        calls["n"] += 1

    monkeypatch.setattr(
        cm.converter, "create_antenna_obj", _fake_create_antenna_obj
    )
    layout = {"stations": {"SKA003": {"lat": 0.0, "lon": 0.0, "elev": 0.0}}}
    cm.array_layout = layout
    assert calls["n"] == 1
    cm.array_layout = layout
    assert calls["n"] == 1


def test_array_layout_getter_returns_top_level_copy(
    cm_pointing_device, monkeypatch
):
    cm = cm_pointing_device
    monkeypatch.setattr(cm.converter, "create_antenna_obj", lambda: None)
    layout = {
        "stations": {"SKA004": {"lat": 12.3, "lon": 45.6, "elev": 789.0}}
    }
    cm.array_layout = layout
    view = cm.array_layout
    view["new_top_level_key"] = 123
    assert "new_top_level_key" not in cm._array_layout
    assert cm._array_layout["stations"]["SKA004"]["lat"] == 12.3
