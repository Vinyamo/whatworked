"""Offline tests for scripts/life_course.py (no server). Run: python3 -m unittest discover tests"""
import importlib.util
import json
import random
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec_ = importlib.util.spec_from_file_location("life_course", ROOT / "scripts" / "life_course.py")
lc = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(lc)

SPEC = {"event": {"label": "partner_died", "regex": r"\bmy (wife|husband) (died|passed away)\b",
                  "definition": "the poster's own spouse died", "hide_regex": r"\b(widow|grief|died)\b"},
        "comparator": "new_dog", "extract_fields": {"who_died": "husband or wife"}}


def pair(author, change, start=5, order="before_first", ev=4, insufficient=False, events_after=()):
    dims = {d: {"before": start, "after": start + change, "change": change, "n_ev_before": 2, "n_ev_after": 2}
            for d in lc.DIMS}
    return {"target": "pair", "pair_version": 3, "author": author, "order": order, "insufficient": insufficient,
            "n_evidence_before": ev, "n_evidence_after": ev, "score_before": start, "score_after": start + change,
            "change": change, "dims": dims, "events_before": [], "events_after": list(events_after)}


class StudyDir:
    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sd = Path(self.tmp.name)
        (self.sd / "work").mkdir()
        (self.sd / "work" / "lc_spec.json").write_text(json.dumps(SPEC))
        return self.sd

    def __exit__(self, *a):
        self.tmp.cleanup()


