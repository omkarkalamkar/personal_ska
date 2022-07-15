import time

import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)

from ska_tmc_dishleafnode.commands.setstandbyfpmode_command import (
    SetStandbyFPMode,
)
from tests.mock_callable import MockCallable
from tests.settings import create_cm, get_dishln_command_obj, logger


def test_setstandbyfpmode_command(tango_context, dish_master_device):
    _, set_standby_fp_mode_command, adapter_factory = get_dishln_command_obj(
        SetStandbyFPMode
    )
    assert set_standby_fp_mode_command.check_allowed()
    (result_code, _) = set_standby_fp_mode_command.do()
    assert result_code == ResultCode.OK
    adapter = adapter_factory.get_or_create_adapter(dish_master_device)
    adapter.proxy.SetStandbyFPMode.assert_called_once_with()


def test_setstandbyfpmode_command_with_exception(
    tango_context, dish_master_device
):
    cm = create_cm(dish_master_device)
    adapter_factory = HelperAdapterFactory()

    # include exception in SetStandbyFPMode command
    adapter_factory.get_or_create_adapter(
        dish_master_device, attrs={"SetStandbyFPMode.side_effect": Exception}
    )
    set_standby_fp_mode_command = SetStandbyFPMode(
        cm, cm.op_state_model, adapter_factory
    )
    assert set_standby_fp_mode_command.check_allowed()
    (result_code, message) = set_standby_fp_mode_command.do()
    assert result_code == ResultCode.FAILED
    assert dish_master_device in message


@pytest.mark.long_running
def test_setstandbyfpmode_command_lr(tango_context, dish_master_device):
    cm = create_cm(dish_master_device)
    adapter_factory = HelperAdapterFactory()

    set_standby_fp_mode_command = SetStandbyFPMode(
        cm, cm.op_state_model, adapter_factory, logger
    )
    assert set_standby_fp_mode_command.check_allowed()
    unique_id = f"{time.time()}_SetStandbyFPMode"
    task_callback = MockCallable(unique_id)

    task_status, response = cm.setstandbyfpmode(
        set_standby_fp_mode_command, task_callback=task_callback
    )
    assert task_status == TaskStatus.QUEUED
    assert task_callback.status == TaskStatus.QUEUED
    time.sleep(0.1)
    assert task_callback.status == TaskStatus.COMPLETED
