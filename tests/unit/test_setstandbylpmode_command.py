import time

import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.test_helpers.helper_adapter_factory import (
    HelperAdapterFactory,
)

from ska_tmc_dishleafnode.commands.setstandbylpmode_command import (
    SetStandbyLPMode,
)
from tests.mock_callable import MockCallable
from tests.settings import create_cm, get_dishln_command_obj, logger


def test_setstandbylpmode_command(tango_context, dish_master_device):
    _, set_standby_lp_mode_command, adapter_factory = get_dishln_command_obj(
        SetStandbyLPMode
    )
    assert set_standby_lp_mode_command.check_allowed()
    (result_code, _) = set_standby_lp_mode_command.do()
    assert result_code == ResultCode.OK
    adapter = adapter_factory.get_or_create_adapter(dish_master_device)
    adapter.proxy.SetStandbyLPMode.assert_called_once_with()


def test_setstandbylpmode_command_with_exception(
    tango_context, dish_master_device
):
    cm = create_cm(dish_master_device)
    adapter_factory = HelperAdapterFactory()

    # include exception in SetStandbyLPMode command
    adapter_factory.get_or_create_adapter(
        dish_master_device, attrs={"SetStandbyLPMode.side_effect": Exception}
    )
    set_standby_lp_mode_command = SetStandbyLPMode(
        cm, cm.op_state_model, adapter_factory
    )
    assert set_standby_lp_mode_command.check_allowed()
    (result_code, message) = set_standby_lp_mode_command.do()
    assert result_code == ResultCode.FAILED
    assert dish_master_device in message


@pytest.mark.long_running2
def test_setstandbylpmode_command_adapter_none(
    tango_context, dish_master_device
):
    cm = create_cm(dish_master_device)

    setstandbylpmode_command = SetStandbyLPMode(cm, cm.op_state_model, logger)
    assert setstandbylpmode_command.check_allowed()
    unique_id = f"{time.time()}_SetStandbyLPMode"
    task_callback = MockCallable(unique_id)

    cm.setstandbylpmode(setstandbylpmode_command, task_callback=task_callback)
    assert task_callback.status == TaskStatus.QUEUED
    time.sleep(0.1)
    assert task_callback.status == TaskStatus.FAILED
    failed_message = "Adapter is None"
    assert failed_message in task_callback.exception
