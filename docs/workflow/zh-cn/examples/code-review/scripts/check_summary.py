#!/usr/bin/env python3
"""Validate that a code-review summary report is complete.

Usage:
    python check_summary.py <report.md>

Checks the report contains the required sections and at least one finding.
Exits 0 when valid, 1 otherwise (prints the reason to stderr).
"""

import re
import sys

REQUIRED_SECTIONS = ["致命问题", "警告", "提示", "总体结论"]


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: check_summary.py <report.md>", file=sys.stderr)
        return 1
    path = sys.argv[1]
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print(f"cannot read report: {exc}", file=sys.stderr)
        return 1
    if not text.strip():
        print("report is empty", file=sys.stderr)
        return 1
    missing = [s for s in REQUIRED_SECTIONS if s not in text]
    if missing:
        print(f"missing sections: {', '.join(missing)}", file=sys.stderr)
        return 1
    if not re.search(r"(error|warning|note)", text, flags=re.IGNORECASE):
        print("no findings found in report", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
