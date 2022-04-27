from ska_tmc_common.device_info import DishDeviceInfo

from tests.settings import create_cm, dish_master_device, logger


def test_dish_working(tango_context):
    logger.info("%s", tango_context)
    cm = create_cm(dish_master_device)
    dev_info = cm.get_device()
    assert dev_info.unresponsive is False
    assert isinstance(dev_info, DishDeviceInfo)


def test_dish_faulty(tango_context):
    logger.info("%s", tango_context)
    cm = create_cm(dish_master_device)
    devInfo = cm.get_device()
    devInfo.update_unresponsive(True)
    assert devInfo.unresponsive
