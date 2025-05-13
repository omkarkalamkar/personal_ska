import json
import time

from ska_dishln_pointing_device.commands.generate_program_track_table import (
    GenerateProgramTrackTable,
)
from ska_dishln_pointing_device.commands.stop_program_track_table import (
    StopProgramTrackTable,
)
from tests.settings import (
    NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES,
    TIMEOUT,
    logger,
)


def test_dish_pointing_device_cm(cm_pointig_device):
    """Test dish pointing device component manager"""
    assert cm_pointig_device.pointing_program_track_table == []
    assert cm_pointig_device.target_data == {}
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

    assert (
        len(cm.pointing_program_track_table)
        == NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES
    )


def test_is_fixed_mapping_scan(cm_pointig_device, json_factory):
    """Tests that is fixed mapping scan return true or false
    based on target data set
    """
    cm = cm_pointig_device
    configure_data = json_factory("delta_configure")
    configure_data = json.loads(configure_data)
    cm.target_data = configure_data
    assert cm.is_fixed_mapping_scan()
    configure_data = json_factory("partial_configure")
    cm.target_data = json.loads(configure_data)
    assert not cm.is_fixed_mapping_scan()


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
    configure_data["pointing"]["target"]["target_name"] = "Urenus"
    cm.target_data = configure_data
    generate_program_track_table = GenerateProgramTrackTable(
        logger=logger, component_manager=cm
    )
    generate_program_track_table.do()
    while not cm.current_track_table_error and timeout < 5:
        time.sleep(1)
        timeout += 1
    assert "unknown *special* body" in cm.current_track_table_error.lower()


def test_dish_pointing_device_multi_command_scenarios(
    cm_pointig_device, json_factory
):
    """
    This test tests following scenarios:
    1. Ensure same thread is not used for tracktable calculation
    in following command sequence:
    GenerateProgramTrackTable -> GenerateProgramTrackTable

    2. Ensure same thread is not are used in following command sequence:
    GenerateProgramTrackTable -> StopProgramTrackTable ->
    GenerateProgramTrackTable

    """
    cm = cm_pointig_device
    configure_data = json_factory("dishleafnode_configure")
    configure_data = json.loads(configure_data)
    del configure_data["dish"]
    cm.target_data = configure_data
    generate_program_track_table = GenerateProgramTrackTable(
        logger=logger, component_manager=cm
    )
    generate_program_track_table.do()
    start_time = time.time()
    while (
        not cm.pointing_program_track_table
        and (time.time() - start_time) < TIMEOUT
    ):
        time.sleep(1)

    assert (
        len(cm.pointing_program_track_table)
        == NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES
    )
    track_table_thread1 = cm.track_table_thread
    generate_program_track_table.do()

    start_time = time.time()
    while (
        not cm.pointing_program_track_table
        and (time.time() - start_time) < TIMEOUT
    ):
        time.sleep(1)

    assert (
        len(cm.pointing_program_track_table)
        == NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES
    )
    track_table_thread2 = cm.track_table_thread

    assert track_table_thread1 is not track_table_thread2

    stop_program_track_table = StopProgramTrackTable(
        logger=logger, component_manager=cm
    )

    stop_program_track_table.do()
    start_time = time.time()
    while (
        cm.pointing_program_track_table
        and (time.time() - start_time) < TIMEOUT
    ):
        time.sleep(1)
    assert len(cm.pointing_program_track_table) == 0

    generate_program_track_table.do()
    start_time = time.time()
    while (
        not cm.pointing_program_track_table
        and (time.time() - start_time) < TIMEOUT
    ):
        time.sleep(1)

    assert (
        len(cm.pointing_program_track_table)
        == NUMBER_OF_PROGRAM_TRACK_TABLE_ENTRIES
    )

    track_table_thread3 = cm.track_table_thread
    assert track_table_thread3 is not track_table_thread1
    assert track_table_thread3 is not track_table_thread2

    stop_program_track_table.do()
    start_time = time.time()
    while (
        cm.pointing_program_track_table
        and (time.time() - start_time) < TIMEOUT
    ):
        time.sleep(1)
    assert len(cm.pointing_program_track_table) == 0


def test_track_table_min_frequency(cm_pointig_device, json_factory):
    timeout = 0
    cm = cm_pointig_device
    configure_data = json_factory("dishleafnode_configure")
    configure_data = json.loads(configure_data)
    del configure_data["dish"]
    cm.target_data = configure_data
    cm.track_table_update_rate = 2.5
    generate_program_track_table = GenerateProgramTrackTable(
        logger=logger, component_manager=cm
    )
    generate_program_track_table.do()
    while not cm.pointing_program_track_table and timeout < 5:
        time.sleep(1)
        timeout += 1
    tracktable1_time = cm.pointing_program_track_table[0]
    time.sleep(3)
    tracktable2_time = cm.pointing_program_track_table[0]
    assert (tracktable2_time - tracktable1_time) == cm.track_table_update_rate


def test_track_table_max_frequency(cm_pointig_device, json_factory):
    timeout = 0
    cm = cm_pointig_device
    configure_data = json_factory("dishleafnode_configure")
    configure_data = json.loads(configure_data)
    del configure_data["dish"]
    cm.target_data = configure_data
    cm.track_table_update_rate = 50
    generate_program_track_table = GenerateProgramTrackTable(
        logger=logger, component_manager=cm
    )
    generate_program_track_table.do()
    while not cm.pointing_program_track_table and timeout < 5:
        time.sleep(1)
        timeout += 1
    tracktable1_time = cm.pointing_program_track_table[0]
    time.sleep(51)
    tracktable2_time = cm.pointing_program_track_table[0]
    assert (tracktable2_time - tracktable1_time) == cm.track_table_update_rate
