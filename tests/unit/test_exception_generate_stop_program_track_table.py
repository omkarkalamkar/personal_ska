import logging
import threading
from unittest import mock

import pytest

from ska_dishln_pointing_device.commands.generate_program_track_table import (
    GenerateProgramTrackTable,
)
from ska_dishln_pointing_device.commands.stop_program_track_table import (
    StopProgramTrackTable,
)


def test_generate_program_track_table(cm_pointig_device):
    generate_program_track_table = GenerateProgramTrackTable(
        logging, cm_pointig_device
    )
    cm_pointig_device.target_data = {"1": 1}  # invalid target data
    with pytest.raises(KeyError, match="pointing"):
        generate_program_track_table.do()
    cm_pointig_device.target_data = {"pointing": [1, 2]}  # invalid target data
    with pytest.raises(Exception):
        generate_program_track_table.do()


def test_stop_program_track_table():
    attrs = {
        "mapping_scan_event.set.side_effect": AttributeError(
            "mapping scan event doesn't have set attribute"
        )
    }
    cm = mock.Mock(track_thread_lock=threading.Lock(), **attrs)
    stop_program_track_table = StopProgramTrackTable(logging, cm)
    # invalid target data
    with pytest.raises(
        Exception, match="mapping scan event doesn't have set attribute"
    ):
        stop_program_track_table.do()
