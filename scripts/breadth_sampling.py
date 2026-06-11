#!/usr/bin/env python3
"""Breadth-mode corpus builder — the starvation-free sampling layer.

Empirically chosen over 4 alternative strategies across 5 topics. The principle:

  1. SCAN every candidate subreddit fully into one pool (per-sub cap + merge, NOT a single global
     cap that starves whichever subs are scanned last).
  2. PREVALENCE / popularity is tallied over that FULL pool — exact, deterministic, no sampling.
  3. The expensive LLM stages (discovery + rate-the-stories) run on a SAMPLE built by
     `balanced_breadth_sample()` below, which guarantees:
       - every present sub a floor (so no community is dropped),
       - every treatment a floor, RAREST FIRST (so the long tail gets enough posts to rate),
       - a prevalence-faithful random fill for the remainder.
     => rare alternatives are oversampled for rating WITHOUT distorting prevalence (which comes
        from the full pool, not the sample).

Pure-Python, deterministic (fixed seed). No network, no studyd dependency — unit-testable.
"""
import random, re


def alias_pattern(aliases):
    """Word-boundary regex over a treatment's aliases (matches only when not flanked by [a-z0-9])."""
    parts = sorted({re.escape(a.lower()) for a in aliases if a}, key=len, reverse=True)
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(parts) + r")(?![a-z0-9])")


def _text(rec, _cap=800):
    """Lowercased, length-capped, memoized matching text for a record (title + body)."""
    t = rec.get("_match_text")
    if t is None:
        t = ((rec.get("title") or "") + ". " + (rec.get("body") or ""))[:_cap].lower()
        rec["_match_text"] = t
    return t


def balanced_breadth_sample(universe, n, treatments=None, *, sub_floor=80, per_treatment=20, seed=1):
    """Build an n-record sample from `universe` (dict: sub -> list[record]) for the LLM stages.

    universe     : {subreddit: [record, ...]} — the full scanned pool, per sub.
    n            : target sample size.
    treatments   : optional list of {"name", "aliases"(opt), "univ_count"(opt)}; enables the
                   rare-treatment floor. Each gets a compiled pattern if missing. If None, falls
                   back to sub-floor + random fill (still starvation-free, no tail oversampling).
    sub_floor    : min records taken from each sub that has them (every community present).
    per_treatment: min mentioning records each treatment should reach in the sample (rarest first).
    seed         : RNG seed (determinism).

    Returns a list of <= n records (dedup by 'uid').
    """
    rng = random.Random(seed)
    out, ids = [], set()

    def add(rec):
        u = rec.get("uid")
        if u in ids:
            return False
        out.append(rec); ids.add(u); return True

    # 1) per-sub floor — every community gets a foothold (no starvation)
    for sub, recs in universe.items():
        pool = recs[:]; rng.shuffle(pool); c = 0
        for r in pool:
            if c >= sub_floor or len(out) >= n:
                break
            if add(r):
                c += 1

    flat = [r for recs in universe.values() for r in recs]
    rng.shuffle(flat)

    # 2) per-treatment floor — rarest treatments first, so the long tail gets enough to rate
    if treatments:
        prepared = []
        for t in treatments:
            pat = t.get("pat") or alias_pattern(t.get("aliases") or [t["name"]])
            prepared.append((t.get("univ_count", 0), pat))
        for _, pat in sorted(prepared, key=lambda x: x[0]):  # rarest in the universe first
            if len(out) >= n:
                break
            have = sum(1 for r in out if pat.search(_text(r)))
            if have >= per_treatment:
                continue
            for r in flat:
                if have >= per_treatment or len(out) >= n:
                    break
                if r.get("uid") not in ids and pat.search(_text(r)):
                    add(r); have += 1

    # 3) prevalence-faithful random fill for the remainder
    for r in flat:
        if len(out) >= n:
            break
        add(r)

    for r in out:            # don't leak the memo field downstream
        r.pop("_match_text", None)
    return out[:n]
