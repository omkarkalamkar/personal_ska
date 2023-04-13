import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory

from tests.settings import DISH_LEAF_NODE_DEVICE, event_remover, logger


def abort_on_dish_leaf_node(
    tango_context,
    group_callback,
):

    logger.info(f"{tango_context}")
    dev_factory = DevFactory()
    dish_leaf_node = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)
    event_remover(
        group_callback,
        ["longRunningCommandsInQueue", "longRunningCommandResult"],
    )
    assert dish_leaf_node.is_Abort_allowed() == True
    result_fp, _ = dish_leaf_node.Abort()
    assert result_fp[0] == ResultCode.OK


@pytest.mark.post_deployment
@pytest.mark.SKA_mid
def test_abort_command(tango_context, group_callback):
    abort_on_dish_leaf_node(
        tango_context,
        group_callback,
    )
