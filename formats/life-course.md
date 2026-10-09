---
id: life-course
kind: standard
title: Life-course report
summary: "What happened to people's lives 1–3 years after X", compared with people who got a new dog. The format for study type B (LIFE_COURSE.md); never used for type A.
---

# Life-course report format (study type B)

**When:** always for a type-B study (series of posts by the same people, `LIFE_COURSE.md`). It is the
only format for type B. The type-A formats (cards, options, Helped%) don't apply.

**Section order:**

1. `# <What happens to people after X?>`, then one line: the date and "WhatWorked life-course study".
2. `## Executive summary`, 3–5 bullets:
   - the headline result in plain words, with its number, CI and n. Example: *"1–3 years after losing
     a partner, people's posts show lower wellbeing than those of people who got a dog: −0.4 on a
     0–10 scale (95% CI −0.7 to −0.1; 150 vs 590 people)"*;
   - which of the seven dimensions moved and which didn't;
   - one line on what this does and does not mean (association, Reddit posters, text-expressed);
   - if useful, how it compares with the literature.
   - No recommendation beyond what the data supports.
3. `## The prompt`: the provenance box, as in STUDY_GUIDELINES.
4. `## How to read this study`: a short legend.
   - **Score:** the rater scores each period 0–10 (5 = ordinary life) from the person's own posts
     about their current state.
   - **Change:** after − before, where *before* is 3 → 1.5 years before the event and *after* is
     1 → 3 years after it.
   - **"vs dog owners":** the group's change minus the comparator's change. 0 means "the same as
     people who got a dog".
   - **CI:** if it crosses 0, there is no measurable difference.
   - **Scale of effects:** ±0.3 is a noticeable group shift. Partner death (the method's
     negative control) measured about −0.4.
   - The *Evidence ≠ proof* note lives here.
5. `## Results`
   - **Main table:** one row per dimension, with columns: dimension · n (group / comparator) ·
     change vs comparator (95% CI) · start-matched (95% CI) · % better / % worse (group vs
     comparator). Wellbeing first. Dimensions with n < 30 get "too few people to estimate".
   - **Optional Mermaid `xychart-beta` bar chart** of "vs comparator" per dimension, only if it
     renders.
   - **Every table and chart gets three lines:**
     - **Key finding:** one sentence;
     - **How to read:** one worked example, e.g. *"−0.4 means: on average the after-period
       was rated 0.4 points lower, relative to the before-period, than for dog owners"*;
     - **Careful:** the most likely misreading, e.g. *"this is a group average — 35% of people in
       the group were rated better off"*.
6. `## Subgroups`, only if `extract_fields` was used and a subgroup has n ≥ 30. Same table shape.
   Never rank subgroups whose CIs overlap heavily.
7. `## What the lives looked like`: 3–5 short, anonymised illustrative arcs drawn from the
   rater's `events_before` / `events_after` and `reason`, e.g. *"Before: caring for a sick husband,
   money worries. After: moved near family, volunteering, new relationship."*
   - Mix better, unchanged and worse cases, in proportion to the data.
   - No usernames. Quote at most a short phrase. Never details that could identify a person.
8. `## What the science says`: 1–3 verified sources on X and long-term wellbeing (or
   `[unverified]` / "no peer-reviewed evidence located"), and how the result compares.
9. `## About this data`, which absorbs the caveats (say-it-once). Cover:
   - **Who is in it:** Reddit users who posted first-hand about X, dated within 60 days, and kept
     posting about their own lives for years.
   - **Funnel:** anchor posts → valid anchored people → people with posts in both windows →
     rated → passed the evidence gate (per group). Use percentages with the base stated,
     plus n.
   - **Limits:**
     - observational, not causal;
     - selection on continued posting;
     - LLM-rated, text-expressed states, not questionnaires;
     - dating error;
     - the topic hidden from the rater, plus the leakage-check result;
     - the comparator's own change.
10. `## Missing information`: 2–4 questions that would sharpen the answer, such as a different
    comparator, a time course, or a subgroup.
11. `## How this study was built`, as the last section. Include:
    - plugin version and date;
    - models: the writer, anchor check = gemini-2.5-flash-lite, rater = claude-haiku-4-5 (rubric C,
      both orders);
    - study type B, the fixed method (windows, gate, hidden topic subs), and the regex and
      definition used;
    - the comparator.

    No job ids: they go in `work/lc_state.json`, which serves as `job_ids.json`. No running costs.

**Never:**
- turn this into treatment cards or Helped%;
- report a number without its n and CI;
- call the outcome "happiness as measured by a questionnaire";
- imply that X *caused* the change.
