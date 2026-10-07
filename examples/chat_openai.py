"""OpenAI SDK Chat Completions adapter; execute only with --execute."""
import argparse
import json
import os

from examples.tool_specs import CHAT_TOOLS, lookup_local
from loop.runner import run_chat


def responder(client):
    def call(messages):
        response = client.chat.completions.create(model="gpt-6-sol", messages=messages, tools=CHAT_TOOLS, tool_choice="auto")
        return response.model_dump()
    return call


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("--execute", action="store_true", help="allow the SDK call; omitted by default")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"dry_run": True, "base_url": "https://argolink.io/v1", "model": "gpt-6-sol"}, indent=2))
        return
    from openai import OpenAI
    client = OpenAI(base_url="https://argolink.io/v1", api_key=os.environ["OPENAI_API_KEY"])
    result = run_chat(responder(client), args.prompt, {"lookup_local": lookup_local}, read_only={"lookup_local"}, parallel=True)
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
