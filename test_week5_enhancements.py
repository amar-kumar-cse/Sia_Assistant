#!/usr/bin/env python3
"""Week 5 enhancement tests: smart cache, parallel context, telemetry."""

import sys
import pathlib
import time
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).parent))

fake_code_repair = types.ModuleType("engine.code_repair")
fake_code_repair.is_code_repair_request = lambda *args, **kwargs: False
fake_code_repair.repair_code = lambda *args, **kwargs: "[CODE] fixed"
sys.modules["engine.code_repair"] = fake_code_repair

fake_knowledge_base = types.ModuleType("engine.knowledge_base")
fake_knowledge_base.search_knowledge = lambda *args, **kwargs: ""
sys.modules["engine.knowledge_base"] = fake_knowledge_base

fake_web_search = types.ModuleType("engine.web_search")
fake_web_search.search_for_brain = lambda *args, **kwargs: ""
sys.modules["engine.web_search"] = fake_web_search

from analytics import telemetry
from engine import brain


class TestWeek5Enhancements(unittest.TestCase):
    def setUp(self):
        telemetry.clear()
        try:
            brain._response_cache.clear()
        except Exception:
            pass

    def test_smart_cache_hits(self):
        """Repeated prompts should be served from cache on the second call."""
        fake_response = SimpleNamespace(text="Cached hello")

        with patch.object(brain, "detect_mood", return_value="HAPPY"), \
             patch.object(brain, "needs_web_search", return_value=False), \
             patch.object(brain, "_check_internet", return_value=False), \
             patch.object(brain, "get_advanced_persona", return_value="persona"), \
             patch.object(brain.memory, "save_chat_history", return_value=True), \
             patch.object(brain, "_extract_and_save_facts", return_value=None), \
             patch.object(brain, "_generate_with_fallback", return_value=fake_response), \
                         patch("engine.code_repair.is_code_repair_request", return_value=False), \
                         patch("engine.knowledge_base.search_knowledge", return_value=""):

            first = brain.think("Hello cache")
            second = brain.think("Hello cache")

        self.assertEqual(first, "Cached hello")
        self.assertEqual(second, "Cached hello")

        events = telemetry.snapshot()["events"]
        event_names = [event.name for event in events]
        self.assertIn("think_cache_miss", event_names)
        self.assertIn("think_cache_hit", event_names)

    def test_parallel_context_builder(self):
        """Knowledge and web context should be built in parallel."""
        with patch("engine.knowledge_base.search_knowledge", side_effect=lambda *args, **kwargs: time.sleep(0.15) or "KB"), \
             patch("engine.web_search.search_for_brain", side_effect=lambda *args, **kwargs: time.sleep(0.15) or "WEB"), \
             patch.object(brain, "needs_web_search", return_value=True), \
             patch.object(brain, "_check_internet", return_value=True):

            start = time.time()
            kb_context, web_context = brain._build_contexts("Tell me latest weather")
            duration = time.time() - start

        self.assertEqual(kb_context, "KB")
        self.assertEqual(web_context, "WEB")
        self.assertLess(duration, 0.25)

    def test_telemetry_records(self):
        """Telemetry recorder should track events and timings."""
        telemetry.record_event("unit_test_event", source="week5")
        telemetry.record_timing("unit_test_timing", 0.123, cached=True)
        snapshot = telemetry.snapshot()

        self.assertEqual(len(snapshot["events"]), 1)
        self.assertEqual(len(snapshot["timings"]), 1)
        self.assertEqual(snapshot["events"][0].name, "unit_test_event")
        self.assertEqual(snapshot["timings"][0]["name"], "unit_test_timing")
        self.assertTrue(snapshot["timings"][0]["metadata"]["cached"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
