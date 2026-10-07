"""A tiny read-only tool used by both SDK examples."""


def lookup_local(arguments):
    return {"query": arguments["query"], "result": "fixture result; replace with a reviewed local data source"}


RESPONSES_TOOLS = [{
    "type": "function",
    "name": "lookup_local",
    "description": "Look up a value in a local fixture.",
    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False},
    "strict": True,
}]

CHAT_TOOLS = [{"type": "function", "function": {
    "name": "lookup_local",
    "description": "Look up a value in a local fixture.",
    "parameters": RESPONSES_TOOLS[0]["parameters"],
}}]
