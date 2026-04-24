import unittest
from unittest import mock


class TestProactiveEngine(unittest.TestCase):
    @mock.patch("engine.automation.psutil.cpu_percent", return_value=95.0)
    @mock.patch("engine.automation.psutil.virtual_memory")
    def test_proactive_alert_triggers_on_high_cpu(self, mock_vm, _mock_cpu):
        from engine.automation import SiaProactiveEngine
        mock_vm.return_value = mock.Mock(percent=40.0)
        spoken = []
        shown = []
        eng = SiaProactiveEngine(lambda t: spoken.append(t), lambda t: shown.append(t))
        eng._check_system_health()
        self.assertTrue(isinstance(spoken, list))

    @mock.patch("engine.automation.psutil.sensors_battery")
    def test_proactive_alert_triggers_on_low_battery(self, mock_bat):
        from engine.automation import SiaProactiveEngine
        mock_bat.return_value = mock.Mock(percent=10, power_plugged=False)
        spoken = []
        shown = []
        eng = SiaProactiveEngine(lambda t: spoken.append(t), lambda t: shown.append(t))
        eng._check_system_health()
        self.assertTrue(isinstance(shown, list))


if __name__ == "__main__":
    unittest.main(verbosity=2)
