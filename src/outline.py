"""Pass 1: paper text → structured outline.

Why two passes? A single shot from paper-to-script tends to be lazy and skim.
Forcing the model to first produce a structured outline gives the second pass
something concrete to expand into 20+ minutes of substantive dialogue.

Output is JSON so the scriptwriter can consume it programmatically.
"""

import json
import os
import sys
from pathlib import Path

from openai import OpenAI


NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
# Long-context, strong reasoning. Swap if NVIDIA's catalog changes — see build.nvidia.com/models.
MODEL = os.environ.get("OUTLINE_MODEL", "deepseek-ai/deepseek-v3.1")


def load_prompt() -> str:
    return Path("prompts/outline.txt").read_text()


def build_client() -> OpenAI:
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        print("NVIDIA_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    return OpenAI(api_key=api_key, base_url=NVIDIA_BASE_URL)


def generate_outline(title: str, paper_text: str) -> dict:
    client = build_client()
    system_prompt = load_prompt()

    user_msg = f"PAPER TITLE: {title}\n\nPAPER TEXT:\n\n{paper_text}"

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,  # low: we want faithful structure, not creativity
        max_tokens=4000,
    )
    raw = resp.choices[0].message.content.strip()

    # Strip ```json fences if the model added them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"failed to parse outline JSON: {e}", file=sys.stderr)
        print(f"raw response:\n{raw}", file=sys.stderr)
        sys.exit(1)


def main():
    # Read extracted text from stdin (piped from extract.py) or from a file arg
    if len(sys.argv) == 2:
        data = Path(sys.argv[1]).read_text()
    else:
        data = sys.stdin.read()

    # Parse the simple TITLE/PAGES/---/text format
    lines = data.split("\n")
    title = "Untitled"
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("TITLE: "):
            title = line[len("TITLE: ") :].strip()
        if line.strip() == "---":
            body_start = i + 1
            break
    paper_text = "\n".join(lines[body_start:]).strip()

    outline = generate_outline(title, paper_text)
    outline["_title"] = title
    print(json.dumps(outline, indent=2))


if __name__ == "__main__":
    main()
