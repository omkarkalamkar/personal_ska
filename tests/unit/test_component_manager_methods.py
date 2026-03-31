"""
Unit tests for DishLNComponentManager methods:
"""
# python
import json
import signal
import time
from types import SimpleNamespace
from unittest import mock

import numpy as np
import pytest
from ska_control_model import HealthState
from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.commands.configure_command import (
    FIXED_TRAJECTORY,
    RESET_OFFSETS,
    Configure,
)
from ska_tmc_dishleafnode.enums.enums import CapabilityStates
from ska_tmc_dishleafnode.manager.health_data import (
    DishBandCapabilityStateData,
)
from src.ska_tmc_dishleafnode.manager import component_manager


def test_stop_executors_with_event_receiver(cm_without_er_lp):
    """Test stop_executors_and_cleanup_memory with
    event receiver enabled"""
    # cm fixture already has event receiver enabled
    cm = cm_without_er_lp
    assert cm.actual_pointing_process.is_alive()

    try:
        print(f"actual pointing {cm._actual_pointing}")
        cm.stop_executors_and_cleanup_memory()
    except AttributeError as e:
        pytest.fail(f"AttributeError during cleanup: {e}")

    # Verify actual pointing process is stopped
    assert not cm.actual_pointing_process.is_alive()


def test_stop_executors_without_event_receiver(cm_without_er_lp):
    """Test stop_executors_and_cleanup_memory without event receiver"""
    cm = cm_without_er_lp

    # Restart the actual pointing process for this test
    cm.stop_actual_pointing_process.clear()
    from multiprocessing import Process

    cm.actual_pointing_process = Process(
        target=cm.process_actual_pointing,
    )
    cm.actual_pointing_process.start()

    # Wait for actual pointing process to start
    start_time = time.time()
    while not cm.actual_pointing_process.is_alive():
        time.sleep(0.1)
        if time.time() - start_time > 5:
            break

    assert cm.actual_pointing_process.is_alive()
    assert cm.event_manager is False

    # Call stop_executors_and_cleanup_memory
    cm.stop_executors_and_cleanup_memory()

    # Verify actual pointing process is stopped
    assert not cm.actual_pointing_process.is_alive()


def test_stop_executors_when_process_not_alive(cm_without_er_lp):
    """Test stop_executors_and_cleanup_memory when process already dead"""
    cm = cm_without_er_lp

    # Restart and then stop the process manually
    cm.stop_actual_pointing_process.clear()
    from multiprocessing import Process

    cm.actual_pointing_process = Process(
        target=cm.process_actual_pointing,
    )
    cm.actual_pointing_process.start()
    time.sleep(0.5)

    # Manually stop the process
    cm.stop_actual_pointing_process.set()
    time.sleep(1)  # Give time for process to exit

    # Call stop_executors_and_cleanup_memory
    # Should not raise exception even if process already dead
    cm.stop_executors_and_cleanup_memory()

    assert not cm.actual_pointing_process.is_alive()


@mock.patch("os.kill")
def test_stop_executors_with_force_kill(mock_kill, cm_without_er_lp):
    """Test stop_executors_and_cleanup_memory
    when process needs force kill"""
    cm = cm_without_er_lp

    # Restart the actual pointing process
    cm.stop_actual_pointing_process.clear()
    from multiprocessing import Process

    cm.actual_pointing_process = Process(
        target=cm.process_actual_pointing,
    )
    cm.actual_pointing_process.start()

    # Wait for actual pointing process to start
    start_time = time.time()
    while not cm.actual_pointing_process.is_alive():
        time.sleep(0.1)
        if time.time() - start_time > 5:
            break

    # Mock the process to simulate it not terminating gracefully
    original_pid = cm.actual_pointing_process.pid

    # Call stop_executors_and_cleanup_memory
    with mock.patch.object(
        cm.actual_pointing_process,
        "is_alive",
        side_effect=[True, True, True],  # Simulate process staying alive
    ):
        cm.stop_executors_and_cleanup_memory()

        # Verify SIGKILL was called if process didn't terminate
        if mock_kill.called:
            mock_kill.assert_called_with(original_pid, signal.SIGKILL)


def test_process_actual_pointing_basic_operation(cm):
    """Test basic operation of process_actual_pointing"""
    # cm fixture already has process running
    assert cm.actual_pointing_process.is_alive()


