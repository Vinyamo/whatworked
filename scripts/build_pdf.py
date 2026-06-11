#!/usr/bin/env python3
"""Render a study markdown file to the final PDF deliverable.

    python3 scripts/build_pdf.py <study.md> [out.pdf]

Default output: alongside the input as <stem>.pdf. The rendering happens
server-side (POST /render_pdf, see API.md): Mermaid fences become images, the
print stylesheet is applied, and the PDF bytes come back — no local weasyprint,
Cairo, or mermaid-cli needed. Stdlib only.

Credentials: ~/.claude/.studyd_credentials (JSON with url/username/password;
created on first run by the agent), or STUDYD_URL/STUDYD_USER/STUDYD_PASS env vars.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

CREDENTIALS_PATH = Path.home() / ".claude" / ".studyd_credentials"
DEFAULT_URL = "https://whatworked.vinyamo.com"


def load_credentials() -> tuple[str, str, str]:
    """Return (url, username, password) from the credentials file or env."""
    if CREDENTIALS_PATH.exists():
        try:
            d = json.loads(CREDENTIALS_PATH.read_text())
            return d.get("url", DEFAULT_URL).rstrip("/"), d["username"], d["password"]
        except (json.JSONDecodeError, KeyError) as e:
            sys.exit(f"malformed {CREDENTIALS_PATH}: {e}")
    url = os.environ.get("STUDYD_URL", DEFAULT_URL).rstrip("/")
    user, pw = os.environ.get("STUDYD_USER"), os.environ.get("STUDYD_PASS")
    if not user or not pw:
        sys.exit(f"no credentials: create {CREDENTIALS_PATH} (the agent does this on "
                 "first run) or set STUDYD_USER/STUDYD_PASS")
    return url, user, pw


def build(md_path: str, out_path: str | None = None) -> str:
    out_path = out_path or os.path.splitext(md_path)[0] + ".pdf"
    md_text = open(md_path, encoding="utf-8").read()
    url, user, pw = load_credentials()

    body = json.dumps({"markdown": md_text,
                       "filename": os.path.basename(out_path)}).encode("utf-8")
    auth = base64.b64encode(f"{user}:{pw}".encode()).decode("ascii")
    req = urllib.request.Request(
        url + "/render_pdf", data=body, method="POST",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            pdf = r.read()
    except urllib.error.HTTPError as e:
        detail = e.read()[:300].decode("utf-8", "replace")
        sys.exit(f"render failed: HTTP {e.code} — {detail}")

    if pdf[:5] != b"%PDF-":
        sys.exit("server response is not a PDF — aborting without writing")
    with open(out_path, "wb") as f:
        f.write(pdf)
    print(f"{md_path} -> {out_path} ({len(pdf) // 1024} KB)")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: build_pdf.py <study.md> [out.pdf]")
        sys.exit(2)
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
