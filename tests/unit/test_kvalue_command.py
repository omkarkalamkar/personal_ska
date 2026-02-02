from unittest import mock

import pytest
from ska_tango_base.commands import ResultCode
from ska_tmc_common import DeviceUnresponsive

from ska_tmc_dishleafnode.commands.set_kvalue import SetKValue
from ska_tmc_dishleafnode.manager.dish_kvalue_validation_manager import (
    DishkValueValidationManager,
)
from tests.settings import (
    DISH_MASTER_DEVICE,
    logger,
    wait_and_validate_attribute_value_available,
)


def test_set_kvalue_command(cm_without_er_lp):
    cm = cm_without_er_lp
    attrs = {
        'SetKValue.return_value': (
            [ResultCode.OK],
            ["Command Completed"],
        ),
    }
    dishMock = mock.Mock(**attrs)
    factory_attrs = {'get_or_create_adapter.return_value': dishMock}
    adapter_factory = mock.Mock(**factory_attrs)
    set_kvalue_command = SetKValue(cm, logger=logger)
    set_kvalue_command._adapter_factory = adapter_factory
    result_code, _ = set_kvalue_command.do(1)
    assert result_code == ResultCode.OK


def test_dish_unavailable_check_after_dln_init_or_restart(dishln_device):
    assert wait_and_validate_attribute_value_available(
        dishln_device,
        "kValueValidationResult",
        str(int(ResultCode.NOT_ALLOWED)),
    )


def test_dm_available_after_dln_init_or_restart(
    cm_without_er_lp, tango_context
):
    cm = cm_without_er_lp
    cm.get_device(cm.dish_dev_name).update_unresponsive(False, "")
    kvalue_validation_obj = DishkValueValidationManager(cm, logger)
    assert kvalue_validation_obj.is_dish_manager_ready()


def test_kvalue_identical_after_dln_restart(cm_without_er_lp):
    cm = cm_without_er_lp
    kvalue_validation_obj = DishkValueValidationManager(cm, logger)
    cm.kValue = 9
    kvalue_validation_obj.dish_manager_kvalue = 9
    kvalue_validation_obj.validate_dish_kvalue()
    assert cm.kValueValidationResult == ResultCode.OK


def test_kvalue_not_identical_after_dln_restart(cm_without_er_lp):
    cm = cm_without_er_lp
    cm.kValue = 9
    kvalue_validation_obj = DishkValueValidationManager(cm, logger)
    kvalue_validation_obj.dish_manager_kvalue = 10
    kvalue_validation_obj.validate_dish_kvalue()
    assert cm.kValueValidationResult == ResultCode.FAILED


def test_setkvalue_command_fail_check_allowed_with_device_unresponsive(
    cm_without_er_lp,
):
    cm = cm_without_er_lp
    cm.get_device(cm.dish_dev_name).update_unresponsive(True, "Not available")
    with pytest.raises(
        DeviceUnresponsive, match=f"{DISH_MASTER_DEVICE} not available"
    ):
        cm.is_set_kvalue_allowed()
