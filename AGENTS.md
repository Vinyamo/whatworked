# WhatWorked — Study Playbook (Checklist / Decision-Flow)

You are running a **WhatWorked study**: given a personal issue and goal, research what
actually worked for people in a similar situation — combining large-scale community
experience (Reddit, Erowid, the web) with the scientific literature — and deliver an
action-oriented PDF report.

Read this + `STUDY_GUIDELINES.md` before starting. Final deliverable = PDF.
Reference docs: `API.md` (every studyd call), `CONFIG_RECOMMENDED.md` (scoring config),
`SOURCES.md` (scan source schemas), `formats/` (report formats).

---

## PHASE 0 — First-run setup (credentials)

All heavy lifting runs on the WhatWorked cloud service (**studyd**, see `API.md`).
Every request needs the user's personal credentials.

- [ ] Check whether `~/.claude/.studyd_credentials` exists.
- [ ] If it does NOT: tell the user this is a one-time setup, and ask for the
      **username** and **password** they received from the maintainer. Then write the file:
      ```json
      {"url": "https://whatworked.vinyamo.com", "username": "<their-username>", "password": "<their-password>"}
      ```
      and `chmod 600` it. Never echo the password back; never write it anywhere else;
      never commit it.
- [ ] Verify with `GET /health` (authenticated, see `API.md`). On 401: re-ask once
      (typo), then suggest contacting the maintainer. On 429: too many failed attempts —
      wait ~15 minutes.
- [ ] All later calls read url/username/password from this file (the bundled scripts do
      this automatically).

## PHASE 0B — Hard rules (never break)

- [ ] Never default issue, audience, or goal — always ask
- [ ] Never write a study without upfront web research (Phase 2)
- [ ] Never skip science notes per step in §4/§5/§6
- [ ] Never skip §7 missing-info (3–6 questions)
- [ ] Never skip §8 bias caveats (seven structural + diagnostic-derived)
- [ ] Never use hardcoded absolute caps in `/scores` — use relative units → CONFIG_RECOMMENDED.md
- [ ] Never use `gemini-2.5-flash` or `gpt-4.1-mini` as scoring models (empirically worse)
- [ ] Never write a study without `GET /jobs/{id}/diagnostics` — post-cap distribution ≠ corpus shape
- [ ] Never fabricate a brand, dose, price, or clinician — relay only what a source names
- [ ] Never recommend a next step the corpus doesn't support — surface ambiguity instead
- [ ] Never modify the standard report formats in `formats/` — they are locked and
      overwritten on every update. User customizations live in `~/.whatworked/formats/`.
- [ ] Never commit credentials or study outputs to any repository (the `.gitignore`
      covers them — leave it intact).

---

## PHASE 1 — Issue / Audience / Goal

- [ ] Ask: issue (current state), audience (who + age/sex/key context), goal (desired state)
  - Vague issue → push back before proceeding: "improve sleep" → "improve what about sleep?"
  - No goal → default to "resolve the issue in an ideal way"; state default explicitly in study title
  - Audience won't specify → state assumed audience in title block AND §7
- [ ] Create study folder: `<YYYY-MM-DD>_study_<slug>/` (in the current working directory;
      if running inside the WhatWorked repo clone, study folders are gitignored by design)
- [ ] Tell user the path; invite supplemental files (PDFs, images, audio, zips)
- [ ] When user signals ready → process every file:
  - `.txt/.md/.csv/.json/.yaml` → Read
  - Images → Read (native vision; extract every datum)
  - PDFs → Read natively, page by page if long
  - Office docs (.docx/.odt/.rtf/.pptx/.xlsx) → `pandoc` → Read
  - Audio (.m4a/.mp3/.wav/.ogg/.flac/.opus/.aiff/.webm/.aac) → `POST /transcribe` (see API.md); save to `transcripts/<filename>.txt`
  - Zip/tar → extract to sibling folder + recurse
