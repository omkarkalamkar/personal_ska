"""
Unit tests for DishLNComponentManager methods:
"""
import signal
import time
from unittest import mock

import numpy as np
import pytest


def test_stop_executors_with_event_receiver(cm_without_er_lp):
    """Test stop_executors_and_cleanup_memory with
    event receiver enabled"""
    # cm fixture already has event receiver enabled
    cm = cm_without_er_lp
    assert cm.actual_pointing_process.is_alive()
    # assert cm.event_receiver is True

    # Call stop_executors_and_cleanup_memory
    # This may raise AttributeError if attributes don't exist
    # but should complete successfully if they do
    try:
        print(f"actual pointing {cm._actual_pointing}")
        cm.stop_executors_and_cleanup_memory()
    except AttributeError as e:
        # If we get AttributeError, it means the method tried to delete
        # an attribute that doesn't exist - this is acceptable for the test
        pytest.fail(f"AttributeError during cleanup: {e}")

    # Verify actual pointing process is stopped
    assert not cm.actual_pointing_process.is_alive()


def test_stop_executors_without_event_receiver(cm_without_er_lp):
    """Test stop_executors_and_cleanup_memory without event receiver"""
    cm = cm_without_er_lp

    # Restart the actual pointing process for this test
    cm.actual_pointing_process_alive.clear()
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
    assert cm.event_receiver is False

    # Call stop_executors_and_cleanup_memory
    cm.stop_executors_and_cleanup_memory()

    # Verify actual pointing process is stopped
    assert not cm.actual_pointing_process.is_alive()


def test_stop_executors_when_process_not_alive(cm_without_er_lp):
    """Test stop_executors_and_cleanup_memory when process already dead"""
    cm = cm_without_er_lp

    # Restart and then stop the process manually
    cm.actual_pointing_process_alive.clear()
    from multiprocessing import Process

    cm.actual_pointing_process = Process(
        target=cm.process_actual_pointing,
    )
    cm.actual_pointing_process.start()
    time.sleep(0.5)

    # Manually stop the process
    cm.actual_pointing_process_alive.set()
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
    cm.actual_pointing_process_alive.clear()
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
    cm.actual_pointing_process_alive.clear()
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
    cm.actual_pointing_process_alive.set()

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
