#!/usr/bin/env python3
"""Categories discovery — playbook step 5.5.

Given a completed scan, propose a closed list of 8-15 topic-axis categories for the
real scoring run. Two LLM calls under the hood: a discovery scoring with a topic-axis-only
prompt, then label consolidation via /consolidate_labels.

Usage:
    python scripts/discover_categories.py SCAN_ID \\
        --topic "SSRI / SNRI withdrawal experiences" \\
        --audience "adult considering tapering, weighing severity of withdrawal" \\
        [--target-n 120] [--rel-desc "..."] [--qual-desc "..."] \\
        [--model gpt-4o-mini]

Credentials: ~/.claude/.studyd_credentials (JSON with url/username/password; the
agent creates it on first run), or STUDYD_URL/STUDYD_USER/STUDYD_PASS env vars.
Writes JSON output to ./discovery_<scan_id>_<YYYY-MM-DD>.json. Prints the proposed
categories table to stdout.

Cost: ~$0.07/study. Wall-clock: ~60-90s. Defaults are the empirical knee from a
14-variant parameter sweep.
"""
from __future__ import annotations
import argparse, base64, json, os, sys, time, urllib.request, urllib.error
from collections import Counter
from datetime import date
from pathlib import Path

CREDENTIALS_PATH = Path.home() / ".claude" / ".studyd_credentials"
DEFAULT_URL = "https://whatworked.vinyamo.com"


def load_env() -> tuple[str, str]:
    """Return (url, b64(user:pass)) from the credentials file or env vars."""
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
            sys.exit(f"no credentials: create {CREDENTIALS_PATH} (the agent does this "
                     "on first run) or set STUDYD_USER/STUDYD_PASS")
    return url.rstrip("/"), base64.b64encode(f"{user}:{pw}".encode()).decode("ascii")


