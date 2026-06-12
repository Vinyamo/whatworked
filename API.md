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
| POST   | `/discover` | server-side map-reduce treatment discovery over a scan's candidates |
| POST   | `/rate` | start an attribution-first rate-the-stories job (references a scan_id) — the breadth-mode rating primitive |
| GET    | `/jobs?kind=&status=&limit=` | list jobs |
| GET    | `/jobs/{id}` | job status + summary |
| GET    | `/jobs/{id}/log` | structured NDJSON log |
| GET    | `/jobs/{id}/results?passed_only=&limit=` | NDJSON of scored / rated records |
| GET    | `/jobs/{id}/discovered` | discovered treatment names (discover jobs) |
| GET    | `/jobs/{id}/profiles` | per-treatment rating profiles (rate jobs) |
| GET    | `/jobs/{id}/excluded?n=20&seed=0` | random sample of failed records (false-negative audit) |
| GET    | `/jobs/{id}/diagnostics` | supply / share / ease metrics per sentiment, category, subreddit |
| POST   | `/consolidate_labels` | LLM-merge free-form discovery labels into a canonical closed list |
| POST   | `/tally` | per-treatment corpus tally (popularity counts + sentiment) over a job's records — the breadth-mode primitive |
| POST   | `/transcribe` | transcribe an audio file via Whisper-1 (auto ffmpeg conversion) |
| POST   | `/render_pdf` | render study Markdown → PDF server-side (returns `application/pdf`) |
| GET    | `/usage` | per-key token + $ totals |

## Logging & data handling

What the WhatWorked API records when you use it — and what it doesn't.

- **Per-account usage log (kept).** Every request appends one line: your username, the action (`scan` / `score` / `rate` / `discover` / `transcribe` / `render_pdf`), a timestamp, the job id, token counts, cost, and duration. It exists so the maintainer can monitor cost and abuse. **It contains no study content** — not your issue description, not the corpus, not the report text.
- **Uploaded audio: format & size only.** Only the **file format** (e.g. `m4a`), byte size, duration, and status are recorded — **never the filename** (a filename can itself be personal, like `bloodwork_2024.pdf`), and never the audio bytes or the transcript text. The file is sent to the transcription service under a generic name, not your original filename.
- **PDF rendering: transient.** The markdown you send to render a PDF is used only to produce the PDF and is not stored as content; only its size and diagram count are noted.
- **Job data (to run your research).** Your job parameters (subreddits, search terms, topic, audience) and the fetched public corpus are stored as files scoped to your account so the study can run and you can fetch results. Other accounts cannot see your jobs.
- **What is sent to third parties, and their policies in a nutshell:**
  - **Google (Gemini API)** — receives the **public Reddit/Erowid post text** to classify, rate, and extract options from, plus your short topic/audience description. Under the Gemini API terms, paid-API content is **not used to train Google's models** and is retained only briefly for abuse monitoring. → https://ai.google.dev/gemini-api/terms
  - **OpenAI (Whisper)** — receives the **audio you choose to transcribe** (under a generic filename). Under the OpenAI API terms, API inputs are **not used to train OpenAI's models** and are retained ~30 days for abuse monitoring, then deleted. → https://openai.com/enterprise-privacy/
  - **Brave Search** — receives the **search queries** only (not your identity). Brave is privacy-focused and does not build user profiles. → https://brave.com/privacy/
- **What stays with you.** Transcripts and finished reports are written to your local study folder, not kept on the server.
- **Minimized before it is sent.** The assistant strips personally-identifying information (your name, exact location, employer, contact details, unique IDs) from what it sends to the API — only the minimal demographic/clinical context the research needs (e.g. "38F, 6-month 3am waking"). Your **supplemental documents and images are read locally and never uploaded**; only audio is sent (to transcribe it), and the assistant tells you before doing so.
- **Credentials & usage.** Usage is logged per account, and accounts may be rate-limited or revoked if costs run away — treat your credentials like a payment method and don't share them.

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
  "max_candidates": 8000,                      // caps EMITTED records, not files read (a scan is read-bound — see Job statuses)
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

## POST /discover

Server-side **treatment discovery** over a finished scan's candidates — a gemini map-reduce that
extracts every distinct treatment / intervention people mention, including the long tail mentioned
once. Replaces the old agent-side discovery sweep (which is now only a fallback). Async job, same
lifecycle as `/scores` (`{job_id}` → poll `GET /jobs/{id}` → `GET /jobs/{id}/discovered`).

