"""A module for mocking the task callback functionality"""
# pylint: disable=W
from typing import Callable

from ska_tango_base.executor import TaskStatus


class MockCallable(Callable):
    """A mock class for task callbacks"""

    def __init__(
        self,
        unique_id: str,
    ):
        """Initialise the callable with unique id"""
        self._unique_id = unique_id

    def __call__(
        self,
        status: TaskStatus = None,
        result: str = None,
        message: str = None,
        exception=None,
    ):
        """Call method to set the status, result and message"""
        self.status = status
        self.result = result
        self.message = message
        self.exception = exception
        return self.status