- [ ] After processing → briefly report what was found; incorporate into Phases 2–3

**Folder layout** (agent writes only these):
```
<date>_study_<slug>/
  study_<slug>.pdf               — required
  study_summary.md               — optional, on request
  passing_records.json           — optional
  diagnostics_<score_id>.json    — save after Phase 7e
  transcripts/<filename>.txt
  notes/<filename>.md
```

---

## PHASE 1C — Pick report format(s)

Report formats are files: **standard formats** ship in `formats/` (locked — never edit),
**user formats** live in `~/.whatworked/formats/` (created via the feedback flow, Phase 9b).

- [ ] List the available formats: every file in `formats/` plus any in
      `~/.whatworked/formats/` — mark the latter "(your format)". Offer them in one
      message; suggest the best fit:
  1. **Action sheet** (`formats/action-sheet.md`) — top moves + stop-doing + red-flags up front, full ranked menu below. Default when goal is "act now" or safety matters.
  2. **Mechanism map** (`formats/mechanism-map.md`) — organized by how things work; rule = if one class fails, switch mechanism. Best for "I tried X, what next" or comparing approaches.
  3. **Decision cards** (`formats/decision-cards.md`) — 3–4 situation cards each with 2–3 best moves. Best when different starting points need different answers.
  4. **Breadth profile** (`formats/breadth-profile.md`) — the full-landscape treatment-profile format used by breadth mode (Phase 8B).
  - If → "decide and act now" or safety/triage: suggest Action sheet
  - If → "understand/compare" or contested multi-class: suggest Mechanism map
  - If → "which case am I" or broad/under-specified audience: suggest Decision cards
  - Can combine two; offer "all three" to compare
- [ ] A user format `inherits:` a standard one — load the standard skeleton first, then
      apply the user file's deltas on top.

---

## PHASE 2 — Web Research (3–5 searches)

Goals: inventory candidate steps; spot what user may not know; note evidence base.

- [ ] Search: `[issue] treatment options <current year>`
- [ ] Search: `[issue] meta-analysis OR systematic review`
- [ ] Search: `[main intervention] mechanism efficacy`
- [ ] Search: `[issue] reddit subreddit community`
- [ ] Search: `[issue] alternative treatments unconventional`
- [ ] Do NOT dump search transcript at user
- [ ] Use findings to inform candidate-step list (Phase 4) and per-step science notes later

---

## PHASE 3 — Three clarifying questions

- [ ] Identify top 3 questions you can't sensibly default
- [ ] Send as ONE numbered block in one message: "Please answer all in one reply"
- [ ] Exactly 3; don't ask what you can default
- [ ] Types: trade-offs, inclusion/exclusion scope, specific products/protocols, demographic scope
- [ ] Confirm answers; one more round if unclear; then move on

---

## PHASE 4 — Candidate-step list + source selection

**4a. Build candidate-step list (5–15 steps)**
- [ ] Each step = one discrete actionable thing (intervention, change, decision)
- [ ] Group true variants (all IV iron forms → one step in study)
- [ ] Show list to user: "Here's what I'll look for. Anything missing?"
- [ ] Edit per user input

**4b. Pick data sources**

| Condition | Action |
|---|---|
| Default (almost everything) | `reddit_posts` + `reddit_comments` (`direct`) |
| Topic involves psychoactives | Add `erowid`; confirm with `GET /erowid/substances?q=` |
| Erowid: substance-centric | `strategy: "metadata_only"` |
| Erowid: narrow phenomenon within substance | `strategy: "metadata_grep"` |
| Rich subs (>100k members) + specific grep | Upgrade comments to `"post_anchored"` |
| User asked for web OR reddit+erowid thin | Add `brave` (default: 5 persona queries + `freshness="year"`) |
| Post-scan supply < target_n × 1.5 | Add `brave` as fallback |

