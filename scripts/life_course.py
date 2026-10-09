#!/usr/bin/env python3
"""Life-course study driver (study type B): what happened to people's lives after an event.

Follows the SAME Reddit users over years. People who wrote a first-hand, datable post about the
event (the "anchor") are compared with people who wrote one about getting a new dog (the
comparator). For each person, a rater sees a sample of their OTHER posts from 3 → 1.5 years
before the event and from 1 → 3 years after it, shuffled, undated and in random order. It scores
both periods 0–10 on seven wellbeing dimensions. Change = after − before. The result is the
group's change minus the comparator's change, with a bootstrap 95% CI. See LIFE_COURSE.md.

    python3 scripts/life_course.py next     <study_dir>   # advance one step; never blocks
    python3 scripts/life_course.py wait     <study_dir>   # advance, polling ≤ 8 min, then exit
    python3 scripts/life_course.py status   <study_dir>
    python3 scripts/life_course.py analyze  <study_dir>   # (re)compute results offline
    python3 scripts/life_course.py validate <study_dir>   # check the spec, submit nothing
    python3 scripts/life_course.py reset    <study_dir> <scan|check|fetch|rate>   # redo from that step on

The spec is <study_dir>/work/lc_spec.json (template: LIFE_COURSE.md). State and every server
artifact go to <study_dir>/work/: lc_state.json, lc_*.ndjson, lc_results.{json,txt}.
Re-running is safe: finished steps are skipped and running jobs are re-polled, never resubmitted.

Credentials: ~/.claude/.studyd_credentials (url/username/password) or
STUDYD_URL/STUDYD_USER/STUDYD_PASS. Stdlib only.
"""
from __future__ import annotations

import base64
import collections
import json
import os
import random
import re
import statistics as st
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CREDENTIALS_PATH = Path.home() / ".claude" / ".studyd_credentials"
DEFAULT_URL = "https://whatworked.vinyamo.com"
ASSETS = Path(__file__).resolve().parent / "life_course_assets"
DAY = 86400

# Validated measure (identical for every study so results stay comparable; LIFE_COURSE.md §Method).
WINDOWS = {"window_before_days": 1095, "min_gap_before_days": 545,     # reference: 3 → 1.5 y before t0
           "min_gap_days": 365, "window_after_days": 1095}             # outcome:   1 → 3 y after t0
RATER = {"model": "claude-haiku-4-5", "pair_version": 3, "pair_both_orders": True,
         "max_posts_per_side": 25, "max_post_chars": 800, "gemini_safety": "block_none", "workers": 24}
HYGIENE = {"other_min_len": 60, "min_before": 3, "min_after": 3, "dedupe_posts": True,
           "max_posts_per_day": 3, "equalize_sides": True}
MIN_EVIDENCE = 3              # evidence posts per period, in BOTH A/B orders, for a person to count
COST_PER_PERSON = 0.015       # ≈ $ per person rated (Haiku, both orders; measured $0.0138–0.0147)
COST_PER_CHECK = 0.00006      # ≈ $ per anchor post checked (flash-lite; measured $0.051–0.054 per 1k)
MIN_GROUP_N = 30              # below this a group's numbers are not reported as estimates
DIMS = ["wellbeing", "happiness", "life_satisfaction", "meaning", "purpose", "self_love", "love_for_world"]

COMPARATOR_NEW_DOG = {
    "label": "new_dog",
    "regex": r"\b(we|i) (just |finally |recently )?(adopted|got|brought home|picked up) (a|an|our|my) "
             r"(new )?([a-z-]+ )?(puppy|pup|dog|rescue dog)\b",
    "subs": ["*"],
    "definition": "the poster (or their household) themselves just got a new dog or puppy",
    "hide_regex": r"\b(dogs?|pupp(y|ies)|pups?|doggos?)\b",
}
GENERIC_SUBS = {s.lower() for s in """AskReddit offmychest TrueOffMyChest relationships relationship_advice
CasualConversation self confession AmItheAsshole AITAH TwoXChromosomes AskWomen AskMen Advice NoStupidQuestions
lonely depression mentalhealth Anxiety careerguidance personalfinance CasualUK LifeProTips unpopularopinion
Showerthoughts pics funny todayilearned GetMotivated DecidingToBeBetter selfimprovement aww""".split()}
DEFAULTS = {
    "kinds": ["submission"],          # anchor posts; add "comment" for more people (scan ≈ 4× slower)
    "min_text_len": 200, "min_score": 1,
    "first_t0": "2013-01-01",         # earliest event date
    "last_t0": "2024-06-30",          # latest event date (the archive ends mid-2026 → ≥ 2 y of after-window)
    "max_days_since": 60,             # strict dating: the event happened ≤ 60 days before the post
    "max_check_authors": 30000,       # per group: authors whose anchor posts get the LLM check (≈ $0.1/1k posts)
    "max_fetch": 4000,                # per group: anchored people whose histories are fetched (free)
    "max_rated": 500,                 # per group: qualifying people sent to the rater (billable, ≈ $0.015 each)
    "budget_usd": 18.0,               # hard stop before any billable step would exceed it
    "seed": 1,
}


