# Report Consistency Guide (Level 3, loaded on demand)

Loaded during the polish pass (step-6 of the report-writing workflow). Process
chapters **one at a time**; never load all chapters into context at once. For
each chapter, run this checklist and apply fixes with `edit_file`.

## Terminology and Glossary

1. Every key term in the chapter matches the glossary exactly — same term, same
   spelling/case (e.g. do not mix "AI Worker" and "AI worker", or "上下文" and
   "上下文语境" for the same concept).
2. If the chapter introduces a term the rest of the report will rely on, add it
   to the glossary **before** fixing the chapter, then enforce it everywhere.
3. Numbers, units, and abbreviations are consistent: choose one of `5000` vs
   `5,000`, one date format, one symbol set, and apply it across the report.

## Cross-references and Numbering

4. Section/figure/table references resolve: "see Chapter 03" actually exists,
   and the target number matches the outline order.
5. Figures, tables, and code listings are numbered sequentially across the whole
   report (not restarted per chapter), and each is referenced in the body text
   at least once (or explicitly marked as optional).

## Transitions and Structure

6. Each chapter opens with a one-sentence lead-in connecting it to the previous
   chapter (what came before, what this one adds).
7. Each chapter's closing sentence sets up the next chapter or sums up the
   chapter's contribution — no dead ends, no duplicated openings.
8. Heading depth is uniform: H2 for chapter titles, H3 for sections, deeper only
   where the outline allows.

## Voice and Tone

9. Person and voice are consistent (e.g. all "we" or all neutral third person —
   not a mix).
10. Tense is consistent within each chapter's argument.
11. Formality matches the audience declared in the outline: no slang for
    executive reports, no unexplained jargon for general readers.

## Facts and Sources

12. Every factual claim carries a source marker that resolves to a
    `materials/` file or a verified web source; nothing is left as bare
    assertion.
13. No `TODO`, `TBD`, `待补充`, `占位`, `lorem ipsum`, or `[...]` placeholder
    markers remain.
14. Any point the outline required but the chapter could not substantiate is
    explicitly marked as unverified (not silently dropped or padded).

## Length and Balance

15. Compare each chapter's actual length against its outline target; flag
    chapters over ~1.5× or under ~0.5× the target for trimming or expansion.
16. No chapter repeats content already established in another chapter — move
    shared background to the earliest chapter and reference it later.

## Per-Chapter Workflow

```
read_file chapters/NN-*.md
for each item above: note violations
edit_file to fix (small targeted edits, one per change)
if a new term was needed: add it to outline.md glossary first
when clean: set Status: polished for the chapter in outline.md
```

## Final Scan

After all chapters are polished, run one `grep` over the chapters directory for
`TODO|TBD|待补充|lorem` and one pass over the merged document's headings to
confirm structure and numbering. Fix any hits, then report the chapter status
table from `scripts/report_status.py`.
