#!/usr/bin/env python3
"""Performance profiling for Sia hot paths."""

import cProfile
import pathlib
import pstats
import sys
import types
from types import SimpleNamespace
from unittest.mock import patch

fake_code_repair = types.ModuleType("engine.code_repair")
fake_code_repair.is_code_repair_request = lambda *args, **kwargs: False
sys.modules["engine.code_repair"] = fake_code_repair
sys.modules["code_repair"] = fake_code_repair

fake_knowledge_base = types.ModuleType("engine.knowledge_base")
fake_knowledge_base.search_knowledge = lambda *args, **kwargs: ""
sys.modules["engine.knowledge_base"] = fake_knowledge_base
sys.modules["knowledge_base"] = fake_knowledge_base

from engine import brain


def profile_think() -> None:
    fake_response = SimpleNamespace(text="Theek hai, kar dete hain.")

    with patch.object(fake_code_repair, "is_code_repair_request", return_value=False), \
         patch.object(brain, "detect_mood", return_value="HAPPY"), \
         patch.object(brain, "needs_web_search", return_value=False), \
         patch.object(brain, "_check_internet", return_value=False), \
         patch.object(brain, "get_advanced_persona", return_value="persona"), \
         patch.object(brain.memory, "save_chat_history", return_value=True), \
         patch.object(brain, "_extract_and_save_facts", return_value=None), \
         patch.object(brain, "_generate_with_fallback", return_value=fake_response), \
         patch.object(fake_knowledge_base, "search_knowledge", return_value=""):

        profiler = cProfile.Profile()
        profiler.enable()

        for _ in range(25):
            brain.think("Test question for profiling")

        profiler.disable()

        stats_path = pathlib.Path("profile_sia.stats")
        stats = pstats.Stats(profiler)
        stats.sort_stats("cumulative")
        stats.dump_stats(str(stats_path))
        stats.print_stats(10)
        print(f"Saved profile data to {stats_path.resolve()}")


if __name__ == "__main__":
    profile_think()
