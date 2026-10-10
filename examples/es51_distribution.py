"""
Divide Catalonia's `G-I` into trade, transport and hospitality — on a table that
also holds the rest of Spain and the rest of Europe.

    G-I  Distribution  (NACE G + H + I), 114,656 of ES51's 520,526
           ->  G   Wholesale and retail trade
           ->  H   Transport and storage
           ->  I   Accommodation and food service

WHAT IS REAL HERE
------------------
The table is the European multiregional archive's (Huang & Koutroumpis 2023) for
2018, loaded with `mrio_scope: with_rest`: thirty sectors in three blocks —
ES51, the rest of Spain, the rest of the archive — so what an impulse sets off
outside Catalonia is inside the multipliers instead of in a footnote.

The sizes are Eurostat's own, for Catalonia, for the table's own year, at the
exact level the split needs: `sbs_r_nuts06_r2`, regional structural business
statistics, sections G, H and I separately. No interpolation, no borrowing from
another region, no year gap. Two indicators are published at that level and both
are registered:

    S1  wages and salaries, million euro     G 12,722.6  H 4,049.8  I 3,521.6
    S2  persons employed, number             G 581,147   H 168,958  I 253,349

WHAT IS NOT REAL, AND IT IS THE POINT OF THE EXAMPLE
-----------------------------------------------------
**Neither indicator is output.** The regional SBS publishes no turnover and no
value added at NUTS-2 — only local units, wages and headcount — so the closest
available proxy to output is a cost. S1 drives the split because wages track
value more closely than a headcount does; S2 is kept because the two disagree,
and by how much is the most useful number here:

    share of G-I given to        by wages (S1)   by headcount (S2)
      G  trade                      62.7 %          57.9 %
      H  transport                  20.0 %          16.8 %
      I  accommodation and food     17.4 %          25.2 %

**7.8 points on hospitality.** That is the equal-productivity assumption made
visible: a waiter and a wholesaler do not carry the same output per head, and
whichever key is chosen imposes one ratio. The engine prints the gap in
`report.md` rather than choosing for you.

**And the table is an estimate.** Every cell of the archive is modelled from the
OECD ICIO, Eurostat regional accounts and truck freight flows, its two
accounting identities do not close — the residue rides in a labelled RESIDUAL
row and column — and against ten surveyed regions it records about a quarter of
the purchases a region makes from the rest of its country. So the report's
figures for where an impulse lands are read as a bound, which the report says
where the numbers are.

WHAT THE SPLIT CANNOT BE CHECKED FOR
-------------------------------------
`check_split` accepts `G-I -> G, H, I` and says what it could not verify: it
does not parse `G-I`, which is the archive's A10 grouping and not a NACE code,
so nothing confirms that the three sections tile it. They do — A10's `G-I` is
NACE G, H and I — but that is read from Eurostat's grouping documentation, not
derived here, and it is registered as an assumption rather than left implied.

Run:
    python3 examples/es51_distribution.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Where the run is written. `outputs/es51_distribution/` is committed verbatim
# and is what the published page narrates, so a check that regenerates this run
# to see whether it still produces the same figures must not write over it.
# `run_published_runs.py` points this at a temporary folder; nothing else does.
OUT = ROOT / "outputs"
sys.path.insert(0, str(ROOT / "src"))

from quadrium.catalogue import proxy_values, scan  # noqa: E402
from quadrium.io_loader import load_eu_mrio_wide  # noqa: E402
from quadrium.models import (AllocationKey, Assumption,  # noqa: E402
                             AssumptionLedger, ProxyStrength, Scenario,
                             SplitSpec)
from quadrium.project import IOProject  # noqa: E402

REGION = "ES51"
YEAR = 2018
SECTOR = "G-I"
NEW_CODES = ["G", "H", "I"]
NEW_LABELS = ["Wholesale and retail trade",
              "Transport and storage",
              "Accommodation and food service"]
WAGES = "v13320"
HEADCOUNT = "v16110"
SBS = ("Eurostat, Structural business statistics by NUTS 2 region and NACE "
       "Rev. 2 (sbs_r_nuts06_r2), Catalonia, 2018")


_SOURCES: list | None = None


def sources() -> list:
    """The catalogue, read once.

    `scan()` walks every table under `data/` and opens each one to record which
    sector codes carry data. In this tree that is 3,058 sources and **21
    seconds**, and this script needs it twice, once per key — so calling it per
    key spent 21 seconds re-reading the same eleven 33 MB workbooks to answer
    the same question.
    """
    global _SOURCES
    if _SOURCES is None:
        _SOURCES = scan(ROOT)
    return _SOURCES


def sbs_key(indicator: str) -> dict:
    """One number per section, read through the catalogue's own proxy reader.

    `proxy_values` pins every dimension that is not a sector and refuses when
    one of them has more than one category, which is why each indicator is
    kept in its own cached file: a cube holding both wages and headcount would
    be summed across two things that do not add up.
    """
    # THE CUBE FOR THIS REGION, NOT WHICHEVER MATCHED FIRST.
    # This read `sources[0]` after filtering on the indicator and the region,
    # which is the same thing as "this region's file" for exactly as long as
    # one file matches. On 2026-10-10 six more cubes of the same dataset went
    # into `data/eurostat/` -- every region, one section each, for
    # `measure_key_disagreement.py` -- and they match the filter too, because
    # they carry 536 regions and ES51 is one of them. `sources[0]` became a
    # single-section file and this function raised `KeyError: 'H'`.
    #
    # So the selection is stated instead of taken: the file that covers this
    # region and nothing else. If several do, that is ambiguity and it is
    # refused by name rather than resolved by sort order.
    matches = [s for s in sources()
               if s.kind == "proxy" and indicator in s.source_id
               and list(s.geos) == [REGION]]
    if not matches:
        raise SystemExit(
            f"no cached Eurostat file in {ROOT / 'data' / 'eurostat'} covers "
            f"{REGION} alone for {indicator}. It is one request:\n"
            f"    quadrium.eurostat.fetch('sbs_r_nuts06_r2', '{REGION}', "
            f"{YEAR}, dest, unit=None, indic_sb='{indicator.upper()}')")
    if len(matches) > 1:
        raise SystemExit(
            f"{len(matches)} cached files cover {REGION} alone for "
            f"{indicator}, and nothing here says which to believe:\n    "
            + "\n    ".join(sorted(s.source_id for s in matches)))
    values = proxy_values(matches[0], REGION, YEAR)["values"]
    return {c: float(values[c]) for c in NEW_CODES}


def build_keys() -> dict:
    wages, heads = sbs_key(WAGES), sbs_key(HEADCOUNT)
    keys = [
        AllocationKey(
            key_id="key_wages_sbs_2018", applies_to="output",
            new_sector_codes=NEW_CODES,
            raw_values=[wages[c] for c in NEW_CODES],
            source=SBS + ", wages and salaries (V13320), million euro",
            source_year=YEAR, strength=ProxyStrength.MEDIUM),
        AllocationKey(
            key_id="key_headcount_sbs_2018", applies_to="output",
            new_sector_codes=NEW_CODES,
            raw_values=[heads[c] for c in NEW_CODES],
            source=SBS + ", persons employed (V16110), number",
            source_year=YEAR, strength=ProxyStrength.MEDIUM),
    ]
    return {k.key_id: k for k in keys}


def build_scenarios() -> list[Scenario]:
    return [
        Scenario(scenario_id="S1_wages", label="Wages (real)",
                 description="Output, final demand and the intermediate blocks "
                             "split by Eurostat's regional wages and salaries "
                             "for sections G, H and I. Wages are the closest "
                             "published proxy to value at NUTS-2: the regional "
                             "SBS carries no turnover and no value added.",
                 keys_by_block={"output": "key_wages_sbs_2018"}),
        Scenario(scenario_id="S2_headcount", label="Persons employed (real)",
                 description="The same split driven by headcount instead, kept "
                             "to measure what the equal-productivity "
                             "assumption costs: it gives accommodation and food "
                             "25.2 % of the sector where wages give it 17.4 %.",
                 keys_by_block={"output": "key_headcount_sbs_2018"}),
    ]


def build_ledger(wages: dict, heads: dict) -> AssumptionLedger:
    ledger = AssumptionLedger(project_id="es51_distribution")
    ws = {c: 100 * wages[c] / sum(wages.values()) for c in NEW_CODES}
    hs = {c: 100 * heads[c] / sum(heads.values()) for c in NEW_CODES}
    worst = max(NEW_CODES, key=lambda c: abs(ws[c] - hs[c]))
    ledger.add(Assumption(
        assumption_id="A-01",
        description=f"The split rests on a COST proxy, not on output. The "
                    f"regional structural business statistics publish local "
                    f"units, wages and persons employed at NUTS-2, and neither "
                    f"turnover nor value added, so nothing published measures "
                    f"the three sections' output for Catalonia. S1 uses wages "
                    f"because they track value more closely than a headcount.",
        applies_to="the size of every subsector",
        source=SBS,
        validated_by=f"MEASURED against the other published indicator: the two "
                     f"disagree most on `{worst}`, {ws[worst]:.1f} % by wages "
                     f"against {hs[worst]:.1f} % by headcount, "
                     f"{abs(ws[worst] - hs[worst]):.1f} points apart",
        confidence=ProxyStrength.MEDIUM,
        impact_on_results=f"up to {abs(ws[worst] - hs[worst]):.1f} points of "
                          f"the parent's output on one subsector; the report "
                          f"prints both scenarios rather than ranking them"))
    ledger.add(Assumption(
        assumption_id="A-02",
        description="Every subsector inherits the parent's input structure. "
                    "With one allocation key the weight cancels in "
                    "a_ij = Z_ij / X_j, so all three share `G-I`'s "
                    "multiplier. Differentiating them would need purchasing "
                    "profiles, and nothing published gives them for a NUTS-2 "
                    "region.",
        applies_to="the multipliers of G, H and I",
        source="Sizes: " + SBS + " || Structures: NOT ESTIMATED",
        validated_by="not attempted",
        confidence=ProxyStrength.STRONG,
        impact_on_results="the three subsectors' multipliers are the parent's "
                          "and should be quoted as such"))
    ledger.add(Assumption(
        assumption_id="A-03",
        description="That sections G, H and I tile the archive's `G-I`. `G-I` "
                    "is Eurostat's A10 grouping, which `check_split` does not "
                    "parse, so the engine accepts the split and says it could "
                    "not verify the tiling. The grouping is documented by "
                    "Eurostat as G, H and I; it is read from there rather than "
                    "derived here.",
        applies_to="whether the parts add up to the parent",
        source="Eurostat, NACE Rev. 2 A*10 aggregation",
        validated_by="read from the classification, not measured",
        confidence=ProxyStrength.STRONG,
        impact_on_results="none on the arithmetic — the parts are scaled to "
                          "the parent's own total either way — but a reader "
                          "who believed the grouping were G and I alone would "
                          "be reading transport into the wrong row"))
    ledger.add(Assumption(
        assumption_id="A-04",
        description="The table is an ESTIMATE, cell by cell: the archive is "
                    "modelled from the OECD ICIO, Eurostat regional accounts "
                    "and truck freight flows. Neither of its accounting "
                    "identities closes, and the residue is carried in a "
                    "labelled RESIDUAL row and column rather than balanced "
                    "away. Against ten surveyed regions it records about a "
                    "quarter of the purchases a region makes from the rest of "
                    "its country, so the share of an impulse that stays in "
                    "Catalonia is an upper bound.",
        applies_to="every figure in this run",
        source="Huang, S. & Koutroumpis, P. (2023), European multi regional "
               "input output data for 2008-2018, Scientific Data 10, 218",
        validated_by="`run_mrio_real_output.py`, `run_mrio_against_surveys.py`, "
                     "`run_wide_against_surveys.py`",
        confidence=ProxyStrength.WEAK,
        impact_on_results="the split is exact arithmetic on estimated cells; "
                          "the report sizes the residue and states the bound "
                          "beside the figures"))
    return ledger


def main() -> int:
    warnings.filterwarnings("ignore")
    table = load_eu_mrio_wide(ROOT / "data" / "mrio", REGION, YEAR)
    p = table.index_of(SECTOR)
    S = table.n // 3

    print(f"Loaded {table.table_id}: {table.n} units in {len(table.regions)} "
          f"blocks — {', '.join(table.regions)}")
    print(f"  unit {table.unit.split(':')[0]}, reference year {table.year}")
    print(f"  splitting [{p}] {SECTOR} {table.sector_labels[p]!r}, output "
          f"{table.X[p]:,.0f} of {table.X[:S].sum():,.0f} in {REGION}")
    lands = table.interregional["lands"][p]
    print(f"  an impulse in it lands {100 * lands[0] / sum(lands):.1f} % in "
          f"{REGION}, {100 * lands[1] / sum(lands):.1f} % in the rest of "
          f"{REGION[:2]}, {100 * lands[2] / sum(lands):.1f} % further away")

    wages, heads = sbs_key(WAGES), sbs_key(HEADCOUNT)
    for name, k in (("wages", wages), ("headcount", heads)):
        total = sum(k.values())
        print(f"  {name:9} " + "  ".join(
            f"{c} {100 * v / total:.1f} %" for c, v in k.items()))

    project = IOProject(
        project_id="es51_distribution", table=table,
        splits=[SplitSpec(SECTOR, NEW_CODES, NEW_LABELS)],
        scenarios=build_scenarios(), keys=build_keys(),
        title=f"Catalonia's distribution sector, divided, on a table that "
              f"holds the rest of Spain and the rest of Europe",
        ledger=build_ledger(wages, heads),
        root=OUT,
        preamble="**Read the assumption ledger before quoting any number.** "
                 "The sizes are Eurostat's own for Catalonia at this table's "
                 "own year; the table they divide is an estimate whose "
                 "identities do not close, and the two published indicators "
                 "that could drive the split disagree by 7.8 points on "
                 "accommodation and food.")
    project.run().write()
    print(f"\nWrote {project.dir}")
    for r in project.results:
        print(f"  {r.scenario_id:14} "
              f"{'PASSED' if r.report.passed else 'FAILED'}")
    return 0 if all(r.report.passed for r in project.results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
