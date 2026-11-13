"""The multiplier table, by the door a workbook user actually opens.

WHAT THIS CHECKS THAT `run_multipliers.py` DOES NOT
-----------------------------------------------------
That one proves the ARITHMETIC: the engine reproduces the ONS's own published
Type I effects and multipliers, 1,434 figures, worst error 7.11e-15. It opens no
workbook and writes no file. So it would have passed unchanged on every day
between then and 2026-11-13, while the table it verifies reached a user only as
prose inside one job's report and as keys inside a diagnostics JSON.

This one checks the DELIVERABLE: the `multipliers` sheet, `multiplier_table.csv`
and the `Multipliers` worksheet. Every figure it compares comes from the
published sheets by the same route `run_multipliers.py` uses -- NOT from a
recomputation inside this file, which would be checking the code against itself.

THREE RULES, EACH CHECKED IN THE DIRECTION THAT FAILS
-------------------------------------------------------
1. No column says "multiplier" without saying which type. Asserted by feeding
   the writer a header that breaks it and requiring the refusal.
2. A type II column travels with its closure and the sentence that forbids
   reading a ranking.
3. A sector withheld from publication is EMPTY with its reason, and a sector
   with no direct coefficient is empty too -- never zero.

AND THE TWO DEFECTS THE FIRST REAL RUN FOUND, now regression tests:
- **The type II closure was attached by one job only.** It lived inside
  `build_config`, so a workbook declaring `type_ii_income_rows` and
  `type_ii_household_column` and asking for a multiplier table got type I and
  nothing said the two rows had been ignored. Extracted to `_attach_type_ii`.
- **The template's example title leaked.** The first report produced came out
  headed "My sector split". A multiplier table under that heading is the
  confidently-wrong artefact this project keeps finding.

Run:
    python3 validators/run_multiplier_table.py
"""

from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

FIXTURE = ROOT / "UK_IOAT_2023_domestic_ixi.xlsx"
FIRST_DATA_ROW = 8

#: The published columns, 0-based, in the fixture's own two sheets. Same
#: indices `run_multipliers.py` establishes and re-asserts against the header
#: text; a re-export that moves a column must fail loudly here too.
#: BOTH NAMES, because they are not the same name. The table's own
#: value-added label is what the sheet asks for; the published heading is what
#: the office prints over the column. For imports they differ outright --
#: "Imports of goods and services (cif)" against "Use of imported products,
#: cif" -- and the first version of this file compared the two to each other,
#: which can only fail.
PUBLISHED = [
    # table's own VA label                  published heading        mul  eff
    ("Imports of goods and services (cif)",
     "Use of imported products, cif",                                 3,   3),
    ("Taxes less subsidies on products",
     "Taxes less subsidies on products",                              4,   4),
    ("Compensation of employees",
     "Compensation of employees",                                     6,   6),
    ("Gross operating surplus and mixed income",
     "Gross operating surplus and mixed income",                      7,   7),
]
#: Gross value added is THREE rows on this table and one on others, which is
#: why the sheet asks for it as a sum rather than knowing the name.
GVA = ("Compensation of employees;"
       "Gross operating surplus and mixed income;"
       "Other taxes less subsidies on production")

#: `M-067`: the ONS publishes output of GBP 260,111 million for this industry
#: and no multiplier. Imputed rent has no transaction, no employment and no
#: supply chain.
EXCLUDED = "L68A"
#: THE TWO FIGURES THE GUIDE QUOTES ABOUT THIS INDUSTRY, as literals, so
#: `run_report_claims.py` can tell whether they have drifted. Transcribed from
#: `docs/GUIDE.md` section 12 and checked against the fixture below -- the
#: output the ONS publishes for it, and the multiplier this engine computes
#: where the ONS publishes none.
GUIDE_L68A_OUTPUT = 260111.0
GUIDE_L68A_TYPE_I = 1.0828
EXCLUDED_WHY = ("the ONS publishes no multiplier for imputed rent: no "
                "transaction, no employment, no supply chain")

