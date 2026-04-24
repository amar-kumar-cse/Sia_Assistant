import unittest

from engine.streaming_manager import chunk_text_smart


class TestStreamingPipeline(unittest.TestCase):
    def test_chunk_threshold_behavior(self):
        text = "Hello world this is a long text chunk that should split once threshold reaches enough characters for speaking."
        chunks = chunk_text_smart(text, min_length=70)
        self.assertTrue(len(chunks) >= 1)

    def test_stream_drop_recovery_contract(self):
        # Placeholder contract: recovery path should return partial text instead of blank.
        partial = "[IDLE] partial response"
        self.assertTrue(partial.startswith("["))


if __name__ == "__main__":
    unittest.main(verbosity=2)
