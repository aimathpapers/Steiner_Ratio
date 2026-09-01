# Audit observations (pre-findings)

Raw observations awaiting triage. Nothing here is a reportable finding until
it has passed the ADR-0005 capsule gate (for certificate defects) or been
reproduced as a documented divergence (for artifact/paper mismatches).

## OBS-8: the published dataset was not produced by the snapshot's generator

The f<=d certificates mark "belongs to the other subcase" boxes with a
sentinel record. The published d_regular f_le_d file encodes it as
split_id 0 / lemma_id 0 (19,413,716 records); the generator source at the
pinned snapshot writes split_id -1 / lemma_id -1
(plot_f_le_d.cpp:250, `int split_id = -1, lemma_id = -1`), and our
regeneration from that source produces exactly 19,413,716 records with
-1/-1 — same regions, different encoding. Conclusion: the published
dataset and the shipped generator source are from different code versions
(the certificate/ directory was updated 2026-02-10, after the v1 paper).
Their checker is insensitive to the difference (it skips these records on
f_low > d_high before indexing the split table), so both files verify —
but byte-level provenance of the published data cannot be established from
the repo at HEAD. Our decoder admits both sentinels; the semantic diff
canonicalizes them to the same non-claim.

## OBS-7: their checker segfaults on the d_steiner f<=d case on this platform

Running their verify_certificate.jl --f-le-d in d_steiner (259,435,950
records, the case their README says dominates the verification budget)
with `--threads auto` (32 threads, julia 1.12.6, macOS ARM) dies with
signal 11 after ~8 minutes. The three other cases complete ("All N regions
verified"). REPRODUCED: `--threads 8` also crashes (task backtrace through
verify_parallel at verify_certificate.jl:332, ~34.9e9 allocations, GC
40916 — a Julia GC/threading failure mode on this workload). The shipped
checker cannot complete its own biggest case in either configuration on
this platform; a single-threaded attempt (multi-hour) was launched with a
persistent log (runs/their_checker_d_steiner_f_le_d_t1.log). Until some
stack completes d_steiner f<=d, the only machine-checked evidence for that
case on our machine is our 10k sample (zero failures). Report material.

## OBS-1: their vertex loop appears to skip the last variable's upper endpoints

`certificate/*/verify_certificate.jl`, `verify_record`:

```julia
for mask in range(0, (1 << n) - 1)
    ...
    v::Float64 = box[((mask >> i) & 1) + 1, i]
```

with `i` running 1..n. The mask has bits 0..n-1, but `(mask >> i)` reads bits
1..n: bit n is always 0, so variable i = n never takes its upper endpoint,
and bit 0 is ignored, so each of the 2^(n-1) assignments is evaluated twice.
If this reading is right, their shipped checker verifies half the claimed
vertex set — the last variable is checked only at its lower endpoint
(mitigation: for f>=d subcases the last box variable is 'e' in d_regular;
whether monotonicity independently covers the skipped endpoints is exactly
what our all-vertices run cross-checks).

- Status: our kernel enumerates all 2^n vertices (bit i of mask = variable
  i). Full-case d_regular f_ge_d run with all-vertices semantics completed
  2026-08-12: all 1,888,501 records pass. For this case, the endpoints their
  loop skips are therefore non-binding — the observation is a
  checker-completeness finding for the report (their shipped verifier checks
  2^(n-1) distinct vertex assignments, each twice, not the 2^n the README
  describes), not a certificate defect. Remaining cases: our sampled runs
  (20k f_le_d, 10k per d_steiner subcase) also all pass at all-vertices
  semantics.
- Triage discipline: reread the Julia semantics before claiming (Julia's
  `range(0, k)` is 0:k inclusive — 2^n masks total, one extra vs C loops;
  bit indexing verified against the C++ generator's `mono_mask` handling
  still pending).

## OBS-2: splits.txt count is 158, not the research doc's 160

`certificate/d_regular/splits.txt` parses to 158 splits (their checker also
loads all non-empty lines). The research doc's "160 splitting definitions"
was a miscount from a summarizing fetch. Real f_ge_d certificate references
41 distinct splits (max split_id 153), all 9 lemmas, 63 (split, lemma) pairs.

## OBS-3: unusable splits exist and must fail closed

47 of 158 d_regular splits reference S+ sets (e.g. {B,D,P,Q}) that no lemma
table prices, or trapped T* edges no lemma bounds. In their checker such a
record dies on a Julia KeyError -> region failure; our evaluator returns an
explicit failure. No real record references them (LLM-proposed splits the
generator never used). Encoded in the oracle suite as the "unusable class".

