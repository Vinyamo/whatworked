# WhatWorked — Life-course studies (study type B: series of posts by the same people)

Read this instead of AGENTS.md Phases 2–6 when the user picked **study type B** (AGENTS.md PHASE 1).
Phases 0, 0B, 1, 8 and 9 of AGENTS.md still apply. The report format is `formats/life-course.md`.

## What it answers and what it can't

**Question shape:** *"What happens to people's lives in the 1–3 years after X?"* X is an event,
decision or treatment that people post about first-hand, for example: losing a partner, a diagnosis,
starting a medication, quitting drinking, a breakup, having a baby, moving abroad, retiring, or a
first psychedelic trip.

**How:** find people who wrote a first-hand, datable post about X ("the anchor"). Read their
*other* posts (anywhere on Reddit, not about X) from 3 → 1.5 years before X and from 1 → 3 years
after it. A rater sees both periods side by side, shuffled, undated and in random order, so it
cannot tell which came first. It scores each period 0–10 on seven dimensions: wellbeing, happiness,
life satisfaction, meaning, purpose, self-love and love for the world. **Change = after − before.**
The same is done for a **comparator group**: by default, people who just got a new dog. Getting a dog
is a mild, common, positive life change that people post about the same way. The result is
**X's change minus the comparator's change**, with a 95% CI.

**Use type A instead (the single-post study, AGENTS.md)** when the user wants to know which options
helped others with a problem, how people use them, or side effects. That is: what people *say*
worked. Type B measures how people's lives *actually went* afterwards, judged from what they wrote
about everything else. Type B is not a treatment ranking: run it for one X at a time, at most two or
three.

**Limits to tell the user up front:**
- Typical results are **small**: ±0.1–0.8 on the 0–10 scale. Many land at "no measurable difference
  from getting a dog".
- **Statistical power is limited.** Even a common event (thousands of first-hand posts) yields only
  about 50–300 people per group after all filters. The CI is then about ±0.3–0.7, so only moderate or
  large differences are detectable. For rarer events, expect only a descriptive answer.
- It is **observational**: people choose X, so this shows association, not cause.
- It only sees people who **keep posting** for years.
- Scores are **LLM-rated, text-expressed** states, not questionnaire scores.
- The funnel is steep. Of the people with a valid, dated anchor, ≈ 5–15% have ≥ 3 posts in both
  periods, and about a third of those pass the evidence gate. In tests, 10,000 valid quitters gave
  542 people with posts in both periods, and 1,300 bereaved partners gave 193. Rare events (lottery
  wins, rare surgeries) can't reach a usable n.
- It takes about **1–2 hours** of mostly waiting and costs about **$5–15** of the user's daily
  server budget.

## Method (fixed: never change it per study)

These settings are locked in `scripts/life_course.py`. They were validated against hand-rated
gold sets (rater agreement with a much stronger model, r ≈ 0.8–0.9) and a negative control: partner
death comes out negative (−0.35 to −0.5 vs dog owners at n ≈ 150), as in the literature. Changing
them breaks comparability with the comparator and with earlier studies.

| Step | What | Detail |
|---|---|---|
| 1. Anchor scan | `POST /cohorts`, scan only | Your regex over all subreddits (or a list), submissions, 2013 → mid-2024, fast storage |
| 2. Anchor check | `POST /cohort_labels` (cheap model) | Is the post first-hand (it happened to the poster)? `days_since`: how long before the post it happened |
| 3. Dating + groups | Local | t0 = post time − days_since. Strict dating keeps only events ≤ 60 days before the post. One anchor per person (the earliest). People who are in both groups are dropped |
| 4. History fetch | `POST /cohorts` with `anchors` | Each person's other posts in both windows; ~500 topic subreddits are hidden, plus subreddits where ≥ 2% of the anchors were posted |
| 5. Blind pair rating | `POST /cohort_labels` `targets:["pairs"]` | Rubric C, claude-haiku-4-5, both A/B orders. ≥ 3 and ≤ 25 posts per side, ≤ 3 per day, sides equalised. Posts with the event's or the comparator's announcement wording are hidden (`hide_regex`) |
| 6. Gate + analysis | Local | A person counts only if both orders found ≥ 3 own-state evidence posts per period. Bootstrap CI vs the comparator; also a start-score-matched comparison |

## Step by step

### B1. Scope the event (in Phase 1 intake)
Pin down X so that a person can say, in one post, that *it happened to me, about this long ago*:
- "My husband died", not "grief".
- "I started sertraline", not "antidepressants help".

If the user's X is a broad class ("therapy", "meditation"), pick the most posted, concrete form with
them ("started seeing a therapist"). Ask 0–2 questions, and only ones that change the scan. If X is
not something people announce first-hand, or the user is really asking "what helps with Y", switch
to type A and say why.

