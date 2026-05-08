# Paper Podcast

Drop an academic PDF into `papers/`, run a GitHub Action, get a 20-minute host-and-expert dialogue MP3 in `episodes/`.

## How it works

```
papers/foo.pdf
   │
   ▼  src/extract.py        (pymupdf)
clean text
   │
   ▼  src/outline.py        (NVIDIA API → DeepSeek)
structured outline (JSON)
   │
   ▼  src/scriptwriter.py   (NVIDIA API → DeepSeek)
HOST/EXPERT dialogue
   │
   ▼  src/synthesize.py     (Groq TTS → PlayAI voices)
episodes/foo.mp3
```

The two-pass LLM approach (outline → dialogue) is deliberate. A one-shot prompt produces lazy, skimming output. Forcing a structured outline first gives the dialogue something concrete to expand into.

## One-time setup

1. **Fork or push this repo** to your own GitHub account.

2. **Add API keys as GitHub Secrets** (Settings → Secrets and variables → Actions → New repository secret):
   - `NVIDIA_API_KEY` — from [build.nvidia.com](https://build.nvidia.com)
   - `GROQ_API_KEY` — from [console.groq.com](https://console.groq.com)

3. **Verify Action permissions**: Settings → Actions → General → Workflow permissions → "Read and write permissions" (so the bot can commit episodes back).

## Generating an episode

1. Drop a PDF into `papers/`, commit, push:
   ```bash
   cp ~/Downloads/attention-is-all-you-need.pdf papers/
   git add papers/ && git commit -m "Add attention paper" && git push
   ```

2. Trigger the workflow: GitHub repo → **Actions** tab → **Generate Podcast Episode** → **Run workflow** → enter `papers/attention-is-all-you-need.pdf` → Run.

3. Wait ~5–15 minutes (most of that is TTS). When done, the MP3 is committed to `episodes/`. `git pull` to grab it.

## Tuning quality

- **The dialogue prompt (`prompts/dialogue.txt`) is where most of the quality lives.** If episodes feel shallow, surface-level, or sycophantic, edit this file. Push back on filler phrases. Demand specificity.
- **Pick a stronger model** by setting `OUTLINE_MODEL` and `SCRIPT_MODEL` env vars in the workflow. Browse [build.nvidia.com/models](https://build.nvidia.com/models) for current options.
- **Voice swap**: set `HOST_VOICE` and `EXPERT_VOICE` to any voice from Groq's PlayAI catalog. Sample them in the Groq console first.

## Costs and limits

- NVIDIA API: free tier is rate-limited but no per-token cost for most open-weight models.
- Groq TTS: free tier has rate limits; one ~20-min episode is ~80 short TTS calls. The synthesis script retries on rate-limit errors with backoff. If you generate several episodes a day, you may hit the wall.
- GitHub Actions: free for public repos; 2000 minutes/month for private repos on the free tier. Each episode uses ~10 minutes.

## V2 ideas (deliberately not built yet)

- **Auto-discovery**: poll arXiv RSS / a Zotero collection / Semantic Scholar API for new papers. Replace `extract.py` input from a path to a paper-source-adapter pattern.
- **Private podcast feed**: instead of committing MP3s, push to S3 or R2 and regenerate an RSS feed. Subscribe in Overcast or Pocket Casts.
- **Per-paper config**: optional `.yml` next to the PDF to override length, voices, or prompt style ("explain this to a freshman" vs "two PhDs in the trenches").
- **Multi-paper episodes**: outline-merge two related papers into a comparative dialogue.

The architecture is set up so each of these slots into one module without touching the others.

## Local testing (without GitHub Actions)

```bash
pip install -r requirements.txt
export NVIDIA_API_KEY=nvapi-...
export GROQ_API_KEY=gsk_...

python -m src.extract papers/foo.pdf > /tmp/extracted.txt
python -m src.outline /tmp/extracted.txt > /tmp/outline.json
python -m src.scriptwriter /tmp/outline.json > episodes/foo.script.txt
python -m src.synthesize episodes/foo.script.txt episodes/foo.mp3
```

Useful for iterating on prompts without burning Action minutes.