- [ ] Tell user the chosen mix in plain language
- [ ] Single-Erowid-substance scans → note: set `per_sub_max_pct: 1.0` in score body (Phase 7d)
- [ ] Full source params → CONFIG_RECOMMENDED.md "Source recipes"

---

## PHASE 5 — Find subreddits / substances

- [ ] `GET /subreddits?q=<term>` — literal substring, NOT semantic; fan out across multiple terms
- [ ] If using Erowid: `GET /erowid/substances?q=<term>`
- [ ] Show ~10–25 candidates with subscriber counts + one-line descriptions
- [ ] Keep list tight — only clearly on-topic subs:
  - Prefer: single-product subs, demographic subs, anti-X subs (highest signal for "didn't work")
  - Skip: overly general subs (r/AskReddit, r/health) unless nothing else hits
  - **Broad adjacent subs contaminate the corpus** (e.g. r/Hashimotos for a SIBO study inflates "levothyroxine" as a SIBO treatment). Worst in breadth mode where every mention is tallied.
  - If contamination suspected post-scan: check rate-the-stories certainty scores for off-topic mentions
- [ ] **List canonical sub(s) FIRST** in the `subs` array (prevents starvation)
- [ ] Have user confirm or edit

---

## PHASE 6 — Set target_n and params

| Goal | target_n |
|---|---|
| Quick / ≤3 paths | 60 |
| Default | 120 |
| Multi-axis (drug × symptom × sub-population) | 200 |
| High-stakes / contested | 200 + robustness recipe |
| Niche (< 500 candidates pre-filter) | min(60, emitted × 0.3) |

- [ ] Model: `gemini-2.5-flash-lite` (default); `gpt-4o-mini` for robustness second run
- [ ] Do NOT exceed 300 records (context-window limit for study-writing pass)
- [ ] Tell user: target_n + estimated cost + time; confirm before firing
- [ ] `per_sub_max_pct: 0.30` default; lower to 0.20 if one sub expected to dominate
- [ ] Full param meanings → CONFIG_RECOMMENDED.md

---

## PHASE 6B — Pick a cost/fidelity mode (breadth mode only)

