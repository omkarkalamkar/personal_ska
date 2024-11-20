import logging
import threading
import time
from unittest import mock

import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.enum import DishMode, PointingState

from ska_dishln_pointing_device.commands.generate_program_track_table import (
    GenerateProgramTrackTable,
)
from ska_dishln_pointing_device.commands.stop_program_track_table import (
    StopProgramTrackTable,
)
from ska_tmc_dishleafnode.commands.abort_command import AbortCommands
from ska_tmc_dishleafnode.commands.set_kvalue import SetKValue
from tests.settings import logger, simulate_dish_mode_event, wait_for_dish_mode


def test_generate_program_track_table(cm_pointig_device):
    generate_program_track_table = GenerateProgramTrackTable(
        logging, cm_pointig_device
    )
    cm_pointig_device.target_data = {"1": 1}  # invalid target data
    with pytest.raises(KeyError, match="pointing"):
        generate_program_track_table.do()
    cm_pointig_device.target_data = {"pointing": [1, 2]}  # invalid target data
    with pytest.raises(Exception):
        generate_program_track_table.do()


def test_stop_program_track_table():
    attrs = {
        "mapping_scan_event.set.side_effect": AttributeError(
            "mapping scan event doesn't have set attribute"
        )
    }
    cm = mock.Mock(track_thread_lock=threading.Lock(), **attrs)
    stop_program_track_table = StopProgramTrackTable(logging, cm)
    # invalid target data
    with pytest.raises(
        Exception, match="mapping scan event doesn't have set attribute"
    ):
        stop_program_track_table.do()


def test_error_propagation_program_track_table(
    cm_without_er_lp,
    task_callback,
    json_factory,
):
    cm = cm_without_er_lp
    cm.kvalue_validation_thread.cancel()
    cm.command_timeout = 5
    attrs = {
        'SetKValue.return_value': ([ResultCode.OK], ["Command Completed"]),
        'TrackLoadStaticOff.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        ),
        'ConfigureBand2.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        ),
        'GenerateProgramTrackTable.side_effect': (Exception("error")),
    }
    dishMock = mock.Mock(
        programTrackTable=[
            775853423.2247269,
            178.758613204265,
            31.165682681453,
        ],
        **attrs,
    )
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)
    cm.adapter_factory = adapter_factory
    simulate_dish_mode_event(cm, DishMode.STANDBY_FP)
    assert wait_for_dish_mode(cm, DishMode.STANDBY_FP)
    assert cm.is_configure_allowed()
    set_kvalue_command = SetKValue(cm, logger=logger)
    set_kvalue_command._adapter_factory = adapter_factory
    result_code, _ = set_kvalue_command.do(1)
    assert result_code == ResultCode.OK
    configure_input_str = json_factory("dishleafnode_configure")
    cm.configure(configure_input_str, task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    time.sleep(1)
    assert (
        cm.current_track_table_error
        == "Exception while generating programTrackTable error"
    )


def test_error_propagation_stop_program_track_table(
    task_callback, cm_without_er_lp
):
    attrs = {
        'StopProgramTrackTable.side_effect': (Exception("error")),
        'TrackStop.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        ),
        'AbortCommands.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        ),
    }
    dishMock = mock.Mock(
        programTrackTable=[
            775853423.2247269,
            178.758613204265,
            31.165682681453,
        ],
        **attrs,
    )
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)
    cm = cm_without_er_lp
    cm.adapter_factory = adapter_factory
    simulate_dish_mode_event(cm, DishMode.OPERATE)
    cm.update_device_pointing_state(PointingState.TRACK)
    assert cm.is_trackstop_allowed()
    cm.trackstop(task_callback=task_callback)
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.QUEUED}
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    time.sleep(1)
    assert (
        cm.current_track_table_error
        == "Exception while stopping programTrackTable error"
    )


def test_error_propagation_abort_stop_program_track_table(
    task_callback, cm_without_er_lp
):
    attrs = {
        'StopProgramTrackTable.side_effect': (Exception("error")),
        'AbortCommands.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        ),
    }
    dishMock = mock.Mock(
        programTrackTable=[
            775853423.2247269,
            178.758613204265,
            31.165682681453,
        ],
        **attrs,
    )
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)
    cm = cm_without_er_lp
    abort_command = AbortCommands(
        cm,
        logger=cm.logger,
    )
    abort_command._adapter_factory = adapter_factory
    cm.abort_event.set()
    resulcode, message = abort_command.invoke_abort()
    assert resulcode == ResultCode.FAILED
    assert message == (
        " StopProgramTrackTable: "
        + "There was an error while stopping the generation of "
        + "program track table: error"
    )
