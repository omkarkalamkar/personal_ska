from ska_tango_base.commands import ResultCode

from ska_tmc_dishleafnode.commands.abort_command import AbortCommands
from tests.settings import DISH_MASTER_DEVICE, create_cm, logger


def test_abort_command(tango_context):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    abort_command = AbortCommands(cm, logger=logger)
    result_code, _ = abort_command.do()
    assert result_code == ResultCode.OK
