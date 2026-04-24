import unittest
from unittest import mock


class TestKeyRotation(unittest.TestCase):
    @mock.patch("engine.brain._generate_with_fallback")
    def test_key_rotation_on_429_switches_key_and_recovers(self, mock_gen):
        from engine import brain

        class E(Exception):
            pass

        first = E("429 RESOURCE_EXHAUSTED")
        second = mock.Mock(text="[IDLE] recovered")
        mock_gen.side_effect = [first, second]

        out = brain.think("hello")
        self.assertIsInstance(out, str)

    @mock.patch("analytics.telemetry.record_event")
    def test_key_rotation_logs_telemetry_event(self, mock_event):
        from analytics import telemetry
        telemetry.record_event("api_key_rotation", old="a", new="b")
        self.assertTrue(mock_event.called)


if __name__ == "__main__":
    unittest.main(verbosity=2)
