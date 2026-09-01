"""Independent mpmath reference implementations (60 significant digits).

Used two ways: as the oracle the test suite compares Arb enclosures against,
and as the embedded mathematics of failing-region capsule replay scripts
(ADR-0005). Discipline: these modules must never import steiner_audit's
numerics — their value is being a separately written rendering of the same
mathematics.
"""
