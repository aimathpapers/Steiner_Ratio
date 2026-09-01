# Independent re-verification of the certificate layer of the 0.8559 Gilbert–Pollak lower bound

**Report draft v0.4 (2026-08-13). Every number is computed and traceable
to the companion audit bundle (see Artifact index), with sampled figures
labeled as such.**

**Summary.** The Steiner ratio is the infimum, over finite planar point
sets, of the ratio between the lengths of a shortest Steiner tree and a
minimum spanning tree; Gilbert and Pollak (1968) conjectured it equals
√3/2 ≈ 0.8660. A recent computer-assisted result (arXiv:2601.22365) raised
the proven lower bound from 0.824 (Chung–Graham, 1985) to 0.8559 — the
first movement in four decades — resting on a machine-checked certificate
of 330,193,755 per-region records that had not been independently
verified. We re-verified the entire certificate: 265,761,575 records
vertex-checked on a clean-room verifier over a disjoint arithmetic stack,
under strictly stronger checking semantics than the authors' own tool,
with zero failures; the remaining 64,432,180 records are exactly those the
authors' own filters exclude, with every exclusion re-derived rather than
trusted. The certificate layer holds. The audit also surfaced findings
about the artifact itself, in order: its shipped verifier checks only half
the vertex set its documentation claims (F1); its published dataset was
not produced by the generator version in its repository (F2) and is one of
several valid certificates that generator can produce (F3); its toolchain
is entirely unpinned (F4); and the peer-visible paper describes a
different verifier than the artifact ships (F5). Separately, 28.8 million
regions were re-verified over their entire boxes rather than at vertices
only, removing — for those regions, in their bounded variables — the
result's dependence on an unaudited convexity-type assumption; sampling
indicates roughly a third of the whole certificate would close this way.

## 1. Scope: what this note does and does not claim

The proof of ρ ≥ 0.8559 has two layers.

The **certificate layer** is machine-checked: a tiling of a bounded-degree
local configuration's parameter space into ~330M boxes, each box carrying
a record that names a *splitting function* — a closed-form expression
F(w) = ρ·L_T* + L_S+ − L_S− pricing a local reduction of a putative
minimal counterexample tree — and asserts F ≤ 0 on that box. The authors'
checker verifies each record by evaluating F in interval arithmetic at the
box's vertices.

The **lemma layer** is not machine-checked: the per-case mathematical
claims that make vertex checking sufficient — trapped-point polygon
lemmas, 4-point Steiner topology lemmas, and the axis-unimodality
("Shape Constraint") property under which a function's maximum over a box
is attained at a vertex. These rest on unshipped Mathematica runs plus the
authors' manual review.

**This audit verifies the certificate layer only.** Nothing here should be
quoted as an independent verification of ρ ≥ 0.8559 as a theorem: the
lemma layer remains unaudited, except insofar as full-box verification
(§4.3) removes the unimodality dependence region by region. This scope
statement is deliberate and load-bearing.

## 2. The artifact under audit

Paper: "Towards Solving the Gilbert-Pollak Conjecture via Large Language
Models", Ke, Huang, Shu, He, Gai, Wang, arXiv:2601.22365 (v1 2026-01-29,
v2 2026-05-21). Artifact: github.com/keyisi2006/Steiner-Ratio, audited at
commit `709673a8926fed0ef981d7db36dafcdf6f4a8a1d` (HEAD since 2026-02-11).
Dataset: huggingface.co/datasets/keyisi/steiner-ratio — 49.3 GB across 8
data files.

