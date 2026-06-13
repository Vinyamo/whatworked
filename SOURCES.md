# Multi-source scans

studyd was originally Reddit-only. As of 2026-05-08 the scan layer accepts a
`sources: [{kind, ...}]` field on `POST /scans`, so a single scan job can fan
out across heterogeneous data sources and produce one merged
`candidates.ndjson` that the existing scorer + diagnostics consume unchanged.

## Source kinds

| kind     | speed   | cost                    | best for                                |
|----------|---------|-------------------------|-----------------------------------------|
| reddit   | fast    | free (local archive)    | most consumer-health / experience topics |
| erowid   | fast    | free (local xlsx import)| psychoactives, recreational substances   |
| brave    | slow    | $5/1k Brave queries + fetch time | filling thin reddit/erowid topics, niche/medical, off-Reddit communities |

## Candidate shape (unified)

Every source emits one NDJSON line per candidate with the same keys that the
Go scanner already produces. Downstream code keys off `subreddit` for the
"source-group" quota (`per_sub_max_pct`), so we reuse it across sources:

```jsonc
{
  "uid": "<source>_<id>",            // globally unique
  "id":  "<source-native-id>",
  "subreddit": "<source-group>",     // reddit: "Anxiety"; erowid: "erowid:psilocybin"; brave: "brave:bluelight.org"
  "kind": "submission|comment|erowid|web",
  "title": "...",
  "body":  "...",
  "score": 0,                         // reddit upvotes; 0 elsewhere
  "created_utc": 0,
  "permalink": "<url-or-reddit-permalink>",
  "author": "...",
  "num_comments": 0,
  "src_file": "<provenance>",
  "source": "reddit|erowid|brave",   // NEW: explicit source tag for filtering/diagnostics
  "meta": {                           // NEW: per-source extras (substance, dose, age, domain, query, ...)
    ...
  }
}
```

`source` is new; everything else preserves the original Go-scanner contract.

## API: POST /scans

**New form (preferred):**
```jsonc
{
  "sources": [
    {"kind": "reddit", "subs": [...], "grep_patterns": [...], ...},
    {"kind": "erowid", "substances": ["psilocybin","lsd"], "grep_patterns": [...], "min_text_len": 200},
    {"kind": "brave",  "queries": [...], "max_results_per_query": 10, "max_total": 100, "freshness": "year", "domains_allow": [], "domains_deny": []}
  ],
  "min_text_len": 150,                 // global default; each source can override
  "min_score": 3,
  "max_candidates": 100000,
  "per_sub_cap": 0,                    // 0 = unlimited (default). >0 = emit at most N matches per
                                       //   subreddit then abandon it — an even, bounded sample for
                                       //   the opt-in wide cross-community discovery (AGENT Phase 3).
  "max_file_bytes": 0                  // 0 = no limit. >0 skips files larger than this (e.g. 30000000)
}
```

**Legacy form (still accepted):**
```jsonc
{"subs": [...], "grep_patterns": [...], "include_monthly": true, "include_torrent": true}
// → translated to sources: [{kind: "reddit", subs, grep_patterns, ...}]
```

When `sources` is present, legacy fields at the top level are ignored.

## Execution

The scan runner kicks off one async task per source. They all append to a
single `candidates.ndjson` under a write lock. Total emission is capped at
`max_candidates`. Per-source progress is tracked in `progress.json` under
`per_source: {reddit: {emitted, ...}, erowid: {...}, brave: {...}}`.

The Go scanner is still used for the reddit source (subprocess). Erowid +
Brave run in-process as Python async tasks.

## Erowid pipeline

1. **One-time import** (`scripts/erowid_import.py`): xlsx → per-substance
   NDJSON.zst at `/mnt/HC_Volume_104776046/data/erowid/<substance>.jsonl.zst`.
   Substance = the xlsx "Subgroup" column normalized (lowercase, snake_case,
   collapsed synonyms via SUBSTANCE_SYNONYMS).
2. **Index** at `/home/studyd/erowid/index.json` listing substances + counts.
3. **Lookup endpoint** `GET /erowid/substances?q=` — substring search like
   `/subreddits`.
