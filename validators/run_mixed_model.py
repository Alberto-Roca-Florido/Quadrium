"""
The mixed exogenous/endogenous model, against its source and against Leontief.

`src/quadrium/mixed.py` implements card `M-073` from `CORE_085` (Steinback 2004,
The Review of Regional Studies 34(1): 57-71). This holds it to three things.

1. THE SOURCE'S OWN NUMBERS. The appendix (pp. 68-70) works a 3 x 3 example
   taken from Miller and Blair (1985, p. 328): sector 3's output is fixed at
   +150,000 and the other two are solved for, once by the output-based route of
   eq. (4) -- printed X1 = 65,346 and X2 = 42,178 (A2) -- and once by the mixed
   model of eqs. (2)-(3) with M^-1 printed to three decimals -- X1 = 65,340 and
   X2 = 42,174 (A5), the gap being, in the paper's words, rounding. Both are
   reproduced: the first from the engine's exact solution, the second by
   applying the PRINTED three-decimal inverse to the printed right-hand side,
   after checking that the engine's inverse rounds to exactly those entries.

2. THE TWO ROUTES AGREE. The paper proves eq. (4) and eqs. (2)-(3) give the same
   outputs (pp. 64-66). Held on the UK 2023 table for several exogenous sets,
   including a set of several sectors at once (footnote 6, p. 64: they must be
   estimated simultaneously).

3. THE TWO ENDS. With no exogenous sector the model must be Leontief; with all
   of them it must be the accounting identity f = (I - A) x. And the residual
   final demand of an exogenous sector must satisfy its own row of the system.

Run:
    python3 validators/run_mixed_model.py
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

FIXTURE = ROOT / "UK_IOAT_2023_domestic_ixi.xlsx"
FAIL = []
NOTHING_CHECKED = 3


def check(label, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {label}")
    if detail:
        print(f"         {detail}")
    if not ok:
        FAIL.append(label)


def main():
    from quadrium.mixed import (MixedModelError, mixed_model,
                                mixed_model_from_table, output_based_inverse)

    print(__doc__.strip().split("Run:")[0].rstrip())
    print("\n" + "=" * 78)

    # ---- 1. CORE_085 appendix, eqs. (A1)-(A5) --------------------------------
    print("\n1. CORE_085's appendix example\n")
    A = np.array([[0.15, 0.25, 0.30],
                  [0.20, 0.05, 0.18],
                  [0.20, 0.20, 0.10]])          # (A1), p. 68
    shock = 150_000.0                            # p. 69
    r = mixed_model(A, [2], delta_x={2: shock})
    x1, x2 = r.x[0], r.x[1]
    check("output-based solution (A2): X1 prints as 65,346 and X2 as 42,178",
          int(x1) == 65_346 and int(x2) == 42_178,
          f"engine {x1:,.2f} and {x2:,.2f}; the paper prints the integer part")
    Lt = output_based_inverse(A, [2])
    printed_Lt = np.array([[1.254, 0.330, 0.436],
                           [0.264, 1.122, 0.281],
                           [0.0, 0.0, 1.0]])     # p. 69
    check("the modified inverse of eq. (4) rounds to every printed entry",
          np.array_equal(np.round(Lt, 3), printed_Lt),
          f"engine {np.round(Lt, 3).tolist()}")
    check("eq. (4) and the mixed model give the same outputs, exactly",
          np.allclose(Lt @ np.array([0, 0, shock]), r.x, rtol=0, atol=1e-8))
    Minv_printed = np.array([[1.254, 0.330], [0.264, 1.122]])   # p. 69
    Minv_engine = r.multipliers[:2, :2]
    check("M^-1's endogenous block rounds to the printed entries",
          np.array_equal(np.round(Minv_engine, 3), Minv_printed),
          f"engine {np.round(Minv_engine, 3).tolist()}")
    rhs = np.array([0.30, 0.18]) * shock         # (A4): 45,000 and 27,000
    a5 = Minv_printed @ rhs
    check("the printed inverse reproduces (A5): X1 = 65,340 and X2 = 42,174",
          np.allclose(a5, [65_340, 42_174], atol=1e-6),
          f"{a5[0]:,.3f} and {a5[1]:,.3f}; the exact solution is "
          f"{x1:,.2f} and {x2:,.2f}, the gap the paper calls rounding")
    resid = (1 - A[2, 2]) * shock - A[2, 0] * x1 - A[2, 1] * x2
    check("the exogenous sector's final demand satisfies its own row",
          abs(r.f[2] - resid) < 1e-8,
          f"Delta f_3 = {r.f[2]:,.2f}")

    # ---- 2 and 3. on a real table --------------------------------------------
    if not FIXTURE.exists():
        print(f"\nNothing was checked: {FIXTURE.name} is absent.")
        return NOTHING_CHECKED if not FAIL else 1
    from quadrium.io_loader import load_uk_analytical_iot
    t = load_uk_analytical_iot(FIXTURE)
    codes = list(t.sector_codes)
    n = len(codes)
    X = np.asarray(t.X, float)
    A = np.where(X > 0, t.Z / np.where(X > 0, X, 1.0), 0.0)
    print(f"\n2. The two routes on the UK {t.year} table ({n} sectors)\n")

    rng = np.random.default_rng(20261010)
    worst = 0.0
    sets = [[codes[3]], [codes[0], codes[1], codes[2]],
            list(rng.choice(codes, 12, replace=False))]
    for ex in sets:
        dx = {c: float(rng.uniform(-50, 50)) for c in ex}
        res = mixed_model(A, ex, delta_x=dx, codes=codes)
        v = np.zeros(n)
        for c, val in dx.items():
            v[codes.index(c)] = val
        alt = output_based_inverse(A, ex, codes=codes) @ v
        rel = np.max(np.abs(res.x - alt)) / max(1.0, np.max(np.abs(alt)))
        worst = max(worst, rel)
    check("mixed model = eq. (4) for 1, 3 and 12 exogenous sectors",
          worst < 1e-9, f"largest relative difference {worst:.2e}")

    print("\n3. The two ends of the model\n")
    f = rng.uniform(0, 100, n)
    leo = np.linalg.solve(np.eye(n) - A, f)
    r0 = mixed_model(A, [], delta_f=f)
    check("no exogenous sector: the mixed model IS Leontief",
          np.allclose(r0.x, leo, rtol=1e-10, atol=1e-8))
    xall = rng.uniform(0, 100, n)
    rall = mixed_model(A, list(range(n)), delta_x=xall)
    check("every sector exogenous: f = (I - A) x",
          np.allclose(rall.f, (np.eye(n) - A) @ xall, rtol=1e-10, atol=1e-8))

    ex = [codes[0]]
    rt = mixed_model_from_table(t, ex, delta_x={codes[0]: -10.0})
    check("from a table: the given output is returned as given",
          rt.x[0] == -10.0 and codes[0] in rt.forward_share,
          f"{codes[0]}: share of output sold to other sectors "
          f"{rt.forward_share[codes[0]]:.3f} (the forward linkage left out)")

    print("\n4. Refusals\n")

    def refused(label, fn, words):
        try:
            fn()
        except MixedModelError as e:
            check(f"refuses {label}", words in str(e), str(e)[:90])
        else:
            check(f"refuses {label}", False, "it solved")

    refused("an output change for an endogenous sector",
            lambda: mixed_model(A, [0], delta_x={1: 5.0}),
            "endogenous")
    refused("a final-demand change for an exogenous sector",
            lambda: mixed_model(A, [0], delta_f={0: 5.0}),
            "exogenous")
    refused("a code the table does not have",
            lambda: mixed_model(A, ["NOT_A_CODE"], codes=codes),
            "not a code")
    refused("a singular endogenous block",
            lambda: mixed_model(np.array([[1.0, 0.0], [0.0, 0.5]]), [1]),
            "singular")

    print("\n" + "=" * 78)
    if FAIL:
        print(f"{len(FAIL)} check(s) FAILED")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
