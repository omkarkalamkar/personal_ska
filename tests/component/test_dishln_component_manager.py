import time

from ska_tmc_common.device_info import DeviceInfo

from tests.settings import create_cm, dish_master_device, logger


def test_dish_working(tango_context):
    logger.info("%s", tango_context)
    cm, start_time = create_cm(dish_master_device)
    dev_info = cm.get_device()
    assert dev_info.unresponsive is False

    elapsed_time = time.time() - start_time
    logger.info("checked %s device in %s", dev_info.dev_name, elapsed_time)
    assert isinstance(dev_info, DeviceInfo)


def test_dish_faulty(tango_context):
    logger.info("%s", tango_context)
    cm, _ = create_cm(dish_master_device)
    devInfo = cm.get_device()
    devInfo.update_unresponsive(True)
    assert devInfo.unresponsive
