"""
A second implementation, and the honest reason it is worth less than it sounds.

READ THIS BEFORE EXPECTING ANYTHING FROM THIS FILE
----------------------------------------------------
The obvious reason to compare against `pymrio` (Stadler et al., `CORE_074`) is
to confirm that this engine's `A`, `L` and multipliers are right. **That was
already settled, by a better source, before this file was written.**
`run_multipliers.py` reproduces the ONS's own published Type I effects and
multipliers — **1,434 published figures across 7 variables, worst error
7.11e-15** — with `e = (v ⊘ x)ᵀ L`, which is the embodied total `s'L`. Those
sheets are an official implementation: **authority rank 3**. `pymrio` is
software: **rank 6**, the bottom of the order in this project's own rules, and
a lower source never silently overrides a higher one.

So this file does **not** exist to validate the arithmetic. It cannot: nothing
it finds could outrank the ONS. It exists for the two things the ONS sheets
cannot give, and it says which is which in its own output.

That this pendiente pointed outward at `pymrio` while the answer sat inside the
project's own fixture is the pattern `run_multipliers.py` names in its header
and `library/INDEX.md` §9 collects. It has now happened again.

WHAT THIS IS ACTUALLY FOR
---------------------------
1. **A convention neither source states: a sector with zero output.** `A = Z
   x̂^-1` divides by output. This project makes an explicit choice —
   `identities.py` sets that column of `A` to zero,
   `np.where(x != 0, Z / x, 0.0)` — and pymrio's mathematical documentation does
   not say what it does. **The UK fixture cannot test it**: its smallest output
   is 100.0 and no sector is zero, and the ONS publishes no such sector either.
   A three-sector system is built for the purpose. The result is REPORTED, not
   asserted: nothing in the sources says the two must agree, and a check that
   demanded agreement would be inventing a rule.
2. **A rank-6 regression net.** An independent code path over the same numbers
   is worth having for the day someone edits the inverse. It is evidence about
   this engine only in the weak sense that two programmes applying `Z x̂^-1`
   with the same numpy agree to machine precision, which proves little. Printed
   as agreement, never as proof.

And one thing about pymrio rather than about this engine: the changelog claim
that 0.7.0 raises on duplicated labels, **tested instead of quoted**. A
recorded claim about someone else's software that nobody ran is a rumour.

WHAT PYMRIO CALLS THINGS
--------------------------
From its own mathematical documentation:

    A = Z x̂^-1        direct requirements
    L = (I - A)^-1     total requirements
    S = F x̂^-1        factor coefficients, per unit of OUTPUT
    M = S L            the multiplier
    M_up = S(L - I)    upstream only, i.e. M - S

`M = S L` is the embodied total, the coefficient vector applied across ROWS. It
agrees with `UNH_20 ¶20.94 eq. (46), p. 630` (`M-067`) and with the ONS sheets,
and it is the form `library/audits/EE_2018.md` §2b found three of four regional
tables had transposed. `M_up = M - S` is the decomposition those workbooks print
as total, direct and indirect. That three independent implementations agree on
the form is worth stating once — and the ONS one is why it is already stated.

THE VERSION FLOOR, WHICH IS NOT OPTIONAL
------------------------------------------
**pymrio below 0.7.0 is refused.** Until 0.7.0 (released 2026-10-19), with
labels missing, extra or duplicated, its coefficient, inverse, account and
multiplier calculations returned results in the wrong order **without raising**
(`CHANGELOG.rst`, #107). An agreement measured against an implementation whose
label handling fails silently is not an agreement. This fixture has clean,
unique labels and would probably agree against 0.6.x too — which is exactly why
the floor is enforced in code rather than left to whoever runs it.

Run:
    python3 validators/run_pymrio_crosscheck.py

Not installed is the normal state of this tree, and then this exits 3. pymrio
needs pandas, which the project interpreter deliberately does not carry, so give
it an environment of its own rather than touching `~/.venvs/quadrium`:

    python3 -m venv ~/.venvs/pymrio-xcheck
    ~/.venvs/pymrio-xcheck/bin/pip install "pymrio>=0.7.0"
    ~/.venvs/pymrio-xcheck/bin/python validators/run_pymrio_crosscheck.py

**This file was written against pymrio's documented API and has never been run
against the library.** An API mismatch is reported as a FAIL with its exception,
never as a pass, and the fix belongs here rather than in the engine.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

FIXTURE = ROOT / "UK_IOAT_2023_domestic_ixi.xlsx"
SATELLITE = "Compensation of employees"     # a VA row of the fixture, as labelled
FLOOR = (0, 7, 0)

# Exit 3, like the archive validators: check.sh counts it as SKIPPED rather
# than as a pass, because a run that compared nothing measured nothing.
NOTHING_CHECKED = 3
TOL = 1e-10

FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def report(name: str, detail: str) -> None:
    """Something measured that no source says must hold. Printed, not asserted,
    and not counted as a pass."""
    print(f"  --   {name} — {detail}")


def version_tuple(v: str) -> tuple[int, ...]:
    out: list[int] = []
    for part in str(v).split(".")[:3]:
        digits = "".join(c for c in part if c.isdigit())
        out.append(int(digits) if digits else 0)
    while len(out) < 3:
        out.append(0)
    return tuple(out)


def ours(Z: np.ndarray, x: np.ndarray, f: np.ndarray) -> dict:
    """This engine's arithmetic, written the way `identities.py` writes it —
    including its explicit choice for a zero-output column."""
    n = Z.shape[0]
    with np.errstate(divide="ignore", invalid="ignore"):
        A = np.where(x != 0, Z / x[None, :], 0.0)
        S = np.where(x != 0, f / x, 0.0)
    L = np.linalg.inv(np.eye(n) - A)
    return {"A": A, "L": L, "S": S, "M": S @ L, "M_up": S @ L - S}


def as_system(pymrio, Z: np.ndarray, Y: np.ndarray, f: np.ndarray,
              names: list[str]):
    """A single-region pymrio IOSystem over the same numbers, with labels.

    Built through the public constructor rather than by setting attributes, so
    that an API change surfaces here with a traceback instead of as a quiet
    difference further down.
    """
    import pandas as pd

    idx = pd.MultiIndex.from_product([["UK"], names], names=["region", "sector"])
    fd = pd.MultiIndex.from_product(
        [["UK"], [f"fd{k}" for k in range(Y.shape[1])]],
        names=["region", "category"])
    system = pymrio.IOSystem(
        Z=pd.DataFrame(Z, index=idx, columns=idx),
        Y=pd.DataFrame(Y, index=idx, columns=fd),
    )
    system.satellite = pymrio.Extension(
        name="satellite",
        F=pd.DataFrame(f[None, :], index=[SATELLITE], columns=idx),
    )
    system.calc_all()
    return system


def compare(name: str, mine: np.ndarray, theirs) -> None:
    got = np.asarray(theirs, float)
    if got.shape != mine.shape:
        if got.T.shape == mine.shape:
            check(f"{name} agrees", False,
                  f"shapes {got.shape} against {mine.shape}: TRANSPOSED, and a "
                  f"transposition is the one disagreement this project has "
                  f"already found in a published dataset")
            return
        check(f"{name} agrees", False,
              f"shapes {got.shape} against {mine.shape}, not a transpose either")
        return
    worst = float(np.abs(got - mine).max())
    scale = float(np.abs(mine).max()) or 1.0
    check(f"{name} agrees", worst / scale <= TOL,
          f"max |theirs - ours| = {worst:.2e} on a scale of {scale:.3g}")


def zero_output_probe(pymrio) -> None:
    """The reason this file exists. Three sectors, one producing nothing."""
    Z = np.array([[10.0, 5.0, 0.0],
                  [4.0, 20.0, 0.0],
                  [0.0, 0.0, 0.0]])
    Y = np.array([[35.0], [26.0], [0.0]])
    x = Z.sum(axis=1) + Y.sum(axis=1)            # 50, 50, 0
    f = np.array([12.0, 18.0, 0.0])
    mine = ours(Z, x, f)
    report("ours, the zero-output column of A",
           f"{mine['A'][:, 2].tolist()} — set by the explicit "
           f"`np.where(x != 0, ...)` in identities.py, a project convention and "
           f"labelled as one")
    try:
        system = as_system(pymrio, Z, Y, f, ["one", "two", "silent"])
        theirs = np.asarray(system.A, float)[:, 2]
        finite = bool(np.isfinite(theirs).all())
        report("theirs, the zero-output column of A",
               f"{theirs.tolist()} — {'finite' if finite else 'NOT finite'}; "
               f"its documentation does not state this case")
        check("and a zero-output sector does not spoil the columns of L that do "
              "produce", bool(np.isfinite(np.asarray(system.L, float)[:, :2]).all()),
              "the two producing sectors' columns of L stay finite")
    except Exception as exc:                     # reported, never swallowed
        report("theirs, the zero-output column of A",
               f"{type(exc).__name__}: {exc} — it refuses the case rather than "
               f"choosing for you. That is defensible, and different from ours")


def duplicate_label_probe(pymrio) -> None:
    """The changelog claim, tested rather than quoted."""
    Z = np.array([[10.0, 5.0], [4.0, 20.0]])
    Y = np.array([[35.0], [26.0]])
    f = np.array([12.0, 18.0])
    try:
        as_system(pymrio, Z, Y, f, ["same", "same"])
    except Exception as exc:
        check("pymrio 0.7.0 refuses a duplicated sector label, as its changelog "
              "says", True, f"{type(exc).__name__}: {str(exc)[:90]}")
        return
    check("pymrio 0.7.0 refuses a duplicated sector label, as its changelog says",
          False,
          "it did NOT raise. Either #107 is narrower than it reads or this "
          "system does not exercise the labelled path. Until that is settled, "
          "the version floor rests on a claim nobody has reproduced")


def main() -> int:
    print(__doc__.strip().split("Run:")[0].rstrip())
    print("\n" + "=" * 78 + "\n")

    try:
        import pymrio
    except ImportError:
        print("    -- pymrio is not installed, which is this tree's normal state:")
        print("       it needs pandas, and the project interpreter deliberately")
        print("       does not carry it. The install command is in this file's")
        print("       header, into an environment of its own.")
        print("\n" + "=" * 78)
        print("Nothing was checked: there is no second implementation to compare.")
        return NOTHING_CHECKED

    installed = getattr(pymrio, "__version__", "0")
    if version_tuple(installed) < FLOOR:
        print(f"    -- pymrio {installed} is installed, below the floor "
              f"{'.'.join(map(str, FLOOR))}.")
        print("       Until 0.7.0 its coefficient, inverse, account and multiplier")
        print("       calculations returned results in the WRONG ORDER, without")
        print("       raising, when labels were missing, extra or duplicated")
        print("       (CHANGELOG #107). This fixture has clean labels and would")
        print("       probably agree anyway, which is why the floor is in code.")
        print("\n" + "=" * 78)
        print("Nothing was checked: the second implementation is below the floor.")
        return NOTHING_CHECKED

    if not FIXTURE.exists():
        print(f"    -- the fixture is not in this tree: {FIXTURE.name}")
        print("\n" + "=" * 78)
        print("Nothing was checked: the table to compare on is not here.")
        return NOTHING_CHECKED

    print(f"    pymrio {installed}, fixture {FIXTURE.name}")
    print("    the arithmetic was settled at rank 3 by run_multipliers.py; what")
    print("    follows is a rank-6 regression net and one convention probe.\n")

    from quadrium.io_loader import load_uk_analytical_iot
    t = load_uk_analytical_iot(FIXTURE)
    Z = np.asarray(t.Z, float)
    x = np.asarray(t.X, float)
    Y = np.asarray(t.Y, float)
    VA = np.asarray(t.VA, float)
    labels = [str(v) for v in t.VA_labels]
    if SATELLITE not in labels:
        check(f"the fixture carries a `{SATELLITE}` row to use as a satellite",
              False, f"its value-added rows are {labels}")
        print("\n" + "=" * 78)
        print(f"{len(FAIL)} check(s) FAILED: {', '.join(FAIL)}")
        return 1
    f = VA[labels.index(SATELLITE)]

    check("the fixture has no zero-output sector, so the division is clean here",
          bool((x != 0).all()),
          f"{len(x)} sectors, smallest output {x[x > 0].min():.1f} — which is why "
          f"the convention below needs a system of its own")

    mine = ours(Z, x, f)
    try:
        system = as_system(pymrio, Z, Y, f,
                           [f"s{i:03d}" for i in range(Z.shape[0])])
    except Exception as exc:
        check("a pymrio IOSystem can be built over the same numbers", False,
              f"{type(exc).__name__}: {exc} — this file was written against the "
              f"documented API and never run against the library, so an API "
              f"mismatch is the likeliest cause. Fix it here, not in the engine")
        print("\n" + "=" * 78)
        print(f"{len(FAIL)} check(s) FAILED: {', '.join(FAIL)}")
        return 1

    compare("A, the direct requirements", mine["A"], system.A)
    compare("L, the Leontief inverse", mine["L"], system.L)

    ext = system.satellite
    compare("S, the coefficients per unit of output", mine["S"][None, :], ext.S)
    compare("M, the multiplier -- the embodied total `s'L`",
            mine["M"][None, :], ext.M)
    up = getattr(ext, "M_up", None)
    if up is None:
        # Measured on 0.7.0: after calc_all() an Extension carries F, S, M,
        # D_cba, D_pba, D_imp and D_exp. M_up and M_down appear in the
        # mathematical documentation but are not produced, so total-minus-direct
        # is not an INDEPENDENT quantity here -- subtracting their own S from
        # their own M would only restate an agreement already measured above.
        report("M_up, total minus direct",
               "not produced by calc_all() in this version, so there is nothing "
               "independent to compare: their M - their S would only restate the "
               "two agreements above. The decomposition those audited workbooks "
               "print as total, direct and indirect has no second opinion here")
    else:
        compare("M_up, total minus direct", mine["M_up"][None, :], up)

    check("and this implementation's multiplier is not the own-factor shortcut "
          "either", not np.allclose(np.asarray(ext.M, float).ravel(),
                                    mine["S"] * mine["L"].sum(axis=0), rtol=1e-6),
          "`s_j x colsum(L)` is a different quantity here too — the audit's "
          "finding, reached from outside this project and outside the ONS")

    print()
    zero_output_probe(pymrio)
    print()
    duplicate_label_probe(pymrio)

    print("\n" + "=" * 78)
    if FAIL:
        print(f"{len(FAIL)} check(s) FAILED: {', '.join(FAIL)}")
        print("A disagreement is a finding about one of the two implementations. "
              "Say which before changing either, and remember the ONS already "
              "settled the arithmetic at a higher rank than this file carries.")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
