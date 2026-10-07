"""Protocol-neutral tool loop plus Responses and Chat Completions adapters.

The responder callback is intentionally injected, so tests can replay fixtures and
never need a key or network access.
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Iterable

Tool = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    name: str
    output: str
    error: bool = False


@dataclass(frozen=True)
class LoopResult:
    text: str
    history: list[dict[str, Any]]
    turns: int
    stop_reason: str


def _arguments(value: Any, max_bytes: int) -> dict[str, Any]:
    if isinstance(value, str):
        if len(value.encode("utf-8")) > max_bytes:
            raise ValueError("tool arguments exceed the configured byte limit")
        value = json.loads(value)
    if not isinstance(value, dict):
        raise ValueError("tool arguments must be a JSON object")
    encoded = json.dumps(value, separators=(",", ":")).encode("utf-8")
    if len(encoded) > max_bytes:
        raise ValueError("tool arguments exceed the configured byte limit")
    return value


def parse_responses(payload: dict[str, Any], max_argument_bytes: int = 64_000) -> tuple[str, list[ToolCall]]:
    calls: list[ToolCall] = []
    text = payload.get("output_text") or ""
    for item in payload.get("output", []):
        if item.get("type") == "function_call":
            calls.append(ToolCall(str(item.get("call_id") or item.get("id") or ""), str(item.get("name") or ""), _arguments(item.get("arguments", {}), max_argument_bytes)))
        elif item.get("type") == "message" and not text:
            for part in item.get("content", []):
                if part.get("type") in {"output_text", "text"}:
                    text += str(part.get("text", ""))
    return text, calls


def parse_chat(payload: dict[str, Any], max_argument_bytes: int = 64_000) -> tuple[str, list[ToolCall], dict[str, Any]]:
    message = (payload.get("choices") or [{}])[0].get("message") or {}
    calls = []
    for item in message.get("tool_calls") or []:
        function = item.get("function") or {}
        calls.append(ToolCall(str(item.get("id") or ""), str(function.get("name") or ""), _arguments(function.get("arguments", {}), max_argument_bytes)))
    return str(message.get("content") or ""), calls, message


def _dispatch(calls: Iterable[ToolCall], tools: dict[str, Tool], read_only: set[str], parallel: bool, max_workers: int, deadline: float | None) -> list[ToolResult]:
    calls = list(calls)
    if len({call.call_id for call in calls}) != len(calls) or any(not call.call_id or not call.name for call in calls):
        return [ToolResult(call.call_id, call.name, "invalid tool call identifier or name", True) for call in calls]

    def one(call: ToolCall) -> ToolResult:
        if deadline is not None and time.monotonic() >= deadline:
            return ToolResult(call.call_id, call.name, "tool deadline exceeded", True)
        function = tools.get(call.name)
        if function is None:
            return ToolResult(call.call_id, call.name, "unknown tool is not allowlisted", True)
        try:
            value = function(call.arguments)
            return ToolResult(call.call_id, call.name, json.dumps(value, ensure_ascii=False), False)
        except Exception as exc:  # tool errors become typed data; no traceback is sent to the model
            return ToolResult(call.call_id, call.name, f"tool failed: {type(exc).__name__}: {exc}", True)

    can_parallel = parallel and len(calls) > 1 and all(call.name in read_only for call in calls)
    if can_parallel:
        with ThreadPoolExecutor(max_workers=min(max_workers, len(calls))) as pool:
            return list(pool.map(one, calls))
    return [one(call) for call in calls]


def run_responses(respond: Callable[[list[dict[str, Any]]], dict[str, Any]], user_input: str, tools: dict[str, Tool], *, max_turns: int = 8, parallel: bool = False, read_only: set[str] | None = None, max_workers: int = 4, max_argument_bytes: int = 64_000, deadline_seconds: float = 120.0) -> LoopResult:
    if max_turns < 1 or max_workers < 1 or deadline_seconds <= 0:
        raise ValueError("loop limits must be positive")
    history: list[dict[str, Any]] = [{"role": "user", "content": user_input}]
    deadline = time.monotonic() + deadline_seconds
    read_only = read_only or set()
    for turn in range(1, max_turns + 1):
        if time.monotonic() >= deadline:
            return LoopResult("", history, turn - 1, "deadline")
        payload = respond(history)
        text, calls = parse_responses(payload, max_argument_bytes)
        if not calls:
            return LoopResult(text, history, turn, "message")
        results = _dispatch(calls, tools, read_only, parallel, max_workers, deadline)
        history.extend({"type": "function_call_output", "call_id": result.call_id, "output": result.output} for result in results)
        if any(result.error for result in results):
            return LoopResult("", history, turn, "tool_error")
    return LoopResult("", history, max_turns, "max_turns")


def run_chat(respond: Callable[[list[dict[str, Any]]], dict[str, Any]], user_input: str, tools: dict[str, Tool], *, max_turns: int = 8, parallel: bool = False, read_only: set[str] | None = None, max_workers: int = 4, max_argument_bytes: int = 64_000, deadline_seconds: float = 120.0) -> LoopResult:
    if max_turns < 1 or max_workers < 1 or deadline_seconds <= 0:
        raise ValueError("loop limits must be positive")
    history: list[dict[str, Any]] = [{"role": "user", "content": user_input}]
    deadline = time.monotonic() + deadline_seconds
    read_only = read_only or set()
    for turn in range(1, max_turns + 1):
        if time.monotonic() >= deadline:
            return LoopResult("", history, turn - 1, "deadline")
        payload = respond(history)
        text, calls, message = parse_chat(payload, max_argument_bytes)
        if not calls:
            return LoopResult(text, history, turn, "message")
        history.append({"role": "assistant", **message})
        results = _dispatch(calls, tools, read_only, parallel, max_workers, deadline)
        history.extend({"role": "tool", "tool_call_id": result.call_id, "name": result.name, "content": result.output} for result in results)
        if any(result.error for result in results):
            return LoopResult("", history, turn, "tool_error")
    return LoopResult("", history, max_turns, "max_turns")