# ---------------------------------------------------------------- http
def creds() -> tuple[str, str]:
    if CREDENTIALS_PATH.exists():
        try:
            d = json.loads(CREDENTIALS_PATH.read_text())
            url, user, pw = d.get("url", DEFAULT_URL), d["username"], d["password"]
        except (json.JSONDecodeError, KeyError) as e:
            sys.exit(f"malformed {CREDENTIALS_PATH}: {e}")
    else:
        url = os.environ.get("STUDYD_URL", DEFAULT_URL)
        user, pw = os.environ.get("STUDYD_USER"), os.environ.get("STUDYD_PASS")
        if not user or not pw:
            sys.exit(f"no credentials: create {CREDENTIALS_PATH} or set STUDYD_USER/STUDYD_PASS")
    return url.rstrip("/"), base64.b64encode(f"{user}:{pw}".encode()).decode("ascii")


def http(method: str, path: str, body: dict | None = None, *, raw: bool = False, timeout: int = 600):
    url, tok = creds()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url + path, data=data, method=method,
                                 headers={"Authorization": f"Basic {tok}", "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = r.read()
                return out if raw else json.loads(out)
        except urllib.error.HTTPError as e:
            detail = e.read()[:400].decode("utf-8", "replace")
            if e.code == 429 and ("spend cap" in detail.lower() or "quota" in detail.lower()):
                sys.exit(f"daily spend quota reached (HTTP 429): {detail}\nResume tomorrow with `next` — "
                         "finished steps are kept.")
            if e.code in (502, 503, 504) and attempt < 3:
                time.sleep(10 * (attempt + 1))
                continue
            sys.exit(f"{method} {path} failed: HTTP {e.code} — {detail}")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 3:
                time.sleep(10 * (attempt + 1))
                continue
            sys.exit(f"{method} {path} failed: {e}")


def download_ndjson(job_id: str, out: Path) -> int:
    data = http("GET", f"/jobs/{job_id}/results", raw=True, timeout=1800)
    out.write_bytes(data)
    return sum(1 for line in data.splitlines() if line.strip())


def read_ndjson(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open() if line.strip()]


# ---------------------------------------------------------------- spec + state
def utc(day: str) -> int:
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def load_spec(sd: Path) -> dict:
    p = sd / "work" / "lc_spec.json"
    if not p.exists():
        sys.exit(f"missing {p} — write it first (template in LIFE_COURSE.md)")
    spec = json.loads(p.read_text())
    ev = spec.get("event") or {}
    for k in ("label", "regex", "definition"):
        if not ev.get(k):
            sys.exit(f"lc_spec.json: event.{k} is required")
    if not re.fullmatch(r"[a-z0-9_]{2,40}", ev["label"]):
        sys.exit("lc_spec.json: event.label must be a short snake_case slug")
    comp = spec.get("comparator", "new_dog")
    if comp == "new_dog":
        comp = dict(COMPARATOR_NEW_DOG)
    elif not isinstance(comp, dict) or not all(comp.get(k) for k in ("label", "regex", "definition")):
        sys.exit("lc_spec.json: comparator must be \"new_dog\" or {label, regex, definition, …}")
    if comp["label"] == ev["label"]:
        sys.exit("lc_spec.json: event and comparator need different labels")
    s = dict(DEFAULTS, **(spec.get("settings") or {}))
    for g in (ev, comp):
        g.setdefault("subs", ["*"])
        for rx in (g["regex"], g.get("hide_regex") or "", g.get("topic_regex") or ""):
            try:
                re.compile(rx, re.I)
            except re.error as e:
                sys.exit(f"lc_spec.json: bad regex {rx!r}: {e}")
            if re.search(r"\(\?[=!<]|\\[1-9]", rx):
                sys.exit(f"lc_spec.json: {rx!r} uses lookarounds/backreferences (the server uses RE2)")
    return {"event": ev, "comparator": comp, "settings": s, "extract_fields": spec.get("extract_fields") or {}}


def state_path(sd: Path) -> Path:
    return sd / "work" / "lc_state.json"


def load_state(sd: Path) -> dict:
    p = state_path(sd)
    return json.loads(p.read_text()) if p.exists() else {"stage": "new", "jobs": {}, "log": [], "spent_est": 0.0}


def save_state(sd: Path, s: dict) -> None:
    state_path(sd).write_text(json.dumps(s, indent=1))


def note(s: dict, msg: str) -> None:
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M')}  {msg}"
    s["log"].append(line)
    print(line)


def job_status(jid: str) -> dict:
    return http("GET", f"/jobs/{jid}")


def groups(spec: dict) -> list[tuple[str, dict]]:
    return [("event", spec["event"]), ("comparator", spec["comparator"])]


# ---------------------------------------------------------------- steps
def step_scan(sd: Path, spec: dict, s: dict) -> None:
    """1. Exposure scan per group (scan only: impossible thresholds skip the history fetch)."""
    cfg = spec["settings"]
    lo, hi = utc(cfg["first_t0"]), utc(cfg["last_t0"]) + int(cfg["max_days_since"]) * DAY
    for g, d in groups(spec):
        key = f"scan_{g}"
        if key in s["jobs"]:
            continue
        req = {"exposure": {"subs": d["subs"], "regex": d["regex"], "kinds": d.get("kinds", cfg["kinds"]),
                            "min_text_len": cfg["min_text_len"], "min_score": cfg["min_score"],
                            "max_exposures_scanned": 2_000_000, "max_body_chars": 3000,
                            "min_created_utc": lo, "max_created_utc": hi},
               "history": {"subs": ["*"], "mode": "index", "fetch_per_side": 1},
               "select": {"min_before": 100000, "min_after": 100000},
               "max_authors": 2_000_000, "seed": cfg["seed"], "storage": "rstore", "regex_engine": "re2"}
        (sd / "work" / f"lc_req_{key}.json").write_text(json.dumps(req, indent=1))
        s["jobs"][key] = http("POST", "/cohorts", req)["job_id"]
        note(s, f"submitted anchor scan for {d['label']}: {s['jobs'][key]}")
    s["stage"] = "scanning"


def step_check(sd: Path, spec: dict, s: dict) -> bool:
    """2. Download anchor posts; LLM check: first-hand? when did it happen (days_since)?"""
    cfg = spec["settings"]
    for g, _ in groups(spec):
        js = job_status(s["jobs"][f"scan_{g}"])
        if js["status"] in ("queued", "running"):
            print(f"  scan {g}: {js['status']} ({(js.get('summary') or {}).get('stage', '')})")
            return False
        if js["status"] != "done":
            sys.exit(f"scan {g} {js['status']}: {js.get('error')} — fix the spec, delete work/lc_state.json, rerun")
    todo = {}
    for g, d in groups(spec):
        out = sd / "work" / f"lc_exposures_{g}.ndjson"
        if not out.exists():
            n = download_ndjson(s["jobs"][f"scan_{g}"], out)
            note(s, f"{d['label']}: {n} candidate anchor posts")
        rows = read_ndjson(out)
        for r in random.Random(cfg["seed"]).sample(rows, min(5, len(rows))):   # precision spot-check
            print(f"  sample {g}: r/{r.get('subreddit')} — {(r.get('title') or r.get('body') or '')[:100]!r}")
        by = collections.defaultdict(list)
        for r in rows:
            if r.get("author") and r["author"] not in ("[deleted]", "AutoModerator"):
                by[r["author"]].append(r)
        authors = sorted(by)
        random.Random(cfg["seed"]).shuffle(authors)
        authors = sorted(authors[:int(cfg["max_check_authors"])])
        n_posts = sum(len(by[a]) for a in authors)
        if not authors:
            sys.exit(f"{d['label']}: the scan found no anchor posts — widen the regex or subs")
        todo[g] = (authors, n_posts)
    est = sum(n for _, n in todo.values()) * COST_PER_CHECK
    if s["spent_est"] + est > cfg["budget_usd"]:
        sys.exit(f"anchor check ≈ ${est:.2f} would exceed budget_usd {cfg['budget_usd']} — lower max_check_authors "
                 "(or raise budget_usd ONLY with the user's explicit OK)")
    for g, d in groups(spec):
        key = f"check_{g}"
        if key in s["jobs"]:
            continue
        authors, n_posts = todo[g]
        fields = {
            "is_event": f"true only if the POSTER says this happened to THEM (or their own household): {d['definition']}. "
                        "It must be exactly this event as defined: false for a similar but different thing (another "
                        "substance, drug, person, procedure or kind of event than the definition names — e.g. "
                        "'30 days sober' from cannabis when the definition is about alcohol) or when the post does not "
                        "make clear which one it is; false for advice to others, questions about what might happen, "
                        "someone else's story, hypotheticals, fiction, jokes, ads",
            "days_since": "integer: how many days BEFORE THIS POST it happened or started (0 = today/tonight, "
                          "'yesterday' = 1, 'last week' = 7, 'a few months ago' = 90, '2 years ago' = 730); "
                          "null if the post gives no clue",
        }
        if g == "event":
            fields.update(spec["extract_fields"])
        req = {"cohort_id": s["jobs"][f"scan_{g}"], "targets": ["exposures"],
               "select": {"min_before": 0, "min_after": 0},
               "definition": f"Each post matched a search for: {d['definition']}. Decide whether the poster "
                             "reports that it happened to them, and when.",
               "extract_fields": fields, "max_exposures": n_posts + 10, "workers": 48,
               "gemini_safety": "block_none", "authors": authors, "ignore_candidates": True,
               "max_post_chars": 2500, "batch_size": 5}
        (sd / "work" / f"lc_req_{key}.json").write_text(json.dumps(req))
        s["jobs"][key] = http("POST", "/cohort_labels", req)["job_id"]
        s["spent_est"] += n_posts * COST_PER_CHECK
        note(s, f"submitted anchor check for {d['label']} ({len(authors)} authors, {n_posts} posts): {s['jobs'][key]}")
    s["stage"] = "checking"
    return True


def build_anchors(sd: Path, spec: dict) -> dict:
    """Earliest valid first-hand, recently dated anchor per author; t0 = post − days_since."""
    cfg = spec["settings"]
    lo, hi = utc(cfg["first_t0"]), utc(cfg["last_t0"])
    per, reasons, subs = {}, {}, {}
    for g, d in groups(spec):
        exp = {r["uid"]: r for r in read_ndjson(sd / "work" / f"lc_exposures_{g}.ndjson")}
        best, why, sc = {}, collections.Counter(), collections.Counter()
        for lab in read_ndjson(sd / "work" / f"lc_check_{g}.ndjson"):
            e = exp.get(lab.get("uid"))
            if not e:
                continue
            if lab.get("is_event") not in (True, "true", "True"):
                why["not_first_hand"] += 1
                continue
            ds = lab.get("days_since")
            if not isinstance(ds, (int, float)) or ds < 0:
                why["undated"] += 1
                continue
            if ds > cfg["max_days_since"]:
                why["dated_too_long_ago"] += 1
                continue
            t0 = int(e["created_utc"] - ds * DAY)
            if not lo <= t0 <= hi:
                why["outside_date_range"] += 1
                continue
            why["valid"] += 1
            sc[e.get("subreddit", "").lower()] += 1
            a = e["author"]
            if a not in best or t0 < best[a]["t0"]:
                extra = {k: lab.get(k) for k in spec["extract_fields"]} if g == "event" else {}
                best[a] = {"author": a, "t0": t0, "label": d["label"], "uid": e["uid"],
                           "subreddit": e.get("subreddit"), "days_since": ds, **extra}
        per[g], reasons[g], subs[g] = best, dict(why), sc
    both = set(per["event"]) & set(per["comparator"])        # in both groups → in neither
    for g in per:
        for a in both:
            per[g].pop(a, None)
    topic = set()
    for g, sc in subs.items():
        tot = sum(sc.values())
        topic |= {x for x, k in sc.items() if tot and k >= 0.02 * tot and x not in GENERIC_SUBS and x}
    return {"anchors": per, "reasons": reasons, "in_both_groups": len(both), "topic_subs": sorted(topic)}


def hide_regex(spec: dict) -> str:
    """Posts matching this are never shown to the rater: by default the two ANNOUNCEMENT regexes (so the
    rater can't tell which group a person is in). Never outcome words (grief, sober, happy…): hiding
    them removes exactly the evidence being measured (a partner-death control with grief words hidden
    came out at 0)."""
    parts = [spec["event"].get("hide_regex") or spec["event"]["regex"],
             spec["comparator"].get("hide_regex") or spec["comparator"]["regex"]]
    return "|".join(f"(?:{p})" for p in parts)


def exclude_subs(design: dict) -> list[str]:
    base = json.loads((ASSETS / "exclude_subs.json").read_text())["exclude_subs"]
    return sorted(set(base) | set(design["topic_subs"]))


def step_fetch(sd: Path, spec: dict, s: dict) -> bool:
    """3. Build anchors → one history fetch for both groups (index fetch of the two windows; free)."""
    cfg = spec["settings"]
    for g, _ in groups(spec):
        out = sd / "work" / f"lc_check_{g}.ndjson"
        if out.exists():
            continue
        js = job_status(s["jobs"][f"check_{g}"])
        if js["status"] in ("queued", "running"):
            print(f"  anchor check {g}: {js['status']}")
            return False
        if js["status"] != "done":
            sys.exit(f"anchor check {g} {js['status']}: {js.get('error')}")
        download_ndjson(s["jobs"][f"check_{g}"], out)
        s["spent_actual"] = s.get("spent_actual", 0) + float((js.get("summary") or {}).get("cost_usd") or 0)
    design = build_anchors(sd, spec)
    rng = random.Random(cfg["seed"])
    anchors = []
    for g, d in groups(spec):
        people = sorted(design["anchors"][g].values(), key=lambda x: x["author"])
        rng.shuffle(people)
        anchors += people[:int(cfg["max_fetch"])]
        note(s, f"{d['label']}: {len(people)} valid anchored people {design['reasons'][g]}")
    (sd / "work" / "lc_anchors.json").write_text(json.dumps({**design, "fetched": anchors}, indent=0))
    for g, d in groups(spec):
        if not design["anchors"][g]:
            sys.exit(f"{d['label']}: no valid anchors — loosen max_days_since/date range or widen the regex")
    req = {"anchors": [{"author": a["author"], "t0": a["t0"], "label": a["label"]} for a in anchors],
           "history": {"subs": ["*"], "mode": "index", "fetch_per_side": 100, "min_text_len": 60,
                       "max_body_chars": 2000},
           "select": dict(WINDOWS, exclude_subs=exclude_subs(design), other_min_len=60, min_before=3, min_after=3),
           "max_authors": 100000, "seed": cfg["seed"], "storage": "rstore"}
    (sd / "work" / "lc_req_fetch.json").write_text(json.dumps(req))
    s["jobs"]["fetch"] = http("POST", "/cohorts", req)["job_id"]
    note(s, f"submitted history fetch for {len(anchors)} people: {s['jobs']['fetch']}")
    s["stage"] = "fetching"
    return True


def pair_select(spec: dict, design: dict) -> dict:
    return dict(WINDOWS, **HYGIENE, exclude_subs=exclude_subs(design), exclude_post_regex=hide_regex(spec))


def step_rate(sd: Path, spec: dict, s: dict) -> bool:
    """4. Who has ≥ 3 posts in both windows → blind pair ratings (billable)."""
    cfg = spec["settings"]
    js = job_status(s["jobs"]["fetch"])
    if js["status"] in ("queued", "running"):
        print(f"  history fetch: {js['status']} ({(js.get('summary') or {}).get('stage', '')})")
        return False
    if js["status"] != "done":
        sys.exit(f"history fetch {js['status']}: {js.get('error')}")
    design = json.loads((sd / "work" / "lc_anchors.json").read_text())
    sel = pair_select(spec, design)
    res = http("POST", f"/cohorts/{s['jobs']['fetch']}/select", dict(sel, selected_only=True), timeout=1800)
    label_of = {a["author"]: g for g in ("event", "comparator") for a in design["anchors"][g].values()}
    qual = collections.defaultdict(list)
    for u in res.get("users", []):
        g = label_of.get(u["author"])
        if g and u.get("selected", True):
            qual[g].append(u["author"])
    rng = random.Random(cfg["seed"])
    plan = {}
    for g, d in groups(spec):
        q = sorted(qual[g])
        rng.shuffle(q)
        plan[g] = sorted(q[:int(cfg["max_rated"])])
    s["qualifying"] = {g: len(qual[g]) for g in qual}
    est = sum(len(v) for v in plan.values()) * COST_PER_PERSON
    if s["spent_est"] + est > cfg["budget_usd"]:
        sys.exit(f"rating {[len(v) for v in plan.values()]} people (of {s['qualifying']} qualifying) ≈ ${est:.2f} "
                 f"would exceed budget_usd {cfg['budget_usd']} (spent ≈ ${s['spent_est']:.2f}) — lower max_rated, "
                 "or raise budget_usd ONLY with the user's explicit OK")
    for g, d in groups(spec):
        note(s, f"{d['label']}: {len(qual[g])} people with ≥3 posts in both windows; rating {len(plan[g])}")
    if min(len(v) for v in plan.values()) < MIN_GROUP_N:
        note(s, f"WARNING: fewer than {MIN_GROUP_N} qualifying people in a group — results will be "
                "descriptive only (see LIFE_COURSE.md: thin supply)")
    rubric = (ASSETS / "pair_rubric.txt").read_text()
    for g, d in groups(spec):
        key = f"rate_{g}"
        if key in s["jobs"] or not plan[g]:
            continue
        req = dict(RATER, cohort_id=s["jobs"]["fetch"], targets=["pairs"], select=sel, authors=plan[g],
                   pair_system_prompt=rubric)
        (sd / "work" / f"lc_req_{key}.json").write_text(json.dumps(req))
        s["jobs"][key] = http("POST", "/cohort_labels", req)["job_id"]
        s["spent_est"] += len(plan[g]) * COST_PER_PERSON
        note(s, f"submitted ratings for {d['label']} ({len(plan[g])} people): {s['jobs'][key]}")
    s["stage"] = "rating"
    return True


def step_collect(sd: Path, spec: dict, s: dict) -> bool:
    for g, _ in groups(spec):
        out = sd / "work" / f"lc_pairs_{g}.ndjson"
        if out.exists() or f"rate_{g}" not in s["jobs"]:
            continue
        js = job_status(s["jobs"][f"rate_{g}"])
        if js["status"] in ("queued", "running"):
            sm = js.get("summary") or {}
            print(f"  ratings {g}: {js['status']} {sm.get('done', '')}/{sm.get('items', '')}")
            return False
        if js["status"] != "done":
            sys.exit(f"ratings {g} {js['status']}: {js.get('error')}")
        download_ndjson(s["jobs"][f"rate_{g}"], out)
        s["spent_actual"] = s.get("spent_actual", 0) + float((js.get("summary") or {}).get("cost_usd") or 0)
    s["stage"] = "rated"
    return True


# ---------------------------------------------------------------- analysis
def person_values(rows: list[dict], dim: str) -> dict[str, tuple[int, float]]:
    """author → (rounded start score, mean change) for people passing the evidence gate."""
    by = collections.defaultdict(list)
    for r in rows:
        if r.get("target") == "pair" or "change" in r:
            by[r.get("author")].append(r)
    out = {}
    for a, xs in by.items():
        if not a or len(xs) < 2:
            continue
        if not all(not x.get("insufficient") and x.get("change") is not None
                   and (x.get("n_evidence_before") or 0) >= MIN_EVIDENCE
                   and (x.get("n_evidence_after") or 0) >= MIN_EVIDENCE for x in xs):
            continue
        v = []
        for x in xs:
            if dim == "wellbeing":
                v.append((x.get("score_before"), x["change"]))
                continue
            dd = (x.get("dims") or {}).get(dim) or {}
            if dd.get("n_ev_before", 1) >= 1 and dd.get("n_ev_after", 1) >= 1 and dd.get("change") is not None:
                v.append((dd.get("before"), dd["change"]))
        if len(v) == len(xs) and all(b is not None for b, _ in v):
            out[a] = (round(st.mean(b for b, _ in v)), st.mean(c for _, c in v))
    return out


def _mean(xs):
    return sum(x for _, x in xs) / len(xs)


def _matched(t, c):
    """Difference after re-weighting the comparator to the group's starting-score mix."""
    bins = collections.defaultdict(list)
    for b, x in c:
        bins[b].append(x)
    s = w = 0.0
    for b, k in collections.Counter(b for b, _ in t).items():
        if bins.get(b):
            s += k * sum(bins[b]) / len(bins[b])
            w += k
    return _mean(t) - s / w if w else None


def _boot(stat, gs, B=2000, seed=7):
    rng = random.Random(seed)
    est = stat(*gs)
    bs = sorted(v for v in (stat(*[[rng.choice(g) for _ in g] for g in gs]) for _ in range(B)) if v is not None)
    q = lambda p: bs[int(p * (len(bs) - 1))]
    return [round(est, 2), round(q(.025), 2), round(q(.975), 2)] if est is not None and bs else None


def leakage(rows: list[dict], rx: str) -> dict:
    """Share of people whose listed after-period (vs before-period) events name the hidden topic."""
    pat = re.compile(rx, re.I)
    seen, hit_a, hit_b = set(), 0, 0
    for r in rows:
        a = r.get("author")
        if not a or a in seen:
            continue
        seen.add(a)
        hit_a += any(pat.search(e or "") for e in r.get("events_after") or [])
        hit_b += any(pat.search(e or "") for e in r.get("events_before") or [])
    n = len(seen) or 1
    return {"people": len(seen), "after_pct": round(100 * hit_a / n, 1), "before_pct": round(100 * hit_b / n, 1)}


def analyze(sd: Path, spec: dict, s: dict) -> dict:
    ev, cp = spec["event"]["label"], spec["comparator"]["label"]
    rows = {g: read_ndjson(sd / "work" / f"lc_pairs_{g}.ndjson") for g in ("event", "comparator")}
    res = {"event": ev, "comparator": cp, "scale": "0-10, change = after − before (1→3 y after vs 3→1.5 y before)",
           "rated_people": {g: len({r.get('author') for r in v}) for g, v in rows.items()},
           "qualifying_people": s.get("qualifying"), "dims": {}}
    for dim in DIMS:
        T = list(person_values(rows["event"], dim).values())
        C = list(person_values(rows["comparator"], dim).values())
        d = {"n_event": len(T), "n_comparator": len(C)}
        if len(T) >= MIN_GROUP_N and len(C) >= MIN_GROUP_N:
            d["event_change"] = _boot(lambda t: _mean(t), [T])
            d["comparator_change"] = _boot(lambda c: _mean(c), [C])
            d["vs_comparator"] = _boot(lambda t, c: _mean(t) - _mean(c), [T, C])
            d["vs_comparator_matched_start"] = _boot(_matched, [T, C])
            d["start_event"] = round(st.mean(b for b, _ in T), 2)
            d["start_comparator"] = round(st.mean(b for b, _ in C), 2)
            for name, xs in (("event", T), ("comparator", C)):
                d[f"pct_better_{name}"] = round(100 * sum(x > 0 for _, x in xs) / len(xs))
                d[f"pct_worse_{name}"] = round(100 * sum(x < 0 for _, x in xs) / len(xs))
        else:
            d["note"] = f"fewer than {MIN_GROUP_N} people passed the evidence gate in a group — not estimated"
        res["dims"][dim] = d
    # subgroups from the caller's extract_fields (e.g. role: mother/father), wellbeing only
    anc_path = sd / "work" / "lc_anchors.json"
    if spec["extract_fields"] and anc_path.exists():
        anc = json.loads(anc_path.read_text())["anchors"]["event"]
        T = person_values(rows["event"], "wellbeing")
        C = list(person_values(rows["comparator"], "wellbeing").values())
        res["subgroups"] = {}
        for f in spec["extract_fields"]:
            vals = collections.defaultdict(list)
            for a, v in T.items():
                key = (anc.get(a) or {}).get(f)
                if isinstance(key, (str, bool, int)) and str(key).strip():
                    vals[str(key).strip().lower()].append(v)
            res["subgroups"][f] = {k: {"n": len(v), "vs_comparator": _boot(lambda t, c: _mean(t) - _mean(c), [v, C])}
                                   for k, v in sorted(vals.items()) if len(v) >= MIN_GROUP_N and len(C) >= MIN_GROUP_N}
    rx = spec["event"].get("topic_regex") or spec["event"].get("hide_regex") or spec["event"]["regex"]
    res["leakage_event_topic"] = {g: leakage(rows[g], rx) for g in rows}
    res["leakage_regex"] = rx
    res["gate"] = f"both A/B orders sufficient with ≥{MIN_EVIDENCE} own-state evidence posts per period"
    res["cost_usd_reported"] = round(s.get("spent_actual", 0), 2)
    (sd / "work" / "lc_results.json").write_text(json.dumps(res, indent=1))
    lines = [f"{ev} vs {cp} — {res['scale']}",
             f"rated people: {res['rated_people']}  (qualifying: {res['qualifying_people']})", ""]
    for dim, d in res["dims"].items():
        if "vs_comparator" in d:
            v, m = d["vs_comparator"], d["vs_comparator_matched_start"]
            lines.append(f"{dim:18s} n={d['n_event']}/{d['n_comparator']}  vs comparator {v[0]:+.2f} "
                         f"({v[1]:+.2f}…{v[2]:+.2f})  matched {m[0]:+.2f} ({m[1]:+.2f}…{m[2]:+.2f})  "
                         f"better/worse {d['pct_better_event']}/{d['pct_worse_event']}% vs "
                         f"{d['pct_better_comparator']}/{d['pct_worse_comparator']}%")
        else:
            lines.append(f"{dim:18s} n={d['n_event']}/{d['n_comparator']}  {d['note']}")
    for f, groups_ in (res.get("subgroups") or {}).items():
        for k, d in groups_.items():
            v = d["vs_comparator"]
            lines.append(f"subgroup {f}={k}: n={d['n']}  wellbeing vs comparator {v[0]:+.2f} ({v[1]:+.2f}…{v[2]:+.2f})")
    lk = res["leakage_event_topic"]["event"]
    lc_ = res["leakage_event_topic"]["comparator"]
    lines += ["", f"leakage: event topic named in after-period events for {lk['after_pct']}% "
                  f"(before-period {lk['before_pct']}%) of the event group; comparator {lc_['after_pct']}% "
                  f"/ {lc_['before_pct']}%"]
    (sd / "work" / "lc_results.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return res


# ---------------------------------------------------------------- driver
STEPS = ["scan", "check", "fetch", "rate"]                    # stage that a reset to each step re-enters
RESET_STAGE = {"scan": "new", "check": "scanning", "fetch": "checking", "rate": "fetching"}
STEP_FILES = {"scan": ["lc_exposures_*"], "check": ["lc_check_*", "lc_anchors.json"], "fetch": [],
              "rate": ["lc_pairs_*", "lc_results.*"]}


def reset(sd: Path, step: str) -> None:
    """Forget `step` and everything after it (jobs + downloaded files); the next `next` redoes them."""
    s = load_state(sd)
    for st_ in STEPS[STEPS.index(step):]:
        for k in [k for k in s["jobs"] if k == st_ or k.startswith(st_ + "_")]:
            del s["jobs"][k]
        for pat in STEP_FILES[st_]:
            for f in (sd / "work").glob(pat):
                f.unlink()
    s["stage"] = RESET_STAGE[step]
    note(s, f"reset to step {step} (stage {s['stage']})")
    save_state(sd, s)


def advance(sd: Path) -> str:
    spec = load_spec(sd)
    s = load_state(sd)
    try:
        if s["stage"] == "new":
            step_scan(sd, spec, s)
        elif s["stage"] == "scanning":
            step_check(sd, spec, s)
        elif s["stage"] == "checking":
            step_fetch(sd, spec, s)
        elif s["stage"] == "fetching":
            step_rate(sd, spec, s)
        elif s["stage"] == "rating":
            if step_collect(sd, spec, s):
                analyze(sd, spec, s)
                s["stage"] = "done"
                note(s, "DONE — results in work/lc_results.txt / lc_results.json")
        elif s["stage"] == "done":
            print("done — results in work/lc_results.txt")
    finally:
        save_state(sd, s)
    return s["stage"]


def main() -> None:
    cmds = ("next", "wait", "status", "analyze", "validate", "reset")
    if len(sys.argv) < 3 or sys.argv[1] not in cmds or (sys.argv[1] == "reset") != (len(sys.argv) == 4):
        print(__doc__)
        sys.exit(2)
    cmd, sd = sys.argv[1], Path(sys.argv[2]).expanduser().resolve()
    (sd / "work").mkdir(parents=True, exist_ok=True)
    if cmd == "reset":
        if sys.argv[3] not in STEPS:
            sys.exit(f"reset step must be one of {STEPS}")
        reset(sd, sys.argv[3])
    elif cmd == "validate":
        spec = load_spec(sd)
        print(json.dumps({k: spec[k] for k in ("event", "comparator", "settings")}, indent=1))
        print("spec OK")
    elif cmd == "status":
        s = load_state(sd)
        print(f"stage: {s['stage']}   est. spend ≈ ${s['spent_est']:.2f}   jobs: {s['jobs']}")
        print("\n".join(s["log"][-12:]))
    elif cmd == "analyze":
        analyze(sd, load_spec(sd), load_state(sd))
    elif cmd == "next":
        advance(sd)
    else:                                   # wait: keep advancing for ≤ 8 min (stays under tool timeouts)
        end = time.time() + 480
        while True:
            before = load_state(sd)["stage"]
            stage = advance(sd)
            if stage == "done" or time.time() > end:
                break
            if stage == before:
                time.sleep(30)
        if stage != "done":
            print(f"still {stage} — run `wait` again later (jobs keep running on the server)")


if __name__ == "__main__":
    main()