## OBS-5: undocumented split_id 0 sentinel in f<=d certificates

The certificate README documents split_ID as an index into splits.txt
(1-based in the checker). The real d_regular f_le_d data also contains
records with split_id = 0 — every one of them (391,195 in the first 5M
records scanned) satisfies f_low > d_high, i.e. the box their checker skips
as belonging to the f >= d subcase, before it ever indexes the split table
(split_id 0 would be a Julia BoundsError otherwise). So 0 is a generator
sentinel for "priced by the other subcase", undocumented in the record
format. Our decoder admits 0; the kernel skips it under the subcase filter
and fails it anywhere else. Report material: record-format documentation gap.

## OBS-6: regeneration reproduces the tiling exactly, but 1.75% of
## certificate identities differ

Their generator, built from the pinned snapshot with g++-16 on Apple
Silicon, regenerated d_regular f_ge_d in ~1 minute. Result vs the published
dataset (artifacts/verification/semantic_diff_d_regular_f_ge_d.json):

- record counts identical (1,888,501 each), file sizes identical, sha256
  different;
- the box multisets are IDENTICAL in both directions — the domain partition
  is fully reproducible;
- 33,048 records per side (1.75%) carry a different (split_id, lemma_id)
  for the same box — the generator's choice of which splitting function
  certifies a region is platform/compiler-dependent (long-double vs double,
  -ffast-math, ARM vs x86 are all candidates; the generator is the
  untrusted layer, so this is a reproducibility finding, not a soundness
  one), concentrated on a few splits (47, 43, 48, 42, 112, 119);
- disposition: BENIGN, confirmed — our stack verified all 1,888,501
  regenerated records with zero failures
  (artifacts/verification/full_regen_d_regular_f_ge_d.run.json): the
  regenerated file is a different but equally valid certificate layer over
  the identical tiling.

Report material: "the published dataset is one of several valid
certificates the shipped generator can produce; the tiling is canonical,
the per-region certificate choice is not".

2026-08-12 update, full sweep: the pattern is systematic across all four
cases — box multisets identical in both directions everywhere; identity
divergence per side: d_regular f>=d 33,048 (1.75%), d_regular f<=d
1,748,112 (2.75%), d_steiner f>=d 39,944 (0.74%), d_steiner f<=d
4,210,428 (1.62%). Artifacts:
artifacts/verification/semantic_diff_*.json (all four).

## OBS-4: no version pins anywhere in their artifact

Their verifier Pkg.adds IntervalArithmetic/StaticArrays unpinned (resolved
1.0.10 / 1.9.18 on our snapshot date, julia 1.12.6, recorded in
julia_smoke.json). Already flagged in the research doc; confirmed at run
time. Report material for the reproducibility section.

## OBS-9: The published tiling's ceiling sits ~1e-6 above the incumbent (ticket #16, sampled)

One-pass critical-rho analysis (50,000 records/case, seed 20260813, vertex
semantics; certified interval width < 1e-10 throughout):

| case | sampled min critical rho | binding region |
|---|---|---|
| d_regular/f_ge_d  | 0.8559006050 | 100907 |
| d_regular/f_le_d  | 0.8559006050 | 1574759 |
| d_steiner/f_ge_d  | 0.8559001030 | 9794997 |
| d_steiner/f_le_d  | 0.8559006050 | 7252129 |

A 10,000-record full-box probe (d_regular/f_ge_d, drive rho 8559/10000)
gives a one-sided full-box ceiling >= 0.8559048474 over its 3,224 closed
regions — the full-box route is not the binding constraint; the vertex
margins are.

