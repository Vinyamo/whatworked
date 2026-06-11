# studyd API reference

The cloud service behind WhatWorked: it scans community archives (Reddit, Erowid, web), scores candidates with an LLM, tallies treatments, transcribes audio, and renders the final PDF.

## Endpoint

```
https://whatworked.vinyamo.com
```

Standard TLS (Let's Encrypt) — verify certificates normally; never use `--insecure`/`-k`.

## Auth

**HTTP Basic** on every request, with the username + password issued to you by the maintainer:

```
Authorization: Basic base64(username:password)
```

Credentials are stored locally in `~/.claude/.studyd_credentials` (chmod 600, JSON: `{"url": ..., "username": ..., "password": ...}`) — the agent creates this file on first run by asking you. With curl:

```bash
curl -sS "https://whatworked.vinyamo.com/jobs" -u "$STUDYD_USER:$STUDYD_PASS"
```

**Brute-force throttle:** ≥10 failed auths from one IP within 5 min → HTTP 429 for 15 min (resets on success).

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET    | `/health` | liveness ping |
| GET    | `/subreddits?q=&min_subscribers=&limit=` | list 2,582 indexed subs |
| GET    | `/erowid/substances?q=&limit=` | list Erowid substances + per-class counts |
| POST   | `/scans` | start a scan job (single or multi-source via `sources: [...]`) |
| POST   | `/scores` | start a scoring job (references a scan_id) |
| GET    | `/jobs?kind=&status=&limit=` | list jobs |
| GET    | `/jobs/{id}` | job status + summary |
| GET    | `/jobs/{id}/log` | structured NDJSON log |
| GET    | `/jobs/{id}/results?passed_only=&limit=` | NDJSON of scored records |
| GET    | `/jobs/{id}/excluded?n=20&seed=0` | random sample of failed records (false-negative audit) |
| GET    | `/jobs/{id}/diagnostics` | supply / share / ease metrics per sentiment, category, subreddit |
| POST   | `/consolidate_labels` | LLM-merge free-form discovery labels into a canonical closed list |
| POST   | `/tally` | per-treatment corpus tally (popularity counts + sentiment) over a job's records — the breadth-mode primitive |
| POST   | `/transcribe` | transcribe an audio file via Whisper-1 (auto ffmpeg conversion) |
| POST   | `/render_pdf` | render study Markdown → PDF server-side (returns `application/pdf`) |
| GET    | `/usage` | per-key token + $ totals |

## GET /subreddits

```
GET /subreddits?q=anxiety&min_subscribers=1000&limit=50
```

`q` is **literal substring match** across `name`, `title`, `public_description` — no LLM, no fuzzy match, no stemming. Fan out across multiple queries (synonyms, related conditions) to get coverage. Returns subs sorted by subscriber count.

Response:
```jsonc
{"count": 24, "total": 2582, "subreddits": [
  {"name": "Anxiety", "title": "Anxiety Disorders", "public_description": "Discussion and support for sufferers and loved ones with anxiety conditions...",
   "subscribers": 744901, "num_posts": 868095, "num_comments": 4024569, ...},
  ...
]}
```

## GET /erowid/substances

```
GET /erowid/substances?q=psilo&limit=50
```

Substring search over the Erowid substance index. Same shape as `/subreddits`. Returns substances sorted by report count, plus a `by_drug_class` breakdown:

```jsonc
{"count": 1, "total": 37, "n_reports": 4297,
 "by_drug_class": {"Mushrooms": 1408, "LSD": 870, "MDMA": 781, "DMT": 517, "Antidepressants": 311, ...},
 "substances": [
   {"substance": "psilocybin", "count": 1408, "file": "by_substance/psilocybin.jsonl"}
 ]}
```

Use this BEFORE adding the `erowid` source to a scan; it confirms which canonical substance keys to pass.

## POST /scans

**Multi-source form** (preferred):
```jsonc
{
  "sources": [
    {"kind": "reddit_posts", "subs": ["Anxiety"], "grep_patterns": ["oxytocin"], "min_text_len": 150, "min_score": 3, "include_torrent": true},
    {"kind": "reddit_comments", "comments_strategy": "post_anchored", "subs": ["Anxiety"], "grep_patterns": ["oxytocin"], "min_text_len": 100, "include_torrent": true, "pass2_max_candidates": 50000},
    {"kind": "erowid", "strategy": "metadata_only", "substances": ["mdma"], "min_text_len": 400, "max_emit": 200},
    {"kind": "brave", "queries": ["oxytocin nasal spray personal experience", "syntocinon experience"], "max_results_per_query": 10, "max_total": 50, "min_text_len": 400, "domains_deny": ["reddit.com","quora.com"]}
  ],
  "max_candidates": 8000
}
```

See `SOURCES.md` for full per-source schemas, strategies, and cost characteristics.

**Legacy single-source form** (still accepted; translates to a single `reddit` source):
```jsonc
{
  "subs": ["Anxiety", "Nootropics"],         // case-sensitive, see /subreddits names
  "grep_patterns": ["oxytocin", "syntocinon"], // case-insensitive substrings (Aho-Corasick)
  "context_keywords": [],                      // optional any-of regex post-decode
  "experience_terms": ["i tried", "worked for me", "didn't work"],
  "min_text_len": 150,
  "min_score": 3,                              // reddit upvote floor
  "max_candidates": 100000,                    // hard cap (per-scan budget)
  "include_monthly": true,                     // /reddit/{Sub}/*.jsonl.zst
  "include_torrent": true,                     // /subreddits24/{sub}_{kind}.zst
  "profile": false                             // write Go pprof to job dir (debug)
}
// → {"job_id": "scan_…", "status": "queued"}
```

Scan summary in `/jobs/{id}` (multi-source):
```jsonc
{"emitted": 365,
 "lines_read": 367,
 "grep_hits": 265,
 "by_source": {
   "reddit_posts": {"kind": "reddit_posts", "emitted": 265, "lines_read": 265, "errors": []},
   "erowid":             {"kind": "erowid", "emitted": 100, "lines_read": 102, "errors": []},
   "brave":              {"kind": "brave", "emitted": 0, "queries_used": 0, "fetch_attempted": 0, "errors": []}
 },
 "brave_cost_usd": 0.0}
```

## POST /scores

See `CONFIG_RECOMMENDED.md` for the full recommended body and what every knob means. Headline:

- All thresholds are **fractions** of `target_n` or `dim.scale` — change `target_n` and everything scales.
- `model` defaults to `gpt-4o-mini`. `gemini-2.5-flash-lite` is an equal-quality drop-in.
- The scorer streams results as they come; you can poll the job for partial progress.

## GET /jobs/{id}/diagnostics

Score-job-only. For each of the three quota dimensions (sentiment / category / subreddit), returns:
- `passed` and `demoted_total` per row, with demotion broken down by reason
- `supply` (= passed + demoted): records that satisfied rel/qual/min_sum filters and competed for that bucket
- `share` (= supply / total_supply): topic-landscape share, sums to 100% across rows
- `binding_supply` (= passed + demotions caused by THIS dim's own cap): how many records the cap would have been the binding constraint on
- `ease` (= binding_supply / cap): ≥1 means the cap was reachable; <1 means supply ran out

```jsonc
{"job_id": "...", "total_scored": 567, "caps": {"sentiment": 20, "category": 12, "subreddit": 18},
 "dimensions": {
   "sentiment": {"cap": 20, "rows": [
     {"key":"pos","passed":20,"demoted_total":46,"demoted_sentiment_cap":3,"demoted_sub_cap":0,"demoted_category_cap":43,
      "supply":66,"binding_supply":23,"share":0.31,"ease":1.15}, ...]},
   "category": {...}, "subreddit": {...}}}
```

Use it to (a) confirm sentiment buckets are filling; (b) spot the dominant binding cap (often `category_cap`); (c) call out genuinely scarce buckets in the report's data-distribution section.

## POST /consolidate_labels

Used by the categories-discovery flow (see `scripts/discover_categories.py`). Takes free-form snake_case labels and counts; returns a canonical closed list, preserving distinct drugs/symptoms/methods.

```jsonc
// Request
{"labels": [{"label":"effexor_withdrawal","count":18},
            {"label":"effexor_taper","count":12},
            {"label":"lexapro_withdrawal","count":14},
            {"label":"brain_zaps","count":6}],
 "topic": "SSRI withdrawal", "target_n_categories": 12, "model": "gpt-4o-mini"}

// Response
{"canonical": [{"name":"effexor","variants":["effexor_withdrawal","effexor_taper"]},
               {"name":"lexapro","variants":["lexapro_withdrawal"]},
               {"name":"brain_zaps","variants":["brain_zaps"]}],
 "tokens_in": 396, "tokens_out": 108, "cost_usd": 0.00012, "model": "gpt-4o-mini"}
```

Cost is negligible (~$0.0005/call). Supports gpt-4o-mini and gemini-2.5-flash-lite.

## Result record shape

Every scored post (passed or demoted) is one NDJSON line in `GET /jobs/{id}/results`:

```jsonc
{
  "uid": "1ohlew2_s",
  "subreddit": "Anemia",
  "score_reddit": 47,
  "scores": {"rel": 9, "qual": 8, "sentiment": 4},  // exactly your dim keys
  "cat": "oral_iron",
  "sentiment_bucket": "neu",                          // pos|neg|neu|null
  "brief": "Woman 30s with ferritin <10 reports...",
  "passed": true,
  "demoted": null,                                    // "category_cap"|"sub_cap"|"sentiment_cap" if demoted
  "title": "...",
  "body": "...",
  "permalink": "/r/Anemia/...",
  "kind": "submission"                                // or "comment"
}
```

## POST /tally

The breadth-mode popularity+effectiveness primitive (see `AGENTS.md` → "Breadth mode"). Runs the
Go Aho-Corasick `corpusmatch` tool server-side over a finished job's records — **no local setup**.

```jsonc
// Request
{
  "scan_id": "scan_…",                 // or a score_id when sentiment=true
  "treatments": [
    {"name": "colchicine", "aliases": ["colchicine"]},
    {"name": "anakinra",   "aliases": ["anakinra", "kineret"]}
  ],
  "sentiment": false                    // false → tally candidates.ndjson w/ lexical sentiment;
                                        // true  → tally a score job's scored.ndjson via sentiment_bucket
}
// Response
{"corpus_n": 12000,
 "counts": {"colchicine": {"count": 53, "pos": 16, "neg": 7},
            "anakinra":   {"count": 15, "pos": 5,  "neg": 0}}}
```

`count` = posts mentioning the treatment (popularity); `pos`/`neg` = effectiveness tally. Boundary
matching is identical to the offline reference (an alias matches only when not flanked by `[a-z0-9]`).
Deterministic and fast (~3 s over 20k posts). Used in breadth mode after the discovery sweep to
attach exact popularity + effectiveness to every discovered treatment.

## POST /transcribe

Multipart upload an audio file; server returns the Whisper-1 transcript.
Server auto-converts non-native formats (ogg, flac, opus, aiff, aac, …)
to mono 16 kHz wav with ffmpeg before uploading. Inputs > 25 MB are
re-encoded to fit Whisper's API limit. Bodies up to 200 MB accepted by
Caddy.

**Logging policy: filename + bytes + duration + status + transcript-length only. The server never logs transcript content or audio bytes.**

```bash
curl -sS -X POST "https://whatworked.vinyamo.com/transcribe" \
  -u "$STUDYD_USER:$STUDYD_PASS" \
  -F "file=@voice_memo.m4a" \
  -F "model=whisper-1" \
  -F "language=en"
```

Form fields:
- `file` (required) — the audio file
- `model` (optional, default `whisper-1`)
- `language` (optional, ISO-639-1 hint, e.g. `en`, `de`)
- `prompt` (optional, glossary or context hint)

Response:
```jsonc
{"text": "Hello world.",
 "duration_s": 0.94,
 "model": "whisper-1",
 "input_bytes": 30052,
 "input_format": "wav",
 "converted": false,                        // true if ffmpeg normalized the input
 "cost_usd": 0.00009}
```

Cost: `whisper-1` = $0.006/minute. Recorded in `/usage` under `transcribes`
+ `audio_seconds` per user. Supported formats: wav, mp3, m4a, ogg, flac, opus, aiff, webm, aac.

## POST /render_pdf

Render a finished study (Markdown) to the final PDF deliverable **server-side**, so
distributed clients need no local weasyprint / Cairo / Pango install. Mermaid fences
are rendered to inline images; the renderer blocks all non-`data:` URLs in the body
(no SSRF / local-file reads). Returns the PDF bytes.

```bash
curl -sS -X POST "https://whatworked.vinyamo.com/render_pdf" \
  -u "$STUDYD_USER:$STUDYD_PASS" \
  -H "Content-Type: application/json" \
  -d '{"markdown": "# Study\n\nbody…", "filename": "study_sleep.pdf"}' \
  -o study_sleep.pdf
```

The standard path is `scripts/build_pdf.py <study.md>`, which wraps this call.
Body: `{"markdown": "<study md>", "filename": "study.pdf"}` (`filename` optional;
sanitized to a safe basename). Limits: markdown ≤ 4 MiB (else **413**); diagram count
capped. Mermaid fences render to inline images server-side.

## Job statuses

`queued` → `running` → `done` | `failed`. Poll `GET /jobs/{id}` every 5s. Scan jobs typically 30–120s; score jobs typically 30–300s depending on `max_scored_factor` and topic pool size.

## Costs (per /usage)

Tracked per user. Returned by `/usage`:
```jsonc
{"keys": {"alice": {"scans": 0, "scores": 75,
  "tokens_in": 22484340, "tokens_out": 3300030, "cost_usd": 20.49}}}
```

Per-study budget for the recommended config (target_n=60, gpt-4o-mini): roughly $0.05–$0.30 depending on how broad the candidate pool is (broader = more LLM calls before bucket quotas fill).

## Rate / concurrency

The studyd service runs all scoring jobs as separate asyncio tasks — submitting multiple scoring jobs in parallel is fine and they don't bottleneck each other. OpenAI tier-3 supports ~5,000 RPM, so practical throughput is fine for the workloads here.

## Common error patterns

- **401** with `missing credentials` body — your `Authorization` header is absent or is neither `Bearer …` nor `Basic …`. (Bad username/password also → 401, `invalid credentials`.)
- **429** with a `Retry-After` header — too many failed auth attempts from your IP; wait out the lockout, then retry with correct credentials.
- **422 Unprocessable Entity** — your JSON body doesn't match the Pydantic schema; check field names (the schema changed: `min_pct` not `min`, `min_sum_pct` not `min_sum`, etc. — see CONFIG_RECOMMENDED.md).
- **Scan returns `emitted: 0`** — patterns are wrong, or sub names are misspelled. Sub names are case-sensitive; cross-check against `/subreddits`.
- **Score `meta.error: "no openai api key…"`** — happens only for `gpt-*` models. Set `OPENAI_API_KEY` server-side or use `gemini-2.5-flash-lite` instead.
- **Score returns `passed < target_n`, `halted_early: true`** — the candidate pool exhausted before bucket quotas filled. The remaining buckets are genuinely sparse for this topic. Note in the report's data-distribution section.
