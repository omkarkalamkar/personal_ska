from unittest.mock import MagicMock


def test_health_state_gpm_rule(cm_without_er_lp):
    """Test that function returns early when health_state is None."""
    cm = cm_without_er_lp
    cm._update_health_state_callback = MagicMock()
    cm.evaluate_and_update_health_state()
    cm._update_health_state_callback.assert_called_once()

    cm.evaluate_health_state = MagicMock()
    cm._update_health_state_callback = MagicMock()
    cm.evaluate_health_state.return_value = None
    cm.evaluate_and_update_health_state()
    cm._update_health_state_callback.assert_not_called()