def http_get(url: str, tok: str, path: str) -> dict:
    req = urllib.request.Request(url + path, headers={"Authorization": f"Basic {tok}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def http_post(url: str, tok: str, path: str, body: dict, timeout: int = 600) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url + path, data=data, method="POST",
                                  headers={"Authorization": f"Basic {tok}",
                                           "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def http_get_text(url: str, tok: str, path: str) -> str:
    req = urllib.request.Request(url + path, headers={"Authorization": f"Basic {tok}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode()


# ---------- prompt templates ----------

DISCOVERY_PROMPT = """You score Reddit posts as user-experience reports for a research study on: {topic}.

IMPORTANT: Score posts that report a NEGATIVE, NULL, or MIXED experience just as highly as posts reporting a positive experience, provided the report is genuine and specific.

For each post in the batch, return one JSON object with these keys:
- i (integer index, starting at 0)
- rel (Relevance, integer 0-10): {rel_desc}
- qual (Quality, integer 0-10): {qual_desc}
- sentiment (Sentiment, integer 0-10): 0=strongly negative, 5=mixed/null, 10=strongly positive. Use the full 0-10 range.
- cat: a short snake_case label that names what the post is *about* — its topic axis. CRITICAL RULES:
   * NEVER use sentiment-style labels like "negative_experience", "positive_experience", "mixed_experience", "success_story". Sentiment is captured separately.
   * NEVER use vacuous labels like "experience", "symptoms", "treatment", "medication" alone. Be specific.
   * DO use labels naming a specific sub-aspect distinguishing this post from others on the topic: a specific drug/supplement/protocol name, a specific symptom, a specific method (taper schedule, route of administration, dose), a specific sub-population (postpartum, athletes, comorbid condition).
   * Reuse the same label across posts that share the same sub-aspect. Aim for 10-20 distinct labels across the whole batch, each capturing a real sub-axis.
- brief: one concise sentence capturing what the post says (include direction of effect).

Return a single JSON object: {{"results": [<one object per post, in input order>]}}.
All score fields (rel, qual, sentiment) MUST be integers."""


# ---------- workflow ----------

def discovery_score(url: str, tok: str, *, scan_id: str, topic: str, audience: str,
                    rel_desc: str, qual_desc: str, target_n: int, model: str,
                    topic_keywords: list[str]) -> str:
    body = {
        "scan_id": scan_id, "topic": topic, "audience": audience,
        "model": model,
        "system_prompt": DISCOVERY_PROMPT.format(topic=topic, rel_desc=rel_desc, qual_desc=qual_desc),
        "prompt_style": "default",
        "shuffle_batch": True, "batch_size": 8, "workers": 16,
        "target_n": target_n, "early_stop_factor": 1.3, "max_scored_factor": 30.0,
        "order": "random", "seed": 1,
        "dimensions": [
            {"key": "rel",       "label": "Relevance", "desc": rel_desc,  "min_pct": 0.6, "scale": 10},
            {"key": "qual",      "label": "Quality",   "desc": qual_desc, "min_pct": 0.6, "scale": 10},
            {"key": "sentiment", "label": "Sentiment", "desc": "0=neg,5=mixed,10=pos", "min_pct": 0.0, "scale": 10},
        ],
        "filter": {"op": "both", "min_sum_pct": 0.4},
        "categories": [],            # discovery: free-form labels
        "per_sub_max_pct": 0.0,      # no demotion
        "per_category_quota_pct": 0.0,
        "per_category_min_pct": 0.0,
        "sentiment_quota": None,
        "topic_keywords": topic_keywords,
        "dedup_content": True,
    }
    resp = http_post(url, tok, "/scores", body)
    return resp["job_id"]


def wait_for(url: str, tok: str, job_id: str, *, max_wait: int = 600) -> dict:
    start = time.time()
    while True:
        try:
            j = http_get(url, tok, f"/jobs/{job_id}")
            elapsed = int(time.time() - start)
            status = j["status"]
            n = (j.get("summary") or {}).get("passed", 0)
            print(f"  [{elapsed:>3}s] {job_id} {status} passed={n}", flush=True)
            if status in ("done", "failed"):
                return j
        except urllib.error.URLError as e:
            print(f"  poll error (retrying): {e}", flush=True)
        if time.time() - start > max_wait:
            raise TimeoutError(f"job {job_id} did not finish in {max_wait}s")
        time.sleep(15)


def fetch_passed(url: str, tok: str, job_id: str) -> list[dict]:
    txt = http_get_text(url, tok, f"/jobs/{job_id}/results?passed_only=true&limit=10000")
    return [json.loads(line) for line in txt.splitlines() if line.strip()]


def consolidate(url: str, tok: str, *, label_counts: dict, topic: str, target_n_categories: int,
                model: str) -> dict:
    body = {
        "labels": [{"label": k, "count": v} for k, v in sorted(label_counts.items(), key=lambda x: -x[1])],
        "topic": topic,
        "target_n_categories": target_n_categories,
        "model": model,
    }
    return http_post(url, tok, "/consolidate_labels", body, timeout=420)


def assemble_categories(records: list[dict], canonical: list[dict]) -> tuple[list[dict], int, int]:
    """Apply canonical merging back to records. Return (rows, other_count, total)."""
    var2canon = {}
    for c in canonical:
        for v in c.get("variants", []):
            var2canon[v] = c["name"]
    counts = Counter()
    sample_briefs = {}
    for r in records:
        canon = var2canon.get(r.get("cat"), "other")
        counts[canon] += 1
        if canon not in sample_briefs:
            sample_briefs[canon] = []
        if len(sample_briefs[canon]) < 2 and r.get("brief"):
            sample_briefs[canon].append(r["brief"])
    rows = []
    for name, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        rows.append({"name": name, "count": cnt, "share": cnt / len(records),
                     "sample_briefs": sample_briefs.get(name, [])})
    other = counts.get("other", 0)
    return rows, other, len(records)


# ---------- CLI ----------

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("scan_id", help="completed scan job_id")
    p.add_argument("--topic", required=True, help="specific topic question")
    p.add_argument("--audience", default="", help="audience description")
    p.add_argument("--rel-desc", default="Personal-experience report ABOUT THE SPECIFIC TOPIC. Reject (rel<5) posts that touch the area but not the topic.",
                   help="relevance dimension description")
    p.add_argument("--qual-desc", default="Information density: clear dose, timeline, mechanism, outcome. A short clear post can score 8-9.",
                   help="quality dimension description")
    p.add_argument("--target-n", type=int, default=120, help="discovery sample target")
    p.add_argument("--model", default="gpt-4o-mini", help="LLM model for discovery + consolidation")
    p.add_argument("--target-n-categories", type=int, default=12, help="aim for the consolidation step")
    p.add_argument("--topic-keywords", default="", help="comma-separated optional pre-LLM keyword filter")
    p.add_argument("--out", default=None, help="JSON output path (default: discovery_<scan>_<date>.json)")
    args = p.parse_args()

    url, tok = load_env()
    print(f"discovery for scan {args.scan_id}", flush=True)
    print(f"  topic    : {args.topic}", flush=True)
    print(f"  target_n : {args.target_n}", flush=True)
    print(f"  model    : {args.model}", flush=True)

    topic_keywords = [k.strip() for k in args.topic_keywords.split(",") if k.strip()]

    # Step 1 — submit discovery scoring
    print("\n[1/3] discovery scoring...", flush=True)
    job_id = discovery_score(url, tok, scan_id=args.scan_id, topic=args.topic, audience=args.audience,
                              rel_desc=args.rel_desc, qual_desc=args.qual_desc,
                              target_n=args.target_n, model=args.model,
                              topic_keywords=topic_keywords)
    print(f"  job_id   : {job_id}", flush=True)
    job = wait_for(url, tok, job_id)
    if job["status"] != "done":
        sys.exit(f"discovery scoring failed: {job.get('error')}")
    summary = job.get("summary") or {}

    # Step 2 — fetch + count raw labels
    print("\n[2/3] fetching passing records...", flush=True)
    records = fetch_passed(url, tok, job_id)
    label_counts = Counter(r.get("cat", "other") for r in records)
    print(f"  records       : {len(records)}", flush=True)
    print(f"  raw labels    : {len(label_counts)} distinct", flush=True)
    print(f"  scoring cost  : ${summary.get('cost_usd', 0):.3f}", flush=True)

    # Step 3 — consolidate via LLM
    print("\n[3/3] consolidating labels...", flush=True)
    cons = consolidate(url, tok, label_counts=dict(label_counts),
                       topic=args.topic, target_n_categories=args.target_n_categories,
                       model=args.model)
    canonical = cons.get("canonical") or []
    print(f"  consolidation cost: ${cons.get('cost_usd', 0):.4f}", flush=True)

    rows, other_n, total = assemble_categories(records, canonical)

    out_path = Path(args.out) if args.out else Path.cwd() / f"discovery_{args.scan_id}_{date.today():%Y-%m-%d}.json"
    out_path.write_text(json.dumps({
        "scan_id": args.scan_id, "discovery_job_id": job_id,
        "topic": args.topic, "audience": args.audience,
        "n_records": total, "raw_label_count": len(label_counts),
        "categories": rows, "other_count": other_n,
        "scoring_summary": summary, "consolidation_meta": {k: v for k, v in cons.items() if k != "canonical"},
    }, indent=2))

    print()
    print("=" * 70)
    print(f"PROPOSED CATEGORIES — {len(rows)} cats from {total} records, "
          f"{other_n*100//total}% in 'other'")
    print("=" * 70)
    print(f"{'count':>6}  {'share':>6}  {'name':<32} sample brief")
    for r in rows:
        s = (r["sample_briefs"] or [""])[0][:60].replace("\n", " ")
        print(f"  {r['count']:>4}  {r['share']*100:>5.1f}%  {r['name'][:32]:<32} {s}")
    print()
    total_cost = (summary.get("cost_usd", 0) or 0) + (cons.get("cost_usd", 0) or 0)
    print(f"total cost: ${total_cost:.3f}    output: {out_path}")
    print()
    print("Edit the proposed list before plugging into the real /scores call. ")
    print("Common edits: drop categories with count < 3, rename labels, split overly broad cats.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
