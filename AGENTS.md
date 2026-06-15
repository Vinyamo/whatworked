# WhatWorked — Study Playbook (Lean-Adaptive pipeline)

You are running a **WhatWorked study**: given a personal issue and goal, research what
actually worked for people in a similar situation — combining large-scale community
experience (Reddit, Erowid, the web) with the scientific literature — and deliver an
action-oriented PDF report.

Read this + `STUDY_GUIDELINES.md` before starting. Final deliverable = PDF.
Reference docs: `API.md` (every studyd call), `CONFIG_RECOMMENDED.md` (params),
`SOURCES.md` (scan source schemas), `formats/` (report formats).

> **One adaptive pipeline, not a mode menu.** Depth is chosen by *measured supply*, not a
> user-picked fidelity mode. There is no Cheap/Moderate/High question, no fixed
> "ask-three-questions" ceremony, no separate upfront-web phase, no target_n / sample-size
> tiers, and no filter-first/breadth duality — each of those was shown to add cost, length, or
> error without adding value. The prevalence count is computed exhaustively; the rates are
> sampled with a confidence interval; the depth deepens itself once when the numbers are thin.

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

**Report methodology (each earned by a recorded failure):**
- [ ] Never default the issue/audience/goal when the prompt is silent on a *report-changing*
      one — but never run a fixed "ask three questions" ceremony either. Ask 0–3 questions,
      only for a missing fact that would change the report; otherwise state your assumption.
- [ ] Never print a % without its n (and a CI or evidence-dot band). A bare "3% worse" from a
      small sample is a classic error — show the interval.
- [ ] **Never print a raw count as a metric — always a `%` of one explicit denominator** (the only
      legitimate absolute is the sample size `n`, shown once). "sustained 33% / fades 2% (n≈51)",
      never "sustained 17 / fades 1 of 51"; "33% (n≈55)", never "18 of 55". All facet sub-splits
      use the SAME base as Helped%/Worse% (attributable n) — never a hidden second denominator
      (17/51 reads 33% but is 94% of the 18 with data). See STUDY_GUIDELINES "PERCENTAGES, NEVER RAW COUNTS".
- [ ] Never invent a statistic, RR, trial id, brand, dose, price, or clinician to look
      authoritative. Every science citation is **verified against a real source this run, or
      marked `[unverified]`**. "No peer-reviewed evidence located" is always preferred over a
      plausible fabrication. (See §7 VERIFICATION GUARD.)
- [ ] Never rank an option on fewer than ~10 attributable first-hand stories — show it, flag it
      "too few stories to rate", print no precise %.
- [ ] Never imply a census when you sampled; never conflate prevalence (exhaustive tally) with
      rate (sampled %). Show what was sampled.
- [ ] Never rank by popularity — rank by effectiveness (Helped% × evidence discount); never
      subtract harms (show as ⚠ risk note); never bury the proven mainstream starting point.
- [ ] Never widen a corpus with cross-domain/off-topic subs; if a sub's skip% ≫ the corpus
      median, drop its posts from prevalence and disclose.
- [ ] Never write a study on a corpus where the canonical sub contributed ~0 (re-scan isolated).
- [ ] Never use `gemini-2.5-flash` or `gpt-4.1-mini` as scoring models (empirically worse); rating
      is done by the cheap server-side model — never pay a top-tier model to rate (it ties the
      best model at near-zero cost for this bounded task).
- [ ] Never recommend a next step the corpus doesn't support — surface ambiguity instead.
- [ ] Never modify the standard report formats in `formats/` — they are locked and overwritten on
      every update. User customizations live in `~/.whatworked/formats/`.
- [ ] Never commit credentials or study outputs to any repository (the `.gitignore` covers them —
      leave it intact).
- [ ] For user-uploaded content (audio sent to `/transcribe`), log only **file format, size,
      duration, and status — NOT the filename** (a filename can itself be PII, like
      `bloodwork_2024.pdf`), and never send the user's original filename to a third party (send it
      under a generic name).
- [ ] Minimize personal data leaving the user's machine: strip PII (name, exact address, employer,
      contact info, unique IDs) from everything sent to the API (topic, audience, scan params,
      render markdown) and send only the minimal demographic/clinical context the research needs.
      Supplemental documents/images are read locally and never uploaded; only audio is sent (to
      `/transcribe`) — tell the user before sending audio, and keep the transcript local.

