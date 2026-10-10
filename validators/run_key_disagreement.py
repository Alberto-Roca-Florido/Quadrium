"""
One region said 7.8 points. Two hundred and seventy-eight say it was ordinary.

WHAT THIS ANSWERS
-------------------
The published run in `outputs/es51_distribution/` divides Catalonia's `G-I`
into trade, transport and hospitality, and the finding its page leads with is
not the split: it is that the only two keys Eurostat publishes at NUTS-2 --
wages and persons employed -- disagree about hospitality by 7.9 percentage
points. A reader is entitled to ask whether that is Catalonia being odd. If it
were, the page would be quoting an anecdote as a lesson.

`sbs_r_nuts06_r2` publishes both indicators for sections G, H and I separately
for every region it covers, so the same split can be done twice everywhere and
the two answers compared. Across **278 regions** the worse of the three
sections moves by a median **8.8 points**, p10 3.4 and p90 14.6, and in exactly
**one** region do the two keys agree to within a point. Catalonia's 7.9 sits at
the 42nd percentile: the published example is a quiet case, not a loud one.

WHAT IS COMPARED
------------------
Shares, not levels: each key is turned into the three shares it would give, and
the gap is the distance between them in percentage points. A key that is a
constant multiple of another gives identical shares, and the last check below
proves this measurement has that property rather than asserting it.

Neither key is output. Eurostat publishes no turnover and no value added at
NUTS-2 for these sections, which is why a cost stands in for a size at all. So
none of this says which key is right. It says what is at stake in choosing, and
that nothing at this level of detail decides it for you -- which is the reason
`AllocationKey` records a second key instead of ranking the two.

AND WHETHER YOUR REGION CAN TAKE EITHER KEY
---------------------------------------------
The distribution is over the regions Eurostat covers. The question a user of
this engine has is narrower: can I do this for MY region of the European
archive? Both keys reach **231 of the archive's 268 regions with data**. Of the
37 they do not reach, 8 are Romania, where Eurostat publishes nothing for these
sections, and 29 are a NUTS vintage mismatch -- the archive codes France and
Poland in an older vintage than this dataset and Croatia in a newer one, and the key lookup
matches codes literally. It does not have to stay that way: the project holds
Eurostat's own correspondence tables in `data/nuts/`, and `run_mrio_nuts_join.py`
composes them to resolve 36 of the archive's codes already -- 26 from NUTS 2013
to 2016, 9 from 2010 to 2013, one left unresolved. Nothing has yet pointed that
machinery at the key.

Matching by code is also where the archive's own mislabelling turns dangerous
rather than merely wrong. Of the eighteen labels `MRIO_RELABEL` corrects, **8
name a region Eurostat also publishes**: EL30, EL41, EL42 and EL43, whose rows
belong to EL62 to EL65, and the four Finnish codes the deposit shifts by one.
Reading those labels as printed would not fail. It would hand another region's
wage bill to the split and produce a result that looks fine. The other ten
would simply not be found.

THE RECORD, AND WHY IT IS CHECKED RATHER THAN TRUSTED
------------------------------------------------------
`data/_key_disagreement.json` is written by
`library/tools/measure_key_disagreement.py`, which downloads. This file
recomputes the whole distribution from the six cubes in the tree, with its own
code, and fails if the record disagrees with them. A record is a claim about
files; if the files are re-downloaded and Eurostat has revised them, the claim
goes stale silently, and the figures above are quoted in a page a stranger
reads.

Run:
    python3 validators/run_key_disagreement.py
"""
from __future__ import annotations

import hashlib
import json
import re
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
DATA = ROOT / "data" / "eurostat"
RECORD = ROOT / "data" / "_key_disagreement.json"
YEAR = 2018
SECTIONS = ("G", "H", "I")
WAGES, PERSONS = "V13320", "V16110"
NUTS2 = re.compile(r"^[A-Z]{2}[0-9A-Z]{2}$")
FAIL: list[str] = []

# Exit 3, like the archive validators: check.sh counts it as SKIPPED rather
# than as a pass, because a run that opened no file measured nothing.
NOTHING_CHECKED = 3


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def cube_path(indic: str, nace: str) -> Path:
    return DATA / f"sbs_r_nuts06_r2_ALL_{YEAR}_{indic}_{nace}.json"


def values(indic: str, nace: str) -> dict[str, float]:
    """Geo code to value, for the one year and one section the file holds."""
    doc = json.loads(cube_path(indic, nace).read_text())
    at = {v: k for k, v in doc["dimension"]["geo"]["category"]["index"].items()}
    return {at[int(i)]: v for i, v in doc["value"].items() if v is not None}