### B2. Write the spec: `<study>/work/lc_spec.json`
```jsonc
{
  "question": "How do people's lives change in the 1–3 years after their spouse or partner dies?",
  "event": {
    "label": "partner_died",                       // snake_case slug
    "regex": "\\bmy (late |beloved )?(husband|wife|partner|spouse) (just |suddenly )?(died|passed( away)?)\\b",
    "subs": ["*"],                                 // "*" = all ~4k archived subreddits (recommended)
    "definition": "the poster's own spouse or partner died",      // for the first-hand LLM check
    "topic_regex": "\\b(widow\\w*|died|passed away|death|late (husband|wife|partner)|grie(f|ving))\\b"
                                                   // broad X vocabulary, ONLY for the leakage check (B4)
    // "hide_regex": optional; default = the event regex (see below)
  },
  "comparator": "new_dog",                         // default; or {label, regex, definition, hide_regex}
  "extract_fields": {"who_died": "one of: husband, wife, partner, other"},   // optional subgroups (≤ 3)
  "settings": {"max_rated": 400, "budget_usd": 18} // optional; defaults in life_course.py DEFAULTS
}
```

**Regex rules.**
- RE2: no lookarounds, no backreferences. Matched case-insensitively on title + body.
- **First-person announcement phrasing**, with high recall: "I (just|finally) got diagnosed with",
  "I started (taking)? sertraline", "my (wife|husband) passed away".
- Not bare topic words: "sertraline" alone matches thousands of advice posts. The LLM check removes
  false positives, but each check costs money, and the scan and check get slow above ~50k posts.
