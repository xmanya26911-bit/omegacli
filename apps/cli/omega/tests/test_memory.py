"""Tests for memory.py — PersistentMemory, ConversationLogger, ShortTermMemory."""
from __future__ import annotations
import json, os, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestShortTermMemory(unittest.TestCase):
    """ShortTermMemory manages conversation token budget and trimming."""

    def setUp(self) -> None:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from memory import ShortTermMemory
        self.STM = ShortTermMemory

    def test_init_defaults(self) -> None:
        stm = self.STM()
        self.assertEqual(stm.max_tokens, 64000)
        self.assertEqual(stm.get_messages(), [])

    def test_init_custom_max(self) -> None:
        stm = self.STM(max_tokens=32000)
        self.assertEqual(stm.max_tokens, 32000)

    def test_add_system(self) -> None:
        stm = self.STM()
        stm.add_system("You are a helpful assistant.")
        msgs = stm.get_messages()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["role"], "system")

    def test_set_system_replaces(self) -> None:
        stm = self.STM()
        stm.add_system("Old")
        stm.set_system("New")
        msgs = stm.get_messages()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["content"], "New")

    def test_add_user_and_assistant(self) -> None:
        stm = self.STM()
        stm.add_system("S")
        stm.add_user("Hello")
        stm.add_assistant("Hi!")
        self.assertEqual(len(stm.get_messages()), 3)

    def test_add_tool(self) -> None:
        stm = self.STM()
        stm.add_system("S")
        stm.add_user("Call")
        stm.add_tool("call_1", '{"ok": true}')
        msgs = stm.get_messages()
        self.assertEqual(msgs[2]["role"], "tool")
        self.assertEqual(msgs[2]["tool_call_id"], "call_1")

    def test_clear(self) -> None:
        stm = self.STM()
        stm.add_system("S")
        stm.add_user("X")
        stm.clear()
        self.assertEqual(stm.get_messages(), [])

    def test_remove_last_n(self) -> None:
        stm = self.STM()
        stm.add_system("S")
        stm.add_user("M1")
        stm.add_user("M2")
        stm.add_user("M3")
        stm.remove_last_n(2)
        self.assertEqual(len(stm.get_messages()), 2)
        self.assertEqual(stm.get_messages()[1]["content"], "M1")

    def test_estimate_tokens(self) -> None:
        stm = self.STM()
        stm.add_system("Hello world " * 20)
        est = stm.estimate_tokens()
        self.assertGreater(est, 0)
        self.assertLess(est, 1000)

    def test_get_token_stats(self) -> None:
        stm = self.STM()
        stm.add_system("Test")
        stm.add_user("More")
        stats = stm.get_token_stats()
        self.assertIn("estimated_tokens", stats)
        self.assertGreater(stats["messages"], 0)

    def test_assistant_with_tool_calls(self) -> None:
        stm = self.STM()
        stm.add_system("S")
        stm.add_assistant(content="", tool_calls=[
            {"id": "c1", "type": "function", "function": {"name": "t", "arguments": "{}"}}
        ])
        msgs = stm.get_messages()
        self.assertIn("tool_calls", msgs[1])

    def test_trim_removes_old(self) -> None:
        stm = self.STM(max_tokens=500)
        stm.add_system("S " * 100)
        for i in range(10):
            stm.add_user(f"M{i} " * 20)
            stm.add_assistant(f"R{i} " * 20)
        before = len(stm.get_messages())
        stm.trim()
        after = len(stm.get_messages())
        self.assertLessEqual(after, before)


class TestPersistentMemory(unittest.TestCase):
    def setUp(self) -> None:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        self.tmp = tempfile.mkdtemp()
        self.patcher = patch('memory.MEMORY_DIR', Path(self.tmp))
        self.patcher.start()
        from memory import PersistentMemory
        self.PM = PersistentMemory
        self.mem = PersistentMemory()

    def tearDown(self) -> None:
        self.patcher.stop()
        import shutil; shutil.rmtree(self.tmp, ignore_errors=True)

    def test_remember_and_recall(self) -> None:
        r = self.mem.remember("k", "v")
        self.assertIsNotNone(r)
        v = self.mem.recall("k")
        self.assertIsNotNone(v)
        self.assertIn("v", str(v))

    def test_forget(self) -> None:
        self.mem.remember("k", "v")
        self.mem.forget("k")
        v = self.mem.recall("k")
        self.assertIn("No memory found", str(v))

    def test_list_memories(self) -> None:
        self.mem.remember("a", "1")
        self.mem.remember("b", "2")
        self.assertGreaterEqual(len(self.mem.list_memories()), 2)

    def test_search(self) -> None:
        self.mem.remember("color", "blue")
        self.assertGreaterEqual(len(self.mem.search("blue")), 1)

    def test_save_and_read_note(self) -> None:
        self.mem.save_note("t", "Hello World")
        c = self.mem.read_note("t")
        self.assertIsNotNone(c)
        self.assertIn("Hello World", str(c))

    def test_delete_note(self) -> None:
        self.mem.save_note("d", "gone")
        self.mem.delete_note("d")
        c = self.mem.read_note("d")
        self.assertIn("No note found", str(c))

    def test_list_notes(self) -> None:
        self.mem.save_note("n1", "one")
        self.mem.save_note("n2", "two")
        self.assertGreaterEqual(len(self.mem.list_notes()), 2)

    def test_export_import(self) -> None:
        self.mem.remember("k", "v")
        data = self.mem.export_all()
        self.assertIn("facts", data)
        mem2 = self.PM()
        mem2.import_all(data)
        v = mem2.recall("k")
        self.assertIn("v", str(v))

    def test_remember_with_tags(self) -> None:
        self.mem.remember("tk", "tv", tags=["important"])
        v = self.mem.recall("tk")
        self.assertIsNotNone(v)

    def test_get_relevant_context(self) -> None:
        self.mem.remember("weather", "sunny")
        ctx = self.mem.get_relevant_context("weather")
        self.assertIsNotNone(ctx)


class TestConversationLogger(unittest.TestCase):
    def setUp(self) -> None:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        self.tmp = tempfile.mkdtemp()
        self.patcher = patch('memory.MEMORY_DIR', Path(self.tmp))
        self.patcher.start()
        from memory import ConversationLogger
        self.CL = ConversationLogger
        self.log = ConversationLogger()

    def tearDown(self) -> None:
        self.patcher.stop()
        import shutil; shutil.rmtree(self.tmp, ignore_errors=True)

    def test_log_and_stats(self) -> None:
        self.log.log_session_start()
        self.log.log_interaction({"user": "Hi", "assistant": "Hey"})
        stats = self.log.get_stats()
        self.assertIsInstance(stats, dict)

    def test_session_end(self) -> None:
        self.log.log_session_start()
        self.log.log_session_end(summary="Done")
        stats = self.log.get_stats()
        self.assertIn("total_sessions", stats)

    def test_get_stats(self) -> None:
        stats = self.log.get_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn("total_sessions", stats)

    def test_all_dates(self) -> None:
        dates = self.log.get_all_conversation_dates()
        self.assertIsInstance(dates, list)


if __name__ == "__main__":
    unittest.main()