FAIL: list = []
TEMPLATE: Path


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {name}"
          + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def refuses(name: str, fn, fragment: str) -> None:
    """A refusal is reached AND says the thing that makes it useful."""
    from quadrium.config import ConfigError
    from quadrium.multipliers import MultiplierError
    try:
        fn()
    except (ConfigError, MultiplierError) as exc:
        got = str(exc)
        check(name, fragment in got,
              f"refused — {got[:150]}" if fragment in got else
              f"refused, but the message does not contain {fragment!r}: "
              f"{got[:150]}")
    except Exception as exc:                       # noqa: BLE001
        check(name, False, f"raised {type(exc).__name__}, not a refusal: "
                           f"{str(exc)[:120]}")
    else:
        check(name, False, "was ACCEPTED, and it must not be")


def _book(dest: Path, rows: list, project: dict) -> Path:
    """A workbook from the engine's own template with only `multipliers` set.

    Built from the template rather than from scratch so that a template that
    stops carrying the sheet, or renames a column, fails here.
    """
    import openpyxl
    shutil.copy(TEMPLATE, dest)
    wb = openpyxl.load_workbook(dest)
    for name in ("splits", "mixed", "regionalise", "charm", "targets"):
        if name in wb.sheetnames:
            ws = wb[name]
            for r in range(2, ws.max_row + 1):
                for c in range(1, ws.max_column + 1):
                    ws.cell(row=r, column=c).value = None
    pj = wb["project"]
    seen = {}
    for r in range(1, pj.max_row + 1):
        k = pj.cell(row=r, column=1).value
        if k:
            seen[str(k).strip().lower()] = r
    for k, v in project.items():
        r = seen.get(k) or (pj.max_row + 1)
        pj.cell(row=r, column=1).value = k
        pj.cell(row=r, column=2).value = v
        seen[k] = r
    ws = wb["multipliers"]
    for r in range(2, ws.max_row + 1):
        for c in range(1, 5):
            ws.cell(row=r, column=c).value = None
    for i, row in enumerate(rows, start=2):
        for c, v in enumerate(row, start=1):
            ws.cell(row=i, column=c).value = v
    wb.save(dest)
    return dest


