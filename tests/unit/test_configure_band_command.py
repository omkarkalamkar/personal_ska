"""Unit Tests for Track command
"""

import json
import threading
from unittest import mock

import pytest
from ska_control_model import TaskStatus
from ska_tango_base.commands import ResultCode
from ska_tmc_common.enum import DishMode
from ska_tmc_common.exceptions import CommandNotAllowed

from ska_tmc_dishleafnode.constants import COMMAND_COMPLETION_MESSAGE
from tests.settings import (
    DISH_CONFIGURE_1_0,
    simulate_dish_mode_event,
    simulate_result_code_event,
)


def test_configure_band_command_completed(task_callback, cm):
    attrs = {
        'ConfigureBand1.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        ),
    }
    dishMock = mock.Mock(
        **attrs,
    )
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)
    cm.adapter_factory = adapter_factory

    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_configureband_allowed()

    argin = json.dumps({"dish": {"receiver_band": "1"}})
    # cm.configureband(argin, task_callback=task_callback)
    cm.configureband(
        argin, task_callback=task_callback, task_abort_event=threading.Event()
    )
    # task_callback.assert_against_call(
    #     call_kwargs={"status": TaskStatus.QUEUED}
    # )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    simulate_dish_mode_event(cm, DishMode.OPERATE)
    simulate_result_code_event(cm, "ConfigureBand1", ResultCode.OK)
    cm.observable.notify_observers(attribute_value_change=True)
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
        lookahead=6,
    )


def test_configureband_command_adapter_none(task_callback, cm_without_er_lp):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_configureband_allowed()
    argin = json.dumps({"dish": {"receiver_band": "1"}})

    # cm.configureband(argin, task_callback=task_callback)
    cm.configureband(
        argin, task_callback=task_callback, task_abort_event=threading.Event()
    )

    # task_callback.assert_against_call(
    #     call_kwargs={"status": TaskStatus.QUEUED}
    # )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    result = task_callback.assert_against_call(
        status=TaskStatus.COMPLETED, lookahead=4
    )
    assert ResultCode.FAILED == result["result"][0]
    assert "TRANSIENT_NoUsableProfile" in result["result"][1]


def test_configureband_command_not_allowed(cm_without_er_lp):
    cm = cm_without_er_lp
    cm.update_device_dish_mode(DishMode.UNKNOWN)
    with pytest.raises(CommandNotAllowed):
        cm.is_configureband_allowed()


def test_configureband_command_with_spfrx_params(task_callback, cm):
    attrs = {
        'ConfigureBand.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        ),
    }

    dishMock = mock.Mock(
        **attrs,
    )
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)
    cm.adapter_factory = adapter_factory

    cm.update_device_dish_mode(DishMode.STANDBY_FP)
    assert cm.is_configureband_allowed()

    # cm.configureband(DISH_CONFIGURE_1_0, task_callback=task_callback)
    cm.configureband(
        DISH_CONFIGURE_1_0,
        task_callback=task_callback,
        task_abort_event=threading.Event(),
    )
    # task_callback.assert_against_call(
    #     call_kwargs={"status": TaskStatus.QUEUED}
    # )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    simulate_dish_mode_event(cm, DishMode.OPERATE)
    simulate_result_code_event(cm, "ConfigureBand", ResultCode.OK)
    cm.observable.notify_observers(attribute_value_change=True)
    task_callback.assert_against_call(
        call_kwargs={
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, COMMAND_COMPLETION_MESSAGE),
        },
        lookahead=6,
    )
