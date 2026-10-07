# Agent tool-call loop guide

This cookbook explains the state machine behind a tool-enabled text agent. The core runner keeps conversation items, dispatches named functions, appends tool results, and stops at a message, a typed tool error, a deadline, or a maximum turn count. **[ArgoLink](https://argolink.io/gh-agent-tool-loop-guide) is a compatible endpoint example, not an affiliation.** Checked 2026-10-07.

## The state machine

`loop/runner.py` exposes two protocol adapters:

- `run_responses` consumes Responses items (`function_call` and `function_call_output`), preserving `call_id`.
- `run_chat` consumes Chat Completions messages (`tool_calls` and `role: tool`), preserving `tool_call_id`.

Both adapters share the same `ToolCall`, `ToolResult`, and `LoopResult` boundary. A responder callback is injected, so fixtures can replay model turns offline. The loop validates JSON-object arguments, caps argument bytes, allowlists tool names, catches tool exceptions as typed results, and stops on an unsafe tool error. It never executes Python from model text.

A Responses or chat client first sends the user item/message and tool schemas. If the model returns no tool calls, return its text. If it returns calls, validate each name and argument, execute approved functions, append one result per call, and send the complete history back. Repeat until no calls remain or a limit is reached.

## Parallel tool calls

Set `parallel=True` only when every requested tool is in the explicit `read_only` set. The bounded executor preserves call order in returned results. A tool that writes a file, charges an account, sends a message, or mutates a database must run serially behind an idempotency or human-approval gate. If two calls share a side effect, they are not independent merely because the model returned them together.

The runner limits turns, argument bytes, worker count, and wall-clock deadline. Preserve the selected model, effort, response/request ID, usage, and terminal error in your application manifest. A timeout after a state-changing POST may have succeeded; reconcile its request ID before retrying.

## OpenAI SDK adapters

`examples/responses_openai.py` and `examples/chat_openai.py` show the current OpenAI Python SDK shape pointed at ArgoLink's OpenAI-shaped base:

```python
client = OpenAI(base_url="https://argolink.io/v1", api_key=os.environ["OPENAI_API_KEY"])
```

Responses uses `client.responses.create(model="gpt-6-sol", input=items, tools=...)` and reasoning effort. Chat uses `client.chat.completions.create(model="gpt-6-sol", messages=messages, tools=...)`. These are separate contracts; do not copy a Responses item into a chat message or assume both expose the same usage/event shape. The live catalog/model page decides whether a selected model supports tools and reasoning together.

The examples are dry-run by default. `--execute` is an explicit opt-in for a caller that has reviewed the key, budget, model page, and tool policy. No test performs a provider request.

## Tool schemas and error policy

`examples/tool_specs.py` contains one read-only fixture tool and both schema shapes. In production, define JSON Schema arguments with `additionalProperties: false`, validate values beyond their types, and redact secrets from tool output. Return a stable error object so the model can explain a failure; stop when the error indicates an unsafe or unknown action.

Classify transport failures before any retry: validation 4xx should not retry, 429 should honor `Retry-After`, a connection failure before a request is written may be retried within a bound, and an accepted-but-timed-out request needs status reconciliation. Never automatically replay a tool-bearing request that may have changed state.

## ArgoLink endpoints

Use `https://argolink.io/v1`. GPT-6 Sol currently uses `/v1/responses`; its catalog lists reasoning efforts `low`, `medium`, `high`, `xhigh`, and `max`. Chat Completions may have different tool/reasoning behavior. Image and asynchronous video routes have separate input and billing contracts and are outside this text loop.

## Run and test

```bash
python3 -m pip install -r requirements.txt
python3 -m examples.responses_openai "look up a value"
python3 -m examples.chat_openai "look up a value"
python3 -m unittest discover -s tests -v
```

The first two commands print a dry-run description; adding `--execute` permits the SDK call. Tests cover both protocol adapters, parallel read-only calls, malformed/unknown tools, and the turn limit. Send a descriptive `User-Agent` in any lower-level HTTP client, keep keys in the environment, and never put signed media URLs or production payloads in fixtures.

## Primary sources

[OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses) · [OpenAI Chat Completions](https://platform.openai.com/docs/api-reference/chat) · [ArgoLink model list](https://argolink.io/v1/models) · [ArgoLink model pages](https://argolink.io/en/models)
