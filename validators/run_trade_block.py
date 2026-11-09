"""The trade declaration is a measurement, not a claim.

WHAT THIS FILE IS FOR
-----------------------
`IOTable.trade` tells the engine which part of a loaded table is exports,
which is imports BY PRODUCT, and which is final use excluding exports. Before
it existed the only code that knew was two validators with the column numbers
written in by hand — `Y[:, 5] + Y[:, 6]`, `-Y[:, 7]`, `Y[:, 0:5]` — one set per
country.

Generalising that is only worth anything if the general version gives the SAME
numbers. So the central check here is not that the declaration exists but that
it reproduces those hand-written indices **to zero**. A generalisation nobody
compared is a claim; this makes it a measurement.

The second check is the partition. Every column of `Y` must be classified as
exports, domestic final use, imports, or named as neither. A loader that gains
a final-demand column and does not classify it would otherwise drop it out of
domestic final use in silence, and a commodity balance short by a whole column
of final demand still looks like a commodity balance.

WHAT IS CHECKED
-----------------
Per loader whose fixture is on disk: that the declaration partitions `Y` or is
absent; that an absent one REFUSES rather than returning zeros; and that the
vectors it hands back close the table's own row identity. Then the hand-built
refusals, and the round trip through this engine's own interchange format.

It prints a `coverage:` line, because passing over a loader that was not there
is exactly the vacuous success this project keeps finding in itself.

Exit 0 pass, 1 fail, 3 checked nothing.

Run:
    python3 validators/run_trade_block.py
"""
from __future__ import annotations

import sys
import tempfile
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

FAIL: list[str] = []
NOTHING_CHECKED = 3

ES = ROOT / "data" / "ine" / "cne_tio_21.xlsx"
CAT = ROOT / "data" / "idescat" / "mioc2021ts64.xlsx"
UK = ROOT / "UK_IOAT_2023_domestic_ixi.xlsx"
BE = ROOT / "data" / "eurostat" / "naio_10_cp1700_BE_2022.json"


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail
                                                    else ""))
    if not ok:
        FAIL.append(name)


def refuses(label: str, fn, fragment: str) -> None:
    try:
        fn()
    except Exception as exc:
        ok = fragment in str(exc)
        check(f"refuses {label}", ok,
              "" if ok else f"it refused, but for {str(exc)[:80]!r}")
    else:
        check(f"refuses {label}", False, "it accepted")


def partition_is_total(t, who: str) -> None:
    """Y is fully classified, and the classification adds back up to Y."""
    tb = t.trade
    k = t.Y.shape[1]
    named = set(tb.export_columns) | set(tb.domestic_columns) | \
        set(tb.other_columns)
    if tb.imports_column is not None:
        named |= {tb.imports_column}
    check(f"{who}: every column of Y is classified",
          named == set(range(k)),
          f"{len(named)} of {k} — exports {tb.export_columns}, domestic "
          f"{tb.domestic_columns}, imports {tb.imports_column}, other "
          f"{tb.other_columns}")
    # And numerically: the parts add back to the whole, so no column was
    # counted twice or dropped. The index sets above are what prove the
    # partition exactly; this reads the same invariant off the FIGURES, which
    # catches nothing the sets do not -- except that it would catch a change
    # to how the accessors sum. It cannot be asked for zero: adding the same
    # columns in three groups instead of one moves the last bits, ~1e-11 on
    # values of hundreds of thousands.
    parts = (t.Y[:, tb.export_columns].sum(axis=1)
             + t.Y[:, tb.domestic_columns].sum(axis=1)
             + (t.Y[:, tb.other_columns].sum(axis=1)
                if tb.other_columns else 0.0)
             + (t.Y[:, tb.imports_column]
                if tb.imports_column is not None else 0.0))
    worst = float(np.abs(parts - t.Y.sum(axis=1)).max())
    tol = 1e-9 * max(float(np.abs(t.Y).max()), 1.0)
    check(f"{who}: and the parts add back up to Y", worst <= tol,
          f"worst {worst:.2e} against {tol:.2e} — a column counted twice or "
          f"dropped shows up here as a whole column, not as a last bit")


