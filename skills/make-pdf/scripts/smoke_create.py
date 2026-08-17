#!/usr/bin/env python3
"""Smoke: create a sample .pdf and run check_pdf_basics.py.

Usage (from repo / workspace root):
  python skills/make-pdf/scripts/smoke_create.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = SCRIPT_DIR.parents[2]
OUT = WORKSPACE / "outputs" / "documents" / "pdf" / "smoke-q3-brief.pdf"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(name="BodySmoke", parent=styles["Normal"], fontSize=11, leading=14)
    )
    story = [
        Paragraph("Q3 Brief (smoke)", styles["Title"]),
        Spacer(1, 12),
        Paragraph(
            "One clear thesis paragraph for make-pdf smoke. H<sub>2</sub>O uses sub tags.",
            styles["BodySmoke"],
        ),
        PageBreak(),
        Paragraph("Appendix", styles["Heading1"]),
        Paragraph("Secondary detail on page two; same A4 page size.", styles["BodySmoke"]),
    ]
    doc.build(story)
    print(f"wrote {OUT}", flush=True)

    checker = SCRIPT_DIR / "check_pdf_basics.py"
    proc = subprocess.run(
        [sys.executable, str(checker), str(OUT)],
        check=False,
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
