# Agent tool-call loop guide

This cookbook explains the state machine behind a tool-enabled text agent. The small runner keeps conversation items, dispatches named functions, appends tool results, and stops at a message or a maximum turn count. **[ArgoLink](https://argolink.io/gh-agent-tool-loop-guide) is a compatible endpoint example, not an affiliation.** Last checked: 2026-10-07.

## The loop

A Responses or chat-completions client first sends the user message and tool schemas. If the model returns no tool calls, return its text. If it returns calls, validate each name and arguments, execute approved functions, append one result per call, and send the complete history back. Repeat until no calls remain or the maximum iteration count is reached. The runner in loop/runner.py is offline and intentionally takes pre-recorded turns so the state machine can be tested without a model.

Parallel calls are safe only when tools are independent. A tool that writes a file, charges an account, or mutates a database needs a human or idempotency gate. Preserve the tool call ID in the real implementation so the model can associate the result correctly. Do not swallow exceptions; return a typed error result and stop when the error is unsafe to recover.

## Responses and chat

Responses and chat-completions use different response item shapes. Build an adapter at the boundary and keep the core loop's ToolCall/ToolResult objects stable. Verify whether the selected model supports tools and reasoning together. The ArgoLink base is https://argolink.io/v1; the model page and catalog decide endpoint, model ID, effort, and tool support. A User-Agent belongs on every urllib request.

## Limits and safety

Set max turns, maximum tool arguments, a wall-clock deadline, and a cost budget. Allowlist tool names; never execute arbitrary Python from model text. Redact secrets and signed URLs. When a request times out, decide whether it was a read or a side effect before replaying. For a video tool, persist its request ID and use status polling instead of submitting again.

## Testing

python3 -m unittest discover -s tests runs no network request. Add adapter tests using a local fake response for parallel calls, malformed arguments, tool exceptions, and max-turn behavior. The sample fixture is not a benchmark and does not claim model quality.

## FAQ

**Why not loop forever?** A model can keep requesting tools after a malformed result. **Can calls run concurrently?** Only with a bounded executor and independent side effects. **Are Responses and chat interchangeable?** No; keep adapters separate. **Where is cost calculated?** Record usage from the final response and use a dated price table; do not infer it from turn count.
