#!/usr/bin/env python3
"""Load test for Sia concurrency paths."""

import copy
import sys
import types
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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

from engine import brain, memory, voice_engine


def run_load_test() -> int:
    errors = []
    base_memory = memory.load_memory()
    fake_response = SimpleNamespace(text="Theek hai bhai.")

    def worker(index: int) -> str:
        try:
            loaded = memory.load_memory()
            assert "personal" in loaded
            assert "files" in loaded
            state = voice_engine.VoiceState()
            state.set_speaking(index % 2 == 0)
            state.set_streaming(index % 3 == 0)
            _ = state.get_duration()
            return brain.think(f"Load test prompt {index}")
        except Exception as exc:
            errors.append(exc)
            return ""

    with patch.object(fake_code_repair, "is_code_repair_request", return_value=False), \
         patch.object(brain, "detect_mood", return_value="HAPPY"), \
         patch.object(brain, "needs_web_search", return_value=False), \
         patch.object(brain, "_check_internet", return_value=False), \
         patch.object(brain, "get_advanced_persona", return_value="persona"), \
         patch.object(brain.memory, "save_chat_history", return_value=True), \
         patch.object(brain, "_extract_and_save_facts", return_value=None), \
         patch.object(brain, "_generate_with_fallback", return_value=fake_response), \
         patch.object(fake_knowledge_base, "search_knowledge", return_value=""):

        with ThreadPoolExecutor(max_workers=25) as executor:
            futures = [executor.submit(worker, i) for i in range(100)]
            responses = [future.result() for future in as_completed(futures)]

    # Save back original state once after the stress run
    memory.save_memory(copy.deepcopy(base_memory))

    print(f"Responses received: {len([r for r in responses if r])}")
    print(f"Errors encountered: {len(errors)}")

    if errors:
        for error in errors[:5]:
            print(f"Error: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(run_load_test())
