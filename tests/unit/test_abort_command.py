import logging

import pytest
from ska_tango_base.commands import ResultCode, TaskStatus
from ska_tmc_common.exceptions import CommandNotAllowed, DeviceUnresponsive
from tango import DevState

from tests.settings import DISH_MASTER_DEVICE, create_cm, logger


@pytest.mark.SKA_mid
def test_abort_command(tango_context, task_callback):
    logger = logging.getLogger(__name__)
    cm = create_cm(DISH_MASTER_DEVICE)
    assert cm.is_abort_allowed()
    result_code, _ = cm.invoke_abort_command(
        logger=logger, task_callback=task_callback
    )
    task_callback.assert_against_call(
        call_kwargs={"status": TaskStatus.IN_PROGRESS}
    )
    task_callback.assert_against_call(
        status=TaskStatus.COMPLETED, result=ResultCode.OK
    )
    assert result_code == ResultCode.OK


@pytest.mark.SKA_mid
def test_abort_command_fail_check_allowed_with_device_unresponsive(
    tango_context,
):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    cm.get_device().update_unresponsive(True)
    with pytest.raises(
        DeviceUnresponsive, match=f"{DISH_MASTER_DEVICE} not available"
    ):
        cm.check_device_responsive()
    cm.op_state_model._op_state = DevState.FAULT
    with pytest.raises(
        CommandNotAllowed,
        match="Reason: The current"
        + f" operational state is {cm.op_state_model.op_state}.",
    ):
        cm.is_abort_allowed()