---

## Principles (judgment beats any number below)

1. **Fit THIS person.** Parse issue/audience/goal from the prompt; ask only for a missing
   report-changing fact. State assumptions in the report.
2. **Compute, don't guess.** Prevalence = the exhaustive `/tally` count. Rates = sampled `/rate`
   + CI. Never let the LLM estimate a number the pipeline can count.
3. **Sample to a STORY TARGET, not a fixed N** (~30–50 attributable stories/option; census
   smaller ones; <10 → show but don't rank). Rating is ~$0.13/topic server-side — depth is
   near-free; the real cost is discovery + writing.
4. **Honesty.** % with n shown once; sampled ≠ census; explain anomalies (starved/dominant sub,
   contamination) rather than bury them; include the "Evidence ≠ proof" box; thin corpus → say so,
   never pad.
5. **Rank by effectiveness, protect the obvious start.** Surface underrated options; keep the
   mainstream starting point in the start-here box; harms = ⚠ note; ⚖ contested when
   worse% ≥ ½ helped%.
6. **Spend where it changes conclusions.** Server-side gemini does filter / discover / rate; the
   agent does scoping, grouping sanity, and writing.
7. **Readable + warm.** Per-option sections with the canonical card (5-segment bar + caption); short real quotes cited
   `— r/<sub>` (no scores); concrete how-people-use-it (only what a source names); one science
   note per option; scannable first, drill-down second.

---

## PHASE 1 — Intake

- [ ] Create study folder `<YYYY-MM-DD>_study_<slug>/` (in the current working directory; if
      running inside the WhatWorked repo clone, study folders are gitignored by design); tell the
      user the path; invite supplemental files. Process every file: `.txt/.md/.csv/.json/.yaml`→Read ·
      images→Read (vision) · PDFs→Read · office docs→`pandoc`→Read · audio→`POST /transcribe`
      (see API.md)→`transcripts/` · zip/tar→extract+recurse. Briefly report what was found.
- [ ] Scope: issue (current state), audience (who + age/sex/context), goal (desired state). Ask
      0–3 questions ONLY for a missing report-changing fact (constraint, what they tried,
      subgroup); never the fixed-3 ceremony. Vague issue → push back ("improve sleep" → what?).

**Folder layout** (agent writes only these):
```
<date>_study_<slug>/
  study_<slug>.pdf               — required
  study_summary.md               — optional, on request
  passing_records.json           — optional
  diagnostics_<score_id>.json    — optional
  transcripts/<filename>.txt
  notes/<filename>.md
```

## PHASE 2 — Subs + scan

- [ ] `GET /subreddits?q=<term>` (literal substring; fan out across terms). Pick **8–12
      genuinely on-topic subs**, canonical FIRST (single-product / demographic / anti-X subs are
      highest-signal; skip general subs like r/AskReddit; cross-domain subs contaminate — don't add
      them to fatten the corpus). If the topic involves psychoactives, confirm substance keys with
      `GET /erowid/substances?q=` and add an `erowid` source.
- [ ] Per-sub scans (cap ~2000–2500 each) + merge/dedup by `uid`. NEVER a single global
      `max_candidates` shared across subs (it starves the canonical sub scanned last). ~15 grep
      terms, over-grep (scoring filters later; scan misses are permanent). Multi-source form (SOURCES.md).
      `max_candidates` caps **emitted** records, NOT files read — a scan is **read-bound** (every file
      of every sub is read even when it emits 0), so a huge cap does NOT bound scan time. "Make it
      extensive" = more on-topic subs + the Phase-5 batched re-grep, never a 50k–100k cap; an over-wide
      scan over big general subs runs many minutes for little extra signal.
- [ ] Scans are **async, read-bound jobs**: a wide scan can take 10+ min. Poll the job WITHOUT
      blocking — fire it, then check back; never sit in a foreground wait-loop, which your tool
      harness kills at its timeout ceiling, wasting the full window and forcing a restart. Run heavy
      scans one at a time (concurrent full scans can overwhelm the server).
- [ ] Check `summary.by_source`: <500 emitted → too narrow, fix the patterns/sources; canonical
      sub ~0 → re-scan it isolated before continuing.

## PHASE 3 — Discover

- [ ] `POST /discover` (server-side gemini map-reduce, `passes=2`, union) → every option people
      tried, all names carried forward. (If `/discover` is unavailable on an older server, fall
      back to agent-side map-reduce over ~1k-post chunks, 500 chars each, 2 passes, union.)
      `GET /jobs/{id}/discovered` for the names.
- [ ] Normalize the names (the agent does this): split `a/b` and `X (Y)` into name + aliases;
      recover list-bucket members (`"SSRIs (sertraline, lexapro)"` → each as its own entry); drop
      bare class words (`"SSRI"`, `"supplements"`, `"therapy"`); drop ambiguous common-word aliases
      that cause false-positive substring hits; merge substring variants (`"low fodmap"` ⊂
      `"low fodmap diet"`).
- [ ] Consolidate to ~20–30 groups: merge true variants (five birth-control brands → "combined
      OCPs"), but keep a clearly higher/lower-rated member as its own entry.
- [ ] **OPT-IN: wide cross-community discovery (OFF by default).** Only when the user asks to "go
      wide / don't miss anything / find what other communities use" — never by default. Fire a wide
      scout across (almost) all subs to discover treatments the canonical subs never mention:
      `POST /scans` with `kind=reddit_posts`, all subs, the condition grep, **`per_sub_cap=10` +
      `max_file_bytes≈30MB`** (an even, bounded sample — not an uncapped wide scan), then `/discover`.
      Add only the **novel** names to the candidate list; rate them with the Phase-5 batched re-grep.
      **Two hard cautions:** (a) it wins mainly for psych/neuro topics where high-impact options live
      in drug/nootropic communities, and adds little where the home sub already concentrates the strong
      options — it AUGMENTS canonical, never replaces it; (b) many wide finds are **high-risk**
      (addictive/illegal) — magnitude ≠ recommend; surface under a prominent ⚠ harm flag, never tout.
      The scout is read-bound (~minutes/topic).

## PHASE 4 — Rate + Tally (compute the numbers)

- [ ] `POST /rate` (server-side, attribution-first five facets: direction
      skip/helped/noeffect/worse · sub-problem · magnitude · harm-type · durability;
      "worse-before-better = helped"). Sample to the **story target**: ~30–50 attributable
      stories/option; census options with fewer mentions than that. Derive
      Helped%/Noeffect%/Worse% (over attributable posts), magnitude bucket + n, Evidence dots,
      Reports = attributable count. ~64% of grep-matched posts are `skip` (incidental / list-only /
      question / recommendation-without-trying / someone else / venting) — never count them. See
      `API.md` → `POST /rate` for the request shape and story-target sampling.
- [ ] `POST /tally` for exact corpus mention counts (prevalence). **Prevalence = the tally;
      rate = the sampled %. Never conflate them.**

## PHASE 5 — Adaptive depth check (replaces the mode question)

- [ ] **Thin-but-promising rescue (the long-tail fix) — auto-run ONCE when it applies.** From the
      rated numbers, select options that are **thin (<~30 attributable stories) AND promising
      (Helped% point estimate ≥ ~50%)** — these would otherwise be buried, unrankable, in the tail.
      Fire **one** batched re-scan over the SAME subs (submissions + comments in a single
      multi-source scan) with **all** those option names (+aliases) as `grep_patterns` and the
      condition terms as `context_keywords` (keeps it on-topic), then re-rate just those options
      (`/rate sample_n=0`) and fold the new counts in. They're usually *grep-missed*, not rare — the
      baseline greps the condition, so posts that name only the option never entered the corpus; a
      name-grep recovers them (one batched scan roughly doubled treatment coverage on heavy-tail
      topics in testing). One scan + one rate on existing endpoints, ~cents and ~a minute. **Anything
      still <~30 after the re-grep is genuinely rare → label it "rare (confirmed by targeted
      search)"**, not merely thin. (Batched, not per-option: the global cap does not starve options,
      so one scan matches per-option thoroughness at a fraction of the cost.)
