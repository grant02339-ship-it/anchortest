"""Extracts the raw-content submission URL from a GitHub issue-form body.

Reads the issue body from the ISSUE_BODY environment variable -- NEVER interpolate untrusted issue content
directly into a shell command (`${{ github.event.issue.body }}` embedded in a `run:` block is a documented
GitHub Actions script-injection vector). The workflow that calls this passes it via `env:` instead, which is
the safe pattern.

Only accepts a URL from a small allowlist of raw-content hosts -- an HTML page URL (a plain gist.github.com
link, say) won't `curl` down to usable Python source, and restricting the host list also bounds what this
step can be tricked into fetching.
"""
from __future__ import annotations

import os
import re

ALLOWED_HOST_PREFIXES = ("https://gist.githubusercontent.com/", "https://raw.githubusercontent.com/")


def extract_url(body: str) -> str:
    """The issue-forms body renders each field as '### <label>\\n\\n<value>\\n\\n...'. Pull the value
    under the 'Link to your submission' field; return "" if missing or not an allowed host."""
    m = re.search(r"###\s*Link to your submission\s*\n+\s*(\S+)", body or "")
    if not m:
        return ""
    url = m.group(1).strip()
    return url if url.startswith(ALLOWED_HOST_PREFIXES) else ""


if __name__ == "__main__":
    url = extract_url(os.environ.get("ISSUE_BODY", ""))
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"url={url}\n")
    print(f"extracted url: {url!r}")
