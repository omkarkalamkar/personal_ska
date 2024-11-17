def test_dish_pointing_device_cm(cm_pointig_device):
    """Test dish pointing device component manager"""
    assert cm_pointig_device.pointing_program_track_table == []
    assert cm_pointig_device.target_data == ""
    cm_pointig_device.target_data = [1, 2]
    assert cm_pointig_device.target_data == [1, 2]
