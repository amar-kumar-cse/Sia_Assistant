#!/usr/bin/env python3
"""Week 4 voice tests: VoiceState atomicity and timing."""

import sys
import time
import pathlib
import threading
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from engine.voice_engine import VoiceState


class TestVoiceStateAtomicity(unittest.TestCase):
    def test_state_transitions(self):
        """VoiceState should track speaking and duration atomically."""
        state = VoiceState()
        self.assertFalse(state.get_speaking())
        self.assertFalse(state.get_streaming())

        state.set_streaming(True)
        self.assertTrue(state.get_streaming())

        state.set_speaking(True)
        time.sleep(0.05)
        self.assertTrue(state.get_speaking())
        self.assertGreaterEqual(state.get_duration(), 0.0)

        state.set_speaking(False)
        self.assertFalse(state.get_speaking())
        self.assertGreaterEqual(state.get_duration(), 0.0)

    def test_concurrent_toggles(self):
        """Concurrent state updates should not raise exceptions."""
        state = VoiceState()
        errors = []

        def worker(index: int):
            try:
                for _ in range(100):
                    state.set_speaking(index % 2 == 0)
                    state.set_streaming(index % 3 == 0)
                    _ = state.get_speaking()
                    _ = state.get_streaming()
                    _ = state.get_duration()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
