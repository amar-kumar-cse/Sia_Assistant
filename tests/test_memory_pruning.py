import unittest

from engine import memory


class TestMemoryPruning(unittest.TestCase):
    def test_weekly_prune_deletes_old_done_todos(self):
        # setup
        memory.add_todo("old test todo")
        result = memory.prune_memory()
        self.assertIn("todos", result)

    def test_weekly_prune_deactivates_low_confidence_facts(self):
        memory.learn_fact("temp low conf fact", fact_key="noise", confidence=0.2, source="inferred")
        result = memory.prune_memory()
        self.assertIn("facts", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
