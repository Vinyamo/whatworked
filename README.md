# WhatWorked

Tell it your issue and your goal — it researches **what actually worked for people in your
situation**, by mining community experience at scale (Reddit, Erowid, the web) and
cross-checking it against the scientific literature. You get a personal, action-oriented
**PDF study**: one recommended next step, ranked alternatives, real quotes, what the science
says, what to stop doing, and honest caveats.

**In short:** built on self-reported anecdotes — not medical advice and no substitute for a
clinician. Quality depends on how much the communities discussed your topic. You need a
username + password from the maintainer. Full picture: [Limitations & disclaimer](#limitations--disclaimer).

## Use with Claude — recommended

### Claude Desktop app (no terminal)

The `/plugin` commands don't exist in the desktop app — instead, you ask Claude itself to
set things up:

1. Install [Claude Desktop](https://claude.com/download), sign in, open the **Code** tab,
   and pick any folder when asked.
2. Copy-paste this whole message to Claude and send it:

   > Please merge the following into my `~/.claude/settings.json` (create the file if it
   > doesn't exist, and keep everything already in it):
   > ```json
   > {
   >   "extraKnownMarketplaces": {
   >     "vinyamo": {
   >       "source": { "source": "github", "repo": "Vinyamo/whatworked" },
   >       "autoUpdate": true
   >     }
   >   },
   >   "enabledPlugins": { "whatworked@vinyamo": true }
   > }
   > ```
3. Quit and reopen the app. The plugin installs itself on startup and stays up to date
   automatically (updates apply when you restart the app).
4. Say **"Run a whatworked study"** and answer its questions. First time, it asks for your username + password.

### Claude Code in the terminal or VS Code

Run these three commands **one at a time** — send one, wait for it to finish, then the
next (pasted together they won't execute):
```
/plugin marketplace add Vinyamo/whatworked
```
```
/plugin install whatworked@vinyamo
```
```
/reload-plugins
```
Recommended: `/plugin` → **Marketplaces** → enable **auto-update**. Updating manually
instead: `/plugin update whatworked@vinyamo`, then `/reload-plugins`.

Then say **"Run a whatworked study"**.

## Use with Codex

1. `git clone https://github.com/Vinyamo/whatworked && cd whatworked`
2. Start Codex in that folder — it picks up `AGENTS.md` automatically. Say **"Run a whatworked study"**.
3. Update later with `git pull`.

## Running a study

Work in (or tell Claude to use) a folder where you want the results, then say **"Run a whatworked study"**
— the agent drives the whole process and asks for what it needs:

1. **First time only:** it asks for your username + password and stores them locally.
2. **Your situation:** the issue (where you are now), who it's for (age/sex/context), and the
   goal (where you want to get). The more specific, the better the study.
3. **Choices along the way:** a report format (it suggests one), three clarifying questions,
   and a confirmation of the data sources and cost before anything is run. A typical study
   costs cents and takes ~15–40 minutes; "map ALL my options" breadth studies cost more —
   it quotes the estimate first.
4. **Optional:** drop supplemental files into the study folder when invited — lab results,
   doctor letters (PDF/photo), even voice memos — they're folded into the research.

You get a **PDF study** in a dated folder: one recommended next step, ranked alternatives
with real quotes and science notes, what to stop doing, open questions, and honest caveats.
Answering its "missing information" questions afterwards gets you a sharper revision — the
expensive data work is reused, so iterating is fast and nearly free.

## Feedback

After each report you'll be asked what worked and what didn't — please send it (the agent
drafts the email for you). You can also create your own report formats locally; the standard
ones update centrally and shouldn't be edited.

## Limitations & disclaimer

**Not medical advice.** Studies summarize what strangers on the internet say worked for them,
cross-checked against published literature. They cannot diagnose you, and they are no
substitute for a clinician — discuss anything you plan to act on with one, and never use this
for emergencies.

**Evidence ≠ proof.** The corpus is self-reported and self-selected: no control group, so it
can't establish causation (placebo effects, regression to the mean, and co-interventions are
all invisible). People who succeed write follow-ups; people who quit on day 3 don't. Fluent
writers, English speakers, and US/UK perspectives are over-represented. Even an option with
many consistent reports means "lots of people say this," not "this will work for you." Every
study spells out these caveats — read them.

**Coverage is uneven.** If the communities barely discussed your topic, the study will be thin
— it says so honestly rather than padding. Niche conditions, very new treatments, and
non-English-world options are systematically under-covered.

**AI is in the loop.** Posts are found, filtered, and rated by language models. They make
mistakes: relevant stories get missed, irrelevant ones slip through, and two runs of the same
study won't pass identical records. The pipeline is built to surface rather than hide this
(confidence labels, sample sizes, diagnostics), but treat every number as approximate.

**Privacy.** Your issue description and study parameters are processed by the maintainer's
server and third-party LLM providers, and basic usage (jobs run, cost) is logged per account.
Supplemental files you add are processed for the study (audio is transcribed via a third-party
API); transcripts and reports stay in your local study folder. Don't include things you
wouldn't put in an email.

**Availability.** The cloud service runs on the maintainer's infrastructure at their expense —
no uptime guarantees, and accounts can be rate-limited or revoked if costs run away.

## License

[PolyForm Noncommercial 1.0.0](LICENSE.md) — free to use, share, and modify for
noncommercial purposes; commercial use requires permission.

Required Notice: Copyright Vinyamo (https://github.com/Vinyamo/whatworked)
