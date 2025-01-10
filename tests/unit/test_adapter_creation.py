import pytest
from ska_tango_base.commands import ResultCode


def test_adapter_creation_success(tango_context, cm_without_er_lp) -> None:
    cm = cm_without_er_lp
    result_code, message = cm.init_adapter()

    assert result_code == ResultCode.OK
    assert message == "Adapter initialisation is successful"


@pytest.mark.mccsmln
def test_adapter_creation_timeout(tango_context, cm_without_er_lp) -> None:
    cm = cm_without_er_lp
    cm.dish_dev_name = ""
    result_code, message = cm.init_adapter()

    assert result_code == ResultCode.FAILED
    assert "Error in creating adapter for" in message
