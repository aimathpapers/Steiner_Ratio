# Test conventions (both seams)

Two seams only — no tests of internal structure (M1 testing decision). New
tickets extend these patterns; they do not invent new seams.

## Seam 1: verifier boundary (`test_records.py`, `test_kernel_boundary.py`)

Certificate records in, per-region verdicts out.

- Fixtures are **miniature hand-crafted certificate files** built with
  `write_records` (or raw `struct.pack` for deliberately malformed bytes).
  Never fixture against the vendored dataset here.
- Splits used by fixtures are embedded as `Split` literals in the test file
  (transcribed from the real splits.txt where realism matters), so this seam
  runs without `vendor/`.
- Required fixture genres per case family: known-good region; sign-flipped
  region that must fail (certified positive); a region whose lemma condition
  cannot be certified; malformed/truncated records rejected at decode; every
  record-validity rule (mono_vars, |S+|, infinite bounds, subcase skip).
- Verdicts must state mode (`vertex_parity` / `full_box` / `skipped` /
  `invalid` / `failed` / `inconclusive`); `ok` is True only for passing or
  skipped records.

## Seam 2: splitting-function oracle (`src/steiner_audit/refmath/<family>.py`, `test_oracle_<family>.py`)

Our Arb enclosures against an independently written mpmath reference
(60 significant digits), marked `@pytest.mark.oracle`.

- The reference modules live in the package (`steiner_audit.refmath`) so
  capsule replay scripts can embed them, but the discipline is the same:
  they re-implement geometry, lemma bounds, lemma conditions, and the
  composed F **from the same mathematical definitions, separately** — they
  must never import from `steiner_audit`'s numerics (`Split` tuples are
  shared shape, not shared math).
- Sample points are exact dyadic floats so both stacks read identical inputs.
  Grids are seeded (deterministic); targeted points cover rare condition
  regions. Points on branch boundaries are out of scope — conditions are
  compared only where both stacks decide with margin.
- Assertions: the mpmath value lies **inside** our enclosure (containment,
  not closeness); branch/condition decisions agree; every priceable split
  gets at least one composed-F comparison, and unpriceable splits (no lemma
  covers their S+/trapped edges) must fail evaluation for every lemma —
  mirroring their checker's KeyError path.
- Spot-checks against their Julia evaluations are cross-check machinery
  (ticket #11), permitted as test oracle by ADR-0002.
- rho is a required exact-rational (`fmpq`) keyword at both seams since
  ticket #15 — tests state the rho they certify (`RHO_M1` for M1 parity).
  `test_rho_param.py` covers the rho-flip fixture, capsule rho, and status
  aggregation; the oracle suites add containment at spot rhos above and
  below 8559/10000 plus the affine-in-rho reference identity.

## Markers

- `oracle`: seam-2 suites.
- `real_data`: needs `vendor/` (snapshot or dataset). CI-less quick runs use
  `pytest -m "not real_data"`.

## Lessons already encoded (do not relearn)

- Never `**` on balls — python-flint `__pow__` NaNs on zero-containing bases
  (`arbcalc.sq`).
- `sqrt` of a sum of squares needs `sqrt_nonneg` — ball multiplication gives
  x*x an infinitesimally negative lower bound.
- Empty S+ is legal (splits that cut off enough terminals reconnect for
  free); the evaluator must price it as 0, not fail.