def row_identity(t, who: str) -> None:
    """The declaration's own vectors close the table's row balance.

    WHICH IDENTITY, and it is `indirect_allocation` that decides -- not
    whether imports are known. A TOTAL-FLOW table distributes imports inside
    `Z`, so they come back out of the row balance as a negative final-demand
    column: `Sum z + D + E - M = X`. A DOMESTIC table's `Z` holds home-produced
    flows only and its imports belong to SUPPLY, outside this identity
    entirely: `Sum z + D + E = X`.

    IDESCAT is the case that makes the distinction concrete. It declares
    imports by product -- from its own supply identity -- and is NOT an
    indirect-allocation table, so subtracting them here is wrong by 12,300.
    Keying this on `has_imports` was this file's own first mistake.

    The tolerance is relative and includes whatever residue the LOADER already
    measured and declared as inherited: Eurostat's Belgian cube is 0.06 out as
    published, which the loader accepted against its own `_rounding_tol`, and
    this check has no business being stricter than the source.
    """
    tb = t.trade
    Z_S = t.Z.sum(axis=1)
    other = (t.Y[:, tb.other_columns].sum(axis=1) if tb.other_columns
             else np.zeros(t.n))
    E = t.Y[:, tb.export_columns].sum(axis=1)
    D = t.Y[:, tb.domestic_columns].sum(axis=1)
    if tb.indirect_allocation:
        M = (-t.Y[:, tb.imports_column] if tb.imports_column is not None
             else np.asarray(tb.imports_vector, float))
        lhs = Z_S + D + E - M + other
        form = "Sum z + D + E - M"
    else:
        lhs = Z_S + D + E + other
        form = "Sum z + D + E"
    worst = float(np.abs(lhs - t.X).max())
    tol = max(1e-6 * float(np.abs(t.X).max()),
              float(getattr(t, "inherited_residue", 0.0) or 0.0), 1e-9)
    check(f"{who}: {form} = X on the declared vectors", worst <= tol,
          f"worst {worst:.2e} against {tol:.2e}"
          + ("" if tb.indirect_allocation else
             " — a domestic table, so imports are supply and are not in this "
             "identity"))


