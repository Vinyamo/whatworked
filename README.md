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

## What can I research?

Almost any personal issue where people share what they tried — health and lifestyle, but also
relationships, family, work, and the bigger questions of growth and meaning. The best prompts
say three things: **the issue, who you are, and the goal** — and mention what you've already
tried. A few realistic examples to spark ideas:

**Sleep**
> "38F, for six months I've woken around 3am almost every night and lie awake an hour or two before drifting off again. Falling asleep initially is fine — it's the middle-of-the-night waking. Melatonin did nothing; cutting afternoon caffeine helped a little. I'd rather avoid prescription sleeping pills. Goal: sleep through to my 6:30 alarm most nights. What's worked for people with this pattern?"

**Gut & digestion**
> "34M, IBS-D for two years — daily bloating, cramping, urgency within an hour of eating. Strict low-FODMAP calmed it ~60% but it's miserable to maintain and I relapse on reintroduction; one round of rifaximin helped briefly. I want the full landscape of what people have tried — diet, supplements, gut-directed therapies, meds — ranked by what worked, not just the popular stuff. Goal: predictable digestion so I can eat out without planning my exit."

**Hormonal & women's health**
> "47 and hitting perimenopause hard — hot flashes several times a day, night sweats, sleep completely shot. Periods still happening but irregular. I'm torn on HRT (my mum had breast cancer so I'm nervous), but the non-hormonal stuff I've half-heartedly tried isn't cutting it. I want an honest comparison of HRT vs the serious non-hormonal options — what worked for women in my spot, and what the risks really look like. Goal: get the flashes and sleep under control."

**Mental health & focus**
> "31M, just diagnosed with adult ADHD. Vyvanse genuinely helps my focus, but it crushes my appetite, spikes my anxiety in the afternoon, and I'm barely sleeping. I don't necessarily want to quit it — I want to know how people manage these exact side effects, or which non-stimulant/lifestyle approaches held up. Goal: keep the focus benefit without feeling wired and underfed."

**Skin**
> "28F with stubborn acne along my jawline and chin that flares about a week before my period — pretty clearly hormonal. I've cycled through benzoyl peroxide, salicylic acid, and a few serums with no lasting change, and I'd like to understand the real options (topical, hormonal, dietary) before going to a derm for Accutane. What worked for people with this cyclical, lower-face pattern? Goal: clear skin that doesn't come back every month."

**Energy & fatigue**
> "33F, exhausted for the better part of a year — dragging through afternoons, foggy, no energy to exercise — even though I sleep eight hours. Bloodwork was 'normal' except ferritin at 18, which my GP shrugged off. I suspect iron but hear oral supplements are hit or miss. I want to know what actually fixed this kind of low-ferritin fatigue, including how people got iron up and whether something else was the real culprit. Goal: get through a day without needing to lie down."

**Chronic pain & migraines**
> "35F with chronic migraines — about 10 days a month, often triggered by stress and my period. Sumatriptan reliably aborts an attack, so acute relief isn't the problem; the frequency is. I've tried magnesium on and off and kept a trigger diary. I want the realistic menu of preventives people have used — supplements, prescription preventives, lifestyle, devices — with a sense of what's worth trying first. Goal: cut my migraine days at least in half."

**Habits & addiction**
> "24, quitting vaping after four years — up to a pod a day, reaching for it the second I'm stressed or bored. I've quit cold turkey twice and caved within a week both times. I want to know what genuinely helped people quit nicotine for good (not just the first few days) — replacement, tapering, apps, the mental side — and which approaches had real staying power. Goal: off nicotine entirely and actually staying off."

**Metabolic health**
> "45M, just told I'm prediabetic with an A1c of 6.0, plus belly weight I've carried for years. I want to avoid metformin if a serious lifestyle effort can do it, but my past attempts to 'eat better' had no structure. I want to see what actually brought A1c back to normal for people in my situation — specific diets, exercise patterns, what order they did things — ranked by what worked. Goal: A1c under 5.7 at my next test in six months, no medication."

