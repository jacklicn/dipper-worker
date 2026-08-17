<!--
Outline / glossary state file — the single source of truth for a report.
Copy this template to outputs/documents/report-<name>/outline.md and fill it in.
The outline stays in the agent's context; chapter bodies live on disk and are
read back on demand, so this file must stay small and machine-parseable.
Status values: planned | drafting | drafted | polished
-->

# Report Outline: <Title>

## Brief

- Topic: <what the report covers>
- Audience: <executives / engineers / general public / ...>
- Length target: <e.g. ~5000 words / 30 pages / comprehensive>
- Language: <zh / en>
- Format: <markdown / docx / pdf / pptx>
- Report root: outputs/documents/report-<name>/

## Glossary

Every chapter must use these exact terms. Add a row when a chapter introduces a
term the rest of the report will rely on.

| Term | Definition | Notes |
| --- | --- | --- |
| <term> | <one-line definition> | <usage notes, variants to avoid> |
| <term> | <one-line definition> | <usage notes, variants to avoid> |

## Chapters

Order is fixed. Update `Status` after every write; keep the one-line note on
where the chapter ended so resuming is trivial.

### 01 <Chapter title>
- Target: ~<N> words
- Key points: <bullet list of what this chapter must establish>
- Sources: <materials/NN-<facet>.md files or verified web sources>
- Status: planned
- Note: <where drafting stopped, once started>

### 02 <Chapter title>
- Target: ~<N> words
- Key points: <bullet list of what this chapter must establish>
- Sources: <materials/NN-<facet>.md files or verified web sources>
- Status: planned
- Note: <where drafting stopped, once started>

<!-- add more chapters as needed -->
