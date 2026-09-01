# A certificate-layer bound of rho >= 0.860 for the Gilbert–Pollak Steiner ratio

Version 1.0 — 2026-08-21. Companion to `verification-note.md` (the M1 audit
of the published 0.8559 certificate layer); reuses its methods, stack, and
vocabulary.

## Summary

Using the lemma set of arXiv:2601.22365 unchanged, we regenerated the
per-case region partitions at a higher target bound and verified every
region with the independently built, previously audited verification stack:
**all 1,104,177,103 regions across the four cases satisfy non-positivity of
their designated splitting functions at the exact rational rho = 43/50
(= 0.860), with zero failures, zero invalid records, and zero inconclusive
enclosures.** Subject to the same lemma-layer obligations as the published
proof (Section 5), this establishes the certificate-layer bound
rho >= 0.860 — up from the published 0.8559, closing 40% of the remaining
gap to the conjectured sqrt(3)/2 = 0.86602540…, with no new mathematics:
the improvement comes entirely from regenerating partitions against the
higher target and from verification semantics that check all box vertices
and, where possible, whole boxes.

## 1. Claim and scope

**Claim.** For each of the four cases (d_regular / d_steiner, subcases
f >= d and f <= d), the regenerated partition at target 0.860 covers its
case domain (by the generator's construction, as in the published work) and
every region's splitting function is certifiably non-positive at
rho = 43/50 over the checked set (all finite box vertices for every region;
the entire box for the 244,138,895 regions closed by full-box
verification).

**Scope.** This is a certificate-layer result in the sense of the M1 audit:
it inherits the published proof's lemma layer (trapped-point polygons,
topology validity of the case decomposition, monotonicity of constituent
lengths, and — only where a region is not full-box-closed — axis
unimodality of the splitting functions). All inherited claims are
rho-uniform: they concern lengths and geometry, never rho, so their
transfer from 0.8559 to 0.860 is immediate. Nothing here should be cited
as an unconditional theorem without those obligations stated.

**Exactness.** rho is held as the exact rational 43/50 end to end
(python-flint `fmpq`); the generator's long-double 0.856/0.860 constants
influence only which partition gets generated, never what is verified.
Every verdict row records the rho it certified.

## 2. Method

1. **Audited stack (M1).** The verifier (Arb ball arithmetic, certified
   comparisons, all-2^n-vertices semantics, full-box-first per ADR-0004)
   independently re-verified the published 0.8559 certificate layer:
   330,193,755 records, zero certificate-layer failures
   (`verification-note.md`).