**Relationships**
> "34F, with my partner six years. We've drifted into roommates — affectionate but no real connection, every conversation is logistics, and weeks pass without anything that feels like *us*. No affair, no big fights, just flat. A couple of forced date nights fizzled. I want to know what actually rebuilt closeness for couples in a long-term rut — not generic 'communicate more,' but the specific things people did. Goal: feel like partners again, not co-managers of a household."

**Parenting a teen**
> "Dad of a 14-year-old who's pulled away hard this year — one-word answers, door always shut, every attempt to talk turns into a fight or silence. I don't want to be the cop, but I also can't reach him. I've tried backing off and tried forcing 'family time'; both flopped. I want to know what genuinely reopened the connection for parents of teens this age. Goal: a kid who'll actually talk to me again, even a little."

**Family of origin**
> "41F, my relationship with my mother has been low-grade toxic my whole life — guilt trips, criticism dressed as concern, and I leave every visit drained. Going fully no-contact feels too extreme and I'd carry the guilt; pretending it's fine isn't working either. I want to understand what people in similar spots actually did — boundaries, limited contact, scripts, therapy approaches — and what brought them peace. Goal: a relationship with her that doesn't cost me my mental health."

**Conflict & hard conversations**
> "29M, new-ish manager and I freeze on conflict — a teammate who keeps missing deadlines, a peer who talks over me in meetings — I either avoid it for weeks or finally snap. I've skimmed a couple of 'crucial conversations' summaries but nothing sticks in the moment. I want to know what actually helped people get good at hard conversations and holding their ground without blowing up. Goal: handle friction directly and calmly instead of dreading it for days."

**Personal growth**
> "26, shy and self-conscious my whole life — I rehearse texts for an hour, dodge phone calls, and replay every social interaction for days afterward. Therapy helped me understand where it comes from but not change it day to day. I want the practical playbook: what actually built real confidence and quieted the overthinking for people who started where I am. Goal: move through social situations without the constant dread and post-mortems."

**Purpose & meaning**
> "52M, financially fine and externally 'successful,' but the last few years feel hollow — I hit the goals I set at 30 and now I'm just running out the clock, going through the motions at work and home. I don't want a midlife-crisis cliché; I want to know what actually helped people rebuild a sense of purpose and direction in midlife. Goal: wake up with something that feels worth doing, not just a list of obligations."

**Intimacy & desire**
> "37F, married eight years, and our sex life has nearly stopped — I love my husband but my desire has cratered and the mismatch is becoming a wound for both of us. Some of it's stress and exhaustion, some I can't explain, and I've been too embarrassed to dig into it. I want an honest look at what actually helped couples with a desire gap — medical, psychological, relational — without the cringe or the snake oil. Goal: rebuild a sex life that works for both of us."

**Sexual confidence**
> "44M, performance anxiety that's snowballed — a couple of off nights turned into dreading sex entirely, and now the anxiety itself is the problem more than anything physical. My GP ran bloods and said it's likely in my head. I want to know what genuinely helped men break this anxiety loop — mental approaches, what to say to a partner, when meds actually help and when they don't. Goal: be present and relaxed with my partner again instead of stuck in my own head."

You don't have to be this complete — say a rough version and the agent asks follow-ups. You can
also steer the *shape*: **"what should I try next?"** gives one recommended step plus alternatives;
**"map all my options / don't miss anything"** gives the full ranked landscape.

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

**Privacy.** **We don't save anything personal.** Studies run on the maintainer's server, but it logs only per-account usage (which actions, when, cost) — never your issue, your corpus, or your report. Documents and images are read locally and never uploaded; the assistant strips identifying details from what it sends; only audio is sent out, to transcribe it. Full detail: [Logging & data handling](API.md#logging--data-handling).

Your issue and study parameters go to the maintainer's server and third-party LLM providers; only basic usage (jobs, cost) is logged, per account. Transcripts and reports stay in your local study folder. Don't include anything you wouldn't put in an email.

**Availability.** The cloud service runs on the maintainer's infrastructure at their expense —
no uptime guarantees, and accounts can be rate-limited or revoked if costs run away.

## License

[PolyForm Noncommercial 1.0.0](LICENSE.md) — free to use, share, and modify for
noncommercial purposes; commercial use requires permission.

Required Notice: Copyright Vinyamo (https://github.com/Vinyamo/whatworked)