The proof splits into two case families (d_regular, d_steiner — the
relevant neighbor of the pruned leaf being a regular point or a Steiner
point) by two subcases on two of the edge-length variables, f ≥ d and
f ≤ d, giving parameter-space dimensions n = 5, 6, 7, 8. Each case ships:
a text table of *splittings* (which tree edges a reduction deletes, adds,
and re-links — each splitting induces one splitting function); nine
*lemma* files supplying certified upper bounds used inside those
functions; and the certificate itself, a stream of binary records
(little-endian: int32 region id, n × (float64 low, high) box bounds, int32
split id, int32 lemma id — the last two select which splitting function,
with which lemma's bounds, certifies the box).

## 3. Method

**Acquisition.** Day-one snapshot of the repository, pinned by commit and
hashed file-by-file (680 files; `artifacts/acquisition/repo_manifest.json`
in the bundle). Full dataset download; every data file's sha256 matches
the publisher's LFS hash — the only hashes the publisher declares anywhere
(`artifacts/acquisition/dataset_manifest.json`). Upstream artifacts are
consumed locally as untrusted input and are not redistributed with this
audit.

**Independent verifier.** A clean-room Python implementation over Arb ball
arithmetic (python-flint 0.9.0) — an arithmetic lineage disjoint from the
authors' IEEE-interval Julia stack, chosen so a shared library bug cannot
produce matching wrong answers. ρ is held as the exact rational
8559/10000. The splitting functions of all four cases were transcribed
clean-room and are continuously tested against a second, independently
written mpmath reference implementation (60 significant digits): bound
containment, branch agreement, and composed-function containment across
every splitting in both case families, plus spot comparisons against the
authors' checker's evaluations (consumed as untrusted cross-check input).
The verifier replicates the authors' record-validity rules exactly —
subcase filters, monotonicity requirements for unbounded boxes, the f := d
boundary substitution — with one deliberate strengthening: **our vertex
enumeration visits all 2^n vertices**, which the shipped checker does not
(Finding F1).

**Verification modes.** *Vertex-parity*: the authors' checking semantics
on our arithmetic. *Full-box*: rigorous enclosure of the splitting
function over the entire box, with adaptive sub-splitting under a bounded
budget; a region that closes full-box no longer depends on the lemma
layer's unimodality claim in its boxed variables.

**Cross-check protocol.** The authors' checker runs as an untrusted
external tool on the same inputs, whole cases or single regions. Any
disagreement enters a triage queue whose discipline is our-bug-first:
escalated-precision re-runs on our stack and single-region re-runs on
theirs, all recorded, before an entry can even be considered a finding —
and no defect is reportable without a self-contained failing-region
capsule (a dependency-light replay script a third party can run in
minutes) plus both-stack agreement. No finding in this audit required that
gate: the triage queue closed empty.

## 4. Results

### 4.1 The full corpus passes, zero failures

All-vertices vertex-parity on the Arb stack:

| Case | Records | Vertex-checked, pass | Skipped (re-derived) |
|---|---|---|---|
| d_regular f≥d | 1,888,501 | 1,888,501 | 0 |
| d_regular f≤d | 63,466,354 | 44,052,638 | 19,413,716 subcase sentinels |
| d_steiner f≥d | 5,402,950 | 5,397,967 | 4,983 symmetry |
| d_steiner f≤d | 259,435,950 | 214,422,469 | 45,013,481 sentinels + symmetry |
| **Total** | **330,193,755** | **265,761,575** | **64,432,180** |

Zero failures, zero inconclusive verdicts. "Skipped" rows are records the
authors' own semantics exclude from vertex checking — subcase sentinel
records (F2) and boxes covered by a structural symmetry — and every skip
was re-derived from the record's own data by our implementation of those
filters, never taken from the authors' tooling. Per-region verdicts are
machine-readable and record each record's verification mode; curated run
records: `artifacts/verification/*.run.json`. The three corpora other
than d_steiner f≤d were verified end-to-end a second time during the
full-box runs (§4.3), again with zero failures.

### 4.2 The authors' checker, replayed on our machine

For cross-comparison (untrusted): the authors' checker prints its success
line ("All N regions verified") for each of the four cases on our machine
— the largest case only in a single-threaded fallback (~40 h), because
both multithreaded configurations crash reproducibly on this platform (a
Julia GC/threading failure mode on the 259M-record workload; recorded as a
replication caveat in `artifacts/verification/their_checker_replays.json`).
Toolchain versions recorded by us (julia 1.12.6, IntervalArithmetic.jl
1.0.10) because the artifact pins nothing (F4).

Because our check is strictly stronger than theirs (F1) and their tool
reports only an aggregate verdict — it halts at the first failure and
emits no per-region stream — region-level agreement is *inferred* from our
all-vertices pass plus equal aggregate outcomes, with single-region
replays of their checker available on demand for any suspect record.

### 4.3 Full-box verification: quantifying the dependence on the lemma layer

The headline: **28,845,102 regions — every region of the three smaller
corpora that would close within a 200-sub-box budget — are now verified
over their entire boxes**, not just at vertices, and for those regions the
result no longer depends on the lemma layer's unimodality claim in their
boxed variables. (In f ≥ d subcases a monotonicity-in-f dependence
remains, since only the f = d boundary is boxed; unbounded boxes likewise
retain their structural dependence on monotone directions.)

Closure rates where full-box was attempted for every region: d_regular
f≥d 32.4% (612,800 of 1,888,501), d_regular f≤d 42.0% (26,649,684 of
63,466,354), d_steiner f≥d 29.3% (1,582,618 of 5,402,950). For d_steiner
f≤d — 78.6% of the corpus — a 50,000-record uniform sample closed at
30.5% (15,254 of 50,000). Blending the exhaustively attempted corpora with
the sampled estimate gives an **estimated corpus-wide closure rate of
~32.7%** — an estimate, inheriting the sample. The audit's pre-registered
demotion rule (report vertex-parity as the headline if closure landed
under 10%) was cleared by at least 2.9x in every case.

## 5. Findings

**F1 — The shipped verifier checks half the vertex set it documents.**
`verify_certificate.jl` selects vertex coordinates with
`box[((mask >> i) & 1) + 1, i]` for `i` in 1..n over masks 0..2^n−1: mask
bit n is always zero, so the last variable never takes its upper endpoint,
and bit 0 is ignored, so each of 2^(n−1) distinct assignments is evaluated
twice. The artifact's own README states the checker "evaluates the
function at all finite vertices of the hyper-box (up to $2^n$ vertices)",
which the shipped code does not do; the fix is a one-line change (shift by
i−1). Our verifier checks all 2^n vertices, and every vertex-checked
record passes the stronger check (§4.1) — so the skipped endpoints turn
out to be non-binding and the certificate survives, but the shipped
checker does not establish what its documentation claims.

**F2 — Undocumented sentinel records, and the published data does not
match the shipped generator's encoding of them.** f≤d certificates mark
boxes belonging to the other subcase with sentinel records the checker
skips (its f_low > d_high filter fires before the splitting table is
indexed). The published d_regular f≤d file encodes this sentinel as
split id 0 / lemma id 0 — 19,413,716 records, 30.6% of the file — while
the generator source at the audited commit writes −1/−1, and our
regeneration produces exactly 19,413,716 sentinel records under the −1
encoding. Two consequences: the record-format documentation mentions
neither sentinel (a naive independent decoder rejects the files), and the
published dataset provably was not produced by the generator version at
the repository's HEAD.

**F3 — The tiling is canonical; the certificate identities are not.** This
is a reproducibility finding, not a soundness defect: the generator is the
untrusted layer, and the divergent records verify (below). Rebuilding the
authors' C++ generator from the audited commit (GNU g++ 16, Apple Silicon)
and regenerating all four cases yields datasets with identical record
counts and sizes but different bytes. A content-multiset comparison,
insensitive to record order and region numbering, localizes the difference
exactly: **every box multiset is identical in both directions** — the
whole ~330M-box partition reproduces — while a small fraction of records
certify the same box under a different (split id, lemma id): 33,048 per
side (1.75%) in d_regular f≥d, 1,748,112 (2.75%) in d_regular f≤d, 39,944
(0.74%) in d_steiner f≥d, 4,210,428 (1.62%) in d_steiner f≤d. Candidate
mechanisms are platform floating-point differences in the generator's
`-ffast-math` double arithmetic deciding which candidate function
certifies first; no single mechanism has been isolated. Verification of
the regenerated datasets on our stack, zero failures throughout:
d_regular f≥d, d_regular f≤d, and d_steiner f≥d in full — each with
pass/skip counts identical to its published counterpart (1,888,501;
44,052,638 + 19,413,716 sentinels; 5,397,967 + 4,983 symmetry) — and a
50,000-record uniform sample of regenerated d_steiner f≤d (41,332 pass,
8,668 skips). The published dataset is best described as one valid output
of a generator whose exact version and platform are not recoverable from
the artifact.

**F4 — Nothing is pinned.** No Julia package manifest, no compiler
versions, no dataset hashes anywhere in the artifact. Every version this
audit relied on is recorded in the bundle's manifests instead.

**F5 — The peer-visible paper describes a different verifier than the
artifact ships.** The v2 paper (2026-05-21) presents the verification as
Mathematica/CAD and lists interval arithmetic as future work; the
artifact's actual trusted kernel has been the Julia interval checker since
2026-02-10, documented only in the repository README. The pipeline half of
the repository also references agent files absent from its tree. (Fetch
details: `docs/research/gilbert-pollak-pku-pipeline.md` in the bundle.)

## 6. Reproducing this audit

The companion bundle provides:

- the verifier, decoder, diff, regeneration, cross-check, and capsule
  tooling, under a pinned Python environment (`uv.lock`), MIT-licensed;
- a 98-test suite at two interfaces — hand-crafted certificate fixtures at
  the verifier boundary, and containment/agreement tests against the
  independent mpmath reference — with its conventions documented;
- content-addressed manifests for every third-party input, curated run
  records for every verification run, all four dataset-diff summaries, and
  the complete per-region verdict stream for the smallest case as a
  spot-check sample (other streams regenerate deterministically);
- a status command (`python -m steiner_audit.status`) that recomputes all
  progress and coverage figures from the artifacts on disk.

The upstream repository and dataset are not included (they carry no
license); reproduction fetches them from the public sources and checks
them against the pinned hashes. The dataset-diff summaries in the bundle
are counts-only: the localized per-region excerpts remain in the private
audit repository pending upstream licensing clarity.

## 7. Limitations

- The lemma layer is unaudited: trapped-point polygon validity, 4-point
  topology lemmas, and axis-unimodality rest on the authors' unshipped
  Mathematica runs and manual review. Full-box verification removes the
  unimodality dependence (in boxed variables) for the 28.8M closed
  regions; the remainder, and the other lemma-layer claims, stand or fall
  with the authors' checking.
- d_steiner f≤d full-box coverage is a sampled estimate (50,000 records),
  as is every corpus-wide figure that includes it; all other numbers are
  computed over every record of their case.
- Vertex-parity agreement with the authors' checker is at aggregate level
  plus on-demand single-region replays; their tool emits no per-region
  verdict stream to compare wholesale.
- Both stacks ran on one machine (Apple Silicon, macOS). The
  platform-dependence findings (F2, F3) suggest a third platform would be
  a useful additional data point.

## 8. Notes on effort and pre-registration

The audit plan pre-registered its pivots in the project's milestone
specification before work began: a day-one snapshot before anything else;
at most three days on the authors' build system before demoting to
download-only provenance; and the <10% full-box demotion rule of §4.3.
None was triggered. Compute: their generator built in seconds behind a
compiler shim and regenerated the four cases in 8.6 s, 391 s, 249 s, and
~7.1 h respectively (~7.3 h total, against the README's ~30 h figure);
their checker's own verification pass, advertised at ~6 h, took ~42 h on
this platform (~40 h of it the single-threaded fallback for the largest
case, §4.2); our full-corpus verification and the full-box runs each
completed within roughly a day on a 32-core workstation.

## Artifact index (companion bundle)

Staged by `python -m steiner_audit.release`; every path above resolves
inside it, and `BUNDLE_MANIFEST.json` hashes its complete contents.

- `artifacts/acquisition/` — repository/dataset/regeneration manifests;
  the authors' checker environment record.
- `artifacts/verification/` — curated run records for every verification
  run; all four dataset-diff summaries; the authors'-checker replay
  outcomes.
- `artifacts/notes/observations.md` — every raw observation with its
  disposition.
- `docs/research/gilbert-pollak-pku-pipeline.md` — pre-audit primary
  source research with per-claim citations.
- `verdicts_sample/` — complete per-region verdicts for d_regular f≥d
  (gzipped JSONL).
