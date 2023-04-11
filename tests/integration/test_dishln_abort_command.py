import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import DISH_MASTER_DEVICE, event_remover, logger


def invoke_abort_commands_from_dishLN(
    tango_context,
    group_callback,
):

    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    event_remover(
        group_callback,
        ["longRunningCommandsInQueue", "longRunningCommandResult"],
    )
    dish_master = dev_factory.get_device(DISH_MASTER_DEVICE)
    (result, _) = dish_master.AbortCommands()
    assert result[0] == ResultCode.OK


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_abort_command(tango_context, group_callback):
    invoke_abort_commands_from_dishLN(
        tango_context,
        group_callback,
    )
