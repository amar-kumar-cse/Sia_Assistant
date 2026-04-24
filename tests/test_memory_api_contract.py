import unittest

from engine import memory


class TestMemoryApiContract(unittest.TestCase):
    def test_required_methods(self):
        self.assertTrue(memory.add_user_fact("wake_word", "sia", 0.9, "explicit"))
        self.assertTrue(memory.reinforce_fact("wake_word"))
        self.assertIsNotNone(memory.get_user_fact("wake_word"))

        memory.set_preference("voice_speed", "1.0")
        self.assertIsNotNone(memory.get_preference("voice_speed"))

        self.assertTrue(memory.log_telemetry("response_latency", {"metric_value": 0.32, "session_id": "s1"}))
        self.assertTrue(memory.save_conversation("s1", "hi", "hello", "HAPPY", "greeting", 120))

        ctx = memory.get_context_for_prompt()
        self.assertIsInstance(ctx, str)

        stats = memory.get_weekly_stats()
        self.assertIn("avg_latency_ms", stats)


if __name__ == "__main__":
    unittest.main(verbosity=2)
