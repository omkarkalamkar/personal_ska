import json
import time

from ska_dishln_pointing_device.commands.generate_program_track_table import (
    GenerateProgramTrackTable,
)
from ska_dishln_pointing_device.commands.stop_program_track_table import (
    StopProgramTrackTable,
)
from tests.settings import logger


def test_dish_pointing_device_cm(cm_pointig_device):
    """Test dish pointing device component manager"""
    assert cm_pointig_device.pointing_program_track_table == []
    assert cm_pointig_device.target_data == ""
    cm_pointig_device.target_data = [1, 2]
    assert cm_pointig_device.target_data == [1, 2]


def test_dish_pointing_device_generate_program_track_table_command(
    cm_pointig_device, json_factory
):
    """Test to check programTrackTable generation on dish leaf
    node pointing device"""
    timeout = 0
    cm = cm_pointig_device
    configure_data = json_factory("dishleafnode_configure")
    configure_data = json.loads(configure_data)
    del configure_data["dish"]
    cm.target_data = configure_data
    generate_program_track_table = GenerateProgramTrackTable(
        logger=logger, component_manager=cm
    )
    generate_program_track_table.do()
    while not cm.pointing_program_track_table and timeout < 5:
        time.sleep(1)
        timeout += 1

    assert len(cm.pointing_program_track_table) == (cm.track_table_entries * 3)


def test_dish_pointing_device_stop_program_track_table_command(
    cm_pointig_device, json_factory
):
    """Test to check stop programTrackTable generation on dish leaf
    node pointing device"""
    timeout = 0
    cm = cm_pointig_device
    configure_data = json_factory("dishleafnode_configure")
    configure_data = json.loads(configure_data)
    del configure_data["dish"]
    cm.target_data = configure_data
    generate_program_track_table = GenerateProgramTrackTable(
        logger=logger, component_manager=cm
    )
    stop_program_track_table = StopProgramTrackTable(
        logger=logger, component_manager=cm
    )

    generate_program_track_table.do()
    while not cm.pointing_program_track_table and timeout < 5:
        time.sleep(1)
        timeout += 1

    stop_program_track_table.do()
    while cm.pointing_program_track_table and timeout < 5:
        time.sleep(1)
        timeout += 1
    assert len(cm.pointing_program_track_table) == 0


def test_dish_pointing_device_program_track_table_error(
    cm_pointig_device, json_factory
):
    """Test to check program track table error"""
    timeout = 0
    cm = cm_pointig_device
    configure_data = json_factory("non_sidereal_tracking")
    configure_data = json.loads(configure_data)
    del configure_data["dish"]
    configure_data["pointing"]["target_name"] = "Urenus"
    cm.target_data = configure_data
    generate_program_track_table = GenerateProgramTrackTable(
        logger=logger, component_manager=cm
    )
    generate_program_track_table.do()
    while not cm.current_track_table_error and timeout < 5:
        time.sleep(1)
        timeout += 1
    assert "exception" in cm.current_track_table_error.lower()
