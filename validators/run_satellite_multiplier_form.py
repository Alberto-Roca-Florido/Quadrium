"""
A satellite multiplier is `s'L`. Three of four tables disagree, and the audit's
central finding stops being prose.

WHAT THIS ANSWERS
-------------------
`library/audits/EE_2018.md` §2b reports that the greenhouse-gas multipliers
published in the East of England 2018 table are not the embodied total but each
sector's OWN emission factor multiplied by its output multiplier, and that the
same defect is in Orkney 2018 and Wales 2019 while Northern Ireland 2017 is
clean. Until this file existed those figures could only be read: the workbooks
are not in this tree, no script named them, and nothing the repository holds
reached `119 of 119`. A finding nobody can re-run is a claim, not a result.

THE TWO FORMS, AND WHY ONE IS THE RIGHT ONE
---------------------------------------------
For a satellite row `s` of coefficients per unit of output:

    embodied    m_j = Σ_i s_i L_ij      the factor applied across ROWS
    own-factor  m_j = s_j × Σ_i L_ij    the sector's own factor, spread over
                                        its whole supply chain

The embodied form is the one the sources give: **UNH_20 ¶20.94 eq. (46),
p. 630**, `Z = B(I − A)^-1`, with `B` a vector of input coefficients and `Z`
the direct and indirect requirements — card `M-067`. **The Handbook states it
for the wage coefficient vector.** Applying the same algebra to an emissions
row is a project convention, labelled here as one: the derivation is identical
and the coefficient vector is the only thing that changes, but no loaded source
writes it out for emissions.

The own-factor form is not a variant of the embodied total. It assumes every
supplier emits at the customer's rate, and it is a different quantity that
happens to carry the same units.

THE DEGENERATE COLUMN, WHICH IS WHY THE DENOMINATOR IS NOT n
--------------------------------------------------------------
In each of these tables exactly one industry buys nothing — households as
employers of domestic personnel. Its column of `L` is a unit vector, so
`Σ_i L_ij = 1` and **both formulas return the same number there**. That column
cannot tell them apart and is evidence for neither. The audit first said
`120 of 120`; the honest figure is `119 of 119` plus one degenerate. This file
prints both counts, because a clean score over a denominator that includes a
column which cannot disagree is the same mistake as a citation checker
reporting 100 % over 37 of 381.

WALES CARRIES A SECOND DEFECT AND IT SHOWS UP HERE
----------------------------------------------------
`WMIOT19` states two different emission factors for one industry: its gas sheet
holds a vector and, beside it, a diagonal matrix, and for `Other personal
service activities` they differ by a factor of 239. The published multiplier
uses the high one. So the own-factor form fits 78 of 79 against the vector and
79 of 79 against the diagonal, and **that gap is the second defect reached from
the other side** rather than a quirk of the scoring.

WHAT IS CHECKED, PER WORKBOOK
-------------------------------
1. The block read as `L` is the inverse of the block read as `A` — `(I-A)L = I`.
   Without it every figure below is about two rectangles that happen to be the
   right size.
2. How many columns discriminate, and how many are degenerate.
3. Which form the published greenhouse-gas row takes on the discriminating
   columns, against the recorded expectation.
4. That income and value added take the embodied form in the same sheet. That
   contrast is what makes the gas row a slip rather than a convention, and it
   is the reason this is reported as a defect at all.

**A failure here does not by itself mean this file is right and the workbook
wrong.** If a workbook is corrected, the expectation recorded below is what has
gone stale, and the output says which one moved. Read it before editing
anything.

WHERE THE WORKBOOKS ARE, AND WHY THIS CAN EXIT 3
--------------------------------------------------
Outside this repository, and they stay outside: they are unpublished working
copies of tables deposited under
doi 10.15124/a76f2b2c-3dd6-435c-abae-a82b5413cafa, not open data, and this
project does not redistribute them. The directory comes from `MSPACE_TABLES`
when set. **On any machine that does not hold them this exits 3 and says it
checked nothing** — never a pass. Nothing is written: the SHA-256 of each
workbook is printed rather than stored, so no file in this tree records a path
on one person's disk.

Run:
    python3 validators/run_satellite_multiplier_form.py
    MSPACE_TABLES=/path/to/tables python3 validators/run_satellite_multiplier_form.py
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import numpy as np

try:
    import openpyxl
except ImportError:                      # reported as a skip, never as a pass
    openpyxl = None                      # type: ignore[assignment]

DEFAULT_DIR = Path(
    "/Users/albertrock/Library/CloudStorage/OneDrive-UniversityofYork/"
    "FINISHED IOT MSPACE (_)/SIMON V1 PROJECT IOTS/BALANCED/FV_CHECKED"
)
TABLES = Path(os.environ.get("MSPACE_TABLES", str(DEFAULT_DIR)))

# Exit 3, like the archive validators: check.sh counts it as SKIPPED rather
# than as a pass, because a run that opened no file measured nothing.
NOTHING_CHECKED = 3
TOL = 1e-9        # relative, every column
IDENTITY_TOL = 1e-9

# What the audit records, as of 2026-10-18. `form` is the form the PUBLISHED
# greenhouse-gas row takes on the discriminating columns. `live` is how many
# columns discriminate; the rest of `n` are degenerate. `short_by` is Wales,
# whose published row uses a factor its DIRECT row does not state.
EXPECTED: dict[str, dict] = {
    "NIMIOT17.xlsx": {"n": 77,  "sheet_l": "Leontief", "live": 76,
                      "form": "embodied"},
    "OMIOT18.xlsx":  {"n": 65,  "sheet_l": "L",        "live": 64,
                      "form": "own-factor"},
    "WMIOT19.xlsx":  {"n": 80,  "sheet_l": "L",        "live": 79,
                      "form": "own-factor", "short_by": 1},
    "EEMIOT18.xlsx": {"n": 120, "sheet_l": "L",        "live": 119,
                      "form": "own-factor"},
}

FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def grid(ws) -> list[list]:
    return [list(row) for row in ws.iter_rows(values_only=True)]


def square(g: list[list], n: int) -> np.ndarray | None:
    """The n x n numeric block, found rather than assumed. These workbooks put
    their data at different offsets, and in one of them the first row is text
    that reads as data if you start at row 1."""
    for r0 in range(6):
        for c0 in range(6):
            try:
                M = np.array([[g[r0 + i][c0 + j] for j in range(n)]
                              for i in range(n)], dtype=float)
            except (TypeError, IndexError, ValueError):
                continue
            if np.isfinite(M).all():
                return M
    return None


def labelled(g: list[list], label: str, n: int) -> list[tuple[int, np.ndarray]]:
    """Every row whose leading text cell is `label`, by label and never by
    position: a MULTIPLIERS sheet repeats `GHG`, `Income` and `GVA` once for
    the total block, once for direct and once for indirect."""
    out: list[tuple[int, np.ndarray]] = []
    for i, row in enumerate(g):
        for j, cell in enumerate(row[:3]):
            if isinstance(cell, str) and cell.strip().lower() == label.lower():
                try:
                    v = np.array(row[j + 1:j + 1 + n], dtype=float)
                except (TypeError, ValueError):
                    break
                if len(v) == n and np.isfinite(v).all():
                    out.append((i + 1, v))
                break
    return out


def score(published: np.ndarray, s: np.ndarray, L: np.ndarray) -> dict:
    """Both forms, counted only where they can differ."""
    embodied = s @ L
    own = s * L.sum(axis=0)
    degenerate = np.isclose(embodied, own, rtol=TOL, atol=1e-15)
    live = ~degenerate

    def hit(cand: np.ndarray) -> int:
        return int(np.isclose(published, cand, rtol=TOL, atol=1e-15)[live].sum())

    def worst(cand: np.ndarray) -> float:
        return float(np.abs(published - cand)[live].max()) if live.any() else float("nan")

    return {"n": len(published), "degenerate": int(degenerate.sum()),
            "live": int(live.sum()), "embodied": hit(embodied), "own": hit(own),
            "res_embodied": worst(embodied), "res_own": worst(own)}


def verdict(sc: dict) -> str:
    if sc["live"] and sc["embodied"] == sc["live"]:
        return "embodied"
    if sc["live"] and sc["own"] == sc["live"]:
        return "own-factor"
    return "neither"


def best_factor(published: np.ndarray, candidates: list[tuple[int, np.ndarray]],
                L: np.ndarray) -> tuple[int, dict] | None:
    """The candidate coefficient vector under which the published row takes one
    of the two forms outright. Chosen by fit rather than by position, so a
    workbook that orders its blocks differently is still read correctly."""
    for row_no, s in candidates:
        sc = score(published, s, L)
        if verdict(sc) != "neither":
            return row_no, sc
    return None


def satellite_contrast(name: str, label: str, gm: list[list],
                       L: np.ndarray, n: int) -> None:
    """Income and value added, which in a sound workbook are the embodied total.

    A row this cannot score is SAID OUT LOUD rather than skipped. Wales is why:
    its income total is reproduced by neither form against the vector its own
    DIRECT row states, and a quiet `continue` would have swallowed a third
    finding in that workbook.
    """
    rows = labelled(gm, label, n)
    if len(rows) < 2:
        print(f"       -- {label.lower()}: not scored, the sheet has "
              f"{len(rows)} row(s) with this label")
        return
    other = best_factor(rows[0][1], rows[1:], L)
    if other is None:
        best = max((score(rows[0][1], v, L) for _, v in rows[1:]),
                   key=lambda sc: max(sc["embodied"], sc["own"]), default=None)
        near = (f"best fit {max(best['embodied'], best['own'])}/{best['live']}"
                if best else "no candidate row")
        print(f"       -- {label.lower()}: NOT SCORED. Neither form reproduces "
              f"the published total from any coefficient row in this sheet "
              f"({near}). That is a finding about this workbook, not about this "
              f"check — see the audit.")
        return
    _, sc = other
    check(f"{name}: and its {label.lower()} multiplier is the embodied total",
          verdict(sc) == "embodied",
          f"embodied {sc['embodied']}/{sc['live']} "
          f"(residual {sc['res_embodied']:.1e})")


def one_workbook(name: str, want: dict) -> tuple[str | None, int, int]:
    """Returns the form found, the discriminating columns and the total."""
    path, n = TABLES / name, want["n"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    wb = openpyxl.load_workbook(path, data_only=True)
    print(f"  {name}  ({n} industries, sha256 {digest}…)")
    try:
        L = square(grid(wb[want["sheet_l"]]), n)
        A = square(grid(wb["A"]), n)
        if L is None or A is None:
            check(f"{name}: the {n}x{n} blocks are where this expects them",
                  False, "block not found — the sheet layout has changed")
            return None, 0, 0

        # THE BLOCK READ AS L IS THE INVERSE OF THE BLOCK READ AS A.
        residual = float(np.abs((np.eye(n) - A) @ L - np.eye(n)).max())
        check(f"{name}: the block read as L is the inverse of the block read as A",
              residual < IDENTITY_TOL, f"max|(I-A)L - I| = {residual:.1e}")

        gm = grid(wb["MULTIPLIERS"])
        ghg = labelled(gm, "GHG", n)
        if len(ghg) < 2:
            check(f"{name}: the MULTIPLIERS sheet has a published and a direct "
                  f"GHG row", False, f"found {len(ghg)} row(s) labelled GHG")
            return None, 0, 0

        published_row, published = ghg[0]
        found = best_factor(published, ghg[1:], L)
        forced: str | None = None   # set only by the Wales branch below

        # WALES: THE FACTOR THAT FITS IS NOT THE ONE ITS DIRECT ROW STATES.
        # Its gas sheet holds a diagonal as well as a vector and the two
        # disagree for one industry, so nothing fits outright. The shortfall IS
        # the second defect, and is checked as such rather than excused.
        if found is None and "short_by" in want:
            near = [(r, score(published, s, L)) for r, s in ghg[1:]]
            near = [(r, sc) for r, sc in near
                    if sc["live"] and sc["own"] == sc["live"] - want["short_by"]]
            if near:
                row_no, sc = near[0]
                check(f"{name}: its published GHG row is the own-factor form on "
                      f"all but {want['short_by']} column(s) against the factor "
                      f"its DIRECT row states", True,
                      f"row {published_row} against row {row_no}: own-factor "
                      f"{sc['own']}/{sc['live']} — the shortfall is the industry "
                      f"whose factor this workbook states twice, 239x apart")
                check(f"{name}: and the discriminating denominator is the "
                      f"recorded one", sc["live"] == want["live"],
                      f"{sc['live']} of {sc['n']} discriminate, "
                      f"{sc['degenerate']} degenerate")
                # NOT a return. An earlier draft left here, and in doing so
                # skipped the income and value-added contrast for the one
                # workbook that has a third oddity in exactly those rows.
                found, forced = (row_no, sc), "own-factor"

        if found is None:
            check(f"{name}: the published GHG row takes one of the two forms",
                  False, "neither form fits any candidate factor vector — read "
                         "the audit before changing this file")
            return None, 0, 0

        row_no, sc = found
        if forced:
            for label in ("Income", "GVA"):
                satellite_contrast(name, label, gm, L, n)
            return forced, sc["live"], sc["n"]
        check(f"{name}: the published GHG multiplier is the {want['form']} form",
              verdict(sc) == want["form"],
              f"row {published_row} against the factor in row {row_no}: embodied "
              f"{sc['embodied']}/{sc['live']} (residual {sc['res_embodied']:.1e}), "
              f"own-factor {sc['own']}/{sc['live']} "
              f"(residual {sc['res_own']:.1e})")
        check(f"{name}: and the discriminating denominator is the recorded one",
              sc["live"] == want["live"],
              f"{sc['live']} of {sc['n']} discriminate, "
              f"{sc['degenerate']} degenerate")

        for label in ("Income", "GVA"):
            satellite_contrast(name, label, gm, L, n)
        return verdict(sc), sc["live"], sc["n"]
    finally:
        wb.close()


def main() -> int:
    print(__doc__.strip().split("Run:")[0].rstrip())
    print("\n" + "=" * 78 + "\n")

    # NO WORKBOOKS IS A SKIP, NOT A FAILURE.
    if openpyxl is None:
        print("    -- openpyxl is not installed, so no workbook can be opened.")
        print("\n" + "=" * 78)
        print("Nothing was checked: this run could not open a file.")
        return NOTHING_CHECKED
    missing = [name for name in EXPECTED if not (TABLES / name).exists()]
    if missing:
        print(f"    -- {len(missing)} of the {len(EXPECTED)} workbooks are not in")
        print(f"       {TABLES}")
        print(f"       missing: {', '.join(missing)}")
        print("       They are unpublished working copies and stay outside this")
        print("       repository. Point MSPACE_TABLES at the directory holding them.")
        print("\n" + "=" * 78)
        print("Nothing was checked: the tables this file measures are not here.")
        return NOTHING_CHECKED

    print(f"    read from {TABLES}\n")
    forms: dict[str, str] = {}
    live_total = col_total = 0
    for name, want in EXPECTED.items():
        form, live, cols = one_workbook(name, want)
        if form:
            forms[name] = form
        live_total += live
        col_total += cols
        print()

    # THE FINDING ITSELF, AS A COUNT.
    bad = sorted(k for k, v in forms.items() if v == "own-factor")
    clean = sorted(k for k, v in forms.items() if v == "embodied")
    check("three of the four tables carry the defect and one does not",
          len(bad) == 3 and len(clean) == 1,
          f"own-factor: {', '.join(bad) or 'none'}; "
          f"embodied: {', '.join(clean) or 'none'}")

    # COVERAGE, PRINTED RATHER THAN IMPLIED.
    print(f"\n  coverage: {live_total} of {col_total} columns discriminate — "
          f"the rest are the one per table whose column of L sums to 1")

    print("\n" + "=" * 78)
    if FAIL:
        print(f"{len(FAIL)} check(s) FAILED: {', '.join(FAIL)}")
        print("If a workbook has been corrected, this file is what is stale. "
              "Read the output above before editing either.")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