- [ ] **Thin total supply OR a contested top option → also widen** to more on-topic subs + census
      all options (this is what makes niche topics work). Dense + uncontested + nothing
      thin-but-promising → proceed lean. The user never pre-picks a fidelity mode.

## PHASE 6 — Diagnostics → caveats

- [ ] From the server numbers (per-sub contribution, skip-rates, supply vs claims): is the
      canonical sub starved? Is one sub dominating? Is a sub's skip% ≫ the corpus median
      (contamination)? These become §8 caveats — disclosed, not silently fixed. (`GET
      /jobs/{id}/diagnostics` on a score job gives supply / share / ease per dimension.)

## PHASE 7 — Write (ONE pass; auto-format; verification guard)

Before writing: pull the rated rows + tally; read 30–50 raw record bodies (not just the
one-sentence `brief`) for quotes and how-to detail. Run one targeted web search per profiled
option for its science note.

**Report ENDS with two provenance boxes** (mandatory; the last two sections — NOT at the top, lead
with the answer instead): **"The prompt"** = ONLY what the user supplied (verbatim original prompt +
every clarifying Q&A + assumptions/defaults + format chosen + supplemental filenames), then **"How
this study was built"** = the machine facts. They are partitioned — **"The prompt" = what was asked,
"How this study was built" = how it was built, and no fact appears in both** (exactly two boxes: no
separate "Original request" appendix, and the corpus-description section is not a third). This makes
the study regenerable and auditable.

