"""
The key comes from the cube for this region alone, and says so when it cannot.

WHY THIS EXISTS
-----------------
On 2026-10-10 `measure_key_disagreement.py` put six cubes of
`sbs_r_nuts06_r2` into `data/eurostat/` -- one NACE section each, every region
in them. `examples/es51_distribution.py` chose its key with `sources[0]` after
filtering the catalogue on the indicator and the region, which had meant "this
region's file" for exactly as long as one file matched. The new cubes match the
same filter, because they carry 536 regions and ES51 is one of them. The first
match became a single-section file and the example died on `KeyError: 'H'` --
in the run whose published page says "regenerate it with
`python3 examples/es51_distribution.py`".

So the selection is no longer "the first that matches". It is the cube that
covers this region and nothing else, and several would be ambiguity, refused by
name rather than settled by sort order.

WHAT IS CHECKED
-----------------
That the ambiguity is real -- several cubes still match the old filter, so this
is not a hypothetical -- that exactly one covers ES51 alone, that an indicator
with no cube at all is refused with a sentence rather than a `KeyError`, and
that the two keys read the numbers the published page quotes, to the cent.

The example itself is run end to end by `run_published_runs.py`, which
regenerates every published run and requires its page's figures to come out
again. This file is about the one line inside it that broke.

Run:
    python3 validators/run_es51_key.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))

EUROSTAT = ROOT / "data" / "eurostat"
CUBES = ("sbs_r_nuts06_r2_ES51_2018_V13320.json",
         "sbs_r_nuts06_r2_ES51_2018_V16110.json")
WAGES_PUBLISHED = {"G": 12722.6, "H": 4049.8, "I": 3521.6}
HEADS_PUBLISHED = {"G": 581147.0, "H": 168958.0, "I": 253349.0}
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

    missing = [c for c in CUBES if not (EUROSTAT / c).exists()]
    if missing:
        print(f"    -- the cached Eurostat cubes for ES51 are not in this "
              f"tree: {', '.join(missing)}. They are two requests, and the "
              f"example's own refusal prints them.")
        print("\n" + "=" * 78)
        print("Nothing was checked: the data this file measures is not here.")
        return NOTHING_CHECKED

    import es51_distribution as ex

    loose = [s for s in ex.sources() if s.kind == "proxy"
             and ex.WAGES in s.source_id and ex.REGION in s.geos]
    strict = [s for s in loose if list(s.geos) == [ex.REGION]]
    check("more than one cached cube matches the filter that used to pick the "
          "key", len(loose) > 1,
          f"{len(loose)} sources carry {ex.WAGES} and cover {ex.REGION}, so "
          f"'the first match' is a choice and not a lookup")
    check("and exactly one of them covers this region alone", len(strict) == 1,
          strict[0].source_id if len(strict) == 1 else
          f"{len(strict)} candidates: "
          f"{', '.join(s.source_id for s in strict)}")

    try:
        ex.sbs_key("v00000")
        refused = ""
    except SystemExit as exc:
        refused = str(exc)
    except Exception as exc:                        # noqa: BLE001
        refused = f"{type(exc).__name__}: {exc}"
    check("an indicator with no cube is refused by name, not by KeyError",
          refused.startswith("no cached Eurostat file"),
          refused.splitlines()[0] if refused else "it did not refuse at all")

    check("the wage key reads what the published page quotes",
          ex.sbs_key(ex.WAGES) == WAGES_PUBLISHED,
          ", ".join(f"{k} {v:,.1f}" for k, v in WAGES_PUBLISHED.items())
          + " million")
    check("and the headcount key too",
          ex.sbs_key(ex.HEADCOUNT) == HEADS_PUBLISHED,
          ", ".join(f"{k} {v:,.0f}" for k, v in HEADS_PUBLISHED.items())
          + " persons")

    print("\n" + "=" * 78)
    if FAIL:
        print(f"{len(FAIL)} check(s) FAILED: {', '.join(FAIL)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
