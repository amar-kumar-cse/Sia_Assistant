#!/usr/bin/env python3
"""Week 4 integration tests: brain -> response -> voice handoff."""

import sys
import pathlib
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).parent))

fake_code_repair = types.ModuleType("engine.code_repair")
fake_code_repair.is_code_repair_request = lambda *args, **kwargs: False
sys.modules["engine.code_repair"] = fake_code_repair
sys.modules["code_repair"] = fake_code_repair

fake_knowledge_base = types.ModuleType("engine.knowledge_base")
fake_knowledge_base.search_knowledge = lambda *args, **kwargs: ""
sys.modules["engine.knowledge_base"] = fake_knowledge_base
sys.modules["knowledge_base"] = fake_knowledge_base

from engine import brain, voice_engine


class TestFullFlow(unittest.TestCase):
    def test_complete_flow(self):
        """User input should flow through brain and into voice synthesis."""
        fake_response = SimpleNamespace(text="Theek hai bhai, ho jayega.")

        with patch.object(fake_code_repair, "is_code_repair_request", return_value=False), \
             patch.object(brain, "detect_mood", return_value="HAPPY"), \
             patch.object(brain, "needs_web_search", return_value=False), \
             patch.object(brain, "_check_internet", return_value=False), \
             patch.object(brain, "get_advanced_persona", return_value="persona"), \
             patch.object(brain.memory, "save_chat_history", return_value=True), \
             patch.object(brain, "_extract_and_save_facts", return_value=None), \
             patch.object(brain, "_generate_with_fallback", return_value=fake_response), \
             patch.object(fake_knowledge_base, "search_knowledge", return_value=""), \
             patch.object(voice_engine, "_use_edge_tts_fallback", return_value=None) as mock_voice:

            response = brain.think("Hello Sia, please help me")
            self.assertEqual(response, "Theek hai bhai, ho jayega.")

            voice_engine.speak(response, emotion="HAPPY")
            self.assertTrue(mock_voice.called)
            called_text = mock_voice.call_args.args[0]
            self.assertEqual(called_text, response)

    def test_streaming_flow(self):
        """Streaming brain path should yield chunks from a mocked model."""
        chunks = [SimpleNamespace(text="Theek "), SimpleNamespace(text="hai "), SimpleNamespace(text="bhai")]

        with patch.object(fake_code_repair, "is_code_repair_request", return_value=False), \
             patch.object(brain, "detect_mood", return_value="HAPPY"), \
             patch.object(brain, "needs_web_search", return_value=False), \
             patch.object(brain, "_check_internet", return_value=False), \
             patch.object(brain, "get_advanced_persona", return_value="persona"), \
             patch.object(brain.memory, "save_chat_history", return_value=True), \
             patch.object(brain, "_extract_and_save_facts", return_value=None), \
             patch.object(brain, "_generate_with_fallback", return_value=iter(chunks)), \
             patch.object(fake_knowledge_base, "search_knowledge", return_value=""):

            output = "".join(list(brain.think_streaming("Hello Sia")))
            self.assertIn("Theek", output)
            self.assertIn("bhai", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