4. **Source runtime** (`api/sources/erowid.py`): given a substance list +
   optional metadata filters + optional grep patterns, stream the substance
   files, apply filters, emit candidates with `subreddit="erowid:<substance>"`,
   `meta={age, gender, year, dose_mg, route, drug_class, link}`.
   Body = the report text.

   **Metadata filters available** (can pre-filter before/instead of grep):
   - `substances`: list of Subgroup names (matches xlsx column)
   - `drug_classes`: list of Drug column values ("Antidepressants", "Psychedelics", ...)
   - `age_min`, `age_max`: numeric age range
   - `genders`: subset of `["Male", "Female", "Other"]`
   - `year_min`, `year_max`: experience year (xlsx Year column)
   - `dose_min_mg`, `dose_max_mg`: total dose
   - `routes`: list of Route values ("oral", "insufflated", ...)
   - `grep_patterns`: optional after metadata filtering (some studies want
     EVERY report on substance X regardless of grep)

   The 20 Erowid experiments compare:
   - **grep-only** (current Reddit-style behavior): grep_patterns on report text
   - **metadata-only**: pre-filter by substance + age/gender/year, NO grep
   - **metadata+grep**: pre-filter THEN grep — narrowest, highest precision
   - **substance-only + LLM**: hand all reports for a substance to the scorer,
     let the LLM decide relevance

   Hypothesis: for substance-specific topics (e.g. "psilocybin for depression
   in 30s women"), metadata-only is dramatically more efficient than
   reddit-style grep. Reddit needs grep because the corpus mixes everything;
   Erowid is already substance-tagged.

## Brave pipeline

1. **Query**: each query → Brave Search API
   (`https://api.search.brave.com/res/v1/web/search`). 1 req/sec free-tier
   limit; otherwise paid-tier rate limits apply.
2. **Filter results**: drop SERP-only results, dedup by URL, optional domain
   allow/deny.
3. **Fetch**: parallel httpx GET (8s timeout). User-agent honest. Drop on
   robots.txt or non-HTML.
4. **Extract**: trafilatura.extract() → main article text. Fallback to
   bs4 article-extraction if trafilatura misses.
5. **Filter**: min_text_len, dedup by content hash.
6. **Emit**: candidate with `subreddit="brave:<domain>"`, `meta={query,
   url, snippet, fetched_at, brave_rank, brave_age}`. `body` = extracted text;
   `title` = page <title>.

Cost tracking:
- Brave $: queries_used × 0.005 USD (Data-for-AI tier) — recorded in scan
  summary as `summary.brave_cost_usd`.
- Fetch failures, dedup hits, total bytes fetched also in summary.

## Auto-source selection (agent-side, in AGENT.md)

The agent picks sources unless the user has opinions:

1. **Default**: `[reddit]`. Cheap, fast, broad. ~99% of consumer-health
   topics work fine here.
2. **Add erowid** when the topic is in the Erowid catalog (psychedelics,
   stimulants, cannabis, dissociatives, antidepressants used recreationally).
   Detected by topic-string match against the `/erowid/substances` index, or
   user mentions a substance by name.
3. **Add brave** when:
   - The user asks for it explicitly.
   - The topic is medical/clinical and Reddit is thin (e.g. rare conditions,
     treatment protocols outside of /r/-discussion communities).
   - After a reddit-only scan, the diagnostics show pre-cap supply <
     `target_n × 1.5` — fall back to brave.

Brave is opt-in / fallback because of cost ($) AND speed (web fetches
serialize at ~1-3s per page).

## See also

- `eval/brave_experiments_2026-05-08.md` — 20-experiment Brave strategy sweep
  + the recommended default config.
- `scripts/erowid_import.py` — xlsx → indexed NDJSON.
- `api/sources/{reddit,erowid,brave}.py` — runtime source modules.


## Reddit comments — separate source

Reddit submissions and comments have very different biases. Submissions are
prepared, edited, often longer; comments are reactive, terser, often implicit
("yeah I had that too at 50mg" in a thread about Lexapro). The original
unified scanner mixed them together and applied the same grep — which works
for submissions but **systematically under-recalls comments** that lean on
the parent-post's context.

So the new design splits them:

| kind                 | what it scans                              | grep semantics |
|----------------------|--------------------------------------------|----------------|
| `reddit_posts` | submissions only                            | direct grep    |
| `reddit_comments`    | comments, optionally filtered by parent-post match | direct grep OR post-anchored |

`reddit_comments` strategies:
- **direct** (legacy): apply grep_patterns to each comment body. Fast, cheap,
  high precision, lower recall on context-dependent comments.
- **post_anchored**: pass 1 over submissions builds a set of matched post IDs;
  pass 2 over comments keeps any comment whose `link_id` ∈ that set, then
  optionally re-applies a softer grep. Slower (2 passes) but catches implicit
  comments.

20 experiments compare across topics: recall (vs ground-truth manual sample),
precision-at-LLM, distinct-author count, and downstream report-quality flags.
Result + recommended default in `eval/comments_experiments_2026-05-08.md`.
