"""
Every provenance sidecar carries the fields a reader of it may expect.

WHY THIS EXISTS
----------------
`data/eurostat/*.provenance` is written two ways: by `eurostat.fetch()` on a
download, and by hand when a file is brought into the repository from a probe
that ran somewhere else. On 2026-08-26 seven were written by hand with the key
`retrieved` where `fetch()` writes `retrieved_at`, and `config.py` read the
second with `rec['retrieved_at']`.

The result was not a warning. The table loaded, transformed and projected, and
then the run died with

    KeyError: 'retrieved_at'

while composing the sentence that says where the data came from. **A note about
the data killed the run that had already produced the answer.**

Two things came out of it and both are here: the seven sidecars are written the
way `fetch()` writes them, and every reader now uses `.get` with a stated
fallback, so a missing field degrades the stamp instead of ending the run.

WHAT CHANGED ON 2026-11-08, AND WHY IT IS NOT A RELAXATION
-----------------------------------------------------------
This check used ONE field list for every sidecar anywhere under `data/`, and
called it "the fields the engine reads". Two of the seven were `geo` and
`year`, and **the engine does not read either of them out of a sidecar.** It
takes both from the configuration request (`req["geo"]`, `req["year"]`) and
only ever reads five fields off a sidecar record: `dataset`, `retrieved_at`,
`sha256`, `bytes`, `url`.

So the check failed two Mendeley sidecars (`UK_MRSAM_2026_Piskin`, acquired
2026-11-06) for lacking fields nothing would have read. A check whose stated
claim is false about two of its own requirements is not a strict check; it is
a wrong one, and it would have been "fixed" one day by adding a made-up `geo`
to a dataset that has no single one.

The requirement is therefore split in two, and NEITHER half is weaker than
what was there before:

  * `READ_BY_ENGINE` — the five fields that are actually read off a record.
    Required of EVERY sidecar, in any folder. This is new: the old list was
    only ever applied where `fetch()` writes, and three of these five were
    incidental to it.
  * `FETCH_WRITES` — what `eurostat.fetch()` writes, `geo` and `year`
    included. Required of every sidecar in `data/eurostat/`, which is the one
    folder `fetch()` writes into. This is the original anti-drift guarantee,
    unchanged and at full strength: a hand-written Eurostat sidecar must still
    be indistinguishable from a fetched one.

WHY THE FIELD LIST IS DECLARED AND NOT DERIVED
-----------------------------------------------
Deriving it from the source was tried first and does not hold. `config.py`
builds one provenance sentence for two branches — cache hit and fresh
download — so the same `rec.get('url', ...)` reads a sidecar on one path and
`fetch()`'s return value on the other. A text scan cannot tell those apart,
and a derivation that quietly gets it wrong is worse than a declaration,
because it reads as a guarantee. The list is written down, each name carrying
the line that reads it.

What IS derived is a superset test: every field name read off any record
anywhere in `src/quadrium` must be declared here, in one list or the other or
as a stated fetch-only exception. That cannot prove the five are the right
five, and it does not claim to — but it fires the moment someone starts
reading a sixth, which is the drift that matters.

Run:
    python3 validators/run_provenance_sidecars.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SRC = ROOT / "src" / "quadrium"

# Read off a sidecar record by `config.py`. Every sidecar must carry these.
#   dataset       config.py:576, 617, 694
#   retrieved_at  config.py:577, 619, 697, 852, 888
#   sha256        config.py:578, 621, 700, 853, 889
#   bytes         config.py:620, 699
#   url           config.py:698
READ_BY_ENGINE = ("dataset", "retrieved_at", "sha256", "bytes", "url")

# What `eurostat.fetch()` writes (eurostat.py:186-189), minus `n_values`,
# which is a property of a JSON-stat cube rather than of the acquisition.
# Required of `data/eurostat/` only -- the one folder `fetch()` writes into.
FETCH_WRITES = ("url", "dataset", "geo", "year", "bytes", "sha256",
                "retrieved_at")
FETCH_FOLDER = "eurostat"

# Read off a FRESH `fetch()` return value and never off a sidecar on disk, so
# a sidecar that lacks it breaks nothing: config.py:670.
FETCH_ONLY = ("n_values",)

_FIELD = re.compile(r"rec(?:ord)?(?:\.get\(|\[)['\"]([a-z_0-9]+)['\"]")
FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def main() -> int:
    print(__doc__.strip().split("Run:")[0].rstrip())
    print("\n" + "=" * 78)

    files = sorted(DATA.rglob("*.provenance"))
    folders = {f.parent.name for f in files}
    check("there are sidecars to check", bool(files),
          f"{len(files)} across {len(folders)} folder(s): "
          + ", ".join(sorted(folders)))

    records, unreadable = {}, []
    for f in files:
        try:
            records[f] = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            unreadable.append((f.name, type(exc).__name__))
    check("every sidecar is readable JSON", not unreadable,
          ", ".join(f"{n}: {e}" for n, e in unreadable) or f"{len(files)} read")

    # (1) The five read fields, everywhere.
    bad = {f.name: m for f, rec in records.items()
           if (m := [k for k in READ_BY_ENGINE if k not in rec])}
    check("every sidecar carries the five fields a reader takes off it",
          not bad,
          "\n".join(f"      {n}: missing {', '.join(m)}"
                    for n, m in list(bad.items())[:8])
          or f"{', '.join(READ_BY_ENGINE)} — present in all {len(records)}")

    # (2) The fetched set, where fetch() writes. The original guarantee.
    fetched = {f: rec for f, rec in records.items()
               if f.parent.name == FETCH_FOLDER}
    bad_f = {f.name: m for f, rec in fetched.items()
             if (m := [k for k in FETCH_WRITES if k not in rec])}
    check(f"and a hand-written {FETCH_FOLDER} sidecar is indistinguishable "
          f"from a fetched one", not bad_f,
          "\n".join(f"      {n}: missing {', '.join(m)}"
                    for n, m in list(bad_f.items())[:8])
          or f"{', '.join(FETCH_WRITES)} — present in all {len(fetched)}")

    # (3) No folder quietly inherits the weaker rule without being named.
    #     A new source directory gets READ_BY_ENGINE and nothing more; that is
    #     a decision, so it is printed rather than assumed.
    other = sorted(folders - {FETCH_FOLDER})
    check("and every folder holding sidecars is accounted for by one rule",
          True,
          f"{FETCH_FOLDER}: both lists ({len(fetched)}); "
          + "; ".join(f"{d}: the five read fields "
                      f"({sum(1 for f in records if f.parent.name == d)})"
                      for d in other))

    # (4) The superset test described in the docstring.
    seen: dict[str, list[str]] = {}
    for p in sorted(SRC.glob("*.py")):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for name in _FIELD.findall(line):
                seen.setdefault(name, []).append(f"{p.name}:{i}")
    declared = set(READ_BY_ENGINE) | set(FETCH_WRITES) | set(FETCH_ONLY)
    undeclared = sorted(set(seen) - declared)
    check("and the engine reads no record field this check has not been told "
          "about", not undeclared,
          "\n".join(f"      {n}: read at {', '.join(seen[n])} — declare it in "
                    f"READ_BY_ENGINE, FETCH_WRITES or FETCH_ONLY"
                    for n in undeclared)
          or f"{len(seen)} field name(s) read, all declared: "
             f"{', '.join(sorted(seen))}")

    # (5) The hashes are the point of the sidecar; check they still hold.
    wrong = []
    for f, rec in records.items():
        data = f.with_suffix("")
        if not data.exists() or "sha256" not in rec:
            continue
        b = data.read_bytes()
        if (hashlib.sha256(b).hexdigest() != rec["sha256"]
                or len(b) != rec.get("bytes", len(b))):
            wrong.append(data.name)
    check("and the file beside it still hashes to what the sidecar records",
          not wrong, ", ".join(wrong) or f"{len(records)} verified")

    print()
    print("    A provenance stamp is a note about the data. A missing field in")
    print("    one must degrade the note, not end a run that has already")
    print("    produced its answer.")

    print("\n" + "=" * 78)
    if FAIL:
        print(f"{len(FAIL)} check(s) FAILED: {', '.join(FAIL)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
