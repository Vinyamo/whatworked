---
name: run-study
description: Run a WhatWorked study — research what actually worked for people with a similar issue (community experience at scale + scientific literature) and deliver an action-oriented PDF report. Use when the user says "run a whatworked study", wants to research a personal health/life issue, asks "what worked for others", wants treatment options compared, asks how people's lives changed after an event/decision/treatment (life-course study), or asks to run/start a study.
---

# Run a WhatWorked study

Everything you need is in the plugin directory (`${CLAUDE_PLUGIN_ROOT}`):

1. **Read `${CLAUDE_PLUGIN_ROOT}/AGENTS.md` now and follow it phase by phase.** It is the
   complete playbook: first-run credential setup, issue/audience/goal intake, report-format
   pick, web research, source selection, scan → discover → score → check, study writing,
   PDF rendering, and the close-out/feedback flow.
   **There are two study types, and the user must always be told both exist** (AGENTS.md PHASE 1
   → "Study type"):
   - **A. Single posts:** "what worked for people with X". Options are rated from people's own
     reports. This is the default pipeline in AGENTS.md.
   - **B. Series of posts by the same people:** "how did people's lives go in the 1–3 years after
     X". Follows the same users' other posts before vs after X, compared with people who got a new
     dog. Follow `${CLAUDE_PLUGIN_ROOT}/LIFE_COURSE.md` and `formats/life-course.md`.
2. Deep references it points into (same directory): `STUDY_GUIDELINES.md` (report structure
   + style + per-option metrics), `API.md` (every studyd HTTP call), `CONFIG_RECOMMENDED.md`
   (scoring config), `SOURCES.md` (scan source schemas), `formats/` (the standard report
   formats — locked; user formats live in `~/.whatworked/formats/`).
3. Bundled scripts (run with `python3`, stdlib-only):
   `${CLAUDE_PLUGIN_ROOT}/scripts/discover_categories.py` (category discovery),
   `${CLAUDE_PLUGIN_ROOT}/scripts/build_pdf.py` (renders the final PDF via the cloud service),
   `${CLAUDE_PLUGIN_ROOT}/scripts/breadth_sampling.py` (breadth-mode sampling),
   `${CLAUDE_PLUGIN_ROOT}/scripts/life_course.py` (type B: the whole life-course pipeline, resumable).

Non-negotiables (details in AGENTS.md PHASE 0/0B): set up `~/.claude/.studyd_credentials` on
first run by asking the user for their username + password; never skip the caveats, science
notes, or missing-info sections; never fabricate brands/doses/clinicians; the study is not
done until the PDF exists; open the finished PDF automatically (`open` / `xdg-open` / `start`);
always run the feedback flow after delivering a report.

Create the study folder in the user's current working directory (ask where, if unclear) —
never inside the plugin directory.