2. **rho as an exact parameter** (ticket #15): the entire stack takes rho
   as a required exact rational; M1 behavior reproduces bit-identically at
   8559/10000.
3. **Exact fixed-tiling ceiling** (ticket #16): F(rho) = rho·L_T* +
   (L_S+ − L_S−) is affine in rho with L_T* >= 0 and no lemma condition
   reads rho, so each record's critical rho is a certified division and
   the corpus minimum is one pass. The published tiling's exact ceiling is
   0.8559000606 — eps-pinned to its target by the generator's termination
   slack, hence regeneration.
4. **Regeneration at the target** (ticket #17): the published generator,
   patched only in its rho constant (verified one-line diff against the
   pinned snapshot commit 709673a8), regenerated all four partitions at
   0.860 in isolated work directories.
5. **Claim-grade verification**: every regenerated region verified at
   43/50 under full-box-first semantics with the 128/256/512-bit
   precision ladder; zero not-ok outcomes.

## 3. Results

Claim-grade runs (16 workers; per-region verdict streams and run
provenance under `artifacts/verification/claim_0.860_*.run.json`):

| case | records | vertex-checked pass | full-box closed | subcase skips | defects |
|---|---|---|---|---|---|
| d_regular/f_ge_d | 105,508,647 | 88,464,876 | 17,043,771 | 0 | 0 |
| d_regular/f_le_d | 306,908,065 | 189,196,066 | 97,215,618 | 20,496,381 | 0 |
| d_steiner/f_le_d | 291,063,158 | 231,250,637 | 46,280,442 | 13,532,079 | 0 |
| d_steiner/f_ge_d | 400,697,233 | 316,783,555 | 83,599,064 | 314,614 | 0 |

Certificates (regenerated locally; not redistributed — see Section 5):

| file | sha256 (prefix) | bytes |
|---|---|---|
| d_regular@0.860/certificate_rho=0.86_f_ge_d.bin | 66c44391167665b6 | 9,706,795,524 |
| d_regular@0.860/certificate_rho=0.86_f_le_d.bin | d4a5c64d7e6e4fca | 33,146,071,020 |
| d_steiner@0.860/certificate_rho=0.86_f_le_d.bin | 464395956f33395b | 40,748,842,120 |
| d_steiner@0.860/certificate_rho=0.86_f_ge_d.bin | ab0d6e967eba66b6 | 49,686,456,892 |

Context (all sampled passes 50,000 records, zero bad outcomes):
rho = 0.856 was additionally certified exhaustively for all four cases
(559,929,762 regions) as the first record step. Sampled ladder evidence
puts the existing lemma set's reach at >= 0.858 for d_steiner (both
subcases; 0.862+ under probe) and >= 0.866 for d_regular — within 2.5e-5
of the conjectured optimum for that family.

## 4. Reproduction

From the released tooling (no redistributed upstream content):

    # pin and fetch the upstream snapshot + dataset (hashes verified)
    uv run python -m steiner_audit.acquire
    # regenerate a partition at the target (their generator, patched rho)
    uv run python -m steiner_audit.regen --family d_steiner --subcase f_ge_d --rho 0.860
    # verify it at the exact rational
    uv run python -m steiner_audit.verify --family d_steiner --subcase f_ge_d \
        --cert vendor/regen/d_steiner@0.860/certificate_rho=0.86_f_ge_d.bin \
        --rho 0.860 --workers 16
    # exact ceiling / margin analysis of any partition
    uv run python -m steiner_audit.ceiling --family d_steiner --subcase f_ge_d \
        --cert <path> --sample 50000

Generation cost at 0.860: 0.9–9.6 h per case (single core). Verification:
~4,600 records/s at 16 workers on Apple Silicon (measured); ~2.5 days for
the largest case.

## 5. Limitations

- **Lemma layer inherited, not verified.** Identical to the published
  proof's posture; the M1 audit's findings (F1–F5) apply unchanged. The
  244.1M full-box-closed regions do not depend on the unimodality claim;
  the remainder check vertices only, as their checker does — but at all
  2^n vertices rather than their 2^(n-1).
- **Generator trusted for coverage.** That the partition tiles each case
  domain is the generator's construction, as in the published work; our
  verification establishes per-region non-positivity, not tiling
  completeness. The semantic-diff and regeneration reproducibility results
  of M1 support (but do not prove) generator determinism.
- **Upstream content not redistributed.** The PKU repository and dataset
  are unlicensed; reproduction fetches them from the public sources
  against pinned hashes (ADR-0002). Regenerated certificates are likewise
  derivatives and stay local; this note ships hashes only.
- **Sampled ladder rungs are not claims.** Only exhaustively verified
  rhos (0.856, 0.860) are claimed; ladder numbers above them are scouting
  evidence.

## 6. Artifact index

- `artifacts/verification/claim_0.860_*.run.json` — four claim-grade run
  records (counts, certificate sha256, code revision, exact rho).
- `artifacts/verification/ceiling_full_*.json` (+ `.bottlenecks.jsonl`) —
  exact fixed-tiling ceilings of the published partitions.
- `artifacts/verification/probe_ceiling_*.json` — sampled ladder passes.
- `artifacts/acquisition/regen_manifest.json` — content-addressed manifest
  of every regenerated certificate.
- `artifacts/notes/observations.md` — OBS-9 through OBS-19 (the campaign
  log, including generator scaling and non-monotonicity observations).
