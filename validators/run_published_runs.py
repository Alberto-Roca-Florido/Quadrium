"""
Every published run still regenerates, and its page still describes what comes out.

WHY THIS EXISTS
-----------------
Two runs are published in full -- `outputs/uk_food_beverage/` and
`outputs/es51_distribution/` -- and each has a page saying what it was and a
`report.md` that is the engine's verbatim output. `run_public_docs.py` checks
that every figure a page quotes is in the report lying beside it. That catches a
page drifting from its report. It cannot catch the report drifting from the
engine, because both files are already in the tree and neither is produced
again.

On 2026-10-10 that mattered. Six new Eurostat cubes changed which file
`examples/es51_distribution.py` picked for its key, and the script died on
`KeyError: 'H'` -- while its page, its report and `run_public_docs.py` all
stayed green, because nothing ran the script. The page says "regenerate it with
`python3 examples/es51_distribution.py`", and that sentence had become false.

WHAT IS CHECKED
-----------------
For each published run, the script named by its folder is run into a temporary
directory -- never over the published folder -- and then every figure the page
quotes must appear in the REGENERATED report. Not a byte comparison: a report
carries the time it was written, so demanding identity would fail every day.
What must hold is that the numbers a reader is told to trust are produced again.

A run whose inputs are not in this tree is said to be unrun, not passed: `REQUIRES`
below names what each one needs, and a published run missing from that table
fails rather than being quietly skipped -- otherwise a skip means nothing.

WHERE THE RUNS ARE
--------------------
`outputs/uk_food_beverage/` lives in the public tree and `outputs/es51_distribution/`
in this one, until the next release carries the second across. Both are looked
for in both places, the same way `run_public_docs.py` finds the README that
only the public tree holds. A check that skips half its subject is the vacuous
pass this project removes validators for.

Run:
    python3 validators/run_published_runs.py
"""
from __future__ import annotations

import importlib
import io
import re
import sys
import tempfile
import time
import warnings
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))

MRIO = ROOT / "data" / "mrio"
EUROSTAT = ROOT / "data" / "eurostat"
# What each published run needs before it can be run at all. A run not named
# here fails: an unexplained skip is indistinguishable from a check nobody
# wrote.
REQUIRES: dict[str, tuple[Path, ...]] = {
    "uk_food_beverage": (ROOT / "UK_IOAT_2023_domestic_ixi.xlsx",),
    "es51_distribution": (
        EUROSTAT / "sbs_r_nuts06_r2_ES51_2018_V13320.json",
        EUROSTAT / "sbs_r_nuts06_r2_ES51_2018_V16110.json",
    ),
}
# The archive is gitignored and either form of it will do.
ARCHIVE_EITHER = {"es51_distribution": (MRIO / "_mrio2018_cache.npz",
                                        MRIO / "MRIO_2018_272regions.xlsx")}
# The same pattern run_public_docs.py reads a page's figures with.
FIGURE = re.compile(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d+\.\d+\b|\b\d{2,}\b")
FAIL: list[str] = []
NOTHING_CHECKED = 3


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def published() -> list[Path]:
    """The runs that are published, in this tree and in its sibling.

    A `report.md` is not enough. This tree's `outputs/` is where the engine
    writes while somebody works -- six folders today, including one whose
    script no longer exists -- and holding those to the standard of a published
    artefact would fail on working files nobody promised anything about.

    What makes a run published is the page beside it: `README.md` is written by
    hand, on purpose, and it is the thing that tells a reader the run can be
    regenerated. So a page is the test, and it also resolves the two trees --
    `uk_food_beverage` exists in both, and only the public copy carries one.
    """
    found: dict[str, Path] = {}
    for base in (ROOT / "outputs",
                 ROOT.parent / "Quadrium" / "outputs"):
        if not base.is_dir():
            continue
        for run in sorted(base.iterdir()):
            if ((run / "report.md").exists() and (run / "README.md").exists()
                    and run.name not in found):
                found[run.name] = run
    return list(found.values())


def missing_inputs(name: str) -> list[str]:
    gaps = [str(p.relative_to(ROOT)) for p in REQUIRES.get(name, ())
            if not p.exists()]
    either = ARCHIVE_EITHER.get(name)
    if either and not any(p.exists() for p in either):
        gaps.append(" or ".join(p.name for p in either))
    return gaps


def main() -> int:
    warnings.filterwarnings("ignore")
    print(__doc__.strip().split("Run:")[0].rstrip())
    print("\n" + "=" * 78 + "\n")

    runs = published()
    if not runs:
        print("    -- no finished run is published in either tree.")
        print("\n" + "=" * 78)
        print("Nothing was checked: there is no published run here.")
        return NOTHING_CHECKED

    ran = 0
    for run in runs:
        script = ROOT / "examples" / f"{run.name}.py"
        page = run / "README.md"
        print(f"  {run.name}  ({run.parent.parent.name})")
        check(f"    {run.name} is produced by a script of its own name",
              script.exists(),
              f"examples/{script.name}" if script.exists() else
              f"no examples/{script.name}; its page tells a reader to "
              f"regenerate the run with a file that is not there")
        if not script.exists():
            continue

        declared = run.name in REQUIRES
        check(f"    and what it needs before it can run is declared",
              declared,
              ", ".join(p.name for p in REQUIRES.get(run.name, ()))
              if declared else
              "add it to REQUIRES in this file: a skip nobody can read is not "
              "a skip")
        if not declared:
            continue

        gaps = missing_inputs(run.name)
        if gaps:
            print(f"    --   not run here: {', '.join(gaps)} is not in this "
                  f"tree, so its figures were not regenerated")
            continue

        module = importlib.import_module(run.name)
        check(f"    and it can be run into another folder",
              hasattr(module, "OUT"),
              "it takes OUT" if hasattr(module, "OUT") else
              "it writes to a fixed path, so this check would overwrite the "
              "published run it is checking")
        if not hasattr(module, "OUT"):
            continue

        with tempfile.TemporaryDirectory() as tmp:
            module.OUT = Path(tmp)
            started = time.time()
            try:
                with redirect_stdout(io.StringIO()):
                    code = module.main()
                failed = ""
            except BaseException as exc:                    # noqa: BLE001
                code, failed = 1, f"{type(exc).__name__}: {exc}"
            took = time.time() - started
            fresh = Path(tmp) / run.name / "report.md"
            check(f"    runs end to end and writes a report",
                  code == 0 and fresh.exists(),
                  f"exit 0, {took:.0f} s, "
                  f"{len(fresh.read_text().splitlines())} lines"
                  if fresh.exists() and code == 0 else
                  failed or f"exit {code}")
            if not (fresh.exists() and code == 0):
                continue
            ran += 1
            regenerated = fresh.read_text()

        quoted = sorted(set(FIGURE.findall(page.read_text()))) if page.exists() else []
        absent = [q for q in quoted if q not in regenerated]
        check(f"    and every figure its page quotes comes out again",
              bool(quoted) and not absent,
              f"{len(quoted)} figures regenerated" if quoted and not absent
              else f"not in the new report: {', '.join(absent[:6])}"
              if quoted else "its page quotes no figures at all, or is missing")
        print()

    print("=" * 78)
    if FAIL:
        print(f"{len(FAIL)} check(s) FAILED: {', '.join(FAIL)}")
        return 1
    if not ran:
        print("Nothing was checked: no published run had its inputs here.")
        return NOTHING_CHECKED
    print(f"All checks passed. {ran} published run(s) regenerated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
