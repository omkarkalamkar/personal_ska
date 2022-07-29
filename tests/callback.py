"""MockCallable class for unit testing."""
import time


class MockCallable:
    """
    MockCallable class for unit testing.

    """

    def __init__(self, timeout):
        self.timeout = timeout
        self.called_args = []
        self.called_kwargs = {}

    def __call__(self, *args, **kwargs):
        self.called_args = args
        self.called_kwargs = kwargs

    def assert_against_call(self, *args, **kwargs):
        """
        Function to assert calls.
        """
        expected_args = args
        expected_kwargs = kwargs
        elapsed_time = 0
        start_time = time.time()
        while elapsed_time <= self.timeout:
            try:
                if args is not None:
                    for expected_value in expected_args:
                        assert expected_value in self.called_args
                if kwargs is not None:
                    for (
                        (expected_key, expected_value),
                        (actual_key, actual_value),
                    ) in zip(
                        expected_kwargs.items(), self.called_kwargs.items()
                    ):
                        if expected_key == actual_key:
                            assert expected_value == actual_value
                elapsed_time = self.timeout + 1
            except AssertionError as ae:
                elapsed_time = time.time() - start_time
                if elapsed_time > self.timeout:
                    raise ae

    def assert_exact_call(self, *args, **kwargs):
        """
        Function to assert exact calls and in same order.

        """
        elapsed_time = 0
        start_time = time.time()
        while elapsed_time <= self.timeout:
            try:
                expected_args = args
                expected_kwargs = kwargs
                if args is not None:
                    assert expected_args == self.called_args
                if kwargs is not None:
                    assert expected_kwargs == self.called_kwargs
                elapsed_time = self.timeout + 1
            except AssertionError as ae:
                elapsed_time = time.time() - start_time
                if elapsed_time > self.timeout:
                    raise ae
