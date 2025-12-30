from unittest.mock import MagicMock


def test_health_state_gpm_rule(cm_without_er_lp):
    """Test that function returns early when health_state is None."""

    # health state is OK
    cm = cm_without_er_lp
    cm._update_health_state_callback = MagicMock()
    cm.update_gpm_data_for_health_aggregation()
    cm._update_health_state_callback.assert_called_once()

    # health state is Degraded
    cm._gpm_validation_result = {'Band_1': 'FAILED'}
    cm._update_health_state_callback = MagicMock()
    cm.update_gpm_data_for_health_aggregation()
    cm._update_health_state_callback.assert_called_once()

    # health state is None
    cm.health_manager.evaluate_health_state = MagicMock()
    cm._update_health_state_callback = MagicMock()
    cm.health_manager.evaluate_health_state.return_value = None
    cm.update_gpm_data_for_health_aggregation()
    cm._update_health_state_callback.assert_not_called()