Reading: their generators terminate subdivision as soon as a region clears
zero by eps = 1e-6 (plot_*.cpp line 5 in all four cases), so the tiling is
pinned to the incumbent by construction and the fixed-tiling ceiling is
0.85590xx — technically above 0.8559, materially nil. Three of four cases
share the identical sampled minimum 0.8559006050, consistent with a
generator-quantized margin floor rather than case geometry. Consequence for
M2: no meaningful record comes from re-certifying the published partition;
the gain must come from regenerating the partition at a higher target rho
(their generator's rho is a one-line patch per case, harness-feasible) plus
new lemmas where regeneration alone stalls. Exact corpus minima need the
exhaustive pass (same cost shape as an M1 full corpus run).

## OBS-10: d_regular certified at rho = 0.856 by regeneration alone (ticket #16, adaptive probe)

Their generator, patched to rho = 0.856 (patched copies in isolated
d_regular@0.856 work dirs; snapshot untouched), regenerated both d_regular
partitions; our stack verified every region at the exact rational 107/125
under full-box-first ADR-0004 semantics:

| subcase | regions (vs incumbent) | vertex_parity | full_box | skipped | bad |
|---|---|---|---|---|---|
| f_ge_d | 60,664,207 (32x) | 58,727,632 | 1,936,575 | 0 | 0 |
| f_le_d | 69,901,321 (1.1x) | 18,505,606 | 29,435,866 | 21,959,849 | 0 |

Certificates pinned in regen_manifest.json (c9d449c2... / 182356ff...).
The existing lemma set stretches to 0.856 for the d_regular family with
zero new mathematics — the cost is partition size (their eps=1e-6
termination forces ~32x more subdivision in f_ge_d). The record claim now
hinges entirely on the d_steiner family at 0.856.

## OBS-11: Exact fixed-tiling ceilings, all four cases (ticket #16, exhaustive)

One-pass critical-rho analysis of every record in the published dataset
(vertex semantics, certified interval width < 1e-10, zero inconclusive):

| case | records | exact ceiling | binding region |
|---|---|---|---|
| d_regular/f_ge_d | 1,888,501 | 0.8559001279 | 2883369 |
| d_regular/f_le_d | 63,466,354 | 0.8559000619 | 50589582 |
| d_steiner/f_ge_d | 5,402,950 | 0.8559000943 | 8327379 |
| d_steiner/f_le_d | 259,435,950 | 0.8559000606 | 444795036 |

The published tiling's ceiling is 0.8559000606 (the d_steiner/f_le_d
minimum): the certificate layer as shipped certifies every rho <= that
value and no more. Full-box semantics is a strictly stronger requirement,
so its fixed-tiling ceiling can only sit at or below this number — the
adaptive route (OBS-10: d_regular already at 0.856 by regeneration) is
where all remaining headroom lives. The 1,000 lowest-ceiling regions per
case are curated as ceiling_full_*.bottlenecks.jsonl (bottleneck
cartography seed data, #17).

## OBS-12: d_steiner/f_ge_d certified at rho = 0.856 (ticket #16, adaptive probe)

Their generator at rho = 0.856 produced 137,442,346 regions (25.4x the
incumbent partition, 9.6h generation) and our stack verified every one at
the exact rational 107/125: 134,936,984 vertex_parity + 2,500,163 full_box
+ 5,199 skipped, zero defects. Three of four cases now certify 0.856.

Generator wall-time scaling at 0.856 so far: d_regular/f_ge_d 256x,
d_steiner/f_ge_d 138x — but d_regular/f_le_d 0.77x (faster than the
incumbent run, 1.1x regions): the f_ge_d blowup tracks the unbounded
directions absent from f_le_d subcases. The remaining monster
(d_steiner/f_le_d, 7.1h at the incumbent) is therefore plausibly a
same-order generation, with tail risk if it scales like its f_ge_d
sibling instead.

## OBS-13: All four cases certified at rho = 0.856 — a new bound from the existing lemma set (ticket #16)

The adaptive probe completed the sweep: their generator at rho = 0.856
(one-line patch, isolated work dirs, pinned snapshot commit) regenerated
all four partitions, and our stack verified every region at the exact
rational 107/125 under full-box-first ADR-0004 semantics:

| case | regions | vertex_parity | full_box | skipped | bad |
|---|---|---|---|---|---|
| d_regular/f_ge_d | 60,664,207 | 58,727,632 | 1,936,575 | 0 | 0 |
| d_regular/f_le_d | 69,901,321 | 18,505,606 | 29,435,866 | 21,959,849 | 0 |
| d_steiner/f_ge_d | 137,442,346 | 134,936,984 | 2,500,163 | 5,199 | 0 |
| d_steiner/f_le_d | 291,921,888 | 148,465,676 | 89,663,364 | 53,792,848 | 0 |

559,929,762 regions total, zero failed / invalid / inconclusive anywhere.
Subject to the same inherited lemma-layer obligations as the published
0.8559 proof (unchanged lemma set; rho-uniform claims), the certificate
layer now certifies rho = 0.856 > 0.8559. Generation cost 4.85-9.6h per
case; verification 1-2 days for the largest. The adaptive ceiling's exact
sup remains unlocated: 0.856 is the last probed passing rho, no failing
probe exists yet, and pushing higher is bottleneck-cartography work (#17).

## OBS-14: d_regular certifies through rho = 0.860 (sampled); the wall is economic, not mathematical (#17)

Probe ladder, their generator patched per rung, 50k-record sampled ceiling
pass per partition (zero failed/invalid/inconclusive everywhere):

| rho | f_ge_d records | f_le_d records | ceiling est (f_ge_d / f_le_d) |
|---|---|---|---|
| 0.8559 | 1.9M | 63.5M | (published) |
| 0.856 | 60.7M | 69.9M | certified exhaustively (OBS-10) |
| 0.857 | 73.0M | 161.4M | 0.8570000828 / 0.8570072405 |
| 0.858 | 87.7M | 450.7M | 0.8580002490 / 0.8580000746 |
| 0.860 | 105.5M | 306.9M | 0.8600002508 / 0.8600004937 |

Generation stayed ~1h per rung. Two readings: (1) the existing lemma set's
reach for d_regular extends at least to 0.860 — 60% of the way from the
old record to the conjectured sqrt(3)/2 = 0.8660; (2) partition size is
NOT monotone in rho (f_le_d: 450.7M at 0.858 vs 306.9M at 0.860) — the
generator's split/subdivision choices shift discontinuously, so cost
extrapolation needs per-rung measurement, not curve fitting. All sampled;
claim-grade rungs need exhaustive verification at the chosen flag rho.

## OBS-15: d_regular certifies through rho = 0.865 (sampled) — 1.03e-3 below the conjecture (#17)

The extension ladder cleared every rung at ~1h generation each, zero
failed/invalid/inconclusive in every 50k-record sampled ceiling pass:

| rho | f_ge_d records | f_le_d records | ceiling est (min of pair) |
|---|---|---|---|
| 0.862 | 235.1M | 219.9M | 0.8620001736 |
| 0.864 | 180.1M | 199.8M | 0.8640000275 |
| 0.865 | 148.8M | 198.9M | 0.8650002971 |

sqrt(3)/2 = 0.8660254. The existing lemma set (sampled evidence) carries
d_regular to within 1.03e-3 of the conjectured optimum, and partition
sizes DECREASE from 0.862 to 0.865 (235M -> 149M for f_ge_d): the
generator shifts split choices, so neither cost nor reach is monotone.
The economic wall never materialized for this family. Next rung 0.866
(2.5e-5 below the conjecture) probes whether the lemma set is effectively
complete for d_regular. Caveat: sampled passes; claim-grade rungs need
exhaustive verification. Ops note: concurrent probe chains raced on the
advisory regen state.json (entries lost, artifacts unaffected) — fix
queued; disk outputs and manifests are the source of truth.

## OBS-16: d_regular certifies rho = 0.866 (sampled) — 2.5e-5 below sqrt(3)/2; d_steiner reaches 0.857 (#17)

d_regular @ 0.866 (f_ge_d 133.1M records, f_le_d 194.3M; ~1h generation
each): sampled ceilings 0.8660002677 / 0.8660021130, zero bad outcomes.
sqrt(3)/2 = 0.86602540. The existing lemma set carries d_regular to within
2.5e-5 of the conjectured optimum — for this configuration family the
lemma set is effectively complete. (A case certifying above sqrt(3)/2
would not by itself be unsound: the global bound is the min over cases,
and the equilateral witness need not lie in d_regular's class.)

d_steiner @ 0.857 (f_ge_d 166.8M records, f_le_d 444.6M): sampled
ceilings 0.8570001252 / 0.8570006694, zero bad. The binding family holds
one millirho above the record flag planted at 0.856. Ladder continues:
0.858, 0.860 (a rung now costs ~1-2 days for this family).

## OBS-17: d_steiner certifies rho = 0.858 (sampled) (#17)

d_steiner @ 0.858: f_ge_d 369,384,514 records (2.2x its 0.857 partition —
the binding family's cost curve is steepening), f_le_d 410,336,013.
Sampled ceilings 0.8580001163 / 0.8580016905, zero bad outcomes. The
0.860 rung is generating (f_le_d at ~198M regions and counting).

## OBS-18: 0.860 gates all green; claim-grade campaign launched (#17)

Gate 1: d_steiner@0.860 generated — f_le_d 291,063,158 records (smaller
than its 0.858 partition), f_ge_d 400,697,233 (1.08x its 0.858 size; the
2.2x step did not compound). Gate 2: sampled ceilings 0.8600005588 /
0.8600005119, zero bad. Gate 3 throughput: 4,567 records/s at 16 workers
(d_regular/f_ge_d@0.860 claim run, 105.5M records in 6.4h, zero defects —
first claim piece banked). d_steiner exhaustive quote: ~2.5-3.5 days.

## OBS-19: THE RECORD — rho = 0.860 exhaustively certified in all four cases (#17)

Claim-grade verification complete at the exact rational 43/50, full-box-
first ADR-0004 semantics, 16 workers, zero defects in every case:

| case | records | vertex_parity | full_box | skipped |
|---|---|---|---|---|
| d_regular/f_ge_d | 105,508,647 | 88,464,876 | 17,043,771 | 0 |
| d_regular/f_le_d | 306,908,065 | 189,196,066 | 97,215,618 | 20,496,381 |
| d_steiner/f_le_d | 291,063,158 | 231,250,637 | 46,280,442 | 13,532,079 |
| d_steiner/f_ge_d | 400,697,233 | 316,783,555 | 83,599,064 | 314,614 |

1,104,177,103 regions total. Subject to the inherited (rho-uniform)
lemma-layer obligations of the published proof, the certificate layer now
establishes rho >= 0.860 — up from the published 0.8559, closing 40% of
the remaining gap to the conjectured sqrt(3)/2 = 0.8660254, with zero new
mathematics: the existing lemma set, regenerated partitions, and our
independent verification stack. 244.1M of the 1.104B regions carry
full-box certificates (no unimodality dependence). Certificates and
manifests pinned; claim package assembly is #21.

## OBS-20: Record frozen at rho = 0.860 by decision; publication package prepared (#21)

The probe ladder above 0.860 was stopped deliberately on 2026-08-21 (the
d_steiner 0.862 generation was killed mid-run; logs kept, no artifacts).
The claim freezes at the exhaustively certified rho = 43/50. The
publication package was prepared at the same time (release checklist,
author notification, scoreboard submission text, curated public bundle,
archive deposit). Sampled scouting above 0.860 (d_steiner >= 0.858
exhaustive candidates unexplored; d_regular to 0.866 sampled) remains
documented as evidence, not claims. LLM lemma-proposal budget spent: $0
of the authorized $2,000 — no new lemmas were needed for this record.

## OBS-21: Full-box closure is margin-limited, not budget-limited (W4 pilot)

Closure-vs-budget curves on the 0.860 partitions (5,000 sampled records
per case, seed 20260822, zero bad outcomes): closure moves from
16.2/34.2/20.0/16.2 percent at budget 200 to only 16.6/34.6/21.2/17.0
percent at budgets up to 20,000 — a 100x compute increase buys under one
point. Cause: eps-pinning. The generator leaves ~1e-6 margins, and
whole-box interval closure needs enclosure width below the margin, i.e.
~1e6-fold refinement. Budget is not the lever; the TARGET GAP is:
verifying a partition generated for rho+delta at rho gives margins ~delta.
Phase 2 measures closure for d_regular@0.862 verified at 0.860 and
d_steiner@0.860 verified at 0.858 (delta = 2e-3).

## OBS-22: Target-gap phase 2 — full-box closure is dependency-limited (W4 closed)

Verifying delta=0.002 below the generation target (5,000 records/case,
budgets 200/2000, zero bad outcomes): d_regular/f_ge_d responds as the
margin theory predicts (16.2% -> 34.4% -> 41.3% at budget 2000), but the
other three cases sit at 17-31% and gain under a point for 10x budget.
Conclusion: beyond eps-pinning, the dominant obstruction is interval
DEPENDENCY (the |rB|-s-style cancellations of OBS-2/M1): whole-box
enclosures stay wide however large the true margin, and subdivision
defeats it only at exponential cost in 7-8 dimensions. Full-box-only
re-verification of a record is NOT reachable with the current evaluator
at any sane compute. The levers that remain: (a) centered/mean-value or
affine-arithmetic enclosures in the evaluator — the engineering fix that
directly targets dependency (M3-track); (b) quantify the vertex-checked
residue precisely and keep the shape-lemma inheritance as the stated,
measured caveat (the paper already does this); (c) W3: prove or
re-derive the shape lemma itself. W4-as-compute is closed.
