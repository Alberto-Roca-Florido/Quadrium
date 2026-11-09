"""CHARM is a job, not a fifth `--method`, and both its doors agree.

THE DECISION THIS IMPLEMENTS
------------------------------
CHARM could have been a fifth value of `--method` beside SLQ, CILQ, RLQ and
FLQ. The owner decided on 2026-11-08 that it is its own job, and the reason is
methodological rather than architectural: `M-075`'s DOMESTIC_IMPORT_TREATMENT
says the quotient family needs the DOMESTIC table and CHARM the TOTAL-FLOW
one, that the two give different multipliers — domestic output against supply
— and that they are **not interchangeable**. Choosing between `--regionalise`
and `--charm` is therefore choosing which multiplier you want, not merely
which estimator.

A flag cannot carry that. One `--method` would have had to load two
incompatible tables and write two different sets of files depending on a word.

WHAT IS CHECKED
-----------------
That both doors — the `charm` sheet of the configuration workbook, and
`--charm` on the command line — run end to end on a published table and
produce **identical numbers**; that the measured cost reaches `report.md`, the
machine-readable ledger and the terminal through each of them, and the terminal
exactly once; and that the refusals fire the same way through both.

The refusal that matters most is the DOMESTIC TABLE. It is the one that would
otherwise return numbers rather than an error, so it is tested through both
doors and by two different routes into each: by `table_kind` on the workbook,
and by handing the flags route a table in this engine's own format whose
declaration says it is domestic.

Exit 0 pass, 1 fail, 3 checked nothing.

Run:
    python3 validators/run_charm_doors.py
"""
from __future__ import annotations

import csv
import io
import json
import shutil
import sys
import tempfile
import warnings
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

ES = ROOT / "data" / "ine" / "cne_tio_21.xlsx"
FAIL: list[str] = []

# The four figures `charm.py` puts in every run's caveats, measured by
# run_charm.py. If a run's records do not carry these, the cost was printed
# somewhere and not written down, which is the thing `CORE_036` p. 35 is cited
# against.
COST = ("0.886", "1.40", "47 of 63", "0.117")
BLOCK = "## What this is known to get wrong"


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {name}"
          + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def run(argv):
    from quadrium.cli import main

    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def employment_file(table, path, *, national=True):
    """A regional employment file. Not real employment — the point here is the
    plumbing, and run_charm.py is where the method is measured against
    published truth."""
    rng = np.random.default_rng(20261108)
    share = np.clip(0.12 * np.exp(rng.normal(0, 0.4, table.n)), 0.01, 0.9)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)                  # quoted: a sector code can hold a
        head = ["sector_code", "regional"]  # comma
        if national:
            head.append("national")
        w.writerow(head)
        for c, x, s in zip(table.sector_codes, table.X, share):
            row = [c, f"{x * s:.6f}"]
            if national:
                row.append(f"{x:.6f}")
            w.writerow(row)
    return share


def workbook(path, *, rows, table_path, kind="ine_total", sheet="charm",
             also=None):
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "project"
    ws.append(["key", "value"])
    for k, v in (("project_id", "doors"), ("table_path", str(table_path)),
                 ("table_kind", kind)):
        ws.append([k, v])
    ws = wb.create_sheet(sheet)
    ws.append(["key", "value"])          # the template's own header row
    for r in rows:
        ws.append(list(r))
    if also:
        ws2 = wb.create_sheet(also[0])
        ws2.append(["key", "value"])
        for r in also[1]:
            ws2.append(list(r))
    wb.save(path)
    return path


def trade_csv(path):
    return np.genfromtxt(path, delimiter=",", skip_header=2,
                         usecols=range(1, 10))


