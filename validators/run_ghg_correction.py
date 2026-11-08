"""The GHG correction of 2026-11-07, as a check rather than as a claim.

WHAT WAS WRONG
----------------
`run_satellite_multiplier_form.py` establishes that three of four deposited
marine tables publish, as their greenhouse-gas multiplier, each sector's OWN
emission factor spread over its whole supply chain instead of the embodied
total. This file checks the corrected copies, and the defect turned out to be
one formula per workbook:

    EEMIOT18  'LxGHG vm'              MMULT(L, diag(e))        wrong
    OMIOT18   'GHG V.Mtr. x Leontief ' MMULT(L, diag(e))       wrong
    WMIOT19   'L x GHG mtrx.'          MMULT(L, diag(e))       wrong
    NIMIOT17  'GHGxL'                  MMULT(diag(e), L)       right

Same author, four workbooks, one with the operands the right way round. The
correct form is `diag(e) L` -- `UNH_20` 20.94 eq. (46), p. 630, `Z = B(I-A)^-1`,
card `M-067`. The Handbook states it for the WAGE coefficient vector; applying
the same algebra to an emissions row is a labelled project convention.

So the correction is the swap and nothing else. Every figure below it -- the
helper sheet's column totals, the published TOTAL row, the INDIRECT row --
follows from the existing formulas.

WHY THE FILES WERE WRITTEN BY XML SURGERY
-------------------------------------------
`OMIOT18` carries fourteen parts of cell comments and threaded comments, which
an openpyxl round-trip silently drops. Each corrected file therefore differs
from its original in exactly three parts -- `xl/workbook.xml` for
`fullCalcOnLoad`, the MULTIPLIERS sheet, and the helper sheet -- and is byte
identical everywhere else. That is checked here.

WALES CARRIES A SECOND DEFECT AND THE CORRECTION MAKES IT WORSE, NOT BETTER
----------------------------------------------------------------------------
`WMIOT19`'s gas sheet states the factor twice: a vector in column A and a
diagonal in `C2:CD81`. They agree in 79 of 80. For `Other personal service
activities` column A says 0.021222 and the diagonal says 5.075135, 239x more.

Under the OLD formula `L diag(e)` that cell reached only its own column. Under
the correct `diag(e) L` row 79 enters every column, so the stray cell moves all
80 multipliers -- five of them by more than 1 %, one by 23,000 %. Three
statements in the workbook say 0.021222 (column A, the MULTIPLIERS DIRECT row,
and the `CO2e factor` row) and one cell says 5.075135.

Two corrected files were therefore delivered and **the owner chooses**. This
check requires the gas sheet's diagonal to equal its own column A, so the
`_diagonal-as-deposited` variant FAILS it by design: that is the measurement,
not a bug in this file.

WHERE THE FILES ARE, AND WHY THIS CAN EXIT 3
----------------------------------------------
Outside this repository and staying outside: they are corrected copies of
tables deposited under doi 10.15124/a76f2b2c-3dd6-435c-abae-a82b5413cafa, not
open data. The directory comes from `MSPACE_CORRECTED` when set. On any machine
that does not hold them this exits 3 and says it checked nothing -- never a
pass. The originals are not touched by anything here.

Run:
    python3 validators/run_ghg_correction.py
    MSPACE_CORRECTED=/path python3 validators/run_ghg_correction.py
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
import zipfile
from pathlib import Path

import numpy as np

try:
    import openpyxl
except ImportError:
    openpyxl = None                      # type: ignore[assignment]

NOTHING_CHECKED = 3
TOL = 1e-9

SRC_DIR = Path(os.environ.get("MSPACE_TABLES", str(Path(
    "/Users/albertrock/Library/CloudStorage/OneDrive-UniversityofYork/"
    "FINISHED IOT MSPACE (_)/SIMON V1 PROJECT IOTS/BALANCED/FV_CHECKED"))))
OUT_DIR = Path(os.environ.get(
    "MSPACE_CORRECTED",
    str(SRC_DIR.parent / "FV_CHECKED_GHG_CORRECTED_2026-11-07")))

# original, corrected, n, helper sheet, gas sheet, diagonal top-left (1-based),
# L top-left, MULTIPLIERS rows total/direct/indirect, first data column
CASES = [
    dict(src="EEMIOT18.xlsx", out="EEMIOT18.xlsx", n=120,
         helper="LxGHG vm", gas="GHG vector-matrix", diag=(3, 11),
         l0=(2, 2), tot=4, dir=11, ind=18, c0=2,
         want="MMULT('GHG vector-matrix'!K3:DZ122, L!B2:DQ121)"),
    dict(src="OMIOT18.xlsx", out="OMIOT18.xlsx", n=65,
         helper="GHG V.Mtr. x Leontief ", gas="GHG vector mtrx.", diag=(3, 12),
         l0=(2, 2), tot=5, dir=13, ind=20, c0=2,
         want="MMULT('GHG vector mtrx.'!L3:BX67,L!B2:BN66)"),
    dict(src="WMIOT19.xlsx", out="WMIOT19_stray-cell-also-fixed.xlsx", n=80,
         helper="L x GHG mtrx.", gas="GHG vector-mtx.", diag=(2, 3),
         l0=(2, 2), tot=5, dir=12, ind=19, c0=2,
         want="MMULT('GHG vector-mtx.'!C2:CD81,L!B2:CC81)",
         # A FOURTH PART, and it is the point of this variant: the stray
         # diagonal cell was corrected in the gas sheet itself, so that the
         # formula and the cache agree and `fullCalcOnLoad` cannot undo the fix.
         parts=4),
]

FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def parts_changed(src: Path, out: Path) -> tuple[list[str], list[str], bool]:
    with zipfile.ZipFile(src) as a, zipfile.ZipFile(out) as b:
        na = [i.filename for i in a.infolist()]
        nb = [i.filename for i in b.infolist()]
        if na != nb:
            return nb, [], False
        changed = [f for f in nb if a.read(f) != b.read(f)]
        comments = [f for f in nb if "omment" in f]
        kept = all(a.read(f) == b.read(f) for f in comments)
        return changed, comments, kept


def formulas(out: Path) -> list[str]:
    with zipfile.ZipFile(out) as z:
        blob = "".join(z.read(i.filename).decode("utf8", "ignore")
                       for i in z.infolist() if "worksheets/" in i.filename)
    return re.findall(r'<f t="array"[^>]*>(MMULT\([^<]*)</f>', blob)


def one(case: dict) -> None:
    src, out, n = SRC_DIR / case["src"], OUT_DIR / case["out"], case["n"]
    digest = hashlib.sha256(out.read_bytes()).hexdigest()[:16]
    print(f"  {case['out']}  ({n} industries, sha256 {digest}…)")

    want_parts = case.get("parts", 3)
    changed, comments, kept = parts_changed(src, out)
    check(f"{case['out']}: differs from the original in exactly "
          f"{want_parts} parts", len(changed) == want_parts,
          f"changed: {', '.join(changed) if changed else 'file list differs'}")
    if comments:
        check(f"{case['out']}: its {len(comments)} comment part(s) are "
              f"byte-identical to the original", kept)

    fs = formulas(out)
    check(f"{case['out']}: the helper sheet applies the factor across ROWS",
          case["want"] in fs,
          f"wanted {case['want']}; found {len(fs)} array formula(s)")
    wrong = [f for f in fs if re.match(r"MMULT\(\s*L!", f) and "GHG" in f]
    check(f"{case['out']}: and no MMULT still puts L first against a gas sheet",
          not wrong, f"offending: {wrong}" if wrong else "none")

    wb = openpyxl.load_workbook(out, data_only=True)
    try:
        r0, c0 = case["l0"]
        L = np.array([[float(wb["L"].cell(r0 + i, c0 + j).value)
                       for j in range(n)] for i in range(n)])
        mw = wb["MULTIPLIERS"]
        e = np.array([float(mw.cell(case["dir"], case["c0"] + j).value)
                      for j in range(n)])
        pub = np.array([float(mw.cell(case["tot"], case["c0"] + j).value)
                        for j in range(n)])
        iv = np.array([float(mw.cell(case["ind"], case["c0"] + j).value)
                       for j in range(n)])

        # THE FACTOR THE WORKBOOK STATES TWICE MUST BE ONE FACTOR.
        #
        # The diagonal the formula multiplies against, and the DIRECT row the
        # table publishes as its emission factor, are the same quantity written
        # in two places. Where they disagree, one of the two is wrong and no
        # arithmetic can say which.
        #
        # An earlier draft compared the diagonal against column A of the gas
        # sheet instead, which is where WMIOT19 keeps its vector. That is not
        # general: EEMIOT18's column A is not the factor and OMIOT18's holds
        # text. The DIRECT row is in every one of these workbooks, and it
        # catches the Wales cell just as well.
        gw = wb[case["gas"]]
        dr, dc = case["diag"]
        diag = np.array([float(gw.cell(dr + i, dc + i).value or 0.0)
                         for i in range(n)])
        off = np.flatnonzero(~np.isclose(diag, e, rtol=TOL, atol=1e-15))
        if len(off):
            den = np.where(e[off] == 0, np.nan, e[off])
            worst = float(np.nanmax(np.abs(diag[off] / den)))
            detail = (f"{len(off)} of {n} column(s) disagree, the worst by "
                      f"{worst:,.0f}x — and under the corrected formula a stray "
                      f"diagonal cell reaches EVERY column, not just its own")
        else:
            detail = f"one factor, stated twice and agreeing in all {n}"
        check(f"{case['out']}: the gas diagonal it multiplies against equals "
              f"the DIRECT row it publishes", len(off) == 0, detail)

        emb, own = e @ L, e * L.sum(axis=0)
        deg = np.isclose(emb, own, rtol=TOL, atol=1e-15)
        live = ~deg
        hit_e = int(np.isclose(pub, emb, rtol=TOL, atol=1e-15)[live].sum())
        hit_o = int(np.isclose(pub, own, rtol=TOL, atol=1e-15)[live].sum())
        check(f"{case['out']}: its cached GHG total is the embodied total e'L",
              hit_e == int(live.sum()),
              f"embodied {hit_e}/{int(live.sum())}, own-factor "
              f"{hit_o}/{int(live.sum())} (was own-factor before the fix), "
              f"{int(deg.sum())} degenerate")
        check(f"{case['out']}: and its indirect row is still total minus direct",
              bool(np.isclose(iv, pub - e, rtol=TOL, atol=1e-12).all()))
    finally:
        wb.close()


def main() -> int:
    print(__doc__.strip().split("Run:")[0].rstrip())
    print("\n" + "=" * 78 + "\n")
    if openpyxl is None:
        print("    -- openpyxl is not installed, so no workbook can be opened.")
        print("\n" + "=" * 78)
        print("Nothing was checked: this run could not open a file.")
        return NOTHING_CHECKED
    missing = [c["out"] for c in CASES if not (OUT_DIR / c["out"]).exists()]
    missing += [c["src"] for c in CASES if not (SRC_DIR / c["src"]).exists()]
    if missing:
        print(f"    -- {len(missing)} file(s) are not on this machine:")
        print(f"       {', '.join(missing)}")
        print(f"       corrected: {OUT_DIR}")
        print(f"       originals: {SRC_DIR}")
        print("       They are not open data and stay outside this repository.")
        print("\n" + "=" * 78)
        print("Nothing was checked: the files this validator measures are not here.")
        return NOTHING_CHECKED

    print(f"    corrected: {OUT_DIR}")
    print(f"    originals: {SRC_DIR}\n")
    for case in CASES:
        one(case)
        print()

    print(f"  coverage: {len(CASES)} corrected workbook(s), "
          f"{sum(c['n'] - 1 for c in CASES)} discriminating columns in all; "
          f"NIMIOT17 needed no correction and is checked by "
          f"run_satellite_multiplier_form.py")
    print("\n" + "=" * 78)
    if FAIL:
        print(f"{len(FAIL)} check(s) FAILED: {', '.join(FAIL)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
