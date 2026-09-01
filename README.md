# Steiner_Ratio — independent verification of the Gilbert-Pollak certificate layer, and a certificate-layer bound of 0.860

This repository contains, in decreasing order of formality:

- paper/steiner-certificate-record.pdf (+ .tex) — the full paper;
- report/verification-note.md — the audit of the published 0.8559
  certificate layer; report/record-note-0.860.md — the record claim;
- the clean-room verifier and its two-seam test suite, content-addressed
  manifests, and curated run records for every verification run.

Archived release: https://doi.org/10.5281/zenodo.22223485
Contact: aimathpapers@gmail.com

Claim scope: this work verifies the CERTIFICATE LAYER of arXiv:2601.22365
only. It is not an independent verification of rho >= 0.8559 as a theorem;
see the report's Section 1. The companion record note
(report/record-note-0.860.md) extends the certificate layer to
rho >= 0.860 via partition regeneration at the higher target — same
scope, same inherited lemma-layer obligations, exact rational 43/50
throughout; regenerated certificates ship as sha256 hashes only.

The upstream artifacts (github.com/keyisi2006/Steiner-Ratio and the
huggingface.co/datasets/keyisi/steiner-ratio dataset) are NOT included:
they carry no license. Reproduction fetches them from the public sources
and checks them against artifacts/acquisition/*.json (the audited commit
and per-file sha256 are pinned there).

Quick start (no dataset needed):

    uv sync
    uv run pytest -m "not real_data"

Full replay: use `python -m steiner_audit.acquire` to fetch and pin the
upstream artifacts, then `python -m steiner_audit.verify` per case
(`--help` for modes and sharding), and `python -m steiner_audit.status`
for the live view. verdicts_sample/ holds the complete per-region verdict
stream for the d_regular f>=d case (gzipped JSONL) as a spot-check sample;
all other verdict streams regenerate deterministically from the tooling.

Curation note: semantic_diff_*.json here are counts-only variants; the
findings_localized sections (which embed upstream region records) are
truncated per the audit's reuse posture (ADR-0002).
