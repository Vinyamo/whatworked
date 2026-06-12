# `POST /scores` config — the OPTIONAL filter-first path

> **Pipeline role:** the default pipeline is `discover → rate → tally` (AGENTS.md) — prevalence
> from the exhaustive `/tally`, rates from `/rate` sampled to a **story target** (~30–50
> attributable stories/option; <10 → don't rank). The `POST /scores` filter below is **no longer
> the primary path**; use it only when you specifically want a curated, sentiment-balanced set of
> quotable records. The mode question (Cheap/Mod/High), the `target_n`/sample tiers, the
> skip-pre-filter step, and the robustness/cross-model second run are **deleted** (they add
> cost/length/error, not value). The numbers below remain valid *for the filter path*;
> `target_n ≈ 80` is plenty.

Empirically tuned across 75 scoring runs and a 20-run threshold sweep. All thresholds and caps are **fractions** — change only `target_n` and everything scales.

## Categories discovery (run BEFORE this body)

Don't draft the `categories` list from your prior. Run `scripts/discover_categories.py <scan_id>` after the scan. It uses a topic-axis-only discovery prompt + LLM consolidation to propose 8–15 categories from the actual rel/qual-passing records. Cost ~$0.07, ~60–90 s. Surface the proposal to the user before plugging into the body below. See AGENT.md step 6.5 and `category_discovery_2026-05-07.md` for the empirical justification (the discovery prompt was the single biggest lever in a 14-variant sweep).

## The default body

```jsonc
{
  "scan_id": "scan_…",
  "topic": "<specific question being researched>",
  "audience": "<who the report is for, including the decision context>",

  "model": "gemini-2.5-flash-lite",        // default — faster, cheaper, better bucket-fill (avg 1.25 vs 3.50 weakness flags in 2026-05-07 10-topic comparison). gpt-4o-mini works equally well for label quality; pick by billing.
  "system_prompt": "",                      // leave empty unless you have a specific reason
  "prompt_style": "default",                // "default" | "terse" | "cot" — leave default
  "shuffle_batch": true,                    // free safety belt against batch-context contamination

  "batch_size": 8,                          // sweet spot (1 = 2× cost, 20 = no gain)
  "workers": 16,
  "target_n": 60,                           // ← the unit of measure; bump this and everything scales
  "early_stop_factor": 1.3,
  "max_scored_factor": 40.0,                // runaway cap = round(target_n × 40)
  "order": "random",
  "seed": 1,

  "dimensions": [
    {"key":"rel","label":"Relevance",
     "desc":"Personal-experience report ABOUT THE SPECIFIC TOPIC. Reject (rel<5) posts about the broader area but not the topic.",
     "min_pct": 0.6, "scale": 10},
    {"key":"qual","label":"Quality",
     "desc":"Information density: clear dose, timeline, mechanism, outcome. A short clear post can score 8-9. A long rambling one scores 3-4. Length is NOT quality.",
     "min_pct": 0.6, "scale": 10},
    {"key":"outcome","label":"Outcome",
     "desc":"Does the post report a concrete OUTCOME/result of trying something for the issue — what happened (better/worse/no change/side-effect)? 0=no outcome (a question, a plan, general info, or a bare mention), 10=a clear before/after result.",
     "min_pct": 0.4, "scale": 10},
    {"key":"sentiment","label":"Sentiment",
     "desc":"0=strongly negative, 5=mixed/null, 10=strongly positive. Use the full 0-10 range.",
     "min_pct": 0.0, "scale": 10}
  ],
  "filter": {"op": "both", "min_sum_pct": 0.4},

  "sentiment_quota": {
    "dim_key": "sentiment",
    "pos_pct": 0.7, "neg_pct": 0.3,
    "min_per_bucket_pct": 0.0,
    "max_per_bucket_pct": 0.333            // 1/3 each — perfectly balanced 3-way
  },
  "per_sub_max_pct": 0.30,                 // any one sub capped at 30% of target_n
  "per_category_quota_pct": 0.20,
  "per_category_min_pct": 0.0,

  "categories": ["...", "no_effect", "side_effects", "other"],  // closed list, 6–10 entries
  "topic_keywords": [],                     // optional pre-LLM substring filter for narrow topics

  "dedup_content": true
}
```

At `target_n: 60` this resolves internally to the absolute values that work best:

| Knob | Resolved at target_n=60, scale=10 |
|---|---|
| `dim.min` (rel, qual, outcome) | 6 / 6 / 4 |
| `filter.min_sum` | 16 (= 0.4 × 40, now 4 dims) |
| `sentiment_quota.{pos,neg}_threshold` | 7 / 3 |
| `sentiment_quota.max_per_bucket` | 20 (= 33% × 60) |
| `per_sub_max` | 18 (= 30% × 60) |
| `per_category_quota` | 12 (= 20% × 60) |
| `max_scored` | 2400 (= 40 × 60) |

## What each knob actually does, and when to deviate

### `target_n`
The number of records you want in the final report. Default 60 is the bucket sweet-spot (3 sentiment buckets × 20 each). Bump to 120 / 180 / 300 for bigger reports — everything else scales automatically. Going below 30 starts to break sentiment balance because each bucket has fewer than ~7 records.

### `model`
- **`gemini-2.5-flash-lite`** (default, as of 2026-05-07) — $0.10/M in, $0.40/M out, ~63s/study, 0% error rate. Empirically lower weakness rate than gpt-4o-mini in a 10-topic comparison: avg 1.25 weakness flags vs 3.50, and lower cost. Hits target_n exactly more often.
- **`gpt-4o-mini`** — $0.15/M in, $0.60/M out, ~93s/study, 0% error rate. Slightly worse on bucket-fill metrics, and systematically more pessimistic on rating — **not** a tiebreaker. Don't default to it.
- Other models cost more at no quality gain on this bounded-classification task; a cheap model is at the ceiling. Don't pay a frontier model to filter or rate.
- **`gemini-2.5-flash`**, **`gpt-4.1-mini`** — empirically worse: high error rates and category sprawl. Don't use.

### Dimensions: `rel.min_pct`, `qual.min_pct`
The 20-run threshold sweep showed the **knee is at 0.6** for both. Going stricter (0.7, 0.8) gives diminishing returns in mean post quality and changes which 60 records pass without meaningfully improving quality. Going looser (0.5, 0.4) lets in noticeably weaker reports.

For high-stakes studies use `0.8 / 0.7` and `filter.min_sum_pct: 0.53` (≈ 16 / 30 for the 3-dim default). Cost roughly 2× because more candidates get scored.

### `outcome.min_pct` — the outcome dimension (added 2026-06-04)
The single highest-leverage filter knob. rel+qual alone caps at **~0.48 precision** on "usable
outcome stories" — over half of what passes is a relevant question/plan/vent with no result. Adding
the `outcome` dimension lifts precision to **0.70–0.81** (12-topic experiment vs a sonnet gold judge,
scored by the real `gemini-2.5-flash-lite`; see `FILTER_OUTCOME_EXPERIMENT_2026-06-04.md`).
- **Default `0.4`** (outcome ≥ 4/10 — "an outcome is at least partially described"): the precision/
  recall sweet spot (P≈0.70 / R≈0.67).
- **Purity** (large pools): raise to `0.6–0.7` → P≈0.77–0.81 (recall drops to ~0.44–0.49).
- **Thin topics / need recall: this is the knob to LOWER first** — `0.3` → R≈0.78 (P≈0.65); `0.2`
  looser still. **Thresholds are NOT lowered automatically** — see the recall fallback below.

### Recall fallback when too few pass (thin topics)
There is **no automatic threshold relaxation**; a thin run returns `halted_early: true` / `passed <
target_n`. When `passed < target_n × 0.6`, relax in this order, re-running the score job each time,
**before** halting and surfacing to the user:
1. **Lower `outcome.min_pct`**: 0.4 → 0.3 → 0.2 (recovers the most recall at least precision cost).
2. Lower `target_n` to what the corpus supports (`min(target_n, emitted × 0.3)`).
3. Loosen `rel/qual` to `0.5` only as a last resort (it admits weaker reports).
If even `outcome ≥ 0.2` + lowered `target_n` is too thin, the corpus genuinely lacks outcome stories —
say so in §3/§8 rather than padding with non-outcome posts.

**Lower `outcome` ONLY — not all thresholds together** (tested on 3 outcome-sparse topics,
`FILTER_OUTCOME_EXPERIMENT_2026-06-04.md` §fallback). `outcome` is the binding constraint on thin
topics; lowering `rel/qual` *as well* recovers essentially **no** extra usable stories and only drops
precision at the bottom (e.g. outcome-0 floor: P 0.26→0.24, recall 0.88→1.0 by admitting junk). So step
3 above is genuinely a last resort.

**Each rung REPLACES the previous run — never accumulate passed sets across rungs.** Re-running at a
lower threshold returns a *superset* of the prior run, so concatenating rungs duplicates ~every prior
record (measured: ~360 duplicate rows over a 5-rung ladder). Use the latest (loosest) run's result, or
if you merge any runs, **dedup by `uid`** (studyd's `dedup_content` only dedups identical text).

### `filter.op`
- `"both"` (default) — `min_each` AND `min_sum`. Strictest, cleanest output.
- `"min_each"` — per-axis floor only. Slightly looser. Use when your `min_sum_pct` would be redundant.
- `"min_sum"` — sum of all dim values ≥ threshold. **Worst** of the three. Lets high-rel-low-qual posts through. Avoid.

### `sentiment_quota` (CRITICAL)
This is the most consequential knob in the whole config. Without it, every report skews 80–95% positive (success-story bias). With `max_per_bucket_pct: 0.333` the output is exactly 1/3 positive, 1/3 negative, 1/3 neutral.

When to disable (`max_per_bucket_pct: 0`):
- You explicitly want a popularity-weighted picture ("how do people most often describe their first 30 days on CPAP?"). For health/efficacy questions you almost never want this.

When to set asymmetric (e.g. `pos_pct: 0.6, neg_pct: 0.4`):
- The sentiment dim's natural spread is narrow; pushing thresholds outward gives buckets more room to fill. Rare; default is fine.

When sentiment buckets won't fill:
- Reality. The topic genuinely has no negative reports (e.g. tongkat ali) or no positive ones (e.g. PVPS). Note in the report's "data distribution" section. The runaway-cap `max_scored_factor` will halt the run.

### `per_sub_max_pct: 0.30`
Caps any single subreddit (or any single source-group, e.g. one Erowid substance, one Brave domain) at 30% of the passed set. Without this, r/Mounjaro alone fills most of an Ozempic report.

- **Multi-source studies**: leave at 0.30 — it caps both per-subreddit AND per-source-group, which is what you want.
- **Single-Erowid-substance studies**: SET TO 1.0. Otherwise all records share the same `subreddit="erowid:<substance>"` and you're capped at 30% of `target_n`, which makes target_n unreachable. Empirically demonstrated in `eval/erowid_experiments_2026-05-08.md`: with `per_sub_max_pct=0.30` every Erowid filter strategy capped at exactly 18/60 regardless of supply.
- **Single-domain Brave studies** (rare): same — set to 1.0 if all results came from one domain.

Loosen to 0.40 if the topic genuinely lives in one sub (very narrow).

### `per_category_quota_pct: 0.20`
Caps any single category at 20% of the passed set. With 6–8 categories this prevents one bucket from dominating. Tighten to 0.15 if you want very even category coverage.

### `per_category_min_pct`
Set to e.g. `0.10` if you want the run to keep scoring until every category has at least 10% of target_n. Useful when you want guaranteed coverage of niche treatment paths. Costs more (more candidates scored). Default `0.0` (no floor).

### `max_scored_factor: 40.0`
Hard runaway cap = round(target_n × factor). At target_n=60 → 2400 candidates max. Empirically catches bucket-saturation cases without paying for excessive scoring. Drop to 20 for fast iteration, raise to 80 for niche-bucket coverage.

### `order: "random"` + `seed: 1`
Random sampling avoids the popularity bias of `score_desc` (which biases toward older / more upvoted posts). Use `random` unless the question is itself "what does the community most-upvote about this." Set `seed` for reproducibility.

### `categories`: closed list
Always pass a closed list of 6–10 entries. Without it the LLM invents 30–80 unique category labels per report (measured: mean 61 categories for one ozempic baseline). Recommended structure:
- 3–5 topic-specific positive categories (specific outcomes / treatment paths)
- 1 category for `"no_effect"` (or `"didn't work"`)
- 1 category for `"side_effects"` (or `"adverse"`)
- 1 catch-all `"other"`

### `topic_keywords`
Optional pre-LLM substring filter. Posts that don't contain any of these strings are dropped before scoring. Use ONLY when:
- The grep patterns are necessarily broad (e.g. `"weight loss"`)
- AND the topic name is itself a unique-ish substring (e.g. `["ozempic","wegovy","mounjaro","semaglutide","tirzepatide"]`)

Don't use if the topic is naturally expressed across many vocabularies — you'll throw out relevant posts.

## High-stakes thresholds — caveat

The earlier recommendation of `rel.min_pct: 0.8, qual.min_pct: 0.7, min_sum_pct: 0.53` for "high-stakes" studies underperformed default thresholds in the 2026-05-07 10-topic comparison: more `W1_underfilled` weaknesses, no detectable quality improvement. **Don't use stricter thresholds without also reducing target_n** — the math is that strict thresholds cut the pass rate, so the same target_n stays unfilled. If you want the rigor of stricter thresholds, halve target_n at the same time. For most studies, default thresholds are fine.

## Robustness recipe — DELETED (do not reintroduce)

The old "run scoring twice with two models and take the intersection" recipe is **removed**. A
same-config re-run already churns ~⅓ of records while the *aggregate* report is identical, and a
second (weaker) model is systematically more pessimistic — so a 2-model intersection adds cost and
noise, not confidence, and changed no conclusion in live reports. Honest uncertainty is the Wilson
CI on the sampled rate (`/rate`), not a second run.

## Sentiment-quota math (don't break this)

`max_per_bucket_pct × N_sentiment_buckets ≥ 1.0` must hold. The default `0.333` × 3 buckets = 0.999, which exactly matches `target_n`. Lowering `max_per_bucket_pct` below 1/N_buckets makes `target_n` structurally unreachable and produces W1 underfill flags by construction. If you want more sentiment-balanced reports than the default, reduce `target_n` instead of lowering the bucket cap.

## Source-selection cheat sheet

```
TOPIC SHAPE                                  → SOURCES
══════════════════════════════════════════════════════════════════════
Default (almost everything)                  → reddit_posts
                                              + reddit_comments(direct)

Topic mentions psychoactive substance        → above
                                              + erowid

Rich subs (>100k subscribers, deep threads)  → upgrade comments_strategy
                                                 from "direct" → "post_anchored"

Topic medical/clinical, weak Reddit          → above
                                              + brave (only if needed)

User explicitly asked for web search         → add brave

Post-scan: pre-cap supply < target_n × 1.5   → add brave as fallback
```

The agent picks before scanning when possible. If the diagnostic shows thin
supply, run brave as a second scan and merge — don't redo the whole thing.

## Source recipes — copy-pasteable bodies

Each block goes inside `sources: [...]` of the `POST /scans` body.
Full body wrappers at the end.

### Reddit — universal default (C4)

```jsonc
[
  {"kind": "reddit_posts",
   "subs": ["sub1", "sub2"],
   "grep_patterns": ["term1", "term2", "..."],
   "min_text_len": 150, "min_score": 3,
   "include_monthly": true, "include_torrent": true},
  {"kind": "reddit_comments", "comments_strategy": "direct",
   "subs": ["sub1", "sub2"],
   "grep_patterns": ["term1", "term2", "..."],
   "min_text_len": 150, "min_score": 2,
   "include_monthly": true, "include_torrent": true}
]
```

Cost: free (local archive). Time: 5-30s.

### Reddit — rich-topic upgrade (C5, opt-in)

Only when subs > 100k subscribers AND grep is specific.

```jsonc
[
  {"kind": "reddit_posts",
   "subs": ["sub1"], "grep_patterns": ["..."],
   "min_text_len": 150, "min_score": 3,
   "include_monthly": true, "include_torrent": true},
  {"kind": "reddit_comments", "comments_strategy": "post_anchored",
   "subs": ["sub1"], "grep_patterns": ["..."],
   "min_text_len": 150, "min_score": 2,
   "pass2_max_candidates": 50000,
   "include_monthly": true, "include_torrent": true}
]
```

Time: 60-180s (post_anchored runs the scanner twice on huge sub comment files).

### Erowid — substance + phenomenon (e.g. "MDMA for relationships")

```jsonc
{"kind": "erowid",
 "strategy": "metadata_grep",
 "substances": ["mdma"],
 "grep_patterns": ["relationship", "partner", "intimacy", "connection"],
 "min_text_len": 400,
 "max_emit": 200}
```

Cost: free. Time: <2s. Score cost: ~$0.011 at target_n=60.

### Erowid — substance-centric, demographic-targeted

```jsonc
{"kind": "erowid",
 "strategy": "metadata_only",
 "substances": ["psilocybin"],
 "age_min": 25, "age_max": 45,
 "genders": ["female"],
 "year_min": 2010,
 "min_text_len": 400,
 "max_emit": 200}
```

Cost: free. Time: <2s. Score cost: ~$0.014 at target_n=60.

### Erowid — substance-centric, broad recall

```jsonc
{"kind": "erowid",
 "strategy": "metadata_only",
 "substances": ["psilocybin"],
 "min_text_len": 400,
 "max_emit": 600}
```

Cost: free. Score cost: ~$0.07 at target_n=60. Use when you can't narrow further.

**For ALL erowid-only scans, in the score body, set `per_sub_max_pct: 1.0`** —
otherwise you'll cap at 30% of target_n because all records share the same source-group.

### Brave — universal default (S5)

```jsonc
{"kind": "brave",
 "queries": [
   "<topic> personal experience",
   "<topic> my story",
   "<topic> reviews",
   "<topic> side effects",
   "<topic> forum"
 ],
 "max_results_per_query": 10,
 "max_total": 30,
 "min_text_len": 400,
 "freshness": "year",
 "domains_deny": ["reddit.com","quora.com","youtube.com","twitter.com","x.com","facebook.com","instagram.com","tiktok.com"],
 "fetch_workers": 8,
 "query_delay_ms": 1100}
```

Cost: $0.025 Brave + ~$0.002 LLM = $0.027/run. Time: 60-90s.

### Brave — minimal cheap probe

If you just want to see if web has anything for the topic:

```jsonc
{"kind": "brave",
 "queries": ["<topic> experience"],
 "max_results_per_query": 20,
 "max_total": 20,
 "min_text_len": 400,
 "domains_deny": ["reddit.com","quora.com","youtube.com","twitter.com","x.com","facebook.com","instagram.com","tiktok.com"]}
```

Cost: $0.005. Time: 20-30s.

### Multi-source: full body wrapper

```jsonc
{
  "sources": [
    /* one or more recipes from above */
  ],
  "max_candidates": 8000
}
```

`max_candidates` is the cross-source emission cap.

## Per-source recommendations

### Reddit (submissions vs comments)

Default: combine `reddit_posts` + `reddit_comments(direct)` with the same subs and grep patterns. Empirically validated across 2 topics × 10 strategies in `eval/comments_experiments_2026-05-08.md`.

- **`reddit_posts` only**: solid baseline, captures the topic narrative. Works alone when the corpus has long detailed self-narratives.
- **`reddit_comments`, strategy=`direct`** (recommended pair): applies grep to comments directly. Catches comments that explicitly mention the topic, complementing the submissions stream. Cheap, fast, robust across topic densities.
- **`reddit_comments`, strategy=`post_anchored`**: two-pass. Pass 1 finds matching submissions; pass 2 keeps any comment whose `link_id` ∈ matched-post set. Captures implicit-context replies (e.g. "yeah, exactly the same here at week 4" in a Lexapro thread). 3-5× more recall on rich topics — but COLLAPSES on thin topics where the matched-submission set is small (passed dropped from 54→40 on the ferritin experiment).
- **Recommended pair `submissions + direct_comments` (C4 in experiments)**: works in both regimes — rich and thin. The universal default.
- **Refinement: `submissions + post_anchored_comments` (C5)**: use ONLY when (a) chosen subs include large active communities (subs > 100k subscribers) AND (b) the grep is specific enough that pass-1 matches thousands of submissions. On rich topics this gives the best sentiment-balance (sent_ease 4.4 vs 3.5 for C4). Don't default to it; opt in.

### Erowid (per-source-cap quirk)

CRITICAL: when `erowid` is the only source, every record has the same `subreddit` field (e.g. `erowid:psilocybin`), so `per_sub_max_pct=0.30` caps the passed set at 30% of `target_n`. Set `per_sub_max_pct: 1.0` for single-Erowid-substance studies. See the note in §`per_sub_max_pct` above.

### Brave (web search)

Empirically tuned in `eval/brave_experiments_2026-05-08.md` (20 runs × 3
topics). The Pareto-optimal default is **5 persona-anchored queries with
`freshness=year`**:

```jsonc
{"kind": "brave",
 "queries": [
   "<topic> personal experience",
   "<topic> my story",
   "<topic> reviews",
   "<topic> side effects",
   "<topic> forum"
 ],
 "max_results_per_query": 10,
 "max_total": 30,
 "min_text_len": 400,
 "freshness": "year",
 "domains_deny": ["reddit.com","quora.com","youtube.com","twitter.com","x.com","facebook.com","instagram.com","tiktok.com"],
 "fetch_workers": 8,
 "query_delay_ms": 1100}
```

- $0.027/run total ($0.025 Brave + $0.002 LLM)
- 11-17 distinct domains in passed set
- 12-18 passed records average

**What to avoid:**
- **20-query breadth (S4)**: 4× the cost for FEWER distinct domains
  (diminishing-returns trap; later ranks repeat the same authoritative pages).
- **Demographic queries (S7)**: ("women experience", "in 30s") — only 3
  domains average in passed set. Apply demographic filtering at scoring
  time via the `audience` field, not at query time.
- **No deny list**: Reddit 403s the bot UA; YouTube/Twitter return
  SERP-clones. Always set the standard deny list.

**When NOT to use Brave at all:**
- Reddit + Erowid pre-cap supply ≥ `target_n × 1.5`. Web adds nothing.
- Topic is medical/clinical with weak personal-blog ecosystem (e.g. low
  ferritin, niche cancer protocols). Web returns paywalled studies + medical
  sites that aren't personal experience. Confirmed empirically: even our
  best Brave strategy hit only 5-8 passed for the ferritin topic.

## Cost summary

| Setup | Cost / study | Time |
|---|---|---|
| Default (gemini-flash-lite, target_n=60) | ~$0.08 | ~60s |
| Default (gemini-flash-lite, target_n=120) | ~$0.13 | ~80s |
| Default (gpt-4o-mini, target_n=60) | ~$0.16 | ~90s |
| Default (gpt-4o-mini, target_n=120) | ~$0.30 | ~120s |
| target_n=300 with default config (gemini) | ~$0.40 | ~300s |

## Breadth mode — discovery sweep + tally params

For "map the full menu" studies (see `AGENTS.md` → "Breadth mode").
Use **instead of** the filter-first `/scores` distillation when long-tail completeness matters.

**Discovery sweep (map-reduce over `candidates.ndjson`):**
- `chunk_size`: ~1000 posts/chunk; truncate each post to ~500 chars for the map stage.
- `map_model`: `gemini-2.5-flash-lite` or Haiku (cheap; cost is dominated by the full read).
- `passes`: **2** — run the map twice and union the discovered names (single pass under-samples
  the tail unpredictably: tail-recall 0.42 → 0.27 between runs). The union stabilises it.
- extraction prompt: "extract EVERY distinct treatment/approach, including ones mentioned once."
- Carry ALL names forward to synthesis; never let an LLM reduce silently drop the tail.

**Normalize discovered names before tally** (see `AGENTS.md` → Breadth mode step 2b):
split slash/paren spellings into one entry + aliases,
recover list-bucket members, drop bare class words (`SSRI`, `supplements`, `therapy`) and
ambiguous common-word aliases (`same`, `work`, `acid`), merge multi-word substring variants.
Tally aliases together so a treatment's count isn't split across spellings.

**Tally (popularity, server-side, deterministic):**
- `POST /tally {scan_id, treatments:[{name,aliases}]}` → `{corpus_n, counts:{name:{count,pos,neg}}}`
  (deployed; runs the Go Aho-Corasick `corpusmatch` server-side, ~3s/20k posts; no local install).
- popularity tier from count: head ≥1% of corpus, torso 0.1–1%, tail <0.1%.

**Effectiveness:** the same `/tally` returns a pos/neg lexical tally per treatment. For LLM-grade
sentiment, run a score job and call `POST /tally` with `sentiment:true` over its `scored.ndjson`
(aggregates each record's `sentiment_bucket`; ≥8 mentions → trust it, else use the lexical tally).

**Corpus sampling (scan-all → starvation-free sample for the LLM stages):**
- Scan every candidate sub fully into one pool (per-sub cap + merge); tally prevalence over that
  full pool. Then build the discovery/rating corpus with
  `scripts/breadth_sampling.balanced_breadth_sample` (strategy **S5**): per-sub floor + per-treatment
  floor (rarest first) + prevalence-faithful fill. Empirically beat random / stratified /
  per-sub-balanced by ~4.5× on rare-treatment coverage at equal-or-better prevalence fidelity over a
  5-topic benchmark. Defaults: `sub_floor≈80`, `per_treatment≈20`,
  target sample `n≈3000`. **Prevalence is read off the full pool, never the sample.**

**Rate-the-stories — ATTRIBUTION-FIRST + chain-of-thought (the 2026-06-05 model; supersedes plain
outcome-first).** Classify **every** mentioning post with a cheap model using **brief per-post
chain-of-thought**: first `skip` if it is not a first-hand result for THIS treatment (incidental /
list-only mention, question, recommendation-without-trying, someone-else, pure venting — usually the
majority), else `helped` / `noeffect` / `worse` (worse-before-better-net-positive = helped) **plus** a
magnitude size 1–5 (either direction). Derive per treatment: **Helped% / No-effect% / Worse%** (over
attributable posts), **Magnitude** (mean size + n), **Confidence** (`max(1,min(5,round(n/4)))` on the
attributable count), **Reports** = attributable count = prevalence numerator. Cap ~150/treatment,
disclose extrapolation; **≤3 treatments per CoT subagent** so it reads each.

- **Why CoT + attribution:** rating sentiment without attribution inflates Worse% (incidental
  mentions + "didn't work" + "hard/worse-before-better process" miscoded as harm). In a 10-method
  bake-off against a strong-model gold, the plain 1–5 baseline scored acc 0.61 / worse-F1 0.20 with
  8% false-worse; the **CoT attribution** method scored **acc 0.88–0.91, self-agreement 0.90,
  false-worse ~0–1.7%** at a cheap-model cost. A cheap classification model is at the task ceiling,
  so rating runs server-side (`POST /rate`); paying a frontier model to rate is wasted spend.
- **Synthesis:** sort groups by **expected improvement = Helped% × Magnitude × min(1, Confidence/3)**
  (NOT harm-aware — do **not** subtract Worse% from the rank; show harms as a per-option **risk note** /
  ⚠ flag instead, so high-ceiling options still surface with the risk stated).
  Then **consolidate into ~20–30 groups (G2)** (`grouping.py`).

*(Legacy outcome-first / mention-count models still work for a quick pass but understate Worse%
quality; prefer attribution-first CoT.)*

**Cost/time:** discovery ≈ a full-corpus read on a cheap model (~$2–3/topic at 20k × 2 passes);
tally is ~free (Go, seconds); synthesis is one strong-model pass. Benchmarked outcome: coverage
0.74 / tail-recall 0.39 / effectiveness-accuracy 0.66, vs filter-first 0.48 / 0.07 / 0.53
(`exp_ctx_overflow_2026-06-02/RESULTS.md`).

> Note: `per_sub_max_pct`, `sentiment_quota`, `target_n` and the rest of this doc apply to the
> filter-first `/scores` path. Breadth mode does **not** distill to `target_n`; it keeps the full
> discovered set and attaches computed stats to each.

## Rate-the-stories — five facets + Evidence (2026-06 generalized)

The attribution-first CoT pass now emits, per attributable post: **direction** (helped/noeffect/worse), **sub-problem** helped (the reader's facet; credit indirect-mechanism with a flag), **magnitude** 1–5, **harm type** (acute vs lasting) for worse posts, and **durability** (sustained vs fades) for helped posts. Aggregate to % of rated.

**Model & coverage (the cost defaults):**
- **Rate server-side via `POST /rate`** (a cheap classification model + CoT attribution). Rating is
  a bounded classification task at which a cheap model is already at the quality ceiling, so paying a
  frontier model to rate is wasted spend. Discovery likewise runs server-side (`POST /discover`).
- **Sample to a STORY TARGET, not a fixed count.** Prevalence (the count) = the exhaustive `tally`
  (free). The rate + splits are **proportions** → sample posts/treatment until **~30–50 attributable
  first-hand stories** (census treatments with fewer mentions); report **% ± Wilson CI** (half-width
  tracks the number of stories, not corpus size). **Options with <10 attributable stories are shown
  but not ranked and get no precise %** ("too few stories to rate"). **Disclose the sample** ("rated
  50 of ~180 attributable") — never imply a census. Rating is ~cents/topic, so depth is near-free;
  the real cost is discovery + writing, not sample size.
- **Evidence** (replaces saturated Confidence): un-saturated volume bands ●●●●● ≥80 / ●●●●○ 40–79 / ●●●○○ 20–39 / ●●○○○ 10–19 / ●○○○○ <10, plus a **⚖️ contested** flag (worse ≥ ½·helped). Base the dot on the number actually rated, not the tally.
- **Uncertainty:** show **Helped% ± Wilson CI** standard whenever sampling (it's the honest readout of the sample size). Cross-model agreement (re-rate a sample with a 2nd model; large per-option |Δ| = low reliability) is a High-mode add-on. Always pair with the "Evidence ≠ proof" caveat (no controls → no causal claim; self-selected sample → representativeness unknown).
- Ranking stays upside-only (`Helped% × Magnitude × Evidence-weight`); harms shown as a risk note, never subtracted.