- Test the regex mentally against 5 phrasings people really use, and against 5 that must not match
  (advice, someone else's story, hypotheticals).

**`hide_regex`** (optional) lists posts that are never shown to the rater, so it can't tell which
group a person is in.
- **The default is the event regex itself**, i.e. the announcement wording, and that is usually right.
- Widen it only with words that *name* X: drug or brand names, the procedure, the community's jargon.
- **Never hide outcome words** (grief, sober, happy, depressed, lonely…). They are the evidence being
  measured. In a test, a partner-death control with grief words hidden came out at 0 instead of
  clearly negative.
- The comparator's announcement wording is hidden too, and both lists apply to both groups.
- Topic subreddits are hidden automatically. Leakage is checked afterwards (B4).

**`extract_fields`** (optional, ≤ 3) adds subgroup splits such as role (mother/father), dose or
setting. Each gets reported against the comparator when it has n ≥ 30.
- Use only facts the **anchor post itself** usually states about the event: who died, which drug,
  planned or sudden.
- Don't use demographics (age, sex). Posts rarely state them, so nearly everyone lands in "unknown".

**`definition`** must name exactly what counts and what doesn't. Example: *"the poster stopped drinking
**alcohol**; not cannabis, caffeine or other substances"*. "Sober" and "quit" are ambiguous on
Reddit. After the check, spot-read about 20 valid anchors (`work/lc_check_event.ndjson` joined to
`work/lc_exposures_event.ndjson` by `uid`). If more than about 10% are the wrong event, tighten the
definition and regex, then `reset <study> check` (or `scan`).

**Comparator.** Keep `"new_dog"` unless the user's question is X *versus* a specific alternative,
for example "SSRIs vs therapy". Then define the alternative as the comparator with the same spec
shape.

Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/life_course.py validate <study>` to check the spec.

### B3. Confirm cost and time, then run
Tell the user: about 1–2 h, about $5–15 of their daily server budget. The script stops before
exceeding `budget_usd`, and the server's own daily quota also applies.

**The budget is the user's.** Set `budget_usd` to what they agreed. If the script stops at the budget,
lower `max_rated` (or `max_check_authors`) to fit. **Never raise `budget_usd` or `max_rated` above
what the user agreed without their explicit OK**, even when told "don't ask me anything". In that
case, stay within the budget and state the trade-off (wider CIs) in the report.

Costs, for planning: the anchor check is ≈ $0.05 per 1,000 anchor posts, and rating is ≈ $0.015 per
person. Rating 500 + 500 people ≈ $15.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/life_course.py next <study>   # advance one step (never blocks)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/life_course.py wait <study>   # advance + poll ≤ 8 min, then exit
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/life_course.py status <study>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/life_course.py reset <study> <scan|check|fetch|rate>   # redo from a step
```

**Never sit in a foreground loop.** Call `wait`, and when it exits with "still …", call it again. Or
run it in the background and check back. Re-running is always safe: finished steps are skipped,
running jobs are re-polled, and nothing is resubmitted. Rough times:
- anchor scans: 10–40 min (all subreddits);
- anchor check: 5–15 min;
- history fetch: 15–40 min;
- ratings: 10–30 min.

**Spot-checks while it runs (required):**
- After the scan, the script prints 5 sample anchor posts per group. If most are off-topic, stop.
  Fix the regex, then `life_course.py reset <study> scan` and rerun.
- After the check, read the `valid anchored people {…}` line:
  - `not_first_hand` ≫ `valid` means the regex catches advice posts. Tighten it.
  - `undated` ≫ `valid` is normal for long-ago events. Keep strict dating, never loosen
    `max_days_since` past 60: undated anchors erase even the partner-death effect.
- After the fetch: `people with ≥3 posts in both windows`. If either group is below about 100,
  expect wide CIs, and say so in the report.

### B4. Read the results: `work/lc_results.txt` and `work/lc_results.json`
For each dimension you get:
- n per group (after the evidence gate);
- **vs comparator** (the headline), plus `matched` (comparator re-weighted to the same starting
  scores, a sensitivity check);
- % better / % worse in each group;
- the starting levels.

**Interpretation rules:**
- **The headline is "vs comparator" with its CI.** A CI that includes 0 means "no measurable
  difference from people who got a dog". Report it like that, never as "no effect".
- **The plain and matched comparisons should agree in sign.** If they disagree, report both, and
  report the effect as uncertain.
- **Groups starting much lower than the comparator** (≥ 0.4 apart) partly regress upward toward
  ordinary life. Say so.
- **Fewer than 30 people** in a group or dimension: no estimate is printed. Describe it, don't rate it.
- **Leakage.** The rater lists each period's life events, and `topic_regex` (always set it) counts how
  often those name X. If the event group's after-period rate exceeds its before-period rate by ≥ 10
  percentage points, the rater partly *knew* which period was after X. Interpret it by type:
  - **Adverse events (loss, diagnosis):** mentions of X *are* the outcome (grief posts). Expected; report
    the rate.
  - **Choices and interventions (quitting, a drug, a practice):** mentions can inflate the result,
    because people write about the thing they're proud of. Widen `hide_regex` with words that *name*
    X, never outcome words. Then `life_course.py reset <study> rate` and `wait` to re-rate (the fetch
    is kept). If you can't, flag the result as possibly topic-inflated.
- **Small effects are the norm.** On this 0–10 scale, ±0.3 is a noticeable shift for a group
  average. Partner death, the method's negative control, measured −0.35 to −0.5 vs dog owners (n ≈ 150)
  with exactly these windows, because the reference period often already holds the partner's illness
  or caregiving. So a CI of ±0.6 (n ≈ 50) cannot detect even a loss: say so.
- **Read 10–20 real rated people** before writing (`work/lc_pairs_event.ndjson`: `reason`,
  `events_before` / `events_after`). Use them for illustrative, anonymised arcs, never usernames.
  The posts themselves are on the server: `GET /jobs/<fetch_id>/history?author=…`.
  Quote at most a short phrase, and never identify a person.

### B5. Write (AGENTS.md Phase 7 rules adapted, format `formats/life-course.md`)
Every number carries n and a CI. Name the measure honestly: "LLM-rated, text-expressed wellbeing",
not a questionnaire. Add one science note: what the literature says about X and wellbeing over
1–3 years, verified this run or marked `[unverified]`. Then deliver (Phase 8: PDF, folder hygiene,
open it) and close out (Phase 9).

## Quick reference: when something goes wrong

| Symptom | Fix |
|---|---|
| Scan finds < 300 anchor posts | Regex too narrow: add phrasings; keep `subs: ["*"]`; consider `"kinds": ["submission","comment"]` in `settings` (scan ≈ 4× slower) |
| Scan > 100k posts, samples mostly off-topic | Regex too broad (bare topic words): require first-person announcement phrasing |
| Few valid anchors, most `undated` | Expected for retrospective topics; widen the phrasing toward "just / today / last week" announcements |
| < 100 people qualify per group | Report descriptively, with wide CIs. Optionally raise `max_fetch` (free); never loosen the method |
| Budget stop | Tell the user the estimate; lower `max_rated` or get their OK to raise `budget_usd` |
| HTTP 429 quota | Today's server budget is used up: resume tomorrow with `next` (state is kept) |
| A job `failed`, or stays `running` for hours | Read the error (`status`). A server restart orphans running jobs: `life_course.py reset <study> <that step>`, then `next` |
| Changed the spec mid-run | `reset` to the earliest step the change affects: regex/subs → `scan`; definition/extract_fields → `check`; dating/date range → `check`; hide_regex/max_rated → `rate` |
