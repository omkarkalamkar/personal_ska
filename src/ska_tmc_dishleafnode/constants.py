"""Constants module for DishLeafNode"""
from os.path import dirname, join

FIRST_PROGRAM_TRACK_TABLE_SIZE = 50
TIME_DELTA_IN_SECONDS = 1
WAIT_TIME_IN_SECONDS = 0.1
TRACK_TABLE_ENTRY_SIZE = 3
TRACK_COMMAND_TIMEOUT = 10
SKA_EPOCH = "1999-12-31T23:59:28Z"
COMMAND_COMPLETION_MESSAGE = "Command Completed"
COMMAND_STARTED_MESSAGE = "Command Started"
IERS_DATA_STORAGE_PATH = join(
    dirname(__file__), "..", "..", "data", "iers_file.all"
)
RESET_OFFSETS = [0.0, 0.0]
ADJUST_TIMEOUT = 10
FIXED_TRAJECTORY = "fixed"
ALLOWED_BANDS = ['1', '2', '3', '4', '5a', '5b']
DISH_BANDPARAMS = {
    'Band_1': 'band1PointingModelParams',
    'Band_2': 'band2PointingModelParams',
    'Band_3': 'band3PointingModelParams',
    'Band_4': 'band4PointingModelParams',
    'Band_5a': 'band5aPointingModelParams',
    'Band_5b': 'band5bPointingModelParams',
}
