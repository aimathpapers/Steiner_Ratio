# The LLM Lemma Pipeline for the Gilbert–Pollak Steiner Ratio Conjecture (arXiv:2601.22365) — Method, Certificate Format, Trust Chain

Research date: 2026-08-11. All claims below are cited to a primary source (URL + section/file). Where a
load-bearing fact could not be verified from a primary source, this is said explicitly. Fetches were made
through a summarizing web-fetch tool; verbatim quotes were requested explicitly and are marked as such.

## 0. Paper and artifact identification

- Paper: "Towards Solving the Gilbert-Pollak Conjecture via Large Language Models", Yisi Ke, Tianyu Huang,
  Yankai Shu, Di He, Jingchu Gai, Liwei Wang. arXiv:2601.22365. v1: Jan 29 2026; v2 (current): May 21 2026.
  44 pages, 11 figures, cs.DM + cs.LG. DOI 10.48550/arXiv.2601.22365.
  [Source: https://arxiv.org/abs/2601.22365, metadata page.]
- Headline result: "a new certified lower bound of 0.8559 for the Steiner ratio", vs. the previous record
  0.824 (Chung–Graham 1985). [Source: https://arxiv.org/abs/2601.22365, abstract; comparison in
  https://arxiv.org/html/2601.22365v2, Introduction and Section 4 / Figure 9.]
- Affiliation caveat: the task brief calls this a "Peking University paper". The arXiv HTML v2 as fetched
  did not surface explicit institutional affiliation lines; the acknowledgments state "LW is supported by
  National Science Foundation of China (NSFC92470123, NSFC62276005) and the State Key Laboratory of General
  Artificial Intelligence". The PKU affiliation is therefore NOT verified here from the primary text (Di He
  and Liwei Wang are publicly known PKU faculty, but that is background knowledge, not a fetched fact).
  [Source: https://arxiv.org/html/2601.22365v2, acknowledgments.]
- Artifact repo: https://github.com/keyisi2006/Steiner-Ratio. Created 2025-12-10; last content push
  2026-02-11; default branch `main`; 7 stars, 0 forks; **no license file and no repo description**.
  Commit history (complete, 7 commits): 2025-12-10 "Initial commit", 2025-12-10 "collect files" (keyisi2006);
  2026-01-29 "Update Final Version", "Picture" (syksykCCC); 2026-02-10 "Update certificate/",
  "Update pipeline/" (keyisi2006); 2026-02-11 "figure label update" (syksykCCC).
  [Sources: https://api.github.com/repos/keyisi2006/Steiner-Ratio ;
  https://api.github.com/repos/keyisi2006/Steiner-Ratio/commits?per_page=30.]
  Note the timeline: the `certificate/` directory in its current form landed 2026-02-10 — after v1
  (Jan 29) and before v2 (May 21). v1 already pointed at the repo: "Reproducible codes and the final proof
  can be found in https://github.com/keyisi2006/Steiner-Ratio" (v1, Introduction).
  [Source: https://arxiv.org/html/2601.22365v1.]

## 1. Mathematical scaffolding (only as needed to read the lemmas)

- The conjecture (Gilbert & Pollak 1968): for any finite planar point set, SMT length / MST length
  ≥ √3/2 ≈ 0.86602540378, with the ratio infimum conjectured to equal √3/2. Lower-bound progression:
  0.5 (1968) → 0.577 (1976) → 0.743 (1978) → 0.8 (Du–Hwang 1983) → 0.824 (Chung–Graham 1985) →
  0.8559 (2026, preprint). [Source: https://raw.githubusercontent.com/teorth/optimizationproblems/main/constants/43a.md,
  which lists this progression and cites Gilbert–Pollak, SIAM J. Appl. Math. 16(1):1–29, 1968.]
  Chung–Graham 1985 and Du–Hwang 1983 were not fetched directly (paywalled journals); the 0.824 and 0.8
  values are taken from Tao's problem file and from the paper's introduction ("Du & Hwang (1983) achieved
  0.8, followed by Chung & Graham (1985) reaching 0.824, with no further improvements ... over nearly four
  decades"). [Source: https://arxiv.org/html/2601.22365v2, Introduction/related work.]
- The 1990 Du–Hwang "proof" and what killed it. Ivanov & Tuzhilin (arXiv:1402.6079, "Du–Hwang
  Characteristic Area: Catch-22", full text extracted): "the proof suggested by D.Z. Du and F.K. Hwang in
  1990 contains serious gaps. Those gaps are due to the concept of so-called characteristic area of a
  minimal Steiner tree, which was introduced informally. All attempts of many authors to cover these gaps
  by giving formal definitions failed because the resulting object must have several properties
  contradicting to each other." Specifically, the Du–Hwang scheme restricts attention to spanning trees
  inside the "characteristic area" (inner spanning trees) and needs two properties simultaneously:
  (a) continuity of the minimal inner spanning tree length under deformations of the boundary set, and
  (b) monotonicity — the characteristic area of the whole tree must contain that of each full component.
  Defining the area of a non-full tree as a union of full components' areas breaks continuity (the minimal
  inner spanning tree length "changes spasmodically"); defining it by continuity/limits breaks
  monotonicity. "The monotonicity property is a key one in the Du–Hwang approach since it is necessary to
  make a reduction of the Steiner ratio estimation to the case of full Steiner minimal trees." Their note
  cites their refereed version: Ivanov & Tuzhilin, "The Steiner Ratio Gilbert-Pollak Conjecture is Still
  Open", Algorithmica 62(1–2):630–632 (2012), and Innami–Kim–Mashiko–Shiohama, Algorithmica 57(4) (2010).
  [Source: https://arxiv.org/pdf/1402.6079, full text, pp. 1–3; the Springer page for the 2012 note
  redirects to an auth wall and was not fetched.]
- Du–Hwang framework reused by the new paper: the paper builds on "the Du & Hwang inductive reduction
  argument" (its Lemma 14, Appendix B.1.2): induction on the number of terminals n, base case "n ≤ 4 is
  shown by Pollak (1978)" (Appendix B.1.1); the induction step prunes a subset V* of terminals via a
  "splitting" and shows the ratio survives the reduction. The characteristic-area machinery that failed in
  1990 is NOT what is reused; what is reused is the induction-on-terminals reduction to local
  configurations. [Source: https://arxiv.org/html/2601.22365v2, Section 2.2, Appendix B.1.]

## 2. The method (paper): LLM lemma-generation loop end to end

All from https://arxiv.org/html/2601.22365v2 unless noted.

- Loop architecture (Section 3): a closed loop of Propose → Translate → Evaluate → Reflect.
  (1) An LLM proposes geometric lemmas as rule-constrained executable code; (2) the lemmas are translated
  into "verification functions"; (3) a symbolic "reward model" runs branch-and-bound with vertex checking
  over the parameter space to compute the tightest certified lower bound the current lemma set supports;
  (4) on failure, the uncertified regions are geometrically abstracted into a "bottleneck region" that is
  fed back to the LLM as structured feedback for the next proposal round (Section 3.3).
- What a lemma is (Section 3.2): not a theorem-proof pair but a **condition/bound predicate pair in code**:
  a boolean `*_cond()` over the parameter vector plus an upper-bound function `*_upper_bound()`. Two types:
  - **Trapped Regular Point Lemmas** (Section 3.2.1): along a "Steiner Spiral Chain" A0…An with 120°
    angles at Steiner points, "Type A"/"Type B" linear conditions on edge lengths imply the regular point
    An is confined ("trapped") inside an explicit polygon, which yields a distance upper bound. Example
    (its Lemma 8, Type B): "If orthogonal projection H of point Au onto line Av·Av+1 lies on the ray AND
    |Au·H| < as, then An is trapped inside polygon Au...Av·H·Au". Formal shape (its Theorem 9): if linear
    constraint C together with the chosen Type-A conditions implies a disjunction of Type-B conditions,
    then An lies in the specified polygon.
  - **Valid 4-Point Steiner Tree Lemmas** (Section 3.2.2): algebraic conditions under which a specific
    4-terminal Steiner topology (e.g. the (AB)-(CD) full topology, its Theorem 16, Appendix B.2) exists,
    together with a closed-form length formula for that tree, used to price S+ in the splitting.
- How lemmas compose into a lower bound (Section 2.2): parameter space W = [0,+∞)^n, "the i-th entry
  represents the length of the i-th edge" (Definition 12) of a local configuration pruned from a full
  Steiner tree (deepest leaf A, sibling B, nearby terminals/residual subtrees D, P, Q..., normalized so
  |AX| = 1; Figure 10). A **splitting** τ = (V*, S−, S+, t*) (Definition 13) removes edge set S− to cut
  off terminals V*, reconnects the survivors with Steiner edges S+, and re-links V* with spanning edges
  t*. The splitting function is F_τ(w, ρ) = ρ·L_{t*} + L_{S+} − L_{S−}, and the reduction theorem
  (Theorem 4) says ρ_Steiner ≥ ρ holds if max_{w∈W} min_{F∈𝓕} F(w, ρ) ≤ 0 — i.e. every configuration is
  killed by at least one splitting. The lemmas supply certified upper bounds on the S+ and t* lengths (and
  trap conditions restricting where regular points can be), which is what makes each F evaluable and sound.
- Why finite checking suffices (Section 3.1): a **verification function** (Definition 5) must be
  axis-unimodal ("Shape Constraint": decreasing-then-increasing along each coordinate) and must lower-bound
  a splitting function ("Bounding Constraint"). Theorem 6 ("Vertex Maximum Property"): the maximum of such
  an f over an axis-aligned hyperrectangle is attained at a vertex, so non-positivity at the 2^n vertices
  certifies non-positivity on the whole box. Branch-and-bound over boxes plus vertex checks then covers W.
- Role of Mathematica/CAD in the loop (Sections 3.1–3.3, Section 6): "The agent first employs
  Mathematica's Reduce function to compute the feasible region" of proposed condition sets (3.2.1);
  validation is offloaded to Mathematica "to perform exact computation" (v1 wording; v2 3.3 similar); the
  limitations section states "Our verifier relies on Cylindrical Algebraic Decomposition (CAD), whose cost
  grows rapidly with the number of variables and the algebraic degree of constraints", and "we adopt a
  conservative policy in which high-complexity 4-point lemmas are excluded from regimes with unbounded
  parameters, since CAD over variable parameters becomes intractable" (Section 6).
- Human in the loop (Section 4 / 3.3): "every LLM-proposed lemma is manually checked for correctness
  before being instantiated as a verification function"; "we performed independent manual verification of
  the generated proofs to confirm that the overall logical argument is sound". The paper does not say
  which author did the checking.
- Cost accounting (Section 4): ~0.5M tokens total (~35K tokens per round), 4.6 hours of LLM reasoning
  time, "roughly a dozen iterative rounds" to converge, "approximately 100 rounds of experiments" across
  development, ~11.7 hours of reward-model (verification) compute, "only thousands of LLM calls" (abstract),
  "total cost of just a few hundred dollars" (introduction/impact statement). So the ~0.5M tokens covers
  the lemma-proposal loop of the final successful trajectory; the ~100 experiment rounds and the symbolic
  verification compute are reported separately. Models: GPT-5 and Gemini 3 Pro; "In all cases, the LLMs
  successfully proposed valid lemmas, and after roughly a dozen iterative rounds, the system consistently
  converged to a Steiner ratio lower bound of approximately 0.8559" (Section 4, robustness across
  backbones).
- Scale not reported: the paper gives **no explicit count** of splits/regions/lemmas in the final
  certificate (that lives only in the repo — see below).

## 3. THE CERTIFICATE FORMAT (repo: github.com/keyisi2006/Steiner-Ratio)

### 3.1 What ships where

Top-level README (verbatim): "This repository is the supplementary material of this paper. The directory
contains two folders `certificate/` and `pipeline/`." … "If you want to quickly verify our theoretical
result ρ = 0.8559, please refer to the `certificate/` folder" … "There are 2 subfolders `d_regular/` and
`d_steiner/` here, corresponding to two cases."
[Source: https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/README.md.]

Exhaustive tree of the certificate half (from the GitHub trees API, HEAD):

```
certificate/README.md                       (9,815 B)   verification guide
certificate/d_regular/                                  case 1
  splits.txt        (27,455 B)   160 splitting definitions, text
  lemmas/lemma_0.jl … lemma_8.jl (419–984 B each)  9 lemma condition/bound files, Julia
  formulas/F0 … F8  (1.6–74.5 KB) C++ template headers, one splitting function per template
  Makefile, plot_f_ge_d.cpp, plot_f_le_d.cpp       partition/certificate generators (C++)
  split_validation.py, mono_check.py, verify_partition.py   Python checkers
  verify_certificate.jl (11,091 B)                 interval-arithmetic verifier, Julia
certificate/d_steiner/                                  case 2, identical structure
  splits.txt (301,189 B), formulas up to 544.5 KB (F0), lemmas ×9, same 7 tool files
pipeline/                                               the LLM-agent side
  Makefile, binsearch.cpp, calc.py, evolve.py, evolve_wsl.py, extract.py, formulas/F0
  geosteiner-5.3/   (vendored GeoSteiner 5.3 source tree, 200+ files)
```
[Source: https://api.github.com/repos/keyisi2006/Steiner-Ratio/git/trees/HEAD?recursive=1, enumerated twice.]

The proof is organized as **two main cases (`d_regular`, `d_steiner`) × two subcases (`f ≥ d`, `f ≤ d`)**,
with parameter-space dimensions n: d_regular f≥d → n=5, f≤d → n=6; d_steiner f≥d → n=7, f≤d → n=8.
"The proof verification consists of two main cases (`d_regular` and `d_steiner`), each with two subcases
(`f ≥ d` and `f ≤ d`)" (certificate README, verbatim). Here `d` and `f` are two of the edge-length
variables (the variable alphabet in d_regular is b, c, d, s, e, f, visible in splits.txt and the lemma
code). **Not verified:** neither the certificate README nor the paper (which never uses the
d_regular/d_steiner notation) states in fetched text what geometric distinction the two main cases encode;
the natural reading (the relevant neighbor of the pruned leaf being a regular point vs. a Steiner point)
is an inference, not a sourced fact.
[Sources: https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/certificate/README.md ;
https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/certificate/d_regular/splits.txt ;
https://arxiv.org/html/2601.22365v2 (notation absence).]

### 3.2 The four artifact layers of one case directory

**(a) `splits.txt` — the splitting definitions.** Text, one splitting per line, five semicolon-separated
fields. First line of d_regular/splits.txt, verbatim:

```
V_star:['A']; S_minus:[('B', 's'), ('s', 'r'), ('A', 's')]; S_plus:('r', 'B'); T_star:[('A', 'B')]; mono_vars: ['c', 'd', 's', 'e', 'f']
```

V_star = terminals cut off; S_minus = Steiner-tree edges deleted; S_plus = the ≤4 points to be re-joined
by a new Steiner tree; T_star = spanning edges re-linking V_star; mono_vars = variables in which the
resulting splitting function is monotone non-increasing (used later for unbounded boxes). d_regular has
160 splits; d_steiner's splits.txt is ~11× larger (301 KB).
[Source: https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/certificate/d_regular/splits.txt,
first 10 lines fetched verbatim; sizes from the trees API.]

**(b) `lemmas/lemma_k.jl` — the lemma conditions and bounds, in Julia with interval arithmetic.** Each
file is small (0.4–1.1 KB) and defines boolean condition functions and interval-valued upper-bound
functions over the parameter vector, plus a Dict mapping geometric edges to (condition, upper-bound)
pairs. Verbatim excerpt from d_regular/lemmas/lemma_1.jl:

```julia
function X_cond1(pos::SVector{8, Point}, vars::Vector{T})::Bool
	(b, c, d, s, e, f) = vars
	return e < interval(1) - c + interval(2)/sqrt(interval(3))*s &&
		   c + e >= interval(1)
end
```

lemma_0.jl (per targeted fetch) pairs e.g. edge A→X with condition `c <= interval(1)` and bound
`max(dist(A,r), dist(A,P))`, and edge D→Y with condition `F_VAL == 1` and bound `max(dist(D,P), dist(D,Q))`
— i.e. exactly the paper's `*_cond()` / `*_upper_bound()` lemma shape, transliterated into
IntervalArithmetic.jl expressions. Note all constants are constructed via `interval(...)` (including
rationals like `interval(2)/sqrt(interval(3))`), so evaluation is outward-rounded.
[Sources: https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/certificate/d_regular/lemmas/lemma_1.jl
(23-line file, quoted verbatim); …/lemmas/lemma_0.jl (structure fetch).]

**(c) `formulas/F0…F8` — the splitting functions as C++ templates** (used by the *generator*, not the
Julia verifier). Extensionless text files containing template specializations, one per
(split, lemma)-instantiated bound. Verbatim head of d_regular/formulas/F0:

```cpp
template<> struct F<0> {
constexpr static int split_id = 1;
constexpr static int lemma_id = 0;
ld operator()(ull mono_mask, ld b, ld c, ld d, ld s, ld e, ld f) {
if(!(true) || (mono_mask | 62) != 62) return INF;
ld L_s_minus = b + s + 1;
ld L_t = sqrt(b*b + b + 1);
ld L_s_plus = sqrt(b*b + b*s + s*s);
return rho*L_t + L_s_plus - L_s_minus;
}};
```

Each functor returns exactly the paper's F_τ(w,ρ) = ρ·L_{t*} + L_{S+} − L_{S−} in `long double`, tagged
with the `split_id`/`lemma_id` it instantiates; the `mono_mask` guard enforces which monotone directions
the formula may be used with.
[Source: https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/certificate/d_regular/formulas/F0,
first template quoted verbatim.]

**(d) The certificate proper: binary region records.** A certificate is a list of records, each asserting
"on this box, this splitting with this lemma is non-positive". Record format from the certificate README,
verbatim: "Each certificate record in `certificate_{suffix}.bin` has the following binary format
(little-endian, no padding)": int32 region_id; then n pairs of float64 (low[i], high[i]); then int32
split_ID; int32 lemma_ID. Matching generator code (plot_f_ge_d.cpp, verbatim):

```cpp
fcert.write((char *)&ID, 4);
for(int i = 0; i < n; i++) {
    fcert.write((char *)&box[i][0], sizeof(box[i][0]));
    fcert.write((char *)&box[i][1], sizeof(box[i][1]));
}
int split_id = split_ids[id], lemma_id = lemma_ids[id];
fcert.write((char *)&split_id, 4);
fcert.write((char *)&lemma_id, 4);
```

**The .bin files are not in the git repo.** They are either regenerated by the C++ programs (~30 hours:
"Approximately 30 hours total across both cases (most time is spent on the `f ≤ d, d_steiner` case)") or
downloaded pre-generated from https://huggingface.co/datasets/keyisi/steiner-ratio (exists; 49.3 GB total;
no dataset card; 55 downloads in the month before this fetch).
[Sources: certificate README (record format, 30-hour figure, HF link);
https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/certificate/d_regular/plot_f_ge_d.cpp ;
https://huggingface.co/datasets/keyisi/steiner-ratio.]

### 3.3 Replay: the five-step verification procedure

From the certificate README (run identically in d_regular/ and d_steiner/):

1. `python split_validation.py` — all splits in splits.txt are well-formed.
2. `python mono_check.py` — the `mono_vars` fields correctly identify non-increasing directions.
3. `make && ./plot_f_ge_d && ./plot_f_le_d` — (re)generate the domain partition + certificate binaries
   (~30 h total), or download them from HuggingFace.
4. `python verify_partition.py "certificate_rho=0.8559_f_ge_d.bin" "child_rho=0.8559_f_ge_d.bin" <n> --reversed`
   — the boxes exactly partition [0,+∞)^n with no gaps or overlaps.
5. `julia --threads auto verify_certificate.jl --f-ge-d` (and `--f-le-d`) — interval-arithmetic
   non-positivity check of every record.

[Source: https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/certificate/README.md, "Quick
Start Commands" and step list, quoted near-verbatim.]

What each verifying program actually does (from the code itself):

- **Generator (`plot_f_ge_d.cpp`, untrusted):** adaptive branch-and-bound in `long double` with epsilon
  1e-6. Picks the widest dimension (reciprocal-of-lower-bound as width for semi-infinite intervals),
  bisects at midpoints, doubles the frontier (`2 * box[dim][0]`) for unbounded dimensions; emits a
  certificate record when some formula F<k> is < −eps at all finite corners. Verbatim dimension-selection:
  `auto dim = max_element(box.begin(), box.end(), [](auto &&x, auto &&y) { ld sepx = isinfinity(x[1]) ? 1 / x[0] : x[1] - x[0]; ... });`
  [Source: …/certificate/d_regular/plot_f_ge_d.cpp.]
- **Partition checker (`verify_partition.py`):** reconstructs the bisection tree bottom-up from the leaf
  and child files and checks (i) siblings are adjacent along exactly one axis
  (`if not (left_high == right_low): raise RuntimeError(...)`), (ii) parents are the exact union of
  children (`2.0 * m == (a + b)` midpoint rule), (iii) the roots tile [0,+∞)^n as the expected dyadic
  cells (`l == 0.0 and h == 1.0` or `l == 1.0 and not math.isfinite(h)` per axis). It uses native float64
  with **exact equality** comparisons — sound only because all endpoints are dyadic values produced by
  midpoint bisection/doubling, hence exactly representable. [Source: …/certificate/d_regular/verify_partition.py.]
- **Certificate verifier (`verify_certificate.jl`, the trusted kernel):** Julia + IntervalArithmetic.jl +
  StaticArrays, multithreaded. Hardcodes the target as an interval over a rational —
  `const rho::T = interval(8559//10000)` (verbatim). Reads each binary record
  (`region_id::Int32`, 2×n `Float64` box, `split_id::Int32`, `lemma_id::Int32`), then for every one of the
  2^n box vertices builds interval-valued variables and checks the splitting function, rejecting unless
  provably ≤ 0. Core loop, verbatim:

  ```julia
  for mask in range(0, (1 << n) - 1)
      ...
      vars[i] = interval(v)
      ...
      if F_VAL == 2
          vars[VarID['f']] = vars[VarID['d']]
      end
      ret = evaluate_split(split, vars, lemma_id)
      if !(ret <= interval(0))
          throw("vertex check failed.")
      end
  end
  ```

  Infinite upper endpoints are only allowed for variables declared in the split's `mono_vars`
  (`if isinf(box[2, i]) && !(i in split.mono_vars) throw(...)`) — monotonicity, checked in step 2, is what
  extends a finite-vertex check to an unbounded box. In the f≥d subcase the verifier substitutes f := d
  (`F_VAL == 2`), i.e. verifies on the f = d boundary only, per the README's "For f≥d cases, verifies only
  at f=d boundaries". On success it prints "All [count] regions verified."
  [Source: https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/certificate/d_regular/verify_certificate.jl,
  verbatim excerpts; certificate README for the f=d boundary rule.]

### 3.4 The exact trust chain from "files in repo" to "0.8559 is proved"

Layered, from must-trust to machine-checked:

1. **Trusted (paper-level mathematics, human-checked only):** Theorem 4 (splitting ⇒ lower bound),
   Theorem 6 (vertex maximum property for verification functions), the Du–Hwang-style induction with
   Pollak's n ≤ 4 base case, and — critically — the **mathematical truth of the nine lemmas per case**
   (that each `X_cond` really implies its `upper_bound`). The lemmas were checked by Mathematica
   Reduce/CAD inside the pipeline and "manually checked for correctness" by the authors; the Julia layer
   *evaluates* them but does not *prove* them. [Sources: arXiv HTML v2 Sections 2.2, 3.1–3.3, 4, 6;
   certificate README trust-chain section.]
2. **Machine-checked, exact-dyadic:** splits well-formedness (split_validation.py), mono_vars correctness
   (mono_check.py), and that the emitted boxes exactly tile [0,+∞)^n (verify_partition.py; exact float
   equality on dyadic endpoints). [Source: certificate README steps 1–2, 4; verify_partition.py code.]
3. **Machine-checked, rigorous numerics:** for every record, non-positivity of the designated splitting
   function at all box vertices in outward-rounded interval arithmetic, with ρ = interval(8559/10000)
   (verify_certificate.jl). [Source: verify_certificate.jl code.]
4. **Untrusted (does not need to be correct, only lucky):** the C++ generators (long double, eps=1e-6),
   GeoSteiner, the LLMs, Mathematica-as-search-tool. Their output is fully re-checked by layers 2–3; a bug
   there can only make verification fail, not make a false bound pass — *except* insofar as layer-1 lemma
   truth was established with Mathematica + eyeballs.

Conclusion of the chain, as the certificate README puts it: passing all steps means "All certificates
prove non-positivity on their respective regions", which with Theorems 4/6 and the lemmas yields
ρ_Steiner ≥ 0.8559. [Source: certificate README, "Trust Chain" and completion checklist.]

## 4. Weaknesses in the trust chain

- **Unrefereed.** arXiv preprint, no journal/DOI beyond arXiv's, no known peer review as of 2026-08-11.
  The scoreboard entry on Tao's repo is marked "(2026, preprint)".
  [Sources: https://arxiv.org/abs/2601.22365 ; https://raw.githubusercontent.com/teorth/optimizationproblems/main/constants/43a.md.]
- **Paper ↔ artifact mismatch (the oddest finding).** The v2 paper (May 2026) still describes the verifier
  as Mathematica/CAD and lists interval arithmetic as *future work* ("Lighter-weight certificates (e.g.,
  interval arithmetic, sum-of-squares relaxations, or learned proof sketches that invoke CAD only on hard
  sub-regions) are a natural next step", Section 6) — while the repo has shipped a Julia
  IntervalArithmetic.jl certificate since 2026-02-10. Two targeted fetches of the v2 HTML found **no
  mention of Julia, IntervalArithmetic, GeoSteiner, or the certificate/ directory layout**. The
  peer-reviewable text and the actual proof artifact have diverged; the certificate is documented only in
  the repo README. [Sources: arXiv HTML v2 (two targeted fetches); repo commits API; certificate README.]
- **Lemma truth is the soft spot.** The interval certificate machine-checks *composition* (non-positivity
  of F over the whole domain) but not the *lemmas* (trapped-point polygons, 4-point topology validity, and
  the axis-unimodality "Shape Constraint" that Theorem 6 needs). Those rest on Mathematica CAD runs that
  are not shipped as replayable artifacts, plus author manual review ("every LLM-proposed lemma is
  manually checked"). There is no Lean/Isabelle formalization; the paper itself says formal proof
  assistants "are required for end-to-end autonomous mathematical discovery" (Section 6).
- **CAD scaling forced conservatism.** "High-complexity 4-point lemmas are excluded from regimes with
  unbounded parameters, since CAD over variable parameters becomes intractable" (Section 6) — i.e. the
  method's ceiling, and part of why the bound stops at 0.8559 rather than approaching 0.866. Extending to
  "5-point or larger Steiner-tree topologies" would amplify the verification bottleneck (Section 6).
- **Floating point.** Present in two places with different risk profiles: (i) the generators — harmless in
  principle (untrusted layer); (ii) verify_partition.py's exact `==` float comparisons — sound only under
  the implicit invariant that every endpoint is dyadic (produced by midpoint bisection and doubling from
  0/1/∞). That invariant is enforced by convention, not checked independently. The trusted numeric kernel
  (Julia) is interval arithmetic throughout, including `rho = interval(8559//10000)`.
- **Certificate data is out-of-repo.** The actual .bin certificates are a 49.3 GB HuggingFace dataset with
  no dataset card, or a 30-hour deterministic-in-principle regeneration; the git repo pins neither hashes
  nor sizes of the expected .bin outputs (none found in fetched README text). Bit-rot or silent dataset
  replacement would be undetectable from the repo alone. [Sources: certificate README; HF dataset page.]
- **Repo hygiene.** No license (reuse/redistribution legally unclear), no description, 7 commits, content
  frozen since 2026-02-11. The top-level README documents pipeline files (`binsearch.py`, `llm.py`,
  `plot.cpp`, `split_rho.cpp`, `splits4.txt`, prompt files) that do **not** appear in the HEAD tree, which
  contains only Makefile, binsearch.cpp, calc.py, evolve.py, evolve_wsl.py, extract.py, formulas/F0 and
  the vendored geosteiner-5.3/. The LLM-agent component (`llm.py`) and the oracle (`plot.cpp`) as named in
  the README are absent or renamed — so the *pipeline* half is not reproducible as shipped, even though
  the *certificate* half is self-contained. (Tree enumerated twice via the trees API; a summarization miss
  by the fetch tool cannot be fully excluded, but both enumerations agree.)
  [Sources: repo README verbatim file-role section; trees API enumeration.]
- **Paper's own to-do list** (Section 6, quoted above): interval-arithmetic/SOS certificate backends,
  restraint of CAD to hard sub-regions, 5-point topologies, Lean formalization, reducing dependence on
  manual lemma checking.

## 5. Replication requirements (as of 2026-08-11)

To re-verify the certificate (the proof artifact) — **no Mathematica license needed**:

- Python 3.x; a C++23 compiler (g++ ≥ 13); GNU Make; Julia with IntervalArithmetic.jl
  (`julia -e 'using Pkg; Pkg.add("IntervalArithmetic")'`) and StaticArrays. [Source: certificate README,
  software requirements section; verify_certificate.jl imports.]
- Compute: ~30 hours CPU for regenerating partitions/certificates across both cases (dominated by
  d_steiner f≤d, n=8), or download 49.3 GB from https://huggingface.co/datasets/keyisi/steiner-ratio and
  skip step 3. The Julia verification step's runtime is not stated in fetched text (it is multithreaded,
  `--threads auto`). Julia version and IntervalArithmetic.jl version are **not pinned** anywhere fetched —
  a reproducibility gap worth noting since IntervalArithmetic.jl changed its API and flavor semantics
  across 0.21/0.22. [Sources: certificate README; verify_certificate.jl. Version-pinning absence: no
  Project.toml/Manifest.toml appears in the tree enumeration.]
- To re-run the *pipeline* (lemma discovery), additionally: GeoSteiner 5.3 installed into
  `pipeline/geosteiner-5.3/` (vendored in-repo), WSL on Windows, LLM API access (GPT-5 / Gemini 3 Pro),
  and a Mathematica installation for the agent's Reduce/CAD calls — plus the README-documented but
  missing-from-tree agent files (see §4), which currently blocks faithful replication of the loop.
  [Sources: repo README; arXiv HTML v2 Section 3.2.1; trees API.]

What swapping the verifier would concretely mean:

- **"Swap to interval arithmetic" is already done** for the composition layer — that is exactly what
  verify_certificate.jl is. The genuine upgrades remaining are:
  1. **Certify the lemmas themselves.** Each lemma is a semialgebraic implication (cond ⇒ bound), so a
     rigorous backend would emit SOS/Positivstellensatz certificates (checkable by rational-arithmetic LP/SDP
     replay) or Lean proofs (e.g. via polyrith/CAD tactics) for the nine lemmas per case, replacing
     "Mathematica said Reduce gave this region + we checked by hand".
  2. **Certify the Shape Constraint** (axis-unimodality) underlying Theorem 6 for every formula — currently
     asserted per-formula by construction and spot-checked via mono_check.py's monotone directions.
  3. **Harden the partition check**: replace exact-float dyadic equality with integer/rational endpoint
     bookkeeping so the tiling proof does not depend on an unchecked dyadic invariant.
  4. **Pin the toolchain** (Julia Manifest, compiler versions, dataset hashes).
  These map one-to-one onto the paper's own Section 6 list (interval arithmetic ✓ done for composition;
  SOS and Lean pending). [Basis: §3–§4 above; paper Section 6.]

## 6. Current status (2026-08-11)

- **Record status: 0.8559 stands.** Tao's optimizationproblems scoreboard row for problem 43 reads
  `| 43 | Gilbert-Pollak conjecture (Steiner ratio) | 0.8559 | 0.86602540378 |`, and
  constants/43a.md lists "0.8559 (2026, preprint)" with reference KHSHGW2026 = arXiv:2601.22365.
  [Sources: https://raw.githubusercontent.com/teorth/optimizationproblems/main/README.md ;
  https://raw.githubusercontent.com/teorth/optimizationproblems/main/constants/43a.md.]
- **Provenance of the scoreboard entry:** it was added by the authors themselves — PR #28 "Added 43a.md
  Steiner Ratio (Gilbert-Pollak Conjecture)", opened 2026-02-02 by **syksykCCC**, the same account that
  commits to keyisi2006/Steiner-Ratio ("Update Final Version", 2026-01-29). All subsequent commits to
  43a.md (2026-06-24, 2026-06-29) are LaTeX-subscript formatting fixes (PRs #112, #120 by Chessing234).
  So the entry reflects self-report accepted into the repo, not an independent verification event recorded
  there. [Sources: https://api.github.com/search/issues?q=repo:teorth/optimizationproblems+steiner ;
  https://api.github.com/repos/teorth/optimizationproblems/commits?path=constants/43a.md.]
- **Critiques / replications / follow-ups:** none found. Web searches for critiques, replications, or
  papers citing 2601.22365 surfaced only the paper itself, its arXiv pages, secondary news commentary
  (machinebrief.com), and pre-2026 literature. A Semantic Scholar citation-graph query was rate-limited
  (HTTP 429, twice) and could not be completed — so "no citing works" is **not verified**, only "none
  found via web search". The paper repo has had no content push since 2026-02-11; v2 (May 21) is the
  latest paper version. [Sources: WebSearch results 2026-08-11; api.semanticscholar.org (429);
  repo metadata API.]
- The conjecture itself remains open; 0.8559 < √3/2, and the paper claims only a lower bound, not the
  conjecture. [Sources: arXiv abstract; Tao constants/43a.md.]

## Sources (all URLs fetched during this research)

Paper:
- https://arxiv.org/abs/2601.22365 (metadata, abstract, version history)
- https://arxiv.org/html/2601.22365v2 (full text, fetched 4× with targeted prompts: method, limitations, theorems, affiliations)
- https://arxiv.org/html/2601.22365v1 (v1 comparison: Mathematica-only, no limitations section)

Certificate/repo (keyisi2006/Steiner-Ratio):
- https://api.github.com/repos/keyisi2006/Steiner-Ratio (repo metadata)
- https://api.github.com/repos/keyisi2006/Steiner-Ratio/commits?per_page=30 (full commit history)
- https://api.github.com/repos/keyisi2006/Steiner-Ratio/git/trees/HEAD?recursive=1 (file tree, fetched 2×)
- https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/README.md (fetched 3×, incl. verbatim file-role section)
- https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/certificate/README.md (fetched 2×, incl. verbatim record format/dimension table)
- https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/certificate/d_regular/splits.txt (verbatim first 10 lines)
- https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/certificate/d_regular/lemmas/lemma_0.jl
- https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/certificate/d_regular/lemmas/lemma_1.jl (verbatim)
- https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/certificate/d_regular/formulas/F0 (verbatim head)
- https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/certificate/d_regular/verify_certificate.jl (fetched 2×, verbatim excerpts)
- https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/certificate/d_regular/verify_partition.py (verbatim excerpts)
- https://raw.githubusercontent.com/keyisi2006/Steiner-Ratio/main/certificate/d_regular/plot_f_ge_d.cpp (verbatim excerpts)
- https://huggingface.co/datasets/keyisi/steiner-ratio (pre-generated certificate dataset, 49.3 GB)

Tao scoreboard:
- https://raw.githubusercontent.com/teorth/optimizationproblems/main/README.md (scoreboard row 43)
- https://raw.githubusercontent.com/teorth/optimizationproblems/main/constants/43a.md (problem writeup)
- https://api.github.com/repos/teorth/optimizationproblems/git/trees/HEAD?recursive=1 (layout)
- https://api.github.com/repos/teorth/optimizationproblems/commits?path=constants/43a.md (entry history)
- https://api.github.com/search/issues?q=repo:teorth/optimizationproblems+steiner (PRs #28, #112, #120)

Mathematical background:
- https://arxiv.org/abs/1402.6079 and https://arxiv.org/pdf/1402.6079 — Ivanov & Tuzhilin, "Du–Hwang
  Characteristic Area: Catch-22" (2014); full text extracted locally from the downloaded PDF. Bibliographic
  chain within it: Du–Hwang 1990 proof; Ivanov–Tuzhilin, Algorithmica 62(1–2):630–632 (2012);
  Innami–Kim–Mashiko–Shiohama, Algorithmica 57(4) (2010).
- https://link.springer.com/article/10.1007/s00453-011-9508-3 — attempted; redirected to Springer auth
  wall, NOT fetched (2012 note cited via 1402.6079's references instead).

Status searches (2026-08-11):
- WebSearch: "Gilbert-Pollak Steiner ratio 0.8559 lower bound LLM"
- WebSearch: ""Steiner ratio" OR "Gilbert-Pollak" 2026 replication OR critique OR verification arXiv"
- WebSearch: ""2601.22365" cited OR discussion OR follow-up" (no relevant hits)
- https://api.semanticscholar.org/graph/v1/paper/arXiv:2601.22365 — attempted 2×, HTTP 429; citation
  count UNVERIFIED.
