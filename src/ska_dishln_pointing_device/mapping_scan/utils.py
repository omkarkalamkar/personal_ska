"""
Module for common utils
"""


class InvalidTargetDataError(Exception):
    """Exception raised when the target data is invalid.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="Invalid target data provided"):
        self.message = message
        super().__init__(self.message)