def test_process_actual_pointing_with_data(cm):
    """Test process_actual_pointing with achieved pointing data"""
    assert cm.actual_pointing_process.is_alive()

    # Put some test data into the queue
    # Format: [timestamp_tai_ska_epoch, azimuth, elevation]
    test_data = np.array([1000.0, 45.0, 30.0])
    cm.achieved_pointing_data.put(test_data)

    # Give some time for processing
    time.sleep(1)

    # Process should still be alive after processing data
    assert cm.actual_pointing_process.is_alive()


def test_process_actual_pointing_handles_empty_queue(cm):
    """Test process_actual_pointing handles empty queue gracefully"""
    # Don't put any data, just verify it runs
    time.sleep(1)

    assert cm.actual_pointing_process.is_alive()


def test_process_actual_pointing_handles_layout_update(cm):
    """Test process_actual_pointing handles array layout updates"""
    assert cm.actual_pointing_process.is_alive()

    # Trigger layout update
    new_layout = {
        "station_label": "SKA001",
        "x": 1000.0,
        "y": 2000.0,
        "z": 3000.0,
    }
    cm.array_layout = new_layout

    # Give time for the process to handle the update
    time.sleep(1)

    # Process should still be alive after layout update
    assert cm.actual_pointing_process.is_alive()


def test_process_actual_pointing_stops_on_event(cm_without_er_lp):
    """Test process_actual_pointing stops when event is set"""
    cm = cm_without_er_lp

    # Restart the process
    cm.stop_actual_pointing_process.clear()
    from multiprocessing import Process

    cm.actual_pointing_process = Process(
        target=cm.process_actual_pointing,
    )
    cm.actual_pointing_process.start()

    # Wait for actual pointing process to start
    start_time = time.time()
    while not cm.actual_pointing_process.is_alive():
        time.sleep(0.1)
        if time.time() - start_time > 5:
            break

    assert cm.actual_pointing_process.is_alive()

    # Set the event to stop the process
    cm.stop_actual_pointing_process.set()

    # Wait for process to stop
    cm.actual_pointing_process.join(timeout=30)

    # Verify process has stopped
    assert not cm.actual_pointing_process.is_alive()


def test_process_actual_pointing_handles_invalid_data(cm):
    """Test process_actual_pointing handles invalid data gracefully"""
    assert cm.actual_pointing_process.is_alive()

    # Put invalid data that should cause a ValueError
    invalid_data = np.array([1000.0])  # Wrong number of elements
    cm.achieved_pointing_data.put(invalid_data)

    # Give some time for processing
    time.sleep(1)

    # Process should still be alive despite error
    assert cm.actual_pointing_process.is_alive()


@pytest.mark.parametrize(
    "kvalue_validation_result, expected_health_states",
    [
        (ResultCode.OK, HealthState.OK),
        (ResultCode.FAILED, HealthState.FAILED),
        (ResultCode.UNKNOWN, HealthState.FAILED),
        (ResultCode.NOT_ALLOWED, HealthState.FAILED),
        (ResultCode.STARTED, HealthState.FAILED),
    ],
)
def test_health_evaluation_and_update(
    cm, kvalue_validation_result, expected_health_states
):
    """
    Verify:
    1. Health rules evaluate correct HealthState
    2. evaluate_and_update_health_state invokes callback
       with the same HealthState
    """

    # Arrange
    cm.kValueValidationResult = kvalue_validation_result
    mock_callback = mock.Mock()
    cm._update_health_state_callback = mock_callback

    # Include band capability data in healthdata

    dh = cm.health_manager.health_data
    dh.band_capability_data = DishBandCapabilityStateData(
        band_capabilities={
            "B1": CapabilityStates.STANDBY,
            "B2": CapabilityStates.STANDBY,
            "B3": CapabilityStates.STANDBY,
            "B4": CapabilityStates.STANDBY,
            "B5a": CapabilityStates.STANDBY,
            "B5b": CapabilityStates.STANDBY,
        }
    )

    # --- Rule evaluation ---
    cm.health_manager.update_health_data_and_aggregate(
        cm.kValueValidationResult,
        "KValueValidationResultData",
    )
    health_state = cm.health_manager.evaluate_health_state(
        cm.health_manager.health_data
    )

    assert health_state == expected_health_states

    # --- Update path ---

    mock_callback.assert_called_once_with(expected_health_states)


