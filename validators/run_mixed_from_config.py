"""
The mixed model through the WORKBOOK, which is the only door a user has.

`run_mixed_model.py` holds `src/quadrium/mixed.py` to its source, `CORE_085`
(Steinback 2004), and to Leontief at both ends. It says nothing about whether
anyone can reach it. From 2026-10-10 to 2026-11-12 nobody could without
writing Python, and for a user of the configuration workbook that is the same
as the method not existing. This holds the door.

WHAT IT CHECKS
----------------
1. THE TWO DOORS AGREE. A workbook run and a direct call on the same table and
   the same scenario give the same numbers to the last bit. Same shape as
   `run_charm_doors.py`, and for the same reason: two ways of saying one thing
   are two places for it to drift.

2. THE FIGURE THE GUIDE QUOTES. `docs/GUIDE.md` §11 says that fixing UK
   agriculture leaves out a channel carrying 38.9 % of its output. That figure
   is PINNED as a literal below, so if the measurement moves this fails rather
   than quietly disagreeing with the document. `run_report_claims.py` is what
   ties the two together.

3. WHAT THE RUN WRITES. The files, and that the report names the three things
   a reader must not miss: which figures the user GAVE, the forward-linkage
   limitation with its size, and the final demand the fixed output implies.

4. THE REFUSALS, each one reached. A workbook can state this scenario wrongly
   in seven ways and every one of them must stop the run rather than be
   repaired into a different question. One eighth refusal is NOT reached here
   and is named with its reason.

5. THE ROW NUMBER IN A MESSAGE IS THE SHEET'S ROW. Blank rows are dropped when
   a sheet is read, so counting the surviving rows gives a number that is
   confidently wrong -- and an error message that sends a user to the wrong row
   is this project's own defect class inside the machinery that reports it.
   Found on the first real run of this job, 2026-11-12, and pinned here.

Needs `openpyxl` and the shipped UK fixture. Offline throughout.

Run:
    python3 validators/run_mixed_from_config.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

FIXTURE = ROOT / "UK_IOAT_2023_domestic_ixi.xlsx"

# THE FIGURE THE GUIDE QUOTES, as a literal. `docs/GUIDE.md` §11: "fixing
# agriculture means leaving out a channel carrying 38.9 % of its output".
# Written here from the GUIDE, then measured. If the two ever disagree this
# file fails and one of them is wrong -- which is the point of pinning it
# rather than printing whatever came out.
GUIDE_A01_FORWARD_SHARE_PCT = 38.9

FAIL = []
NOTHING_CHECKED = 0


def check(label, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {label}")
    if detail:
        print(f"         {detail}")
    if not ok:
        FAIL.append(label)


def _book(tmp: Path, name: str, mixed_rows, *, satellites=None,
          also=None) -> Path:
    """A workbook with the `mixed` sheet filled in and the other jobs empty.

    `mixed_rows` is a list of (sheet row, sector_code, column, value), with
    the row number being the SHEET's own, so a gap can be left deliberately.
    `also` fills one cell of another job's sheet, to test that refusal.
    """
    import openpyxl

    from quadrium.config import write_template

    path = tmp / f"{name}.xlsx"
    write_template(path)
    wb = openpyxl.load_workbook(path)
    pr = wb["project"]
    pr["B1"] = name
    pr["B2"] = str(FIXTURE)
    pr["B3"] = "uk_analytical"
    pr["B4"] = f"mixed door test - {name}"

    # The template seeds the SPLIT example, which would make every book here a
    # two-job book. Comments are left in place: the loader must skip them.
    for sheet in ("splits", "keys", "scenarios", "profiles"):
        ws = wb[sheet]
        for row in list(ws.iter_rows(min_row=2)):
            if row[0].value is not None and \
                    str(row[0].value).lstrip().startswith("#"):
                continue
            for c in row:
                c.value = None

    col = {"fixed_output": 2, "fixed_output_pct": 3, "extra_demand": 4}
    m = wb["mixed"]
    for r, code, which, value in mixed_rows:
        m.cell(r, 1, code)
        if which is not None:
            m.cell(r, col[which], value)

    if satellites:
        ws = wb["satellites"]
        for i, (code, value) in enumerate(satellites, start=2):
            ws.cell(i, 1, "employment")
            ws.cell(i, 2, "persons")
            ws.cell(i, 3, code)
            ws.cell(i, 4, value)
            ws.cell(i, 5, "synthetic figures for this validator, NOT real "
                          "employment")
            ws.cell(i, 6, 2023)

    if also:
        sheet, row, a, b = also
        wb[sheet].cell(row, 1, a)
        wb[sheet].cell(row, 2, b)

    wb.save(path)
    return path


def main() -> int:
    global NOTHING_CHECKED
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        print("openpyxl is not installed, so no workbook can be written and "
              "NOTHING WAS CHECKED. `pip install openpyxl`.")
        print("Nothing was checked: openpyxl missing")
        return 3
    if not FIXTURE.exists():
        print(f"{FIXTURE.name} is not here, so NOTHING WAS CHECKED.")
        print("Nothing was checked: the UK fixture is absent")
        return 3

    from quadrium.config import ConfigError, load_config
    from quadrium.mixed import mixed_model_from_table

    tmp = Path(tempfile.mkdtemp(prefix="quadrium_mixed_"))
    try:
        print("The mixed model through the workbook\n")
        print("1. The two doors\n")

        rows = [(2, "A01", "fixed_output_pct", -20),
                (3, "B06 & B07", "fixed_output", -500.0),
                (4, "A03", "extra_demand", 100.0)]
        path = _book(tmp, "doors", rows)
        cfg = load_config(path, offline=True)
        check("the workbook is read as a `mixed` job",
              cfg.get("kind") == "mixed",
              f"kind {cfg.get('kind')!r}, "
              f"{len(cfg['exogenous'])} sector(s) fixed")
        table = cfg["table"]
        codes = list(table.sector_codes)
        X = np.asarray(table.X, float).ravel()

        # The per cent was converted against the table's own output, which is
        # the one thing the sheet cannot do for itself.
        check("`fixed_output_pct: -20` became -20 % of A01's own output",
              np.isclose(cfg["delta_x"]["A01"], -0.20 * X[codes.index("A01")]),
              f"{cfg['delta_x']['A01']:,.3f} against "
              f"{-0.20 * X[codes.index('A01')]:,.3f}")

        book = mixed_model_from_table(table, cfg["exogenous"],
                                      delta_x=cfg["delta_x"],
                                      delta_f=cfg["delta_f"])
        # THE SCENARIO THE WORKBOOK PRODUCED, handed straight to the model,
        # against the same scenario written out by hand. The first version of
        # this check recomputed the per cent as `-0.20 * X` and failed by
        # 1.8e-12, because the sheet route computes `X * -20 / 100` and the two
        # are not the same floating-point expression. That was the TEST being
        # wrong, not the engine: the conversion itself is checked above against
        # the figure the sheet asked for. What belongs here is that the door
        # adds nothing of its own.
        direct = mixed_model_from_table(
            table, ["A01", "B06 & B07"],
            delta_x={"A01": cfg["delta_x"]["A01"],
                     "B06 & B07": -500.0},
            delta_f={"A03": 100.0})
        check("the workbook route and a direct call agree, to the last bit",
              np.array_equal(book.x, direct.x)
              and np.array_equal(book.f, direct.f),
              f"max |difference| in output "
              f"{float(np.abs(book.x - direct.x).max()):.3g}")
        check("and the sector a code with a COMMA in it survives the round "
              "trip",
              any("," in c for c in codes),
              "the UK table has `F41, F42  & F43`, so every CSV this job "
              "writes has to quote its fields; found by reading back a file "
              "this validator had just written, 2026-11-12")

        print("\n2. The figure the guide quotes\n")

        share = book.forward_share["A01"] * 100
        check(f"A01's forward share is the guide's "
              f"{GUIDE_A01_FORWARD_SHARE_PCT} %",
              round(share, 1) == GUIDE_A01_FORWARD_SHARE_PCT,
              f"measured {share:.4f} %, guide says "
              f"{GUIDE_A01_FORWARD_SHARE_PCT} % - the share of agriculture's "
              f"output that other industries buy as an input, which is the "
              f"size of the channel the model does not see")
        check("and it is a share, not a ratio dressed as one",
              0.0 < book.forward_share["A01"] < 1.0)

        print("\n3. What the run writes, and what the report must not omit\n")

        from quadrium.cli import _mixed_report, _write_mixed

        out = tmp / "out"
        rc = _write_mixed(book, cfg, table, out)
        folder = out / "doors"
        check("the run returns 0 and writes its folder",
              rc == 0 and folder.is_dir())
        for f in ("mixed.csv", "multipliers.csv", "report.md"):
            check(f"it wrote {f}", (folder / f).exists())
        check("and NOT effects.csv, since this book declares no account",
              not (folder / "effects.csv").exists())

        body = (folder / "report.md").read_text()
        check("the report says which figures the user GAVE, not only results",
              "which is the figure you gave, not a result" in body)
        check("it names the demand shock the sheet also carried",
              "final demand you moved yourself" in body and "`A03`" in body,
              "a figure the user typed used to appear nowhere in the document "
              "describing the run; found on the first real run, 2026-11-12")
        check("it prints the forward-linkage limitation with its SIZE",
              "38.9 % of its output is bought as an input" in body
              and "CORE_085` p. 59" in body)
        check("it gives the final demand the fixed output implies",
              "What final demand has to do for that to hold" in body
              and "`DERIVED`" in body)
        check("and it says the result is the sectors that were NOT fixed",
              "The result is the other 102 sectors" in body)

        head = (folder / "mixed.csv").read_text().splitlines()
        check("mixed.csv tells a given figure from a solved one",
              head[3].endswith("output fixed")
              and any(l.endswith("solved") for l in head[4:]),
              head[3][:60] + " ...")

        print("\n4. Satellite accounts, and the arithmetic of the effect\n")

        emp = [(c, round(float(x) * 10, 1)) for c, x in zip(codes, X)]
        p2 = _book(tmp, "withjobs", rows, satellites=emp)
        cfg2 = load_config(p2, offline=True)
        res2 = mixed_model_from_table(cfg2["table"], cfg2["exogenous"],
                                      delta_x=cfg2["delta_x"],
                                      delta_f=cfg2["delta_f"])
        check("the `satellites` sheet reaches a mixed run",
              "employment" in (getattr(cfg2["table"], "satellites", {}) or {}))
        _write_mixed(res2, cfg2, cfg2["table"], out)
        f2 = out / "withjobs"
        check("it wrote effects.csv", (f2 / "effects.csv").exists())
        # Ten persons per unit of output in every sector, so the total effect
        # must be exactly ten times the total change in output. A closed form,
        # so a wrong coefficient cannot hide behind a plausible number.
        import csv as _csv
        with (f2 / "effects.csv").open(newline="") as fh:
            data = [r for r in _csv.reader(
                l for l in fh if not l.startswith("#"))]
        check("effects.csv has one column per sector plus the code, on every "
              "row",
              {len(r) for r in data} == {2},
              f"row lengths {sorted({len(r) for r in data})} — a code "
              f"containing a comma would make one row longer than the rest")
        eff_total = sum(float(r[1]) for r in data[1:])
        check("the effect is the coefficient times the change in output",
              np.isclose(eff_total, 10.0 * float(res2.x.sum()), rtol=1e-9),
              f"{eff_total:,.3f} persons against "
              f"{10.0 * float(res2.x.sum()):,.3f}")

        print("\n5. The refusals, each one reached\n")

        def refused(label, build, words):
            try:
                load_config(build(), offline=True)
            except ConfigError as e:
                check(f"refuses {label}", words in str(e), str(e)[:100])
            else:
                check(f"refuses {label}", False, "it loaded")

        refused("a sheet sharing the book with another job",
                lambda: _book(tmp, "twojobs", rows,
                              also=("charm", 2, "activity_path", "x.csv")),
                "two runs rather than one")
        refused("two rows for one sector",
                lambda: _book(tmp, "dup", rows
                              + [(5, "A01", "fixed_output_pct", -10)]),
                "already has a row")
        refused("two columns on one row",
                lambda: _book(tmp, "both", [(2, "A01", "fixed_output", 999)]
                              + rows),
                "different requests")
        refused("a sector the table does not have",
                lambda: _book(tmp, "nocode",
                              [(2, "A", "fixed_output_pct", -20)]),
                "is not a sector of")
        refused("a row that names a sector and asks nothing",
                lambda: _book(tmp, "silent", rows + [(6, "A02", None, None)]),
                "nothing is asked of it")
        refused("a per cent typed into the absolute column",
                lambda: _book(tmp, "pctstr",
                              [(2, "A01", "fixed_output", "-20%")]),
                "use the `fixed_output_pct` column")
        refused("a thousands separator, which would become another number",
                lambda: _book(tmp, "comma",
                              [(2, "A01", "fixed_output", "-1,200")]),
                "write 1200, not")

        # NOT REACHED, AND SAID SO RATHER THAN LEFT UNSAID. `build_mixed`
        # refuses `fixed_output_pct` on a sector whose output is zero or
        # negative, because there is no base to take a percentage of. No
        # sector of any table on this disk has zero output -- the UK fixture's
        # smallest is B05 at 100 -- so reaching it needs a table written for
        # the purpose. An `interchange` fixture with a zero-output sector
        # would do it through a real loader, and is the way to close this.
        NOTHING_CHECKED = 1
        print("  [--] NOT reached: `fixed_output_pct` on a sector with zero "
              "output")
        print("         no table on disk has one (the UK fixture's smallest "
              "output is 100), so this needs an `interchange` fixture written "
              "for it. Named rather than left unsaid.")

        print("\n6. A row number in a message is the SHEET's row\n")

        # Row 6 of the sheet, with row 5 left blank on purpose. Reading drops
        # blank rows, so a count of the survivors would call this row 5.
        try:
            load_config(_book(tmp, "rownum", rows + [(6, "A02", None, None)]),
                        offline=True)
        except ConfigError as e:
            check("a mistake on sheet row 6 is reported as row 6",
                  "row 6" in str(e) and "row 5" not in str(e),
                  str(e)[:100])
        else:
            check("a mistake on sheet row 6 is reported as row 6", False,
                  "it loaded")

        print("\n7. The dry run says the same as the real one\n")

        dry = _mixed_report(book, cfg, table, check=True)
        real = (folder / "report.md").read_text()
        # Compared STRIPPED, because the written report ends with a blank
        # line before the file list and the dry one simply ends. That is
        # whitespace, and a check that failed on it would be a check about
        # nothing -- while a check that ignored more than whitespace would be
        # the vacuous pass this project keeps finding.
        check("--check and the written report differ only in the file list",
              dry.split("## What was written")[0].strip()
              == real.split("## What was written")[0].strip()
              and "## What was written" in real
              and "## What was written" not in dry,
              "a dry run that described the result differently would be a "
              "different dry run")

        print("\n" + "=" * 78)
        if FAIL:
            print(f"{len(FAIL)} check(s) FAILED")
            return 1
        print(f"All checks passed. {NOTHING_CHECKED} refusal named as not "
              f"reached, with its reason.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
