#!/usr/bin/env python3
"""Week 4 memory tests: concurrency and cache isolation."""

import copy
import sys
import threading
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from engine import memory


class TestMemoryConcurrency(unittest.TestCase):
    def test_concurrent_load_save(self):
        """Concurrent load/save should not corrupt memory state."""
        base_memory = memory.load_memory()
        errors = []

        def worker():
            try:
                loaded = memory.load_memory()
                self.assertIn("personal", loaded)
                self.assertIn("files", loaded)
                memory.save_memory(copy.deepcopy(base_memory))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])

    def test_load_memory_returns_isolated_copy(self):
        """Mutating loaded memory should not affect future loads."""
        first = memory.load_memory()
        first["personal"]["name"] = "Changed In Test"

        second = memory.load_memory()
        self.assertNotEqual(second["personal"]["name"], "Changed In Test")
        self.assertIn("resume_path", second["files"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
