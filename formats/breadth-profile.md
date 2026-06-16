---
id: breadth-profile
kind: standard
title: Breadth profile (full landscape)
summary: The full-landscape treatment-profile format produced by breadth mode — every option ranked by expected improvement, with the long tail preserved.
---

# Breadth profile format

**When to suggest:** the user asked to "map the full menu" / "what are ALL my options / don't miss
anything" — i.e. breadth mode (AGENTS.md → PHASE 8B). This is the canonical output shape for that
pipeline; the other three formats are alternative *top-level organisations* of the same data.

**Shape:**

1. **Executive summary** leading with the most interesting / surprising findings (standout
   high-rated option, anything underrated or counter-intuitive, the clearest thing to avoid) as
   3–5 bold-lead-in beats. Then one sentence: ranking is by *expected improvement (Helped% ×
   Magnitude × certainty), not popularity* — the reader should think for themselves.
2. **No separate `## Start here`** — name the mainstream / highest-leverage first move inside the Executive summary. Then `## Successful paths` (the triage Mermaid) **before** the rated menu.
3. One `###` section per treatment **group** (~20–30 groups, consolidated; merge true variants,
   keep standouts visible), sorted by expected improvement. **Never subtract harms from the rank**
   — surface risk as a per-option ⚠ risk note. Don't bury a proven mainstream first-line option —
   keep it prominent even if the sort puts it lower.
4. `## What to stop doing` — 3–6 corpus-anchored anti-patterns.
5. **Long-tail table** at the very end (treatment · prevalence · rating · certainty) with REAL
   per-row ratings; `—` = genuinely unrated; never impute a uniform "3"; never silently drop.
6. `## Sources & corpus` — data description + one row per subreddit (posts and comments split).

**Per-option section content** (exact spec in `STUDY_GUIDELINES.md` → "Breadth-mode report format"
and "Per-option card & metrics"): the canonical card — 5-segment outcome bar + one-line caption
(`n · Helped%+CI · Evidence · Magnitude · Prevalence`) · 1–2 readable paragraphs (who it's for, what experiences say) · `**How:**`
line · `**Science:**` line · 1–2 blockquoted arc-quotes cited `— r/<sub>`.

**Always include:** who's-in-the-data (folded into caveats, not a standalone section) · missing-info
questions · caveats (incl. the required "Evidence ≠ proof" box; disclose sampling: "rated 50 of ~180
attributable", % ± Wilson CI) · next steps · the `### How to read these cards` legend as the lead
subsection of `## Rated options` · `## The prompt` right after the executive summary · `## How this
study was built` (machine facts; job ids → folder `job_ids.json`, not the report) as the very last
section — templates in `STUDY_GUIDELINES.md`.
