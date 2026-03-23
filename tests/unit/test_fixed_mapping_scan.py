import json
import time

import katpoint
import pytest

from ska_dishln_pointing_device.mapping_scan.point_mapping import (
    FixedMappingScan,
)
from tests.settings import logger


def test_wrap_sector_key(cm_pointig_device, json_factory):
    """Test to check wrap key"""
    cm = cm_pointig_device
    configure_data = json_factory("dishleafnode_configure_adr106")
    configure_data = json.loads(configure_data)
    cm.target_data = configure_data
    cm.set_wrap_sector_data()
    assert cm.wrap_sector_key
    assert cm.wrap_sector == -1
    cm.wrap_sector_key = False
    cm.wrap_sector = 0
    assert not cm.wrap_sector_key
    assert cm.wrap_sector == 0
    assert cm.is_fixed_mapping_scan()


def test_fixed_mapping_scan(cm_pointig_device, json_factory):
    """Test to check all the functions and variables implemented
    in FixedMappingScan class"""
    cm = cm_pointig_device
    cm.entries_tt_schedular_queue = 20
    configure_data = json_factory("dishleafnode_configure_adr106")
    configure_data = json.loads(configure_data)
    ra = configure_data['pointing']['field']['attrs']['c1']
    dec = configure_data['pointing']['field']['attrs']['c2']
    cm.target_data = configure_data
    fms_obj = FixedMappingScan("fixed", cm, logger=logger)
    fms_obj.extract_target_from_config()
    fms_obj.main_target_ra == ra
    fms_obj.main_target_dec == dec
    fms_obj.setup_observation_target()
    assert isinstance(fms_obj.ra_dec_target, katpoint.Target)
    projection_name, projection_alignment = fms_obj.get_projection()
    assert projection_name == 'SIN'
    assert projection_alignment == 'azel'
    configure_data['pointing']['projection']['name'] = "temp"
    with pytest.raises(Exception):
        assert cm.pointing_program_track_table
    configure_data['pointing']['projection']['name'] = "SIN"
    fms_obj.set_target_and_start_process()
    timeout = 0
    while timeout < 10 and not cm.pointing_program_track_table:
        timeout += 1
        time.sleep(0.5)
    assert cm.pointing_program_track_table
    assert cm.wrap_sector == -1
    del configure_data['pointing']['field']['attrs']['c1']
    del configure_data["pointing"]["field"]["target_name"]
    cm.target_data = configure_data
    with pytest.raises(Exception):
        fms_obj.extract_target_from_config()


def test_wrap_key_set_with_pointing_scan(cm_pointig_device, json_factory):
    """Test to check wrap sector also gets set with normal configure"""
    cm = cm_pointig_device
    configure_data = json_factory("dishleafnode_configure_adr106")
    configure_data = json.loads(configure_data)
    # Add wrap sector key to normal configure
    configure_data['pointing']['wrap_sector'] = -1
    cm.target_data = configure_data
    pointing_scan_obj = FixedMappingScan("point", cm, logger=logger)
    pointing_scan_obj.set_target_and_start_process()
    assert cm.wrap_sector == -1
