---
id: action-sheet
kind: standard
title: Action sheet
summary: Top moves + stop-doing + red-flags up front, full ranked menu below. Default when the goal is "act now" or safety matters.
---

# Action sheet format

**When to suggest:** the user wants to decide and act now, or safety/triage matters. This is the
default all-rounder.

**Shape — two layers** (skim the sheet, or drill into the menu):

1. `## Action sheet` — one page, first:
   - **Top 3–4 moves**, each with its concrete `**How:**` line (dose / brand / protocol / cost when
     a source names them) and its canonical card (bar + caption).
   - **Top 3 things to stop doing** (one line each: anti-pattern + why it fails + what instead).
   - A **red-flags / see-a-clinician** line.
2. `---` then the full ranked menu: `## Options`, one `###` section per treatment group,
   best-rated first.

**Shared content rules** (all formats): every option uses the canonical per-option card (5-segment
outcome bar + one-line caption `n · Helped%+CI · Evidence · Magnitude · Prevalence`),
per-option `**How:**` and `**Science:**` lines, and 1–2 blockquoted quotes cited `— r/<sub>` —
see `STUDY_GUIDELINES.md` → "Breadth-mode report format" and "Per-option card & metrics".

**Always include:** `## What to stop doing` (no separate "Start here" — the mainstream first move is
named in the executive summary) · long-tail table (real ratings, never a uniform "3") · `## About this data` (per-sub table + data
description + limits: who's-in-the-data, structural biases, sampling; Evidence ≠ proof stays in the
legend) · missing-info questions · the `### How to
read these cards` legend as the lead subsection of `## Rated options` · `## The prompt` right after the
executive summary · `## How this study was built` (machine facts; job ids → folder `job_ids.json`, not
the report) as the very last section — templates in `STUDY_GUIDELINES.md`.
