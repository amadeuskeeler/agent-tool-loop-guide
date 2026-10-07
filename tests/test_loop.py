import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from loop.runner import run_chat, run_responses


class LoopTests(unittest.TestCase):
    def test_responses_repeats_until_message(self):
        responses = iter([
            {"output": [{"type": "function_call", "call_id": "c1", "name": "echo", "arguments": '{"value":"ok"}'}]},
            {"output_text": "done", "output": []},
        ])
        result = run_responses(lambda _: next(responses), "hello", {"echo": lambda args: args["value"]})
        self.assertEqual(result.text, "done")
        self.assertEqual(result.stop_reason, "message")
        self.assertEqual(result.history[-1]["call_id"], "c1")

    def test_chat_repeats_and_preserves_tool_id(self):
        responses = iter([
            {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "echo", "arguments": '{"value":"ok"}'}}]}}]},
            {"choices": [{"message": {"role": "assistant", "content": "done", "tool_calls": []}}]},
        ])
        result = run_chat(lambda _: next(responses), "hello", {"echo": lambda args: args["value"]})
        self.assertEqual(result.text, "done")
        self.assertEqual(result.history[-1]["tool_call_id"], "c1")

    def test_parallel_only_for_allowlisted_read_tools(self):
        responses = iter([
            {"output": [{"type": "function_call", "call_id": "a", "name": "one", "arguments": "{}"}, {"type": "function_call", "call_id": "b", "name": "two", "arguments": "{}"}]},
            {"output_text": "done", "output": []},
        ])
        result = run_responses(lambda _: next(responses), "hello", {"one": lambda _: 1, "two": lambda _: 2}, parallel=True, read_only={"one", "two"})
        self.assertEqual(result.stop_reason, "message")
        self.assertEqual([item["call_id"] for item in result.history[-2:]], ["a", "b"])

    def test_unknown_and_malformed_tools_stop_with_typed_error(self):
        result = run_responses(lambda _: {"output": [{"type": "function_call", "call_id": "x", "name": "missing", "arguments": "{}"}]}, "hello", {})
        self.assertEqual(result.stop_reason, "tool_error")
        self.assertIn("unknown tool", result.history[-1]["output"])
        with self.assertRaises(ValueError):
            run_responses(lambda _: {"output": [{"type": "function_call", "call_id": "x", "name": "echo", "arguments": "[]"}]}, "hello", {"echo": lambda _: 1})

    def test_max_turn_limit(self):
        result = run_responses(lambda _: {"output": [{"type": "function_call", "call_id": "x", "name": "echo", "arguments": "{}"}]}, "hello", {"echo": lambda _: 1}, max_turns=2)
        self.assertEqual(result.stop_reason, "max_turns")
        self.assertEqual(result.turns, 2)


if __name__ == "__main__":
    unittest.main()
