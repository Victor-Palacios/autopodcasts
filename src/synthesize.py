"""Synthesize a HOST/EXPERT script into a single MP3 using Groq TTS.

Approach:
  - Iterate script lines, render each with the appropriate voice
  - Save individual WAVs to a temp dir
  - Concatenate with ffmpeg into one MP3
  - Insert ~250ms silence between turns for natural pacing

Voice choices below are placeholders — the Groq voice catalog updates often.
Override with HOST_VOICE / EXPERT_VOICE env vars if you want to swap.

Note on rate limits: Groq's free tier rate-limits TTS. For a 20-min episode
(~80 lines), you may hit transient limits. We retry with exponential backoff.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from groq import Groq


GROQ_TTS_MODEL = os.environ.get("GROQ_TTS_MODEL", "playai-tts")
HOST_VOICE = os.environ.get("HOST_VOICE", "Celeste-PlayAI")
EXPERT_VOICE = os.environ.get("EXPERT_VOICE", "Fritz-PlayAI")
SILENCE_BETWEEN_TURNS_MS = 250


def build_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    return Groq(api_key=api_key)


def parse_script(script_text: str) -> list[tuple[str, str]]:
    lines = []
    for raw in script_text.splitlines():
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
    return lines


def synthesize_line(client: Groq, speaker: str, text: str, out_path: Path,
                    max_retries: int = 5) -> None:
    voice = HOST_VOICE if speaker == "HOST" else EXPERT_VOICE
    delay = 2.0
    for attempt in range(max_retries):
        try:
            response = client.audio.speech.create(
                model=GROQ_TTS_MODEL,
                voice=voice,
                input=text,
                response_format="wav",
            )
            response.write_to_file(str(out_path))
            return
        except Exception as e:
            msg = str(e).lower()
            # Retry on rate limit or transient network errors
            if "rate" in msg or "429" in msg or "timeout" in msg or "5" in msg[:3]:
                if attempt < max_retries - 1:
                    print(f"  retry {attempt + 1}/{max_retries} after {delay}s ({e})",
                          file=sys.stderr)
                    time.sleep(delay)
                    delay *= 2
                    continue
            raise


def make_silence(duration_ms: int, out_path: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=channel_layout=mono:sample_rate=48000",
         "-t", f"{duration_ms / 1000}", str(out_path)],
        check=True, capture_output=True,
    )


def concatenate(wav_paths: list[Path], out_mp3: Path) -> None:
    """Use ffmpeg's concat demuxer to join all the wavs, then encode as mp3."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for p in wav_paths:
            # ffmpeg concat list format requires this exact escape style
            f.write(f"file '{p.absolute()}'\n")
        list_file = f.name

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
             "-c:a", "libmp3lame", "-b:a", "128k", str(out_mp3)],
            check=True, capture_output=True,
        )
    finally:
        os.unlink(list_file)


def synthesize_script(script_text: str, out_mp3: Path) -> None:
    client = build_client()
    lines = parse_script(script_text)
    if not lines:
        raise ValueError("no HOST/EXPERT lines found in script")

    print(f"synthesizing {len(lines)} lines...", file=sys.stderr)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        wav_paths = []

        # Build silence clip once and reuse
        silence_path = tmp / "silence.wav"
        make_silence(SILENCE_BETWEEN_TURNS_MS, silence_path)

        for i, (speaker, text) in enumerate(lines):
            line_path = tmp / f"line_{i:04d}.wav"
            print(f"  [{i + 1}/{len(lines)}] {speaker}: {text[:60]}...",
                  file=sys.stderr)
            synthesize_line(client, speaker, text, line_path)
            wav_paths.append(line_path)
            if i < len(lines) - 1:
                wav_paths.append(silence_path)

        out_mp3.parent.mkdir(parents=True, exist_ok=True)
        concatenate(wav_paths, out_mp3)

    print(f"wrote {out_mp3}", file=sys.stderr)


def main():
    if len(sys.argv) != 3:
        print("usage: python -m src.synthesize <script_file> <out_mp3>",
              file=sys.stderr)
        sys.exit(1)
    script_text = Path(sys.argv[1]).read_text()
    out_mp3 = Path(sys.argv[2])
    synthesize_script(script_text, out_mp3)


if __name__ == "__main__":
    main()
