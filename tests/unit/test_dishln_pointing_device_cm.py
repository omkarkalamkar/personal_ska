import logging
from unittest import mock

from dishln_pointing_device.dishlnpd_component_manager import (
    dishlnpd_component_manager,
)


def test_dish_pointing_device_cm():
    update_program_track_table = mock.Mock()
    cm = dishlnpd_component_manager.DishlnPointingDataComponentManager(
        logging, update_program_track_table
    )
    assert cm.logger == logging
    assert (
        cm.update_pointing_program_track_table_callback
        == update_program_track_table
    )
    assert cm.pointing_program_track_table == {}
    assert cm.target_data is None
    cm.target_data = [1, 2]
    assert cm.target_data == [1, 2]
