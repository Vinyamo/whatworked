---
id: mechanism-map
kind: standard
title: Mechanism map
summary: Options organized by how they work (drug class / pathway); if one class fails, switch mechanism. Best for "I tried X, what next" or comparing approaches.
---

# Mechanism map format

**When to suggest:** the user wants to *understand/compare* the space, the topic is contested
across multiple drug classes, or they've tried a first-line option and ask "what next".

**Shape:**

1. A short intro stating the organizing principle and the **explicit decision rule near the top**:
   *if one option in a class fails, switch to a different mechanism rather than another option in
   the same class.*
2. A **compact Mermaid mechanism diagram** (≤ ~10–12 nodes, `graph TD`) showing the classes and
   where each acts.
3. `##` heading per **mechanism / drug class** (not a flat rank); under each, the `###` option
   sections that belong to it, best-rated first within the class.

**Shared content rules** (all formats): every option uses the canonical per-option card (5-segment
outcome bar + one-line caption `n · Helped%+CI · Evidence · Magnitude · Prevalence`),
per-option `**How:**` and `**Science:**` lines, and 1–2 blockquoted quotes cited `— r/<sub>` —
see `STUDY_GUIDELINES.md` → "Breadth-mode report format" and "Per-option card & metrics".

**Always include:** `## Start here` box · `## What to stop doing` · long-tail table (real ratings,
never a uniform "3") · `## Sources` appendix (one row per subreddit, posts and comments split) ·
demographics · missing-info questions · caveats (incl. the "Evidence ≠ proof" box) · key takeaways ·
the `### How to read these cards` legend as the lead subsection of `## Rated options` · then, LAST, the
two provenance boxes: `## The prompt` (verbatim prompt + clarifying Q&A + assumptions — human inputs
only) followed by `## How this study was built` (machine facts + job ids) — templates in `STUDY_GUIDELINES.md`.