def write_ndjson(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


class TestSpec(unittest.TestCase):
    def test_defaults_and_comparator(self):
        with StudyDir() as sd:
            s = lc.load_spec(sd)
        self.assertEqual(s["comparator"]["label"], "new_dog")
        self.assertEqual(s["settings"]["max_days_since"], 60)
        self.assertEqual(s["event"]["subs"], ["*"])

    def test_rejects_lookaround_and_missing_fields(self):
        with StudyDir() as sd:
            bad = dict(SPEC, event=dict(SPEC["event"], regex=r"(?<=my )wife died"))
            (sd / "work" / "lc_spec.json").write_text(json.dumps(bad))
            with self.assertRaises(SystemExit):
                lc.load_spec(sd)
            (sd / "work" / "lc_spec.json").write_text(json.dumps({"event": {"label": "x_y"}}))
            with self.assertRaises(SystemExit):
                lc.load_spec(sd)

    def test_hide_regex_covers_both_groups(self):
        with StudyDir() as sd:
            rx = lc.hide_regex(lc.load_spec(sd))
        import re
        self.assertTrue(re.search(rx, "my grief is heavy", re.I))
        self.assertTrue(re.search(rx, "walked the puppy", re.I))
        self.assertFalse(re.search(rx, "work was fine today", re.I))


class TestAnchors(unittest.TestCase):
    def test_dating_first_hand_and_overlap(self):
        D = lc.DAY
        t = lc.utc("2018-06-01")
        with StudyDir() as sd:
            write_ndjson(sd / "work" / "lc_exposures_event.ndjson", [
                {"uid": "e1", "author": "ann", "created_utc": t, "subreddit": "widowers"},
                {"uid": "e2", "author": "ann", "created_utc": t + 400 * D, "subreddit": "widowers"},
                {"uid": "e3", "author": "bob", "created_utc": t, "subreddit": "GriefSupport"},
                {"uid": "e4", "author": "cat", "created_utc": t, "subreddit": "widowers"},
                {"uid": "e5", "author": "dan", "created_utc": t, "subreddit": "widowers"},
                {"uid": "e6", "author": "eve", "created_utc": lc.utc("2025-03-01"), "subreddit": "widowers"},
            ])
            write_ndjson(sd / "work" / "lc_check_event.ndjson", [
                {"uid": "e1", "is_event": True, "days_since": 10, "who_died": "husband"},
                {"uid": "e2", "is_event": True, "days_since": 3},
                {"uid": "e3", "is_event": False, "days_since": 1},          # not first-hand
                {"uid": "e4", "is_event": True, "days_since": 400},        # dated too long ago
                {"uid": "e5", "is_event": True, "days_since": 5},          # also a dog owner → dropped
                {"uid": "e6", "is_event": True, "days_since": 2},          # after last_t0
            ])
            write_ndjson(sd / "work" / "lc_exposures_comparator.ndjson", [
                {"uid": "c1", "author": "dan", "created_utc": t, "subreddit": "puppy101"},
                {"uid": "c2", "author": "fay", "created_utc": t, "subreddit": "puppy101"}])
            write_ndjson(sd / "work" / "lc_check_comparator.ndjson", [
                {"uid": "c1", "is_event": True, "days_since": 0}, {"uid": "c2", "is_event": "true", "days_since": 7}])
            d = lc.build_anchors(sd, lc.load_spec(sd))
        ev = d["anchors"]["event"]
        self.assertEqual(sorted(ev), ["ann"])
        self.assertEqual(ev["ann"]["t0"], t - 10 * D)                      # earliest, re-dated
        self.assertEqual(ev["ann"]["who_died"], "husband")
        self.assertEqual(sorted(d["anchors"]["comparator"]), ["fay"])
        self.assertEqual(d["in_both_groups"], 1)
        r = d["reasons"]["event"]
        self.assertEqual((r["not_first_hand"], r["dated_too_long_ago"], r["outside_date_range"]), (1, 1, 1))
        self.assertIn("widowers", d["topic_subs"])


class TestAnalysis(unittest.TestCase):
    def test_gate_and_effect(self):
        rng = random.Random(3)
        ev, cp = [], []
        for i in range(80):
            c = rng.choice([-2, -1, -1, 0])
            ev += [pair(f"e{i}", c), pair(f"e{i}", c, order="after_first")]
            d = rng.choice([-1, 0, 0, 1])
            cp += [pair(f"c{i}", d), pair(f"c{i}", d, order="after_first")]
        ev += [pair("thin", -5, ev=2), pair("thin", -5, ev=2, order="after_first")]          # fails the gate
        ev += [pair("half", -5), pair("half", -5, insufficient=True, order="after_first")]  # one order insufficient
        ev += [pair("solo", -5)]                                                             # one order only
        ev[0]["events_after"] = ["became a widow"]
        with StudyDir() as sd:
            write_ndjson(sd / "work" / "lc_pairs_event.ndjson", ev)
            write_ndjson(sd / "work" / "lc_pairs_comparator.ndjson", cp)
            res = lc.analyze(sd, lc.load_spec(sd), {"qualifying": {"event": 83, "comparator": 80}})
            self.assertTrue((sd / "work" / "lc_results.txt").exists())
        w = res["dims"]["wellbeing"]
        self.assertEqual((w["n_event"], w["n_comparator"]), (80, 80))
        est, lo, hi = w["vs_comparator"]
        self.assertLess(hi, 0)                       # clearly worse than the comparator
        self.assertTrue(lo <= est <= hi)
        self.assertEqual(res["leakage_event_topic"]["event"]["after_pct"], round(100 / 83, 1))

    def test_small_groups_not_estimated(self):
        with StudyDir() as sd:
            write_ndjson(sd / "work" / "lc_pairs_event.ndjson",
                         [pair("a", 1), pair("a", 1, order="after_first")])
            write_ndjson(sd / "work" / "lc_pairs_comparator.ndjson",
                         [pair("b", 0), pair("b", 0, order="after_first")])
            res = lc.analyze(sd, lc.load_spec(sd), {})
        self.assertNotIn("vs_comparator", res["dims"]["wellbeing"])
        self.assertIn("note", res["dims"]["wellbeing"])


class TestReset(unittest.TestCase):
    def test_reset_drops_later_steps(self):
        with StudyDir() as sd:
            st = {"stage": "rating", "jobs": {"scan_event": "c1", "check_event": "l1", "fetch": "c2",
                                              "rate_event": "l2"}, "log": [], "spent_est": 1.0}
            lc.save_state(sd, st)
            (sd / "work" / "lc_pairs_event.ndjson").write_text("{}\n")
            (sd / "work" / "lc_check_event.ndjson").write_text("{}\n")
            lc.reset(sd, "rate")
            s = lc.load_state(sd)
            self.assertEqual(s["stage"], "fetching")
            self.assertEqual(sorted(s["jobs"]), ["check_event", "fetch", "scan_event"])
            self.assertFalse((sd / "work" / "lc_pairs_event.ndjson").exists())
            self.assertTrue((sd / "work" / "lc_check_event.ndjson").exists())
            lc.reset(sd, "check")
            s = lc.load_state(sd)
            self.assertEqual((s["stage"], sorted(s["jobs"])), ("scanning", ["scan_event"]))


class TestAssets(unittest.TestCase):
    def test_assets_present(self):
        subs = json.loads((lc.ASSETS / "exclude_subs.json").read_text())["exclude_subs"]
        self.assertGreater(len(subs), 400)
        self.assertIn("dogs", subs)
        self.assertIn("STEP 1", (lc.ASSETS / "pair_rubric.txt").read_text())


if __name__ == "__main__":
    unittest.main()