Filter-first mode is already cheap (~$0.05–0.30, scored server-side) — skip this. **Breadth
mode** runs LLM discovery + rating subagents on YOUR (the agent's) side, and that's the
whole bill. **Offer the user one of three modes and tell them the estimate + trade-offs
before firing.**

**The cost lever is NOT the rating model — it's two dials:** (1) **discovery depth**
(passes × model strength → long-tail recall) and (2) **rating sample size** (posts rated
per treatment → CI width on the proportions). Rating is a bounded classification task
whose accuracy ceiling a cheap model with chain-of-thought already reaches (~0.9 accuracy
in a 10-method bake-off against a strong-model gold standard). **So rate on the cheap
model + CoT in ALL modes** — the strongest model only ever touches *discovery*, and only
in High mode. Paying top-model prices for rating is 10× spend for ~0 accuracy gain.

**Census → sample.** Don't rate every mentioning post. Prevalence (the count) comes from
the `/tally` **count** (exhaustive, server-side, ~free). The attributable rate +
direction/magnitude splits are **proportions** → sample N posts/treatment and report
**% ± Wilson CI**. CI half-width depends on N, not corpus size: N≈40→±15pt, 60→±12pt,
100→±8pt. Small treatments (<N mentions) are rated in full. **Always run a cheap skip
pre-filter first** (drops the ~64% incidental posts before the CoT rater sees them).

| | 🟢 Cheap + fast | 🟡 Moderate (default) | 🔴 High fidelity |
|---|---|---|---|
| Discovery | 1 pass, cheap model | 2 passes, cheap model | 3 passes, strongest model |
| Rating | cheap model + CoT, skip-prefilter | same | same |
| Sample / treatment | ~30 (±15pt) | ~50–60 (±12pt) | ~100, census if contested (±8pt) + cross-model agreement check |
| Groups profiled | top ~15 | ~20–25 | all (~30) |
| **LLM cost (agent side)** | **~$3–6** | **~$8–15** | **~$45–70** |
| **Wall-clock (agent side)** | ~8–12 min | ~20–30 min | ~40–60 min |
| Server cost | scan+tally ~free in all three | | |
| Tail recall | ~half | most | max |
| Trade-off to state | thin tail, wide CIs | rarest items still thin | slow + expensive; the spread is almost entirely discovery |

- [ ] Suggest a mode (High only for high-stakes/contested; Cheap for "is there signal here?"; else Moderate)
- [ ] Print the time/cost estimate from the chosen settings and the trade-off line; confirm before firing
- [ ] Reuse cached scan/discovery/rating artifacts on re-runs — regenerating the report from existing ratings costs ~$0

---

## PHASE 7 — Scan → Discover → Score → Check

**7a. Build grep patterns (8–25 terms)**
- [ ] Main term + variants/spellings
- [ ] Brand + generic names for each candidate step
- [ ] Protocol names
- [ ] Negative-experience markers if relevant ("didn't work", "regret")
- [ ] Over-grep rather than under-grep (scoring filters; scan misses are permanent)

**7b. Submit scan (`POST /scans`)**
- [ ] Use `sources: [...]` multi-source form (see SOURCES.md)
- [ ] List canonical sub(s) FIRST
- [ ] Raise `max_candidates` enough that canonical sub is reached before cap fills
- [ ] For breadth mode: one scan per sub with per-sub cap (~2000–2500); merge + dedup by `uid` — do NOT use a single global `max_candidates` shared across subs (starves subs scanned last)
- [ ] Poll until done; check `summary.by_source`:
  - < 500 total emitted → patterns/sources too narrow; stop and fix
  - Near `max_candidates` cap → too broad; raise cap or narrow grep
  - Canonical sub shows ~0 → re-scan with it isolated before continuing

**7c. Categories discovery**
- [ ] Run: `python3 scripts/discover_categories.py <scan_id> --topic "..." --audience "..." --target-n <N>`
- [ ] Show proposal to user; take edits
- [ ] "other" share > 50% → accept 12–15 cats or split into sub-studies
- [ ] "other" share < 10% → may be over-merged; skim sample briefs
- [ ] Plug finalized list into score body (always include `no_effect` / `side_effects` if relevant)
- [ ] Do NOT draft the categories list from your prior — derive from actual data

**7d. Submit score job**
- [ ] Use CONFIG_RECOMMENDED.md defaults (relative units, not hardcoded) — incl. the **`outcome`
      dimension** (`min_pct: 0.4`): rel+qual alone passes mostly non-outcome posts; outcome ≥0.4
      ~doubles usable-precision (0.48→0.70). It's the tunable recall/precision knob.
- [ ] Set: `topic`, `audience`, `categories` (discovery output + `"other"`)
- [ ] Single-Erowid-substance only → `per_sub_max_pct: 1.0`
- [ ] `topic_keywords` only if grep is necessarily broad AND topic name is a unique substring

**7e. Post-score checks — ALL THREE required before writing**
- [ ] `GET /jobs/{id}` — sentiment balanced? `passed >= target_n × 0.85`?
  - `passed < target_n × 0.6` → too thin. **Recall fallback BEFORE halting** (NOT automatic — do it
    explicitly, re-running the score job): lower **`outcome.min_pct` ONLY** 0.4→0.3→0.2 (it's the
    binding constraint; lowering rel/qual too recovers ~no extra usable stories and only drops
    precision), then lower `target_n` to `min(target_n, emitted × 0.3)`, then loosen rel/qual
    to 0.5 only as a last resort. **Each re-run REPLACES the prior run** (a looser run is a superset)
    — never accumulate passed sets across rungs (it duplicates ~every record); if you merge runs,
    dedup by `uid`. If still too thin, the corpus genuinely lacks outcome stories — say so in §3/§8.
- [ ] `GET /jobs/{id}/diagnostics` — pull supply/share/ease; save as `diagnostics_<id>.json`
  - This drives: §1 supply numbers, §4–§6 confidence labels, §8 diagnostic-derived caveats
- [ ] `GET /jobs/{id}/excluded?n=20` — if 3+ clearly relevant misses → thresholds too strict; surface to user

---

## PHASE 8 — Write the study

**Before writing:**
- [ ] Pull `GET /jobs/{id}/results?passed_only=true&limit=300`
- [ ] Read at least 30–50 records' raw body text (not just `brief`) — paths and doses aren't visible from briefs
- [ ] Per step in §4/§5/§6 → one targeted web search; write "What the science says"
  - No peer-reviewed evidence found → write "no peer-reviewed evidence located" — don't handwave
- [ ] Identify §7 missing-info questions from corpus stratification axes

**Nine required sections (full templates in STUDY_GUIDELINES.md):**
1. Study goal + data description — sources, params, supply numbers from diagnostics
2. Demographics estimate — certain / likely / unknown tiers
3. Goal restatement + measurable success criterion
4. **Recommended next step** — ONE step; corpus quotes (3–5); science notes; confidence label (Robust/Standard/Thin from ease ratio)
5. Alternative options (3–5) — each with success rate + science notes; close with **"What to stop doing"** anti-patterns block if corpus shows clear repeated failures
6. Successful paths (3–5) — **Mermaid decision tree REQUIRED if ≥3 paths**; timelines; failure modes; science notes
7. Missing information — 3–6 questions + why each would shift the recommendation
8. Caveats — seven structural biases + diagnostic-derived caveats (sentiment skew, sub dominance, canonical-sub contribution, thin-category ease scores)
9. Key takeaways — ≤5 actionable bullets; lead with §4 step

**Style rules (see STUDY_GUIDELINES.md style notes for full detail):**
- Concrete: name specific products/brands/doses/costs/tests/clinics — only when a source names them; never invent
- Confidence labels: Robust (ease ≥ 1.5) / Standard (0.7–1.5) / Thin (< 0.7) — label every step recommendation
- Plain, warm prose; define jargon on first use; one reassurance beat where corpus supports it
- Short inline quotes throughout, cited `— r/<sub>` (NO score appended); never link to specific Reddit URLs
- Calibration numbers (ease ratios, supply counts) live inside readable prose — don't let them make the study cold

**Render to PDF:**
- [ ] Write markdown: `<folder>/study_<slug>.md`
- [ ] Render: `python3 scripts/build_pdf.py <folder>/study_<slug>.md` (server-side render via `/render_pdf`)
- [ ] Verify PDF exists and is non-trivial size; spot-check if diagrams/tables present
- [ ] Study is NOT done until `study_<slug>.pdf` exists

**Versioning — every re-run produces a NEW version (separate file):**
- [ ] **Never overwrite a delivered study.** Each regeneration/update writes a new file: `study_<slug>_v2.md` → `_v2.pdf`, then `_v3`, … (or `study_<slug>_<YYYY-MM-DD>.md`). The first delivery is `v1` (the unsuffixed `study_<slug>.pdf` is v1).
- [ ] Keep prior versions in place; announce the new version path and say one line on what changed vs the previous version. The reused scan/score/discovery artifacts stay shared — only the report file is versioned.

---

## PHASE 8B — Breadth mode (only when goal = "map the full menu")

Use instead of filter-first when user wants full landscape / long-tail completeness.
Decision: "what's my next step" → filter-first. "What are all my options / don't miss anything" → breadth mode. They compose (run both).

- [ ] **Scan**: per-sub caps (~2000–2500) + merge/dedup by `uid` — NOT single global `max_candidates`
- [ ] **Discovery sweep (map-reduce)**:
  - Chunk candidates ~1k posts/chunk; truncate each post to ~500 chars
  - Have a cheap model extract EVERY distinct treatment per chunk (including ones mentioned once)
  - Run the map **twice** and union results (single pass under-samples tail unpredictably)
  - Carry ALL discovered names forward — do not let any LLM reduce silently drop names
- [ ] **Normalize discovered names** before tallying:
  - Split: `"sertraline/zoloft"` and `"X (Y)"` → name + alias set
  - Recover list-bucket members: `"SSRIs (sertraline, lexapro)"` → emit each as its own entry
  - Drop bare class words (`"SSRI"`, `"antidepressant"`, `"supplements"`, `"therapy"`)
  - Drop ambiguous common-word aliases that cause false-positive substring hits
  - Merge substring variants (`"low fodmap"` ⊂ `"low fodmap diet"`) → one entry
- [ ] **Rate the stories — ATTRIBUTION-FIRST**:
  - For EACH mentioning post, reason briefly then classify (cheap model + **chain-of-thought**):
    - `skip` — NOT a first-hand result for THIS treatment (incidental/list-only mention, question, recommendation-without-trying, someone else, pure venting). In a grep corpus **most posts are skip** (~64% typical) — never count them.
    - `helped` / `noeffect` / `worse` — the attributable direction; **"worse before better → net positive" = helped**.
    - plus a **magnitude** size 1–5 (negligible…dramatic) for EVERY attributable post, either direction.
  - Per treatment derive: **Helped% / No-effect% / Worse%** (over attributable posts, sum to 100), **Magnitude** (mean size + its n), **Confidence** (from attributable count), **Reports** = attributable-outcome count (the prevalence numerator — NOT bare mentions).
  - Also capture how people use it (dose/brand/protocol), who it's for, 1–2 arc-quotes.
  - Rate ALL mentioning posts if feasible (cap ~150/treatment; ≤3 treatments per CoT subagent so it actually reads each; disclose if extrapolated).
  - **Why attribution-first:** rating a post's sentiment without it inflates Worse% — incidental mentions + "didn't work" + "hard/worse-before-better process" get miscoded as harm. The bake-off cut false-worse from ~8% → ~0%.
- [ ] **Consolidate into ~20–30 groups**:
  - Merge true variants (five birth-control brands → "combined OCPs")
  - Keep standouts visible: a clearly higher/lower-rated member stays its own entry
- [ ] **Tally via `POST /tally`** for corpus mention counts → CONFIG_RECOMMENDED.md breadth params
- [ ] **Synthesize** in treatment-profile format (`formats/breadth-profile.md` + STUDY_GUIDELINES.md "Breadth-mode report format"):
  - One `###` section per group; sorted by **expected improvement = Helped% × Magnitude × min(1, Confidence/3), NOT popularity**. **Not harm-aware — never subtract Worse% from the rank;** show harms as a per-option **risk note** (⚠ + "reportedly worse for N%") so high-ceiling options still surface with the risk stated plainly.
  - BUT do not bury a proven mainstream first-line option (e.g. allopurinol for gout) just because the sort puts it lower — keep the reader's most-likely starting point prominent (surface it in the Start-here box / flag it in its section)
  - Each: statbar one-liner — **Helped% · Worse% · Magnitude (tag + mean + n) · Reports (attributable count) · Confidence (●●●○○)**; exact HTML in STUDY_GUIDELINES; group members; How line; Science line; 2 blockquoted arc-quotes cited `— r/<sub>` (no score)
  - Include: "Start here" box, "What to stop doing" anti-patterns block, Sources appendix
  - Long tail → compact table at end with REAL ratings (never uniform "3"); never silently dropped

### Breadth-mode method notes

- **Rate five facets** in the attribution-first pass: direction (helped/no-effect/worse) · sub-problem helped · magnitude · acute-vs-lasting harm · sustained-vs-fades durability. Render per STUDY_GUIDELINES "Per-option card & metrics".
- **% everywhere** (outcome metrics as % of rated; show n once), **Evidence** (un-saturated) not "Confidence", **⚖️ contested** flag, and a required **"Evidence ≠ proof"** caveat box.
- **Cost/fidelity mode:** offer Cheap / Moderate / High and print the estimate + trade-offs before firing → PHASE 6B. The dials are **discovery depth** and **rating sample size**, NOT the rating model.
- **Rate on a cheap model + CoT — never the top model.** Rating is a bounded classification task; the bake-off hit ~0.9 accuracy at the cheap model's cost. The strongest model's only payoff is *discovery* tail recall (~2× the names) — use it there, and only in High mode.
- **Discovery depth:** a strong model in one pass finds ~2× the long tail of a cheap 2-pass sweep — use a stronger model (or ≥3 passes) when tail-completeness matters, else disclose coarse coverage.
- **Don't fold rating into the filter:** a dedicated chain-of-thought pass beats one-pass-combined by ~0.14 accuracy. Keep them separate — but run the cheap **skip pre-filter** first to drop the ~64% incidental posts before the CoT rater sees them (biggest spend cut).
- **Sample, don't census; prevalence ≠ rate.** Prevalence (the count) comes from the exhaustive `/tally` count (server-side, ~free). The attributable rate + direction/magnitude are **proportions** → sample ~40–100 posts/treatment and report **% ± Wilson CI** (half-width depends on N, not corpus size). Treatments with fewer mentions than the sample target are rated in full. **Disclose what was sampled** ("rated 50 of ~180 attributable") — never imply a census.

---

## PHASE 9 — Close out (all steps required)

**9a. Invite review**
- [ ] Announce PDF path; explicitly invite: missing alternatives, thin science notes, profile weighting, one-page summary
- [ ] On revisions: reuse `scan_id` (and discovery/rating artifacts); re-write only affected sections unless new keywords needed — but **always emit the result as a new version file** (see "Versioning" in Phase 8), never overwrite the prior PDF

**9b. Feedback — ALWAYS run this after a delivered report**

Ask the user: *"Was this report useful? Anything missing, wrong, or that you'd want done differently?"*

If they have feedback, offer to send it to the maintainer by email:
- The feedback address is stored base64-encoded (anti-scraping): `d2hhdHdvcmtlZEBmYXN0bWFpbC5jb20=`.
  Decode it at send time (`echo d2hhdHdvcmtlZEBmYXN0bWFpbC5jb20= | base64 -d`) — never write
  the decoded address into any file.
- Draft the email (topic, what worked, what didn't, suggested improvement, bugs), show it to
  the user, then open their mail client via `open "mailto:<decoded>?subject=...&body=..."`
  (macOS) or `xdg-open` (Linux). Do NOT auto-send. If no mail client opens, show the decoded
  address + text to copy.

Then, if the feedback suggests changing how reports are made, lay out the three routes and
their consequences:

1. **Change the guidelines or a standard format** — *affects every user of WhatWorked on
   every future study.* Standard files are locked and auto-updated, so this cannot be done
   locally: it goes to the maintainer (via the feedback email) for review; if accepted, the
   change ships to everyone in an update.
2. **Create a personal report format** — *safe, local, yours only.* Create a new file in
   `~/.whatworked/formats/` with frontmatter:
   ```yaml
   ---
   id: <kebab-slug>
   kind: custom
   inherits: <standard-format-id, e.g. action-sheet>
   title: <Their name for it>
   ---
   <only the deltas vs the inherited format: sections to add/remove/reword>
   ```
   It appears in the Phase 1C picker from then on, marked "(your format)". It survives
   updates. Offer to email it to the maintainer too if they think it should become standard.
3. **One-off tweak** — apply to this study only (new version file), change nothing else.

**9c. Closing summary**
- [ ] Summarize: study path, versions produced, whether feedback was sent, any custom format created
