import unittest

from engine.lipsync_scheduler import LipSyncScheduler


class TestLipSyncScheduler(unittest.TestCase):
    def test_amplitude_mapping(self):
        s = LipSyncScheduler()
        self.assertEqual(s.amplitude_to_state(0.1), "talk_closed")
        self.assertEqual(s.amplitude_to_state(0.3), "talk_semi")
        self.assertEqual(s.amplitude_to_state(0.8), "talk_open")

    def test_schedule_monotonic(self):
        s = LipSyncScheduler(min_hold_ms=10)
        arr = [0.1, 0.3, 0.8, 0.2, 0.7]
        schedule = s.to_schedule(arr, 0.05)
        times = [t for t, _ in schedule]
        self.assertEqual(times, sorted(times))


if __name__ == "__main__":
    unittest.main(verbosity=2)