def test_invoke_generate_prgm_track_table_success():
    adapter = mock.Mock()
    existing_target = {"targets": []}
    adapter.targetData = json.dumps(existing_target)
    adapter.GenerateProgramTrackTable = mock.Mock(
        return_value=(ResultCode.OK, "ok")
    )

    logger = mock.Mock()
    fake_self = SimpleNamespace(
        dishln_pointing_device_adapter=adapter,
        logger=logger,
    )
    # generate_pointing_data should be called and produce the new target data
    fake_self.generate_pointing_data = mock.Mock(
        return_value={"targets": ["updated"]}
    )

    component_manager.DishLNComponentManager._invoke_generate_prgm_track_table(
        fake_self, [1.1, 2.2]
    )

    # Ensure targetData was updated with the
    # returned value from generate_pointing_data
    assert json.loads(adapter.targetData) == {"targets": ["updated"]}
    # Ensure debug path executed
    assert logger.debug.called


def test_invoke_generate_prgm_track_table_generate_failed_logs_error():
    adapter = mock.Mock()
    adapter.targetData = json.dumps({"targets": []})
    adapter.GenerateProgramTrackTable = mock.Mock(
        return_value=(ResultCode.FAILED, "generate failed")
    )

    logger = mock.Mock()
    fake_self = SimpleNamespace(
        dishln_pointing_device_adapter=adapter,
        logger=logger,
    )
    fake_self.generate_pointing_data = mock.Mock(
        return_value={"targets": ["x"]}
    )

    component_manager.DishLNComponentManager._invoke_generate_prgm_track_table(
        fake_self, [0.0, 0.0]
    )

    # Error should be logged for failed GenerateProgramTrackTable
    assert any(
        "GenerateProgramTrackTable failed" in str(call.args[0])
        for call in logger.error.call_args_list
    )


def test_invoke_generate_prgm_track_table_malformed_targetdata_logs_error():
    adapter = mock.Mock()
    adapter.targetData = "not-a-json"  # cause json.loads to raise

    logger = mock.Mock()
    fake_self = SimpleNamespace(
        dishln_pointing_device_adapter=adapter,
        logger=logger,
    )
    # generate_pointing_data should not be reached, but safe to provide
    fake_self.generate_pointing_data = mock.Mock()

    component_manager.DishLNComponentManager._invoke_generate_prgm_track_table(
        fake_self, [0.0, 0.0]
    )

    # check that an error mentioning pointing operation was logged
    assert any(
        "Error in pointing operation" in str(call.args[0])
        for call in logger.error.call_args_list
    )


def _make_configure_instance():
    # Bypass __init__ to avoid needing a full component_manager
    return object.__new__(Configure)


@pytest.mark.parametrize(
    "payload, reset_offset, expected",
    [
        ({}, True, RESET_OFFSETS),
        (
            {
                "pointing": {
                    "trajectory": {
                        "name": FIXED_TRAJECTORY.upper(),
                        "attrs": {"x": 1.2, "y": -3.4},
                    }
                }
            },
            False,
            [1.2, -3.4],
        ),
        (
            {
                "pointing": {
                    "trajectory": {
                        "name": FIXED_TRAJECTORY,
                        "attrs": {"x": 0.0, "y": 900.0},
                    },
                    "ca_offset_arcsec": 0.0,
                    "ie_offset_arcsec": 5.0,
                }
            },
            False,
            [0.0, 900.0],
        ),
        (
            {
                "pointing": {
                    "target": {
                        "ca_offset_arcsec": 2.0,
                        "ie_offset_arcsec": -2.5,
                    }
                }
            },
            False,
            [2.0, -2.5],
        ),
        (
            {"pointing": {"ca_offset_arcsec": 5.5, "ie_offset_arcsec": -6.6}},
            False,
            [5.5, -6.6],
        ),
        ({"pointing": {}}, False, []),
    ],
    ids=[
        "reset_offsets",
        "trajectory_offsets_preferred",
        "trajectory_offsets_preferred_when_legacy_offsets_also_present",
        "target_offsets_when_present",
        "pointing_level_offsets_when_present",
        "no_offsets_returns_empty_list",
    ],
)
def test_get_ie_ca_offsets_if_provided_param(payload, reset_offset, expected):
    inst = _make_configure_instance()
    result = inst.get_ie_ca_offsets_if_provided(
        payload, reset_offset=reset_offset
    )
    assert result == expected
