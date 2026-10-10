"""
Every example the guide offers still runs. Nothing used to check that.

WHY THIS EXISTS
-----------------
`docs/GUIDE.md` §2 hands a reader five scripts in `examples/` and says each one
states in its docstring what is real in it and what is illustrative.
`run_public_docs.py` checks that the guide names them all. Nothing ran them.

On 2026-10-10 that cost something. Six new Eurostat cubes changed which file
`examples/es51_distribution.py` picked for its key and the script died on
`KeyError: 'H'`, while every validator in the suite stayed green, because an
example is a file the suite only ever read. It was found by a person running it
by hand.

`run_published_runs.py` closed half of it: the two examples whose runs are
published are regenerated, and their pages' figures must come out again. This
file closes the rest. The two halves do not overlap -- the published set is
imported from there rather than listed again here, so publishing a third run
moves it from this file to that one without anybody editing a list.

WHAT IS CHECKED, AND WHAT IS NOT
----------------------------------
That each example runs to exit 0 into a temporary folder and writes a report.
No figures are compared: these runs are not published, so there is no page
making a promise about them, and inventing expected numbers here would be
writing a second copy of the engine's own validators.

`REQUIRES` names what each example needs. One not listed there fails rather
than being skipped quietly, for the reason the same table gives in
`run_published_runs.py`: a skip nobody can read is not a skip.

Run:
    python3 validators/run_examples.py
"""
from __future__ import annotations

import importlib
import io
import sys
import tempfile
import time
import warnings
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_published_runs import (published, missing_inputs,     # noqa: E402
                                REQUIRES as PUBLISHED_REQUIRES)

# What each example needs before it can run at all.
#
# THE PUBLISHED ONES ARE LISTED TOO, THOUGH THIS FILE USUALLY SKIPS THEM.
# Which examples are published is read from the tree -- a run counts as
# published when its folder carries a page -- and `outputs/` is maintained by
# hand in the public repository, so a tree can legitimately hold the script and
# not the folder. On 2026-10-10 that happened: the public suite ran while
# `outputs/es51_distribution/` was still being copied across, es51 fell out of
# the published set, landed here undeclared, and this file went red over a file
# that was arriving. Declaring them here as well means that case is a skip or a
# run, never a complaint about a missing table entry.
REQUIRES: dict[str, tuple[Path, ...]] = {
    "synthetic_accommodation": (),
    "uk_hospitality": (ROOT / "UK_IOAT_2023_domestic_ixi.xlsx",),
    "es_hosteleria": (ROOT / "data" / "ine" / "cne_tio_22.xlsx",),
}
FAIL: list[str] = []
NOTHING_CHECKED = 3


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def main() -> int:
    warnings.filterwarnings("ignore")
    print(__doc__.strip().split("Run:")[0].rstrip())
    print("\n" + "=" * 78 + "\n")

    covered = {run.name for run in published()}
    scripts = [p for p in sorted((ROOT / "examples").glob("*.py"))
               if p.stem not in covered]
    print(f"    {len(covered)} example(s) are run by run_published_runs.py "
          f"({', '.join(sorted(covered))}); {len(scripts)} here.\n")

    ran = 0
    for script in scripts:
        name = script.stem
        # A published example is normally skipped above, but a tree can hold
        # the script and not the published folder -- `outputs/` is maintained
        # by hand in the public repository, and on 2026-10-10 a copy of one
        # arrived after the suite had started and then turned out to be
        # gitignored. In that case the example lands here, and what it needs is
        # whatever run_published_runs.py says it needs: that table knows the
        # archive arrives in either of two forms, which this one has no reason
        # to learn twice.
        theirs = name in PUBLISHED_REQUIRES
        declared = theirs or name in REQUIRES
        check(f"{name}: what it needs before it can run is declared", declared,
              ("declared in run_published_runs.py, which usually runs it"
               if theirs else
               ", ".join(p.name for p in REQUIRES.get(name, ())) or "nothing")
              if declared else
              "add it to REQUIRES in this file, or to run_published_runs.py if "
              "its run is published")
        if not declared:
            continue

        gaps = (missing_inputs(name) if theirs else
                [str(p.relative_to(ROOT)) for p in REQUIRES[name]
                 if not p.exists()])
        if gaps:
            print(f"    --   not run here: {', '.join(gaps)} is not in this "
                  f"tree")
            continue

        module = importlib.import_module(name)
        check(f"{name}: can be run into another folder", hasattr(module, "OUT"),
              "it takes OUT" if hasattr(module, "OUT") else
              "it writes to a fixed path, so this check would write over "
              "whatever is in outputs/")
        if not hasattr(module, "OUT"):
            continue

        with tempfile.TemporaryDirectory() as tmp:
            module.OUT = Path(tmp)
            started = time.time()
            try:
                with redirect_stdout(io.StringIO()):
                    code = module.main()
                failed = ""
            except BaseException as exc:                       # noqa: BLE001
                code, failed = 1, f"{type(exc).__name__}: {exc}"
            took = time.time() - started
            reports = sorted(Path(tmp).glob("*/report.md"))
            check(f"{name}: runs end to end and writes a report",
                  code == 0 and bool(reports),
                  f"exit 0, {took:.0f} s, "
                  f"{len(reports[0].read_text().splitlines())} lines"
                  if code == 0 and reports else failed or f"exit {code}")
            if code == 0 and reports:
                ran += 1

    print("\n" + "=" * 78)
    if FAIL:
        print(f"{len(FAIL)} check(s) FAILED: {', '.join(FAIL)}")
        return 1
    if not ran:
        print("Nothing was checked: no example had its inputs here.")
        return NOTHING_CHECKED
    print(f"All checks passed. {ran} example(s) ran.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