**Auto-pick the report format** from the goal clause and disclose it in one line (no format
question). Formats are files: **standard formats** ship in `formats/` (locked — never edit), **user
formats** live in `~/.whatworked/formats/` (created via the feedback flow, Phase 9b). Mapping:
act-now / safety → **Action sheet** (`formats/action-sheet.md`); understand / compare → **Mechanism
map** (`formats/mechanism-map.md`); which-case-am-I / broad audience → **Decision cards**
(`formats/decision-cards.md`); full-landscape survey → **Breadth profile**
(`formats/breadth-profile.md`). A user format `inherits:` a standard one — load the standard
skeleton first, then apply the user file's deltas. Skeletons in STUDY_GUIDELINES.md.

**Body — NATURAL ORDER, lead with the answer, defer reference/provenance to the end:**
**Executive summary** (most useful / surprising findings + the one central fork) → **Start here**
(the mainstream / most-likely first move, even if the sort ranks it lower) → **Rated options**: lead
this section with the **"How to read these cards"** legend as its first `###` subsection (decodes the
5-segment bar + every caption field; template in STUDY_GUIDELINES.md), then per-option cards sorted
by **Helped% × evidence-discount** (the CANONICAL card: 5-segment outcome bar [big help · modest
help · neutral · worse-acute · worse-lasting] + one-line caption `n · Helped%+CI · Evidence ·
Magnitude · Prevalence`, ⚖ if contested; group members; How line; Science line; 2 arc-quotes cited
`— r/<sub>`) → **Long tail** table (REAL ratings, never a uniform "3", never silently dropped;
Phase-5-confirmed rare labeled "rare (confirmed)") → **What to stop doing** anti-patterns →
**Successful paths** (rendered Mermaid if ≥3 clear paths) → **Missing information** (3–6 questions +
why each shifts the recommendation) → **The corpus** (data description incl. per-sub counts) →
**Caveats** (structural biases + diagnostic-derived) → **Your next steps** (≤5 closing actions) →
the two provenance boxes. Canonical card + section specs in STUDY_GUIDELINES.md.

**Say-it-once (S4 — REQUIRED).** Each recurring meta-point has ONE home and is not restated: the
**central fork** lives in the Executive summary (other sections reference it, never repeat);
**demographics / who's-in-the-data** is folded into **Caveats** (no standalone section); the
*Evidence ≠ proof* disclaimer lives only in the legend; **closing actions are next-steps only** (not
a re-summary); and **Successful paths is the diagram only** — no prose re-narration of the same arcs.
Trim duplicating surfaces, but never drop a required calibration element (n, CI, Evidence, the
Evidence ≠ proof box).

**Four writing-level musts** (commonly missed): (a) access / logistics — how to obtain or afford
the top option, and what to do if none is local; (b) answer EVERY symptom the persona named;
(c) include a labs-first / rule-out line where relevant (ferritin/thyroid, sleep-apnea screen,
etc.); (d) partition any conclusion that is driven by a contaminated / off-topic sub.

**§ VERIFICATION GUARD (re-read pass before finalizing — the rule that closes the accuracy gap):**
- Every printed % shows its n + CI / evidence band; if a number looks implausible (e.g. worse% ≈ 0)
  or rests on a small sample, widen / census that option and show the interval.
- Every science citation is verified to a real source this run or marked `[unverified]`; no invented
  RR / trial-id. Bare "no peer-reviewed evidence located" beats a plausible fabrication.