def main() -> int:
    warnings.filterwarnings("ignore")
    from quadrium.io_loader import (load_idescat_mioc, load_ine_tio,
                                    load_io_table, load_uk_analytical_iot)
    from quadrium.models import TradeBlock

    print(__doc__.strip().split("Run:")[0].rstrip())
    print("\n" + "=" * 78)

    present = [p for p in (ES, CAT, UK, BE) if p.exists()]
    if not present:
        print("\nNothing was checked: not one of this file's fixtures is on "
              "disk.")
        for p in (ES, CAT, UK, BE):
            print(f"    ABSENT   {p}")
        print("\n  Every check below reads a real published table. With none "
              "of them there is")
        print("  nothing to measure, and a refusal test alone would not show "
              "that the general")
        print("  declaration reproduces the hand-written column numbers, "
              "which is the point.")
        return NOTHING_CHECKED

    declared = absent = undeclared = 0

    # ---- 1. Spain, where the hand-written indices were ---------------------
    print("\n  SPAIN, against the column numbers this replaced")
    if ES.exists():
        es = load_ine_tio(ES, variant="total")
        declared += 1
        E, M, D = es.trade_vectors()
        # The three expressions that were written into run_charm.py and
        # run_charm_heterogeneity.py by hand, one set per country.
        check("the declaration reproduces `Y[:, 5] + Y[:, 6]` for exports",
              float(np.abs(E - (es.Y[:, 5] + es.Y[:, 6])).max()) == 0.0,
              f"{E.sum():,.1f} million EUR")
        check("and `-Y[:, 7]` for imports by product",
              float(np.abs(M - (-es.Y[:, 7])).max()) == 0.0,
              f"{M.sum():,.1f}")
        check("and `Y[:, 0:5]` for final use excluding exports",
              float(np.abs(D - es.Y[:, 0:5].sum(axis=1)).max()) == 0.0,
              f"{D.sum():,.1f} — all three to zero, which is what makes the "
              f"general version a measurement rather than a claim")
        partition_is_total(es, "ES total")
        row_identity(es, "ES total")
        check("the total table is declared INDIRECT ALLOCATION",
              es.trade.indirect_allocation,
              "Tabla 1 distributes imports across Z, which is the table CHARM "
              "needs and the opposite of the one the quotient family needs")

        interior = load_ine_tio(ES, variant="interior")
        declared += 1
        partition_is_total(interior, "ES interior")
        row_identity(interior, "ES interior")
        check("the interior table is NOT indirect allocation",
              not interior.trade.indirect_allocation)
        check("and it declares no imports by product",
              not interior.trade.has_imports,
              "Tabla 2's imports are the first VA row, summed over axis 0 — "
              "by PURCHASING INDUSTRY, a different quantity")
        refuses("a commodity balance on the interior table",
                lambda: interior.trade_vectors(), "BY PRODUCT")
    else:
        absent += 1
        print(f"    -- {ES.name} is absent, so the comparison against the "
              f"hand-written indices did not run.")

    # ---- 2. the other loaders ---------------------------------------------
    print("\n  THE OTHER LOADERS")
    if UK.exists():
        uk = load_uk_analytical_iot(UK)
        declared += 1
        partition_is_total(uk, "UK")
        row_identity(uk, "UK")
        check("the UK analytical table declares no imports by product",
              not uk.trade.has_imports,
              "the ONS carries imports as a value-added row, read along the "
              "industry axis")
    else:
        absent += 1
        print(f"    -- {UK.name} is absent.")

    if BE.exists():
        from quadrium import eurostat
        be = eurostat.load_iot(BE, variant="total")
        declared += 1
        partition_is_total(be, "Eurostat BE total")
        row_identity(be, "Eurostat BE total")
        check("Eurostat's exports are its own P6 codes",
              [be.Y_labels[c] for c in be.trade.export_columns]
              == [x for x in be.Y_labels if str(x).startswith("P6")],
              f"{[be.Y_labels[c] for c in be.trade.export_columns]} — chosen "
              f"from the codes the country populates, which is why a fixed "
              f"table of indices could not have been written")
    else:
        absent += 1
        print(f"    -- {BE.name} is absent.")

    if CAT.exists():
        cat = load_idescat_mioc(CAT)
        declared += 1
        partition_is_total(cat, "IDESCAT")
        row_identity(cat, "IDESCAT")
        check("IDESCAT's imports by product come from its supply identity, "
              "not from VA",
              cat.trade.imports_vector is not None
              and float(cat.trade.imports_vector.min()) >= 0.0,
              f"{cat.trade.imports_vector.sum():,.1f} million EUR from rows "
              f"94 and 95 of 'ts total' — the VA rows are intermediate "
              f"imports by purchasing branch and leave the identity 6,588 out")
    else:
        absent += 1
        print(f"    -- {CAT.name} is absent (it is not redistributed).")

    # ---- 3. what must NOT be declared -------------------------------------
    print("\n  AND WHAT IS DELIBERATELY NOT DECLARED")
    if ES.exists():
        from quadrium.diagnostics import technical_coefficients
        from quadrium.regionalise import regionalise
        base = load_ine_tio(ES, variant="interior")
        A = np.nan_to_num(technical_coefficients(base.Z, base.X))
        q = np.ones(base.n) * 0.1
        res = regionalise(A, q, base.X, method="SLQ")
        out = res.to_table(sector_codes=base.sector_codes,
                           sector_labels=base.sector_labels,
                           country="XX-region", year=base.year,
                           unit=base.unit, classification=base.classification,
                           source="run_trade_block.py", national=base)
        undeclared += 1
        check("a regionalised table carries NO trade declaration",
              out.trade is None,
              "its single Y column is final demand AND exports together, so "
              "there is no column that is exports — which is also what stops "
              "a CHARM run being chained onto an LQ result")
        refuses("a commodity balance on a regionalised table",
                lambda: out.trade_vectors(), "NOT SPECIFIED")

    # ---- 4. the refusals, hand-built --------------------------------------
    print("\n  THE REFUSALS")
    good = dict(export_columns=[2], domestic_columns=[0, 1],
                indirect_allocation=True, declared_by="this file",
                imports_column=3)
    refuses("a negative imports_vector",
            lambda: TradeBlock(**{**good, "imports_column": None,
                                  "imports_vector": [1.0, -1.0]}),
            "negative at index 1")
    refuses("imports declared twice, as a column and as a vector",
            lambda: TradeBlock(**{**good, "imports_vector": [1.0, 1.0]}),
            "not both")
    refuses("one column declared export and domestic at once",
            lambda: TradeBlock(**{**good, "domestic_columns": [0, 1, 2]}),
            "BOTH export and domestic")
    refuses("a declaration with no source",
            lambda: TradeBlock(**{**good, "declared_by": " "}),
            "where it was read from")

    # ---- 5. the round trip through this engine's own format ---------------
    print("\n  THE ROUND TRIP")
    if ES.exists():
        from quadrium.export import write_interchange_xlsx
        es = load_ine_tio(ES, variant="total")
        with tempfile.TemporaryDirectory() as td:
            p = write_interchange_xlsx(es, Path(td) / "t.xlsx",
                                       derived_from="run_trade_block.py")
            if p is None:
                print("    -- openpyxl cannot write, so the round trip did "
                      "not run.")
            else:
                back = load_io_table(p)
                a, b = es.trade, back.trade
                check("the declaration survives being written and read",
                      b is not None
                      and b.export_columns == a.export_columns
                      and b.domestic_columns == a.domestic_columns
                      and b.imports_column == a.imports_column
                      and b.indirect_allocation == a.indirect_allocation,
                      "resolved by LABEL and not by index, so a reordered "
                      "table cannot come back saying a different column is "
                      "exports")
                # The vectors agree to the FORMAT's float precision and not to
                # zero, and that is a property of writing Y into a spreadsheet
                # rather than of the declaration: the indices above are
                # identical.
                w = max(float(np.abs(x - y).max()) for x, y in
                        zip(es.trade_vectors(), back.trade_vectors()))
                check("and the vectors come back within the format's own "
                      "float precision", w < 1e-9,
                      f"worst {w:.1e} — the indices are identical, so this is "
                      f"xlsx round-tripping Y and not the declaration")

    print("\n" + "=" * 78)
    total = declared + absent
    print(f"coverage: {declared} loader(s) declared a trade block, "
          f"{undeclared} deliberately declared none, {absent} fixture(s) "
          f"absent of {total + undeclared} looked at")
    if FAIL:
        print(f"{len(FAIL)} check(s) FAILED: {', '.join(FAIL)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