def main_() -> int:
    warnings.filterwarnings("ignore")
    from quadrium.io_loader import load_ine_tio

    print(__doc__.strip().split("Run:")[0].rstrip())
    print("\n" + "=" * 78)

    if not ES.exists():
        print(f"\nNothing was checked: the national table is absent — {ES}")
        print("\n  This file exists to prove the two doors agree, and that "
              "needs both of them run")
        print("  against a real total-flow table. With none there is nothing "
              "to compare. Exit 3")
        print("  says CHECKED NOTHING, which check.sh names separately and "
              "never counts as a pass.")
        return 3

    tmp = Path(tempfile.mkdtemp(prefix="quadrium_charm_doors_"))
    try:
        table = load_ine_tio(ES, variant="total")
        act = tmp / "employment.csv"
        employment_file(table, act)

        # ---- 1. the flags door
        code, out_f, err_f = run(["--charm", str(act), "--national", str(ES),
                                  "--national-kind", "ine",
                                  "--outputs", str(tmp), "--name", "flags"])
        check("the flags door runs end to end on a published total-flow table",
              code == 0,
              f"exit {code}" + (f"; stderr: {err_f[:90]}" if err_f else ""))

        # ---- 2. the workbook door
        wb = workbook(tmp / "wb.xlsx", rows=[("activity_path", str(act))],
                      table_path=ES)
        code, out_w, err_w = run([str(wb), "--outputs", str(tmp)])
        check("and so does the workbook door", code == 0,
              f"exit {code}" + (f"; stderr: {err_w[:90]}" if err_w else ""))

        d_f, d_w = tmp / "flags", tmp / "doors"
        for who, d in (("the flags door", d_f), ("the workbook door", d_w)):
            wrote = {p.name for p in d.glob("*")} if d.exists() else set()
            check(f"{who} writes the trade, the heterogeneity and both records",
                  wrote >= {"trade.csv", "heterogeneity.csv", "report.md",
                            "assumption_ledger.json"},
                  ", ".join(sorted(wrote)))
            check(f"{who} writes NO regional table and no coefficients",
                  not (wrote & {"regional_table.xlsx", "coefficients.csv",
                                "implicit_imports.csv"}),
                  "CHARM estimates trade, not a technology: a table with one "
                  "residual final-demand column would net E against M and "
                  "destroy the one quantity the method computes")

        # ---- 3. THE SAME NUMBERS. Not close: the same.
        if (d_f / "trade.csv").exists() and (d_w / "trade.csv").exists():
            a, b = trade_csv(d_f / "trade.csv"), trade_csv(d_w / "trade.csv")
            worst = float(np.abs(a - b).max()) if a.shape == b.shape else -1.0
            check("the two doors produce IDENTICAL numbers", worst == 0.0,
                  f"worst {worst:.3e} over {a.shape[0]} products x "
                  f"{a.shape[1]} columns — one function behind two doors, so a "
                  f"result cannot depend on how it was asked for")

        # ---- 4. the cost reaches every sink, through both doors
        for who, d, out in (("flags", d_f, out_f), ("workbook", d_w, out_w)):
            if not (d / "report.md").exists():
                continue
            report = (d / "report.md").read_text()
            ledger = json.loads((d / "assumption_ledger.json").read_text())
            led = " ".join(ledger.get("caveats", []))
            # `wants_source` only where the BLOCK is printed. The ledger
            # carries the caveat strings and no citation, so demanding
            # CORE_036 of it would have to be satisfied by something this
            # check appended itself — which is the vacuous pass this project
            # removes validators for, and the first draft of this loop did it.
            for where, text, wants_source in (
                    ("report.md", report, True),
                    ("the ledger", led, False),
                    ("the terminal", out, True)):
                missing = [c for c in COST if c not in text]
                no_src = wants_source and "CORE_036" not in text
                check(f"{who}: the measured cost is in {where}, unasked for",
                      not missing and not no_src,
                      f"missing {missing}" if missing else
                      "it does not say where the position comes from"
                      if no_src else
                      "the transported heterogeneity carries the ordering and "
                      "not the level — 0.886, 1.40x, 47 of 63, 0.117"
                      + (", and CORE_036 p. 35 for why it is printed at all"
                         if wants_source else ""))
            check(f"{who}: and the terminal gets that block exactly once",
                  out.count(BLOCK) == 1, f"{out.count(BLOCK)} of them")
            check(f"{who}: the ledger says where eps came from",
                  ledger.get("eps_source") == "national, transported"
                  and ledger.get("indirect_allocation") is True,
                  "so a later reader knows the heterogeneity was the "
                  "nation's, which is the method's central assumption")

        # ---- 5. THE DOMESTIC TABLE, refused through both doors and by two
        #         routes into each. This is the refusal that would otherwise
        #         return numbers instead of an error.
        print()
        code, _, err = run([str(workbook(tmp / "dom.xlsx",
                                         rows=[("activity_path", str(act))],
                                         table_path=ES,
                                         kind="ine_interior")),
                            "--outputs", str(tmp)])
        check("the workbook refuses the DOMESTIC table and names the right one",
              code != 0 and "ine_total" in err and "DOMESTIC" in err,
              "by `table_kind`, before the load — the cheap refusal")

        from quadrium.export import write_interchange_xlsx
        dom = write_interchange_xlsx(load_ine_tio(ES, variant="interior"),
                                     tmp / "domestic.xlsx",
                                     derived_from="run_charm_doors.py")
        if dom is not None:
            code, _, err = run(["--charm", str(act), "--national", str(dom),
                                "--national-kind", "interchange",
                                "--outputs", str(tmp)])
            check("and the flags door refuses one that arrives DECLARED "
                  "domestic",
                  code == 2 and "DOMESTIC" in err and "STE_14" in err,
                  "the only route a domestic table can reach this door by, "
                  "since --national-kind ine loads the total variant — so the "
                  "declaration is what catches it, and the refusal names who "
                  "declared it")

        for kind, word in (("uk_analytical", "uk"), ("eu_mrio", "eu_mrio")):
            code, _, err = run([str(workbook(tmp / f"{kind}.xlsx",
                                             rows=[("activity_path",
                                                    str(act))],
                                             table_path=ES, kind=kind)),
                                "--outputs", str(tmp)])
            check(f"and refuses `table_kind: {kind}` by name", code != 0,
                  str(err).strip().splitlines()[-1][:110] if err else "")

        # ---- 6. the mistakes both doors must refuse in the same words
        print()
        short = tmp / "short.csv"
        employment_file(table, short)
        lines = short.read_text().splitlines()
        short.write_text("\n".join(lines[:-3]) + "\n")
        code_f, _, err_f2 = run(["--charm", str(short), "--national", str(ES),
                                 "--national-kind", "ine",
                                 "--outputs", str(tmp)])
        code_w, _, err_w2 = run([str(workbook(tmp / "short.xlsx",
                                              rows=[("activity_path",
                                                     str(short))],
                                              table_path=ES)),
                                 "--outputs", str(tmp)])
        check("an employment file that does not cover the table is refused by "
              "both, in the same words",
              code_f != 0 and code_w != 0
              and "do not describe the same sectors" in err_f2
              and "do not describe the same sectors" in err_w2,
              "both call config.read_activity, so one mistake cannot get two "
              "different refusals depending on the door")

        nonat = tmp / "nonat.csv"
        employment_file(table, nonat, national=False)
        code_f, _, err_f3 = run(["--charm", str(nonat), "--national", str(ES),
                                 "--national-kind", "ine",
                                 "--outputs", str(tmp)])
        code_w, _, err_w3 = run([str(workbook(tmp / "nonat.xlsx",
                                              rows=[("activity_path",
                                                     str(nonat))],
                                              table_path=ES)),
                                 "--outputs", str(tmp)])
        check("and so is one with no `national` column, which this job alone "
              "may not default",
              code_f != 0 and code_w != 0
              and "EMPLOYMENT" in err_f3 and "EMPLOYMENT" in err_w3,
              "read_activity fills the national side with the table's own "
              "OUTPUT when the column is absent — right for a location "
              "quotient, and in eq. (30) it would put output where employment "
              "belongs")

        # ---- 7. and the two jobs are not combinable
        code, _, err = run(["--charm", str(act), "--regionalise", str(act),
                            "--national", str(ES)])
        check("--charm and --regionalise together are refused, not ranked",
              code == 2 and "two different tables" in err,
              "they are two jobs on two tables and M-075 says the "
              "multipliers are not interchangeable, so a precedence rule "
              "would quietly answer a question nobody asked")

        code, _, err = run([str(workbook(tmp / "both.xlsx",
                                         rows=[("activity_path", str(act))],
                                         table_path=ES,
                                         also=("regionalise",
                                               [("method", "FLQ"),
                                                ("delta", "0.25"),
                                                ("activity_path", str(act))]))),
                            "--outputs", str(tmp)])
        check("and a workbook with BOTH sheets filled in is refused too",
              code != 0 and "two different jobs" in err,
              "the same refusal through the other door")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 78)
    if FAIL:
        print(f"{len(FAIL)} check(s) FAILED: {', '.join(FAIL)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main_())