def distribution(cubes: dict[tuple[str, str], dict[str, float]],
                 scale: float = 1.0) -> tuple[list[dict], dict[str, int]]:
    """Recomputed here, not imported: an independent arithmetic of the same files.

    `scale` multiplies one key everywhere. Shares cannot move, and the last
    check uses that.
    """
    seen = sorted({g for c in cubes.values() for g in c if NUTS2.match(g)})
    rows, dropped = [], {"extra_regio": 0, "incomplete": 0, "zero_total": 0}
    for geo in seen:
        if geo.endswith("ZZ"):
            dropped["extra_regio"] += 1
            continue
        got = {(i, n): cubes[(i, n)].get(geo)
               for i in (WAGES, PERSONS) for n in SECTIONS}
        if any(v is None for v in got.values()):
            dropped["incomplete"] += 1
            continue
        shares, bad = {}, False
        for i in (WAGES, PERSONS):
            factor = scale if i == WAGES else 1.0
            total = sum(got[(i, n)] * factor for n in SECTIONS)
            if total <= 0:
                bad = True
                break
            shares[i] = {n: got[(i, n)] * factor / total for n in SECTIONS}
        if bad:
            dropped["zero_total"] += 1
            continue
        gaps = {n: abs(shares[WAGES][n] - shares[PERSONS][n]) * 100
                for n in SECTIONS}
        worst = max(gaps, key=lambda n: gaps[n])
        rows.append({"geo": geo, "worst_section": worst,
                     "worst_pp": round(gaps[worst], 2),
                     "gap_pp": {n: round(gaps[n], 2) for n in SECTIONS}})
    return rows, dropped


def spread(vals: list[float]) -> dict:
    q = st.quantiles(vals, n=10)
    return {"min": round(min(vals), 2), "p10": round(q[0], 2),
            "median": round(st.median(vals), 2), "p90": round(q[8], 2),
            "max": round(max(vals), 2)}