def main() -> int:
    global TEMPLATE
    import tempfile
    try:
        import openpyxl
    except ImportError:
        print("Nothing was checked: openpyxl missing")
        return 3
    if not FIXTURE.exists():
        print("Nothing was checked: the UK fixture is absent")
        return 3

    from quadrium.config import TEMPLATE_TITLE, load_config, write_template
    from quadrium.export import (_multiplier_header, write_multiplier_table,
                                 write_multiplier_xlsx)
    from quadrium.io_loader import load_uk_analytical_iot
    from quadrium.multipliers import multiplier_table

    print(__doc__.strip().split("Run:")[0].rstrip())
    print("\n" + "=" * 78)

    tmp = Path(tempfile.mkdtemp(prefix="quadrium_mult_"))
    TEMPLATE = tmp / "template.xlsx"
    write_template(TEMPLATE)

    t = load_uk_analytical_iot(FIXTURE)
    n = t.n
    wb = openpyxl.load_workbook(FIXTURE, read_only=True, data_only=True)

    def published(sheet: str, c: int) -> np.ndarray:
        rows = wb[sheet].iter_rows(min_row=FIRST_DATA_ROW,
                                   max_row=FIRST_DATA_ROW + n - 1,
                                   values_only=True)
        return np.array([float(r[c]) if isinstance(r[c], (int, float))
                         else np.nan for r in rows])

    def heading(sheet: str, c: int) -> str:
        return str(list(wb[sheet].iter_rows(min_row=6, max_row=6,
                                            values_only=True))[0][c] or "")

    # ---- 1. every column against what the office published ---------------
    print("\n  1. EVERY COLUMN AGAINST THE PUBLISHED FIGURES\n")
    mt = multiplier_table(t, rows=[lbl for lbl, _, _, _ in PUBLISHED] + [GVA],
                          names={GVA: "gross_value_added"})
    worst = 0.0
    compared = 0
    print(f"    {'quantity':<44}{'effect':>12}{'multiplier':>14}")
    pairs = [("output", mt.output, 9, 10)] + [
        (lbl, mt.rows[lbl], cm, ce) for lbl, _h, cm, ce in PUBLISHED] + [
        ("gross_value_added", mt.rows["gross_value_added"], 8, 9)]
    for label, r, cm, ce in pairs:
        pe, pm = published("Effects", ce), published("Multipliers", cm)
        de = float(np.nanmax(np.abs(r.effect - pe)))
        dm = float(np.nanmax(np.abs(r.multiplier - pm)))
        compared += int(np.isfinite(pe).sum() + np.isfinite(pm).sum())
        worst = max(worst, de, dm)
        print(f"    {label:<44}{de:>12.1e}{dm:>14.1e}")
    print()
    check("the delivered table holds the ONS's own published figures",
          worst < 1e-12,
          f"{compared:,} published figures across {len(pairs)} quantities, "
          f"worst error {worst:.2e}. The same worst error "
          f"`run_multipliers.py` reports, by a different route: that one "
          f"computes the formula, this one reads the object the user is "
          f"handed")

    # A HEADING CHECK, so a re-exported fixture cannot silently compare the
    # wrong series. `run_multipliers.py` asserts this; a second file reading
    # the same columns has to assert it too or it inherits a false confidence.
    moved = [h for _lbl, h, cm, _ce in PUBLISHED
             if h != heading("Multipliers", cm)]
    check("and the published columns are still the ones these indices name",
          not moved,
          f"{len(PUBLISHED)} column headings re-read from row 6"
          if not moved else f"moved: {moved}")

    # ---- 2. rule 1: no multiplier without its type -----------------------
    print("\n  2. NO COLUMN SAYS 'MULTIPLIER' WITHOUT SAYING WHICH TYPE\n")
    names = mt.column_names()
    bad = [c for c in names if "multiplier" in c.lower()
           and "_type_i" not in c.lower()]
    check("every multiplier column names its type",
          not bad,
          f"{len([c for c in names if 'multiplier' in c])} multiplier columns, "
          f"all tagged. M-067: an output saying 'multiplier' without saying "
          f"'type I' understates by more than half"
          if not bad else f"untagged: {bad}")

    class Untagged:
        """A table whose header breaks rule 1, to prove the writer refuses."""
        provenance = mt.provenance
        table_id = "untagged"
        closure = None
        suppressed: dict = {}
        leontief = mt.leontief

        def column_names(self):
            return ["output_multiplier"]

    refuses("and the writer REFUSES a header that breaks the rule — "
            "tested in the direction that fails",
            lambda: _multiplier_header(Untagged()),
            "do not say which type")

    # ---- 3. the empty cells, and that they are not zeros ------------------
    print("\n  3. AN EMPTY CELL IS A WITHHELD OR UNDEFINED VALUE, NEVER A "
          "ZERO\n")
    sup = multiplier_table(t, rows=["Compensation of employees"],
                           exclude={EXCLUDED: EXCLUDED_WHY})
    j = sup.codes.index(EXCLUDED)
    check(f"{EXCLUDED} is withheld, and as NaN rather than as a number",
          bool(np.isnan(sup.output.multiplier[j]))
          and sup.suppressed[EXCLUDED] == EXCLUDED_WHY,
          f"output GBP {float(t.X[j]):,.0f} million and no multiplier "
          f"published — the engine computes "
          f"{float(mt.output.multiplier[j]):.4f} and the ONS's refusal is the "
          f"better judgement (M-067)")
    check("and withholding it does NOT move any other sector's multiplier",
          float(np.nanmax(np.abs(
              np.delete(sup.output.multiplier, j)
              - np.delete(mt.output.multiplier, j)))) < 1e-15,
          "suppression is applied to the built arrays, after the inverse. "
          "Applied earlier it would make every OTHER sector's multiplier "
          "depend on an editorial decision")
    blank_published = [c for i, c in enumerate(mt.codes)
                       if not np.isfinite(published("Multipliers", 9)[i])]
    check("and it is the same industry the ONS itself leaves blank",
          blank_published == [EXCLUDED],
          f"published blanks: {blank_published}")
    check("and the two figures the guide quotes about it are still its "
          "figures",
          abs(float(t.X[j]) - GUIDE_L68A_OUTPUT) < 1.0
          and abs(float(mt.output.multiplier[j]) - GUIDE_L68A_TYPE_I) < 5e-5,
          f"output {float(t.X[j]):,.0f} against the "
          f"{GUIDE_L68A_OUTPUT:,.0f} section 12 prints, and type I "
          f"{float(mt.output.multiplier[j]):.4f} against "
          f"{GUIDE_L68A_TYPE_I}. Quoted in the guide, so pinned here: a "
          f"figure nothing carries as a literal cannot be told to have "
          f"drifted")

    # THE UNDEFINED CASE IS A DIFFERENT CASE, and the two must not be merged:
    # one is an editorial refusal and the other is arithmetic.
    und = multiplier_table(
        t, rows=["Other taxes less subsidies on production"])
    r = und.rows["Other taxes less subsidies on production"]
    zeros = np.where(np.nan_to_num(r.direct) == 0)[0]
    check("a sector whose direct coefficient is zero has NO multiplier, and "
          "it is not a zero one",
          r.undefined > 0 and zeros.size > 0
          and bool(np.isnan(r.multiplier[int(zeros[0])])),
          f"{r.undefined} of {n} sectors have no multiplier for this row. "
          f"Calling it zero would say the quantity is perfectly absent "
          f"rather than that there is nothing to divide by")

    # ---- 4. the file, read back ------------------------------------------
    print("\n  4. THE FILE, READ BACK — INCLUDING THE CODE WITH A COMMA IN "
          "IT\n")
    csv_path = write_multiplier_table(sup, tmp / "multiplier_table.csv")
    rows = list(csv.reader(csv_path.open(newline="", encoding="utf-8")))
    data = [r for r in rows if r and not r[0].startswith("#")]
    head, body = data[0], data[1:]
    widths = {len(r) for r in body}
    comma = [r for r in body if "," in r[0]]
    check("every row has exactly as many fields as the header",
          widths == {len(head)} and len(body) == n,
          f"{len(body)} rows x {len(head)} fields. The UK table has a sector "
          f"whose CODE contains a comma — {comma[0][0]!r} — and the first "
          f"version of the mixed-model writer split that row in two "
          f"silently on 2026-11-12")
    check("and the comma-bearing code survives as ONE field",
          len(comma) == 1 and len(comma[0]) == len(head),
          f"{comma[0][0]!r} read back whole")
    l68 = [r for r in body if r[0] == EXCLUDED][0]
    k = head.index("output_multiplier_type_i")
    check("the withheld sector's cell is EMPTY in the file and its reason is "
          "in the row",
          l68[k] == "" and EXCLUDED_WHY[:20] in l68[-1],
          "a blank cell with no reason beside it cannot be told apart from a "
          "defect, which is why the reason is a refusal in the sheet and not "
          "a nicety")
    notes = [r[0] for r in rows if r and r[0].startswith("#")]
    check("and the caveats travel in the file, not only in the report",
          any("TYPE I" in x for x in notes)
          and any("NOT A ZERO" in x.upper() for x in notes)
          and any("NOT PUBLISHED" in x.upper() for x in notes),
          f"{len(notes)} comment lines: the formulas, the empty-cell rule and "
          f"the exclusions. A caveat in one file and absent from the other is "
          f"worse than absent from both")
    check("the workbook is written too, with the same header",
          write_multiplier_xlsx(sup, tmp / "multipliers.xlsx") is not None,
          "CSV to read back with a program, worksheet to paste into a report")

    # ---- 5. the door: the sheet, end to end ------------------------------
    print("\n  5. THE SHEET A USER FILLS IN\n")
    tbl = str(FIXTURE.resolve())
    base = {"project_id": "mult_test", "table_path": tbl,
            "table_kind": "uk_analytical"}
    ok_book = _book(tmp / "ok.xlsx",
                    [["all", None, None, None],
                     [None, None, EXCLUDED, EXCLUDED_WHY]], base)
    cfg = load_config(ok_book)
    check("a workbook with only the `multipliers` sheet is that job",
          cfg.get("kind") == "multipliers"
          and cfg["exclude"] == {EXCLUDED: EXCLUDED_WHY},
          f"{len(cfg['want'])} quantities asked for by one row saying `all`")
    through = multiplier_table(cfg["table"], rows=cfg["want"],
                               names=cfg["names"], exclude=cfg["exclude"])
    check("and the sheet route gives the same numbers as the Python route",
          float(np.nanmax(np.abs(
              np.nan_to_num(through.output.multiplier, nan=0.0)
              - np.nan_to_num(sup.output.multiplier, nan=0.0)))) < 1e-15,
          "the workbook is a door onto the same object, not a second "
          "implementation of it")

    # THE TITLE. Found on the first real run: the report came out headed
    # "My sector split", which is what the template writes as an EXAMPLE.
    check("the template's example title does NOT become the run's title",
          cfg["title"] != TEMPLATE_TITLE
          and "multiplier" in cfg["title"].lower(),
          f"{cfg['title']!r} — a multiplier table headed "
          f"{TEMPLATE_TITLE!r} is the confidently-wrong artefact this "
          f"project keeps finding, and this workbook never edited the cell")

    # THE CLOSURE. Found on the same run: it was attached by `build_config`
    # alone, so this job silently produced type I.
    t2_book = _book(
        tmp / "t2.xlsx", [["all", None, None, None]],
        {**base, "type_ii_income_rows": "Compensation of employees",
         "type_ii_household_column": "P3 S14"})
    t2cfg = load_config(t2_book)
    t2 = multiplier_table(t2cfg["table"], rows=t2cfg["want"],
                          names=t2cfg["names"], exclude=t2cfg["exclude"])
    check("a declared type II closure REACHES this job",
          t2.output_type_ii is not None and t2.closure is not None,
          f"closed on {'; '.join(t2.closure['income_rows'])} through "
          f"{t2.closure['household']}. Until 2026-11-13 the closure was "
          f"attached inside `build_config` only: these two rows were dropped "
          f"in silence and the run reported type I")
    check("and its uplift and propensity are the figures the project has "
          "already pinned",
          abs(float(np.nanmean(t2.induced_uplift)) - 1.573) < 0.01
          and abs(t2.closure["propensity"] - 0.892) < 0.002,
          f"uplift {float(np.nanmean(t2.induced_uplift)):.3f} against the "
          f"1.573 `run_type_ii_engine.py` pins, propensity "
          f"{t2.closure['propensity']:.3f} against 0.892")
    check("and the sentence that forbids reading a ranking travels with them",
          "do not read the order" in
          t2.closure["read_the_uplift_not_the_order"].lower(),
          "OQ-T-05 closed as NOT SPECIFIED: the economy-wide uplift is firm "
          "(1.573 / 1.614 / 1.612) and the industry spread nearly halves. "
          "The caveat is not a nicety the writer may drop")

    # ---- 6. the refusals -------------------------------------------------
    print("\n  6. WHAT THE SHEET REFUSES\n")
    refuses("a row that asks for nothing",
            lambda: load_config(_book(tmp / "r1.xlsx",
                                      [[None, None, None, "why"]], base)),
            "neither `what` nor `exclude_sector`")
    refuses("a row that both asks and withholds",
            lambda: load_config(_book(tmp / "r2.xlsx",
                                      [["output", None, EXCLUDED, "why"]],
                                      base)),
            "two different statements")
    refuses("a quantity this table does not have",
            lambda: load_config(_book(tmp / "r3.xlsx",
                                      [["Wages and salaries", None, None,
                                        None]], base)),
            "is not a row of")
    refuses("an excluded sector that is not a sector",
            lambda: load_config(_book(tmp / "r4.xlsx",
                                      [["all", None, None, None],
                                       [None, None, "ZZZ", "why"]], base)),
            "is not a sector of")
    refuses("an exclusion with no reason",
            lambda: load_config(_book(tmp / "r5.xlsx",
                                      [["all", None, None, None],
                                       [None, None, EXCLUDED, None]], base)),
            "`reason` is empty")
    refuses("the same sector excluded twice for two reasons",
            lambda: load_config(_book(tmp / "r6.xlsx",
                                      [["all", None, None, None],
                                       [None, None, EXCLUDED, "one"],
                                       [None, None, EXCLUDED, "two"]], base)),
            "already excluded")
    refuses("the same quantity asked for twice",
            lambda: load_config(_book(tmp / "r7.xlsx",
                                      [["output", None, None, None],
                                       ["output", None, None, None]], base)),
            "asked for twice")
    refuses("`all` with a name, which would name nothing",
            lambda: load_config(_book(tmp / "r8.xlsx",
                                      [["all", "everything", None, None]],
                                      base)),
            "nothing for one name to name")
    refuses("a sheet that only withholds and asks for nothing",
            lambda: load_config(_book(tmp / "r9.xlsx",
                                      [[None, None, EXCLUDED, "why"]], base)),
            "asks for nothing")
    refuses("a sector excluded that this table does not have, through the "
            "Python door",
            lambda: multiplier_table(t, rows=[], exclude={"ZZZ": "why"}),
            "cannot be excluded")
    refuses("and an exclusion whose reason is blank, through the Python door",
            lambda: multiplier_table(t, rows=[], exclude={EXCLUDED: "   "}),
            "excluded with no reason")

    # ---- 7. the sheet cannot share a workbook ----------------------------
    print("\n  7. TWO JOBS IN ONE WORKBOOK\n")
    both = _book(tmp / "both.xlsx", [["all", None, None, None]], base)
    bk = openpyxl.load_workbook(both)
    ws = bk["mixed"]
    ws.cell(row=2, column=1).value = "A01"
    ws.cell(row=2, column=3).value = -20
    bk.save(both)
    refuses("the two describing sheets together",
            lambda: load_config(both),
            "each one asks its own question")

    withsplit = _book(tmp / "split.xlsx", [["all", None, None, None]], base)
    bk = openpyxl.load_workbook(withsplit)
    ws = bk["splits"]
    ws.cell(row=2, column=1).value = "A01"
    ws.cell(row=2, column=2).value = "A01a"
    bk.save(withsplit)
    refuses("and a describing sheet with a building one",
            lambda: load_config(withsplit),
            "two runs rather than one")

    # ---- 7b. THE COMMAND THE USER ACTUALLY TYPES -------------------------
    # Added 2026-11-13, hours after the rest of this file, because the
    # reachability census named two functions nothing had ever entered:
    # `_multiplier_report` and `_write_multipliers`. Everything above tests
    # the OBJECT and the workbook that configures it; neither of those is
    # what a user receives. The two functions that turn the object into a
    # folder of files had no case at all -- which is, one level down, the
    # same finding this whole job was built to fix: arithmetic that is right
    # and not delivered.
    print("\n  7b. WHAT THE RUN ACTUALLY WRITES\n")
    from quadrium.cli import _multiplier_report, _write_multipliers

    cli_out = tmp / "cli"
    rc = _write_multipliers(through, cfg, cli_out)
    folder = cli_out / "mult_test"
    check("the run returns 0 and writes its own folder",
          rc == 0 and folder.is_dir(), str(folder))
    for f in ("multiplier_table.csv", "report.md"):
        check(f"it wrote {f}", (folder / f).exists())
    check("and the workbook is named multipliers.xlsx, NOT multipliers.csv",
          (folder / "multipliers.xlsx").exists()
          and not (folder / "multipliers.csv").exists(),
          "`multipliers.csv` is the FIFTH job's sector-by-sector matrix. Two "
          "different files with one name in neighbouring folders is the "
          "confidently-wrong artefact this project keeps finding in itself")

    body = (folder / "report.md").read_text(encoding="utf-8")
    check("the report never says 'multiplier' without saying which type",
          "type I" in body,
          "M-067: the unlabelled word makes the larger claim silently and "
          "understates by more than half")
    check("it names the price basis and the transformation model",
          "basic" in body.lower() or "purchas" in body.lower(),
          "M-028: a multiplier means nothing without the table it came from")
    check("it says which sector was withheld and why",
          EXCLUDED in body and EXCLUDED_WHY.split(".")[0][:24] in body,
          f"{EXCLUDED} is the ONS's own refusal, and a blank cell with no "
          f"reason beside it cannot be told apart from a bug")
    check("and the title is the user's, not the template's example",
          TEMPLATE_TITLE not in body, TEMPLATE_TITLE)

    screen = _multiplier_report(through, cfg, check=True)
    check("the --check report prints without writing anything",
          bool(screen.strip()) and "type I" in screen
          and "Nothing was written" in screen,
          f"{len(screen.splitlines())} lines")

    # ---- 8. the OTHER door: a job that BUILDS a table writes it too ------
    print("\n  8. A BUILDING JOB HANDS THE SAME FILE OVER UNASKED\n")
    from quadrium.models import (AllocationKey, ProxyStrength, Scenario,
                                 SplitSpec)
    from quadrium.multipliers import known_wrong
    from quadrium.project import IOProject

    # A one-sector split on the fixture, with a size key and no input profile
    # -- which is the case the warning below exists for.
    parent = "A01"
    proj = IOProject(
        project_id="mult_stage_b", table=load_uk_analytical_iot(FIXTURE),
        splits=[SplitSpec(parent, [f"{parent}a", f"{parent}b"],
                          ["part a", "part b"])],
        scenarios=[Scenario(scenario_id="S", label="halves",
                            description="a size key and nothing else",
                            keys_by_block={"output": "k"})],
        keys={"k": AllocationKey(
            key_id="k", applies_to="output",
            new_sector_codes=[f"{parent}a", f"{parent}b"],
            raw_values=[60.0, 40.0], source="synthetic", source_year=2023,
            strength=ProxyStrength.WEAK)},
        title="stage B", source_file=FIXTURE, root=tmp / "b")
    proj.run().write()
    sd = tmp / "b" / "mult_stage_b" / "scenarios" / "S"
    wrote = {q.name for q in sd.glob("*")}
    check("the disaggregation job writes the multiplier table of the table it "
          "just built",
          {"multiplier_table.csv", "multipliers.xlsx"} <= wrote,
          f"in scenarios/S/ beside the table itself. Before 2026-11-13 these "
          f"numbers existed only as prose in report.md and as keys inside "
          f"diagnostics.json: a reader who wanted the cut retyped a markdown "
          f"table")
    check("and nothing was left unaccounted for",
          not proj.multiplier_refusals,
          "a scenario that cannot have a multiplier table is named in "
          "`summary()`, never skipped quietly"
          if not proj.multiplier_refusals else
          f"{proj.multiplier_refusals}")

    body = (sd / "multiplier_table.csv").read_text()
    check("the file itself carries the split warning, not only the report",
          "DISAGGREGATED BY THIS ENGINE" in body
          and "SAME multiplier as its parent" in body,
          "with no input profile every subsector carries its parent's "
          "multiplier — the weight cancels in a_ij = Z_ij / X_j. The CSV and "
          "the report travel separately, and the first version of this had "
          "the caveat in the report while a code comment claimed the file "
          "had it too")
    check("and its data status says the cells were built, not observed",
          "DERIVED from a table this engine built" in body,
          "a multiplier of an estimated table is no firmer than the estimate, "
          "and the file says which it is")

    # The two halves must come out with the SAME multiplier, which is the
    # measured statement the warning makes. If they ever differ on a key-only
    # split, the warning is wrong and must be rewritten rather than kept.
    rows = [r for r in csv.reader((sd / "multiplier_table.csv").open(
        newline="", encoding="utf-8")) if r and not r[0].startswith("#")]
    hd, bd = rows[0], rows[1:]
    km = hd.index("output_multiplier_type_i")
    halves = [float(r[km]) for r in bd if r[0] in (f"{parent}a",
                                                   f"{parent}b")]
    check("and the two halves really do carry the identical multiplier",
          len(halves) == 2 and abs(halves[0] - halves[1]) < 1e-9,
          f"{halves[0]:.6f} and {halves[1]:.6f} — equal to the last bit, "
          f"which is what makes the warning a measurement rather than a "
          f"worry")

    # THE WARNINGS ARE ONE FUNCTION, so the report cannot drift from the file.
    check("the warnings come from one place for both",
          any("DISAGGREGATED" in w
              for w in known_wrong({"lineage": ["x -> y::S"]}))
          and not known_wrong({"lineage": []}),
          "`known_wrong` is read by the CSV writer and by the report, and "
          "returns nothing for a table nobody here built")

    # AND EVERY WARNING CAN ACTUALLY FIRE. `known_wrong` reads the lineage;
    # three other modules WRITE it. A branch whose trigger nobody writes is
    # not a warning, it is a warning-shaped silence — and the projection
    # branch was exactly that until 2026-11-13, because a projected table
    # recorded no lineage at all and its transformation model, which `M-028`
    # says a multiplier is meaningless without, printed as NOT SPECIFIED.
    #
    # So the two halves are held to each other: every lineage sentence the
    # engine writes is taken out of the source that writes it, and must set
    # off a warning or a transformation line.
    import re as _re
    src = (ROOT / "src" / "quadrium")
    written = []
    for mod, pat in (
        ("config.py", r'table\.lineage\s*=\s*list\([^)]*\)\s*\+\s*\[\s*f?"([^"]+)"'),
        ("config.py",
         r'table\.lineage\.append\(\s*' + "\\n" + r'?\s*f?"([^"]+)"'),
        ("regionalise.py", r'lineage=\[f?"([^"]+)"'),
        ("scenarios.py",
         r'lineage=list\(table\.lineage\) \+ \[\s*f?"([^"]+)"'),

    ):
        for m in _re.finditer(pat, (src / mod).read_text()):
            written.append((mod, m.group(1)))
    # f-string placeholders stand in for values; what matters is the words.
    cooked = [(mod, _re.sub(r"\{[^}]*\}", "X", t)) for mod, t in written]
    silent = [t for mod, t in cooked
              if not known_wrong({"lineage": [t]})
              and "model" not in t.lower()]
    check("every lineage sentence the engine writes sets off a warning or "
          "names a model",
          bool(cooked) and not silent,
          f"{len(cooked)} sentence(s) read out of config.py, regionalise.py "
          f"and scenarios.py, each one answered. A branch of `known_wrong` "
          f"whose trigger nobody writes is a warning-shaped silence"
          if not silent else f"written and never answered: {silent}")
    check("and a projected table now says it was projected, and by which "
          "model",
          any("projected" in t for _m, t in cooked)
          and any("model" in t.lower() for _m, t in cooked),
          "until 2026-11-13 a projected table's lineage was EMPTY: the "
          "projection was unrecorded and the transformation model printed as "
          "NOT SPECIFIED in the multiplier table's own provenance block, on a "
          "table whose model the engine had in hand")

    print("\n" + "=" * 78)
    print("""
    The arithmetic was verified in October and reached a user as prose. What
    this file checks is the difference between a formula being right and a
    figure being handed over with everything needed to read it.
""".rstrip())
    print("\n" + "=" * 78)
    if FAIL:
        print(f"{len(FAIL)} check(s) FAILED: {', '.join(FAIL)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
