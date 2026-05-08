"""V1 publish step: write a small metadata file alongside the MP3.

The actual git commit happens in the GitHub Action (cleaner separation than
shelling out to git from Python). This script just emits metadata.

V2 would extend this: push to S3, regenerate a podcast RSS feed, send an email,
etc. Keeping it isolated means none of the other modules need to change.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def write_metadata(mp3_path: Path, title: str, source_pdf: str,
                   script_path: Path) -> Path:
    meta = {
        "title": title,
        "source_pdf": source_pdf,
        "mp3": str(mp3_path.name),
        "script": str(script_path.name),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_path = mp3_path.with_suffix(".json")
    meta_path.write_text(json.dumps(meta, indent=2))
    return meta_path


def main():
    if len(sys.argv) != 5:
        print("usage: python -m src.publish <mp3> <title> <source_pdf> <script_path>",
              file=sys.stderr)
        sys.exit(1)
    mp3 = Path(sys.argv[1])
    title = sys.argv[2]
    source = sys.argv[3]
    script_path = Path(sys.argv[4])
    meta_path = write_metadata(mp3, title, source, script_path)
    print(f"wrote {meta_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