The map chunks the candidates (`chunk_posts` per chunk, each post truncated to `max_post_chars`),
asks a cheap model to extract every distinct treatment per chunk, runs the map `passes` times, and
**unions** the results so the tail isn't under-sampled (single-pass discovery drops rare names
unpredictably). All discovered names are carried forward — no silent reduce-side dropping.

```jsonc
// Request
{
  "scan_id": "scan_…",
  "topic": "trauma sleep-maintenance insomnia",
  "audience": "35M with hyperarousal",       // optional — sharpens relevance
  "passes": 2,                                // map runs (≥2 recommended; union)
  "chunk_posts": 1000,                        // posts per map chunk
  "max_post_chars": 500,                      // truncate each post before the map
  "workers": 24,                              // concurrency
  "seed": 1
}
// Response: {"job_id": "discover_…", "status": "queued"}
```

`GET /jobs/{id}/discovered` → the unioned list of distinct discovered names (with per-name mention
counts). Normalize them agent-side before tallying (split `a/b` and `X (Y)` into name + aliases,
recover list-bucket members, drop bare class words, merge substring variants) — see AGENTS.md PHASE 3.

## POST /rate

Attribution-first **rate-the-stories** (the S5 model), server-side — the breadth-mode rating
primitive. Default model `gemini-2.5-flash-lite` (a bounded classification task whose accuracy
ceiling a cheap model with chain-of-thought already reaches; a top-tier model adds ~0 accuracy here).
Async job, same lifecycle as `/scores` (`{job_id}` → poll `GET /jobs/{id}` → `GET /jobs/{id}/profiles`).

Per treatment: match mentioning posts in the scan's candidates → **sample** to a story target
(`sample_n`) → rate each post with a five-facet CoT call. **Sampling is the point: the rate is a
proportion, so a sample + Wilson CI suffices.** Target ~30–50 attributable (first-hand) stories per
option; treatments with fewer mentions than the target are **rated in full (census)**; an option with
**<10 attributable stories is shown but NOT ranked** (no precise %). Prevalence (the corpus count)
comes from `/tally`, not from this sample — never conflate the two.

**Batches are single-treatment** (the cheap model collapses to ~all-skip on mixed-treatment batches),
and each profile carries reliability flags: `low_n` (< `min_attributable` first-hand stories) and
`high_skip` (> `skip_rate_warn` skipped — a degenerate-rater signature). Consumers must not show
precise %s when `rateable` is false.

```jsonc
// Request
{
  "scan_id": "scan_…",
  "treatments": [{"name": "prazosin", "aliases": ["prazosin","minipress"]}, ...],
  "topic": "trauma sleep-maintenance insomnia", "audience": "35M with hyperarousal",
  "model": "gemini-2.5-flash-lite",          // gpt-* also dispatch (for cross-model checks)
  "facets": ["magnitude","sub","harm","durability"],   // subset to go cheaper/faster
  "sub_labels": ["onset","maintenance"],     // sub-problem axis ([] disables 'sub')
  "sample_n": 50,                            // story target per treatment (0 = census)
  "batch_size": 8, "workers": 24, "seed": 1,
  "min_attributable": 8, "skip_rate_warn": 0.9
}
// Response: {"job_id": "rate_…", "status": "queued"}
```

`GET /jobs/{id}/profiles` → one profile per treatment: `helped/noeffect/worse` counts + `_pct`,
`helped_ci` (Wilson 95%), `size` (m1–m5), `mag_mean`/`mag_bucket`, `sub`/`worse_type`/`dur` splits,
`evidence` (1–5), `contested`, and `low_n`/`high_skip`/`skip_pct`/`rateable`. `GET /jobs/{id}/results`
streams the per-post rated NDJSON. Cost / tokens land in the job `summary` and `/usage` (kind `rate`).
Rating is cheap (~$0.13/topic) — depth is near-free, so sample to a generous story target.

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

`queued` → `running` → `done` | `failed`. Poll `GET /jobs/{id}` every ~5s — but **poll without
blocking**: a scan is **read-bound** (it reads every file of every sub, even ones that emit 0), so
while a narrow scan is ~30–120s, a **wide scan over big subs can take many minutes (10+)**. Don't
sit in a foreground sleep-loop waiting for it — your tool harness kills long-running calls at its
timeout ceiling, so a blocking wait dies at the ceiling, wastes the full window, and forces a
restart. Fire the job and poll in the background / re-check on a later turn. Score jobs typically
30–300s depending on `max_scored_factor` and topic pool size. `max_candidates` caps emitted records,
not files read, so raising it does NOT bound scan time. Run heavy scans one at a time.

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