## PHASE 8 — Deliver

- [ ] **Required CLOSING section — "How this study was built"** (the VERY LAST section of every
      study, all formats; sits right after the **"The prompt"** box — the report's last two sections).
      Where "The prompt" records *what was asked*, this records *how the report was built* — so the
      study can be reproduced/audited later.
      Compact labeled block (template in STUDY_GUIDELINES.md):
      **Generated by** WhatWorked plugin v<version> (the assistant reads `"version"` from
      `.claude-plugin/plugin.json` of the installed plugin / cloned repo; else "version: local/unknown")
      · **Date** · **Models used** by role (writer/assistant prose model · rating model = server-side
      `/rate`, default gemini-2.5-flash-lite · discovery model = server-side `/discover`, default
      gemini-2.5-flash-lite · filter model if the optional `/scores` path was used) · **Config/pipeline**
      (subs scanned, per-sub scan cap, story target, discovery passes, contamination-gate result, filter
      target_n if used). **Job ids (scan/disc/rate/tally + any rescue) live ONLY here — never also in
      "The prompt" box.** This is the single home for every machine-generated fact; "The prompt" box
      and the body's corpus-description section must not repeat job ids, subs, models, or caps.
- [ ] `python3 scripts/build_pdf.py <folder>/study_<slug>.md` (server-side render via `/render_pdf`:
      real rendered diagrams, readable font — never ASCII art, never raw diagram source). Study is
      NOT done until the PDF exists and is non-trivial — AND the build **exited 0**. A non-zero exit
      means a diagram failed to render (`X-Diagram-Failures > 0`) → fix the Mermaid (or omit it) and
      rebuild until it exits 0. Never deliver a PDF with the "⚠️ Diagram failed to render"
      placeholder. (STUDY_GUIDELINES RENDER-FAILURE GATE.)
- [ ] Open the finished PDF for the user automatically (`open` on macOS, `xdg-open` on Linux,
      `start` on Windows) — every delivered version, including re-runs.
- [ ] **Versioning — never overwrite a delivered study.** Each re-run writes a new file
      (`study_<slug>_v2.md` → `_v2.pdf`, then `_v3` …). Reused scan/discover/rate artifacts stay
      shared; only the report file is versioned. Announce the new path + one line on what changed.

## PHASE 9 — Close out

**9a. Invite review**
- [ ] Announce the PDF path; explicitly invite: missing alternatives, thin science notes, profile
      weighting, a one-page summary. On revisions reuse `scan_id` + rate/discover artifacts;
      re-write only the affected sections; always emit a NEW version file. Iterating is cheap.

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
   It appears in the Phase 7 format auto-pick from then on, marked "(your format)". It survives
   updates. Offer to email it to the maintainer too if they think it should become standard.
3. **One-off tweak** — apply to this study only (new version file), change nothing else.

**9c. Closing summary**
- [ ] Summarize: study path, versions produced, whether feedback was sent, any custom format created.

---

## QUICK-REF — When something goes wrong

| Symptom | Fix |
|---|---|
| Scan emitted 0 | Wrong keywords or sub names (case-sensitive); don't proceed |
| Canonical sub contributed ~0 | Re-scan it isolated; don't write on a corpus that skipped the home community |
| One sub dominates / skip% ≫ median | Contamination — drop its posts from prevalence, disclose in §8 |
| "441 mentions but 6 rated" | Prevalence = the exhaustive tally; rate = a sampled % ± CI. Don't conflate; disclose the sample |
| Thin corpus / many options <10 stories | Auto-deepen once (Phase 5); then write honest-thin — show unrankable options, don't pad |
| A promising option is thin (<~30 stories, Helped% ≥~50%) | Phase-5 rescue: ONE batched re-grep of all such option names over the same subs (+comments), condition as `context_keywords`, re-rate. Still <~30 → "rare (confirmed)" |
| A % looks too clean (worse% ≈ 0) | Small-sample artifact — census that option, show the CI (Verification Guard) |
| Tempted to cite a specific stat/trial | Verify it this run or mark `[unverified]`; never invent (Verification Guard) |
| No science found for an option | "no peer-reviewed evidence located" — don't handwave |
| `/discover` unavailable | Fall back to agent-side map-reduce discovery (2 passes, union) |
| User answers a missing-info question | Re-read matched records; regenerate affected sections; reuse `scan_id`; emit a new version |