def main() -> int:
    print(__doc__.strip().split("Run:")[0].rstrip())
    print("\n" + "=" * 78 + "\n")

    # NO DATA IS A SKIP, NOT A FAILURE.
    # The six cubes are data files, and this ran red in a tree that simply did
    # not have them yet -- which is every fresh clone of the public repository
    # until `data/eurostat/` is copied across. The archive validators settled
    # this convention: exit 3, counted as SKIPPED by check.sh, because a file
    # that measured nothing must not report either a pass or a fault.
    missing = [cube_path(i, n).name for i in (WAGES, PERSONS) for n in SECTIONS
               if not cube_path(i, n).exists()]
    if missing or not RECORD.exists():
        how = ("none of the six cubes are in this tree" if len(missing) == 6
               else f"{len(missing)} of the six cubes are not in this tree")
        print(f"    -- {how}"
              f"{'' if RECORD.exists() else ', and neither is the record'}. "
              f"They are six requests: "
              f"library/tools/measure_key_disagreement.py takes them.")
        print("\n" + "=" * 78)
        print("Nothing was checked: the data this file measures is not here.")
        return NOTHING_CHECKED
    check("the six cubes the record describes are in the tree", True,
          "6 of 6 present")

    # THE FILES ARE THE ONES THE RECORD WAS TAKEN FROM.
    # Each cube has a provenance sidecar with the SHA-256 of what arrived. A
    # re-download that Eurostat has revised changes the hash, and then every
    # figure in this docstring is about a file that no longer exists.
    bad_hash = []
    for i in (WAGES, PERSONS):
        for n in SECTIONS:
            p = cube_path(i, n)
            said = json.loads(Path(f"{p}.provenance").read_text())["sha256"]
            got = hashlib.sha256(p.read_bytes()).hexdigest()
            if said != got:
                bad_hash.append(p.name)
    check("and each is the file its provenance records", not bad_hash,
          "six SHA-256 digests match their sidecars" if not bad_hash else
          f"changed since download: {', '.join(bad_hash)}")

    cubes = {(i, n): values(i, n) for i in (WAGES, PERSONS) for n in SECTIONS}
    rows, dropped = distribution(cubes)
    record = json.loads(RECORD.read_text())

    check("the record counts the regions this arithmetic keeps",
          record["regions_measured"] == len(rows)
          and record["dropped"] == dropped,
          f"{len(rows)} measured, dropped {dropped}")

    mine = spread([r["worst_pp"] for r in rows])
    check("and its spread of the worse section is the one in the files",
          record["worst_section_gap_pp"] == mine,
          f"p10 {mine['p10']}, median {mine['median']}, p90 {mine['p90']}, "
          f"max {mine['max']}, min {mine['min']} percentage points")

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["worst_section"]] = counts.get(r["worst_section"], 0) + 1
    check("hospitality is the section the two keys disagree about most often",
          record["which_section_disagrees_most"] == counts
          and max(counts, key=lambda k: counts[k]) == "I",
          f"worst in {counts.get('I', 0)} of {len(rows)} regions, against "
          f"{counts.get('H', 0)} for transport and {counts.get('G', 0)} for "
          f"trade")

    # THE POINT OF THE WHOLE FILE.
    # The published page quotes one region. If that region were unusual, the
    # page would be teaching from an outlier.
    es = next((r for r in rows if r["geo"] == "ES51"), None)
    below = sum(1 for r in rows if r["worst_pp"] < es["worst_pp"]) if es else 0
    pct = round(100 * below / len(rows)) if es else -1
    check("the published example is an ordinary region, not an outlier",
          es is not None and record["es51"]["percentile"] == pct and 25 <= pct <= 75,
          f"ES51 moves {es['worst_pp']} pp on {es['worst_section']}, "
          f"percentile {pct} of {len(rows)}" if es else "ES51 not measured")

    under = sum(1 for r in rows if r["worst_pp"] < 1.0)
    check("and the keys agree nowhere worth calling agreement",
          record["regions_under_1pp"] == under,
          f"{under} of {len(rows)} regions inside a single percentage point; "
          f"the quietest moves {mine['min']} pp, so choosing a key moves the "
          f"answer in every region Eurostat covers")

    # CAN THIS BE DONE FOR MY REGION? The archive's side of the match.
    from quadrium.io_loader import MRIO_RELABEL

    geos = {r["geo"] for r in rows}
    wrong = {raw: right for raw, right in MRIO_RELABEL.items() if raw != right}
    silent = sorted(raw for raw in wrong if raw in geos)
    check("the archive's mislabelled codes are the dangerous kind, not the "
          "harmless kind", len(silent) == 8,
          f"{len(silent)} of the {len(wrong)} labels MRIO_RELABEL corrects "
          f"name a region Eurostat ALSO publishes "
          f"({', '.join(silent[:4])}...), so reading them as printed hands "
          f"another region's key to the split instead of failing; the other "
          f"{len(wrong) - len(silent)} would not be found at all")

    from quadrium.catalogue import scan
    archive = sorted({s.source_id.split(":")[2] for s in scan(ROOT)
                      if s.source_id.startswith("mrio:eu2018:")})
    said = record.get("archive_coverage")
    if not archive:
        print("    --   the 2018 archive is not in this tree, so how many of "
              "its regions could take a key was NOT checked here. The record "
              f"says {said['reached_by_both_keys']} of "
              f"{said['archive_regions_with_data']}, measured "
              f"{said['measured_at'][:10]}." if said else
              "    --   the 2018 archive is not in this tree and the record "
              "carries no measurement of it.")
    else:
        reached = sorted(set(archive) & geos)
        missed = sorted(set(archive) - geos)
        check("the record's count of archive regions that can take either key "
              "is this tree's",
              bool(said) and said["reached_by_both_keys"] == len(reached)
              and said["archive_regions_with_data"] == len(archive),
              f"{len(reached)} of {len(archive)} regions with data")
        no_data = sorted({c[:2] for c in missed
                          if not any(g.startswith(c[:2]) for g in geos)})
        check("and the reason each unreached country is unreached is recorded",
              bool(said) and said["no_data_at_all"]
              == len([c for c in missed if c[:2] in no_data])
              and said["vintage_mismatch"]
              == len([c for c in missed if c[:2] not in no_data]),
              f"{len(missed)} unreached: "
              f"{said['no_data_at_all'] if said else '?'} in countries "
              f"Eurostat does not publish ({', '.join(no_data)}) and "
              f"{said['vintage_mismatch'] if said else '?'} coded in a "
              f"different NUTS vintage on one side or the other")

    # A PROPERTY OF THE MEASUREMENT, NOT OF THE DATA.
    # Shares are scale-free, so a key reported in thousands rather than units
    # must give the same gaps. If this ever fails, the measurement is reading
    # levels and the whole distribution above means something else.
    scaled, _ = distribution(cubes, scale=1000.0)
    check("a key in other units gives the same shares, so this measures "
          "proportions",
          [r["gap_pp"] for r in scaled] == [r["gap_pp"] for r in rows],
          "wages multiplied by a thousand: every gap identical")

    print("\n" + "=" * 78)
    if FAIL:
        print(f"{len(FAIL)} check(s) FAILED: {', '.join(FAIL)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
