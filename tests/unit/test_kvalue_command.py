import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common.dev_factory import DevFactory
from ska_tmc_common.exceptions import DeviceUnresponsive

from ska_tmc_dishleafnode.commands.set_kvalue import SetKValue
from tests.settings import (
    DISH_LEAF_NODE_DEVICE,
    DISH_MASTER_DEVICE,
    KVALUE,
    create_cm,
    logger,
    retry_for_attribute_value_after_restart,
    wait_for_unresponsive,
)


def test_set_kvalue_command(tango_context):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    set_kvalue_command = SetKValue(cm, logger=logger)
    result_code, _ = set_kvalue_command.do(1)
    assert result_code == ResultCode.OK


def test_dish_unavailable_check_after_dln_init_or_restart(tango_context):
    dev_factory = DevFactory()
    dishln_device = dev_factory.get_device(DISH_LEAF_NODE_DEVICE)
    assert retry_for_attribute_value_after_restart(
        dishln_device, "kValueValidationResult", "dish unavailable"
    )


def test_kvalue_identical_after_dln_restart(tango_context):
    """Directly setting the k-value.
    Component manager looses the dish_dev_name after
     device restart. The below code runs successfully if default
     value of DishMasterFQDN device property is set in tango device class.
    """
    cm = create_cm(DISH_MASTER_DEVICE)
    cm.kValue = KVALUE
    cm.check_kvalue_match(KVALUE) == "identical"


def test_kvalue_not_identical_after_dln_restart(tango_context):
    """Directly setting the k-value.
    Component manager looses the dish_dev_name after
     device restart. The below code runs successfully if default
     value of DishMasterFQDN device property is set in tango device class.
    """
    cm = create_cm(DISH_MASTER_DEVICE)
    cm.kValue = KVALUE
    cm.check_kvalue_match(KVALUE + 1) == "not identical"


def test_kvalue_dish_available(tango_context):
    cm = create_cm(DISH_MASTER_DEVICE)
    dish_kvalue = []
    cm.is_dish_manager_available(dish_kvalue)
    assert dish_kvalue


@pytest.mark.skip("unstable")
def test_setkvalue_command_fail_check_allowed_with_device_unresponsive(
    tango_context,
):
    logger.info("%s", tango_context)
    cm = create_cm(DISH_MASTER_DEVICE)
    cm.get_device().update_unresponsive(True)
    wait_for_unresponsive(cm)
    with pytest.raises(DeviceUnresponsive, match=f"{DISH_MASTER_DEVICE} not available"):
        cm.is_set_kvalue_allowed()
