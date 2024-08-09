"""Constants module for DishLeafNode"""
from os.path import dirname, join

PROGRAM_TRACK_TABLE_SIZE = 150
TRACK_TABLE_ENTRY_SIZE = 3
TRACK_COMMAND_TIMEOUT = 10
SKA_EPOCH = "1999-12-31T23:59:28Z"
COMMAND_COMPLETION_MESSAGE = "Command Completed"
IERS_DATA_STORAGE_PATH = join(
    dirname(__file__), "..", "..", "data", "iers_file.all"
)
RESET_OFFSETS = [0.0, 0.0]
