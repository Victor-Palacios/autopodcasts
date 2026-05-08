"""Pass 2: outline → host-and-expert dialogue script.

Output format is line-delimited so synthesize.py can iterate trivially:
  HOST: ...
  EXPERT: ...
  HOST: ...

Lines are kept short-ish (under ~400 chars) to play nicely with TTS chunking
and to give the audio natural cadence.
"""

import json
import os
import sys
from pathlib import Path

from openai import OpenAI


NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = os.environ.get("SCRIPT_MODEL", "deepseek-ai/deepseek-v4-flash")


def load_prompt() -> str:
    return Path("prompts/dialogue.txt").read_text()


def build_client() -> OpenAI:
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        print("NVIDIA_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    return OpenAI(api_key=api_key, base_url=NVIDIA_BASE_URL)


def generate_script(outline: dict) -> str:
    client = build_client()
    system_prompt = load_prompt()
    user_msg = f"OUTLINE:\n\n{json.dumps(outline, indent=2)}"

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.7,  # higher: we want natural-sounding dialogue
        max_tokens=8000,  # ~6000 words ceiling, comfortably above 20-min target
    )
    return resp.choices[0].message.content.strip()


def validate_script(script: str) -> list[tuple[str, str]]:
    """Parse and lightly validate the script. Returns list of (speaker, line) tuples.

    Raises on malformed input rather than letting bad data hit the TTS step.
    """
    lines = []
    for raw in script.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        if raw.startswith("HOST:"):
            text = raw[len("HOST:") :].strip()
            if text:
                lines.append(("HOST", text))
        elif raw.startswith("EXPERT:"):
            text = raw[len("EXPERT:") :].strip()
            if text:
                lines.append(("EXPERT", text))
        # Silently drop anything else (stage directions, headers, etc.)

    if len(lines) < 20:
        raise ValueError(f"script too short ({len(lines)} lines); something went wrong")
    return lines


def main():
    if len(sys.argv) == 2:
        data = Path(sys.argv[1]).read_text()
    else:
        data = sys.stdin.read()

    outline = json.loads(data)
    script = generate_script(outline)
    # Validate before emitting so failures surface here, not in synthesis
    validate_script(script)
    print(script)


if __name__ == "__main__":
    main()
