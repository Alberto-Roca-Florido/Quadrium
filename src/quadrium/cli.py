#!/usr/bin/env python3
"""
Quadrium — run a disaggregation from a configuration workbook.

No Python required. Fill in a spreadsheet, run one command, read the report.

    quadrium --template my_config.xlsx    # get a blank workbook
    quadrium my_config.xlsx               # run it
    quadrium my_config.xlsx --check       # validate, do not run
    quadrium my_config.xlsx --offline     # refuse to download anything

A configuration can name a file, or it can name a country and a year and let
the engine fetch the table from Eurostat. A fetched table is cached with its
SHA-256 and never downloaded twice, so the second run of a configuration reads
the same bytes as the first.

From a checkout, without installing: `python3 run_quadrium.py …` does the same.

Exit code 0 means every scenario passed validation. Anything else means read
the message: the errors are written for an economist, not for a programmer, and
they say which subsector or which proxy is the problem.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

# Relative imports would do here, but the absolute ones keep this file
# runnable as a script from a checkout as well as importable from an
# install; `run_quadrium.py` at the repository root puts `src/` on the
# path and calls `main` below.
from quadrium.config import ConfigError, load_config, write_template  # noqa: E402
from quadrium.project import IOProject  # noqa: E402
from quadrium.regionalise import METHODS  # noqa: E402
from quadrium.scenarios import ScenarioInfeasible  # noqa: E402


def _describe(cfg: dict) -> None:
    t = cfg["table"]
    print(f"Table   : {t.table_id} — {t.country} {t.year}, {t.n} sectors")
    print(f"          {t.unit}")
    print(f"          balance verified on load; negatives: "
          f"Z={int((t.Z < 0).sum())} Y={int((t.Y < 0).sum())} "
          f"VA={int((t.VA < 0).sum())}")
    for s in cfg["splits"]:
        i = t.index_of(s.sector_code)
        print(f"Split   : {s.sector_code} ({t.sector_labels[i].strip()[:38]}) "
              f"-> {', '.join(s.new_codes)}")
    for k in cfg["keys"].values():
        print(f"Key     : {k.key_id} [{k.strength.value}] "
              + ", ".join(f"{c} {w:.1%}" for c, w
                          in zip(k.new_sector_codes, k.weights)))
    for sc in cfg["scenarios"]:
        n = sum(len(v) for v in sc.input_profiles.values())
        print(f"Scenario: {sc.scenario_id} — {sc.label}"
              + (f" ({n} input intensities)" if n else " (no input profiles)"))



def _warn_about_substance(cfg: dict) -> None:
    """Say what is WEAK about a configuration that is structurally VALID.

    `--check` parses the workbook and confirms the table balances. A reader
    takes "valid" for "ready", and the two are not the same: a split driven by
    a key its own author marked `weak` parses perfectly. The engine already
    knew — it printed `[weak]` next to the key — and then said "valid" without
    connecting the two (2026-08-10).

    Everything here is a caution, never an error. It changes no exit code.
    """
    notes = []
    for note in cfg.get("defaults_taken", []):
        notes.append(f"a default was taken: {note}")
    weak = sorted(k.key_id for k in cfg["keys"].values()
                  if getattr(k.strength, "value", str(k.strength)) == "weak")
    if weak:
        notes.append(
            f"the key(s) {', '.join(weak)} are marked WEAK by whoever "
            f"registered them. Every figure a split driven by one produces "
            f"inherits that, and no check in this system will object")
    profiled = sorted(s.scenario_id for s in cfg["scenarios"]
                      if getattr(s, "input_profiles", None))
    if profiled:
        notes.append(
            f"scenario(s) {', '.join(profiled)} carry input profiles. No "
            f"allocation key backs a purchasing pattern, so the differentiated "
            f"multipliers they produce are demonstrations, not estimates")
    spare = [k.key_id for k in cfg["keys"].values()]
    if len(spare) < 2:
        notes.append(
            "only one allocation key is registered, so nothing can corroborate "
            "the split. Registering a second key you do NOT use turns it into "
            "an external check — the only kind this system can make")
    if not notes:
        return
    print("\nValid is not the same as well founded:")
    for n in notes:
        print(f"  - {n}")


def _catalogue(args) -> int:
    """`--sources` and `--find`, which need no configuration and no network."""
    from quadrium.catalogue import advise, scan

    sources = scan(args.data)
    if not sources:
        # STDOUT AND EXIT 0, AND THE TWO GO TOGETHER.
        # This said "Nothing is wrong" on stderr and then exited 1, which is
        # the message contradicting itself: a shell, a CI step or any wrapper
        # reads the code, not the prose. It is also the FIRST thing every new
        # user sees, because a fresh `pip install` ships no tables at all --
        # found by release_check.py, which installs the wheel into an empty
        # interpreter and runs the documented commands from an empty
        # directory.
        print(f"No loadable table found under {args.data.resolve()}.\n"
              f"Nothing is wrong: this looks in `data/eurostat/`, `data/ine/`, "
              f"`data/mrio/` and for `UK_IOAT_*.xlsx`. A configuration with "
              f"`table_kind: eurostat` fetches one without any of them.")
        return 0

    if args.sources:
        tables = [s for s in sources
                  if s.kind == "table" and s.table_kind != "eu_mrio"]
        regional = [s for s in sources if s.table_kind == "eu_mrio"]
        proxies = [s for s in sources if s.kind == "proxy"]

        print(f"{len(tables)} table(s) you can load and split\n")
        print(f"  {'source':56s}{'sectors':>8}{'discarded':>11}")
        for s in tables:
            more = f"{len(s.finer)}" if s.finer else "—"
            print(f"  {s.source_id:56s}{s.resolution:>8}{more:>11}")

        if any(s.finer for s in tables):
            print("\n  `discarded` is detail the PUBLISHER publishes and this "
                  "engine drops: where\n  a country serves both a code and its "
                  "components, the loader keeps the coarser\n  tiling. "
                  "`--find CODE --geo XX` says when that affects the sector "
                  "you want.")

        # 259 lines would bury everything above them. One paragraph.
        if regional:
            countries = sorted({s.geo[:2] for s in regional})
            years = sorted({s.year for s in regional})
            span = (f"{years[0]}" if len(years) == 1 else
                    f"{years[0]}-{years[-1]} ({len(years)} years)")
            print(f"\n  and {len(regional)} regional tables from the European "
                  f"MRIO (Huang & Koutroumpis 2023),\n  {span}, 10 sectors "
                  f"each, one per NUTS-2 region and year in {len(countries)} "
                  f"countries:\n  {', '.join(countries)}.\n  `--find CODE "
                  f"--geo <region>` asks about one, e.g. --geo "
                  f"{min(s.geo for s in regional)}. They are estimates, the "
                  f"archive does not\n  balance, and a region that trades "
                  f"with no other region is refused on\n  loading, with the "
                  f"reason: docs/GUIDE.md, Route B.")

        if proxies:
            print(f"\n{len(proxies)} source(s) that measure sectors — "
                  f"candidate allocation keys\n")
            print(f"  {'source':56s}{'sectors':>8}  countries")
            for s in proxies:
                geos = (",".join(s.geos[:5]) + ("…" if len(s.geos) > 5 else "")
                        ) if s.geos else "—"
                print(f"  {s.source_id:56s}{s.resolution:>8}  {geos}")

        print("\n  Sectors counted are the codes that CARRY DATA. Eurostat "
              "lists the whole CPA\n  hierarchy in its metadata whether a "
              "country publishes at that level or not:\n  Spain's symmetric "
              "table lists CPA_I55 and CPA_I56 and populates neither.")
        print("\n  Resolution is the only thing this ranks by, and it is NOT "
              "comparability.\n  Eurostat harmonises the format and neither "
              "harmonises nor records the method.")
        return 0

    a = advise(args.find, sources, args.geo)
    print(f"\n  {a['target']} — {a['action'].replace('_', ' ')}\n")
    for line in _wrap(a["why"], 74):
        print(f"  {line}")

    # NOTHING ON DISK FOR THAT COUNTRY IS A TRUE ANSWER AND A USELESS ONE.
    # On a fresh install the catalogue holds whatever shipped, so the first
    # question a new user asks -- about their own country -- lands here. What
    # they need next is which years exist, which is one small query per
    # dataset and is cached afterwards.
    # Only for a COUNTRY: the probe asks Eurostat, which publishes nothing
    # under a region's code.
    if a["action"] == "none" and args.geo and len(args.geo.strip()) == 2 \
            and not args.offline:
        _availability(args, a)

    # The verdict belongs on EVERY answer that names a country, not only on
    # the branch that found nothing on disk. A user whose table IS here is the
    # one who most needs to know it refuses: Ireland's and Sweden's are in this
    # checkout precisely because they do.
    if args.geo:
        _verdicts(args.geo.strip().upper(), args.data)

    if a["action"] == "choose_country":
        print(f"\n  {'country':>9}  verdict     finest table")
        for g, h in sorted(a["by_geo"].items()):
            where = (h["container"] or "—") if h["verdict"] != "SEPARATE" \
                else a["target"]
            print(f"  {g:>9}  {h['verdict']:<10}  {h['source'].source_id} "
                  f"({where})")
        print(f"\n  Add --geo XX to get a recommendation.")
        return 0

    if a["best"] and a["action"] in ("load", "split"):
        s = a["best"]["source"]
        note = _year_advice(s, args.geo, args.data) if args.geo else ""
        print(f"\n  Put this in the `project` sheet:\n")
        for line in s.config_lines():
            if note and line.startswith("eurostat_year"):
                line = line.split()[0] + f"    {note[0]}"
            print(f"      {line}")
        if note:
            print(f"\n  {note[1]}")
        if a["action"] == "split":
            print(f"\n  and divide `{a['best']['container']}` in the `splits` "
                  f"sheet.")
        if s.table_kind == "eu_mrio" and s.note:
            print(f"\n  Note: {s.note}.")

    for pr in a.get("proxies", [])[:4]:
        print()
        head = ("A key that measures its parts:" if pr["tiles"] else
                "Related, but NOT a key for this split:")
        print(f"  {head}")
        print(f"      {pr['source'].source_id}")
        print(f"      measures {', '.join(pr['parts'])}")
        if not pr["tiles"]:
            print(f"      — these are parts of {', '.join(pr['covers'])}, not "
                  f"of `{a['best']['container']}`. They cover one")
            print(f"        piece of it and say nothing about the rest, so "
                  f"they cannot drive this split.")
            continue
        # OQ-E-01. The numbers, not just the name of the file that has them.
        # Only for a proxy that TILES the sector -- printing rows a user can
        # paste for a key the engine would then refuse is worse than printing
        # nothing, and this module already knows which is which.
        _print_key_rows(pr, args.geo.strip().upper(),
                        getattr(args, "measure", None))
    if a.get("proxies"):
        print("\n  A proxy is a candidate, not a recommendation. Whether "
              "employment is the\n  right key is a judgement about the "
              "sectors — two subsectors share a\n  headcount far more evenly "
              "than they share an output.")
    return 0


def _gap_lines(i: int, g: dict) -> None:
    """One gap, wrapped so a paragraph of reasoning stays readable."""
    import textwrap
    print(f"  {i}. [{g['sheet']}] {g['what']}")
    for tag, body in (("why", g["why"]), ("put", g["fix"])):
        for j, line in enumerate(textwrap.wrap(body, 66) or [""]):
            print(f"     {tag + ':' if j == 0 else '    '} {line}")
    print()


def _plan(rep: dict, as_json: bool) -> int:
    """Print what the workbook still needs — all of it, once.

    Exit code is 0 whether or not the workbook is ready, and that is
    deliberate. `--check` is the gate; this is advice, and advice that exits
    non-zero is the defect `--sources` carried until v1.85, printing "Nothing
    is wrong" while telling the shell otherwise. The REPORT says whether it is
    ready; the exit code says whether the report could be produced.
    """
    if as_json:
        import json
        print(json.dumps(rep, indent=2, ensure_ascii=False))
        return 0

    blocking = [g for g in rep["gaps"] if g["severity"] == "blocking"]
    weak = [g for g in rep["gaps"] if g["severity"] == "weak"]
    have = rep["have"]

    print(f"\n  {Path(rep['path']).name}")
    print(f"  job: {have.get('job') or 'none named'} · "
          f"table_kind: {have.get('table_kind') or 'not set'} · "
          f"{have.get('splits', 0)} split row(s), {have.get('keys', 0)} key "
          f"row(s), {have.get('profiles', 0)} profile row(s)")

    if blocking:
        print(f"\n  {len(blocking)} thing(s) stop it running:\n")
        for i, g in enumerate(blocking, 1):
            _gap_lines(i, g)
    else:
        print("\n  Nothing stops it running.\n")

    if weak:
        print(f"  {len(weak)} thing(s) it will run WITHOUT, and the report "
              f"will say so:\n")
        for i, g in enumerate(weak, 1):
            _gap_lines(i, g)

    if rep["ready"]:
        print("  Ready. `quadrium <this file> --check` loads the table and "
              "says what it would do;\n  without --check it runs.")
    else:
        print("  Not ready yet. Everything above is listed at once on "
              "purpose: --check\n  stops at the first problem, which costs a "
              "sitting per gap.")
    print("\n  Nothing was computed, fetched or written.")
    return 0


def _print_key_rows(pr, geo: str, measure: str | None = None) -> None:
    """The `keys` sheet, filled in, for a proxy that tiles the sector.

    WHY THE ROWS AND NOT A FILE
    -----------------------------
    Because the user has to see the numbers before they use them. Writing the
    workbook directly would put a figure behind a split without anyone having
    read it, and the population question -- whether the proxy counts the same
    objects the table does -- is exactly what no cube can answer and every
    analyst must. Spanish product 36 is the standing proof: the survey counts
    ENTERPRISES classified to a NACE code, the table counts PRODUCT, and the
    conceptually closest key is 40.8 % out because of it.

    So this prints what to paste, with the source string already written, and
    stops there.
    """
    from quadrium.catalogue import ProxyValueError, proxy_values
    try:
        got = proxy_values(pr["source"], geo, measure=measure)
    except ProxyValueError as exc:
        print(f"      — its numbers cannot be read as a key: {exc}")
        return

    vals = {c: v for c, v in got["values"].items() if c in pr["parts"]}

    # ONE LEVEL, NOT EVERY LEVEL. `parts` is every code inside the container,
    # so for `C10` it holds C101 AND C1011, C1012, C1013 -- the group and the
    # classes inside it. Pasted as a key those would count the same euro twice
    # and the shares would be meaningless while looking perfectly ordinary.
    # Keep only the codes no other code in the set contains.
    from quadrium.catalogue import tiling_only
    vals = {c: vals[c] for c in tiling_only(vals)}

    if len(vals) < 2:
        print(f"      — it carries {len(vals)} of these sectors for {geo}, "
              f"which is not a split.")
        return

    # The measure's OWN label, never a guess about what it counts. The first
    # version of this said "a count of ENTERPRISES" whatever was asked for,
    # and printed it over value added in millions of euro.
    what = got["measure_label"] or got["label"]
    src = f"Eurostat {pr['source'].dataset}, {got['label'][:60]}"
    print(f"      and here are its numbers for {geo} in {got['year']} — "
          f"paste into the `keys` sheet:")
    print()
    print(f"        {'key_id':10s} {'new_sector_code':16s} {'value':>14s} "
          f"{'source_year':>12s} {'strength':>9s}")
    kid = f"k_{pr['source'].dataset.split('_')[0]}"[:10]
    for code, v in sorted(vals.items()):
        print(f"        {kid:10s} {code:16s} {v:14,.0f} "
              f"{got['year']:>12d} {'medium':>9s}")
    print(f"\n        source: {src}")
    print(f"        measures: {what}")
    print(f"        pinned:  {', '.join(f'{k}={v}' for k, v in got['pinned'].items())}")
    print("\n      Read them before you use them. This measures enterprises "
          "classified\n      to a NACE code; your table may count PRODUCT, "
          "which is a different\n      population. On Spanish product 36 that "
          "difference alone put the\n      best-matching proxy 40.8 % out.")


def _availability(args, a) -> None:
    """What Eurostat actually carries for a country whose tables are not here.

    Every count comes from the VALUE map and not from the `time` dimension,
    which lists the years a dataset spans rather than the years a country
    populates. Read the wrong one and this printed a configuration naming 2024
    for Germany, which fails: Eurostat answers 200 with an empty result for a
    year a country does not publish. Advice you have not run is not advice.
    """
    from quadrium.catalogue import available_years
    from quadrium.eurostat import DATASETS

    geo = args.geo.strip().upper()
    print(f"\n  Asking Eurostat what it carries for {geo}…")
    years = available_years(geo, Path(args.data) / "data" / "eurostat",
                            refresh=args.refresh)
    if not years:
        print(f"  Nothing came back for {geo}. Either it is not a code "
              f"Eurostat knows,\n  or the network is not there. `--offline` "
              f"skips this question entirely.")
        return

    taken = str(years.pop("_taken", ""))[:10]
    labels = {"product_by_product": "symmetric, product x product",
              "industry_by_industry": "symmetric, industry x industry",
              "supply": "supply", "use_purchasers": "use, purchasers' prices",
              "use_basic": "use, basic prices, split DOM / IMP"}
    print(f"\n  {'dataset':<22}{'years':>7}  range")
    for name in ("product_by_product", "industry_by_industry", "supply",
                 "use_purchasers", "use_basic"):
        ys = years.get(name)
        row = f"{len(ys):>7}  {ys[0]}–{ys[-1]}" if ys else f"{'—':>7}  none  "
        print(f"  {DATASETS[name]:<22}{row}  {labels[name]}")
    print(f"\n  (years a country POPULATES, not the years the dataset spans; "
          f"asked {taken},\n  cached, and `--refresh` asks again)")

    sym_kind = ("product_by_product" if years.get("product_by_product")
                else "industry_by_industry" if years.get("industry_by_industry")
                else None)
    pair = years.get("supply") and years.get("use_purchasers")
    transformable = pair and years.get("use_basic")

    if sym_kind:
        ys = years[sym_kind]
        print(f"\n  A symmetric table, most recent {ys[-1]}:\n")
        for line in ("table_kind       eurostat",
                     f"eurostat_geo     {geo}",
                     f"eurostat_year    {ys[-1]}",
                     f"eurostat_dataset {sym_kind}"):
            print(f"      {line}")

    if transformable:
        newest = min(years["supply"][-1], years["use_purchasers"][-1],
                     years["use_basic"][-1])
        extra = ("" if sym_kind and years[sym_kind][-1] >= newest
                 else f"  — and {newest} exists ONLY as a pair")
        print(f"\n  Or the supply-use pair, most recent {newest}{extra}:\n")
        for line in ("table_kind       eurostat_sut",
                     f"eurostat_geo     {geo}",
                     f"eurostat_year    {newest}",
                     "eurostat_model   D"):
            print(f"      {line}")

    if not sym_kind and not transformable:
        print(f"\n  {geo} HAS NO ROUTE TO A SYMMETRIC TABLE HERE, and that is "
              f"the answer,\n  not a failure to look. Eurostat carries no "
              f"symmetric table for it, and")
        if pair:
            print(f"  the supply-use pair it does carry has no "
                  f"`{DATASETS['use_basic']}` —\n  use at basic prices split "
                  f"into domestic and imported. Without that\n  split a "
                  f"transformation would have to assume every user of a "
                  f"product\n  imports the same share of it, which is an "
                  f"economic hypothesis this\n  engine will not make for you.")
            print(f"\n  The pair still loads, and every supply-use identity "
                  f"still holds on it.\n  What it cannot do is become a "
                  f"symmetric table. For that, {geo}'s own\n  statistical "
                  f"office is the place to look — Eurostat is not the only\n"
                  f"  publisher, only the harmonised one.")
        else:
            print(f"  it carries no usable supply-use pair either.")


def _year_advice(source, geo: str, data_root):
    """Do not print a configuration for a year that is known to refuse.

    The recommendation names whatever file happens to be cached, and for
    Ireland that was its 2020 symmetric table — 50 % short of its own printed
    total, refused at every year tried. Handing a user a configuration for it
    and letting the refusal explain itself later is not advice.

    Returns `(year, sentence)` when the recommended year refuses and something
    can be said about it, or `""` when the recommendation stands as it is.
    """
    import json

    route = "symmetric" if getattr(source, "dataset", "") in (
        "naio_10_cp1700", "naio_10_cp1750") else "pair"
    if getattr(source, "table_kind", "") != "eurostat":
        return ""
    try:
        rec = json.loads((Path(data_root) / "data" / "eurostat"
                          / "_verdicts.json").read_text()).get(geo.upper())
    except (OSError, ValueError, AttributeError):
        return ""
    e = (rec or {}).get(route) or {}
    if not e or e.get("verdict") == "loads" or e.get("year") != source.year:
        return ""
    good = sorted(y for y, v in (e.get("also_tried") or {}).items()
                  if v == "loads")
    if good:
        return (good[-1],
                f"{source.year} is refused for this country — {e['cause']} — "
                f"so the year above is {good[-1]}, the newest that was tried "
                f"and loaded"
                + (f" (also {', '.join(good[:-1])})" if len(good) > 1 else "")
                + ".")
    tried = sorted(e.get("also_tried") or {})
    return (source.year,
            f"**{source.year} is refused for this country** — {e['cause']}: "
            f"{e['detail']}"
            + (f", and so {'is' if len(tried) == 1 else 'are'} "
               f"{', '.join(tried)}" if tried else "")
            + ". The configuration above is what you would write if it "
              "loaded; it will refuse, and say why.")


def _verdicts(geo: str, data_root) -> None:
    """What the newest table of each kind actually did, when it was checked.

    "Eurostat carries this, which is not a promise it loads" was a fair caveat
    while nothing better was known. The sweep of 2026-08-25 loaded every
    country's newest table by both routes, so the verdict can be named instead
    of hedged.

    EVIDENCE, NOT PREDICTION. Each line says which year was checked, and which
    others were. That caveat used to be the whole of this docstring and it was
    load-bearing: **three of the ten symmetric refusals turned out to be about
    the year and not the country.** France's 2022 table is refused for sparse
    final demand and its 2010, 2016 and 2021 tables load — twelve usable years
    behind a verdict that said "France refuses". Slovakia and Croatia are the
    same. Ireland, Lithuania, Luxembourg, Malta, Norway, Poland and Sweden
    refuse in every year tried, which is a different fact and now a stated one.

    Years not tried are still not claimed either way.
    """
    import json

    f = Path(data_root) / "data" / "eurostat" / "_verdicts.json"
    try:
        rec = json.loads(f.read_text()).get(geo)
    except (OSError, ValueError):
        rec = None
    if not rec:
        print(f"\n  Whether any of this LOADS has not been checked for {geo}. "
              f"Carrying is not\n  loading: the engine verifies the "
              f"publisher's own identities and refuses a\n  table whose books "
              f"do not close within its own printed precision.")
        return

    print(f"\n  And what happened when they were last loaded:\n")
    for key, label in (("symmetric", "symmetric table"), ("pair", "the pair")):
        e = rec.get(key)
        if not e:
            continue
        year = e.get("year")
        also = e.get("also_tried") or {}
        good = sorted(y for y, v in also.items() if v == "loads")
        bad = sorted(y for y, v in also.items() if v != "loads")
        if e["verdict"] == "loads":
            print(f"      {label:16s} {year}   LOADS")
        elif e["verdict"] == "not published":
            print(f"      {label:16s}  —     {e['cause']}, {e['detail']}")
        else:
            print(f"      {label:16s} {year}   REFUSED — {e['cause']}: "
                  f"{e['detail']}")
        # A refusal at the newest year is not a refusal of the country, and
        # saying so is the difference between France having no table and
        # France having twelve.
        if good:
            print(f"      {'':16s}        but {', '.join(good)} "
                  f"{'LOADS' if len(good) == 1 else 'LOAD'} — set the year in "
                  f"your configuration")
        elif bad and e["verdict"] not in ("loads", "not published"):
            verb = "does" if len(bad) == 1 else "do"
            print(f"      {'':16s}        and so {verb} {', '.join(bad)}")
    print(f"\n  Checked on the years named and on those only — evidence, not "
          f"a\n  prediction about the rest.")


def _wrap(text: str, width: int) -> list[str]:
    import textwrap
    return textwrap.wrap(text, width) or [""]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Run an IO disaggregation from a configuration workbook.")
    ap.add_argument("config", nargs="?", type=Path,
                    help="the .xlsx configuration workbook")
    ap.add_argument("--template", type=Path, metavar="PATH",
                    help="write a blank workbook to PATH and exit")
    ap.add_argument("--plan", action="store_true",
                    help="say what a configuration workbook still needs — ALL "
                         "of it, in one pass, in plain language. `--check` "
                         "stops at the first problem, which is right for a "
                         "gate and wrong for a person. Add `--json` for the "
                         "same thing machine-readable.")
    ap.add_argument("--json", action="store_true",
                    help="with `--plan`, print the report as JSON instead of "
                         "prose, so an assistant can fill the workbook in and "
                         "hand it back for you to approve.")
    ap.add_argument("--measure", metavar="CODE",
                    help="which measurement of a proxy cube to read, when it "
                         "carries several — employment, turnover, wages. "
                         "`--find` names the ones it holds when it needs "
                         "telling.")
    ap.add_argument("--key-alternatives", action="store_true",
                    help="re-run each split under every other registered "
                         "allocation key and report what came out. Costs one "
                         "full run per key. Also settable in the workbook: "
                         "`key_alternatives  yes` in the `project` sheet.")
    ap.add_argument("--check", action="store_true",
                    help="validate the configuration and the table, then stop")
    ap.add_argument("--outputs", type=Path, default=Path("outputs"),
                    help="where project folders are written "
                         "(default: ./outputs)")
    ap.add_argument("--sources", action="store_true",
                    help="list every table on disk this engine can load, and "
                         "how many sectors each distinguishes")
    ap.add_argument("--find", metavar="CODE",
                    help="say where a sector code is available, and if "
                         "nowhere, which coarser code to split")
    ap.add_argument("--geo", metavar="XX",
                    help="the country --find is asking about. Without it "
                         "nothing is recommended, because a finer table for "
                         "another economy answers a different question")
    ap.add_argument("--data", type=Path, default=Path("."),
                    help="where --sources and --find look (default: .)")
    ap.add_argument("--offline", action="store_true",
                    help="never touch the network. A table_kind that would "
                         "need a download fails, naming the URL to fetch by "
                         "hand")
    ap.add_argument("--refresh", action="store_true",
                    help="re-download a cached table even though it is "
                         "already here. Statistical offices revise, so this "
                         "can change your results — it says so when it does")
    ap.add_argument("--regionalise", type=Path, metavar="ACTIVITY.csv",
                    help="estimate a region's table from a national one, given "
                         "the region's activity by sector. Needs --national. "
                         "Every run prints what the method is known to get "
                         "wrong, because it is known and the number would "
                         "otherwise look unqualified")
    ap.add_argument("--national", type=Path, metavar="TABLE.xlsx",
                    help="the national table --regionalise starts from, in "
                         "this engine's interchange format. It must be the "
                         "DOMESTIC table")
    ap.add_argument("--national-kind", default="interchange",
                    choices=["interchange", "ine", "idescat", "uk", "eurostat"],
                    help="where --national came from, so the DOMESTIC variant "
                         "is the one loaded (default: interchange, this "
                         "engine's own format)")
    ap.add_argument("--method", default="FLQ", choices=list(METHODS),
                    help="which location quotient (default: FLQ)")
    ap.add_argument("--delta", type=float, metavar="D",
                    help="the FLQ's convexity parameter. There is no default: "
                         "measured across ten regions in two countries it runs "
                         "from 0.14 to 0.60, median 0.26, so any default would "
                         "be a guess wearing a number")
    ap.add_argument("--charm", metavar="ACTIVITY.csv",
                    help="estimate a region's GROSS two-way trade (CHARM, "
                         "M-075). Needs --national, and that table must be "
                         "the TOTAL-FLOW one — the opposite of what "
                         "--regionalise needs")
    ap.add_argument("--name", metavar="NAME",
                    help="the output folder's name (default: regionalised_<method>)")
    args = ap.parse_args(argv)

    if args.regionalise and args.charm:
        # TWO JOBS ON TWO DIFFERENT TABLES, so this is not a combination to
        # resolve by precedence. M-075's DOMESTIC_IMPORT_TREATMENT: the
        # quotient family needs the DOMESTIC table and CHARM the TOTAL-FLOW
        # one, and the multipliers they give are not interchangeable.
        print("--regionalise and --charm are two different jobs and they need "
              "two different tables: the location quotient family needs the "
              "DOMESTIC table, CHARM the TOTAL-FLOW one. Run them separately, "
              "each with its own --national.", file=sys.stderr)
        return 2
    if args.regionalise:
        if not args.national:
            print("--regionalise needs --national: a location quotient scales "
                  "a national table down, so there has to be one.",
                  file=sys.stderr)
            return 2
        return _regionalise(args)
    if args.charm:
        if not args.national:
            print("--charm needs --national: CHARM estimates a region's trade "
                  "from a national table, so there has to be one.",
                  file=sys.stderr)
            return 2
        return _charm(args)
    if args.national:
        print("--national only means something with --regionalise or --charm.",
              file=sys.stderr)
        return 2

    if args.template:
        p = write_template(args.template)
        print(f"Template written to {p}")
        print("Fill it in — every sheet carries its own instructions — then:")
        # The installed user has no run_quadrium.py. Echo whatever
        # they actually typed -- a clean-venv install test is what
        # found this telling them to run a file they do not have.
        print(f"    {Path(sys.argv[0]).name} {p}")
        return 0

    if args.sources or args.find:
        return _catalogue(args)

    if not args.config:
        # Fifteen options with no hierarchy was the whole of the first contact.
        # Someone who has just installed this needs one sentence about what to
        # do, not a list of flags to rank for themselves.
        print("Quadrium divides a sector of an input-output table, or "
              "estimates a region's\ntable from a national one, and says what "
              "it assumed either way.\n")
        print("Start here:\n")
        print("    quadrium --template my_split.xlsx    a workbook that "
              "explains itself,")
        print("                                         then: quadrium "
              "my_split.xlsx")
        print("    quadrium --sources                   every table this "
              "engine can load, here")
        print("    quadrium --find I55 --geo ES         which table separates "
              "a sector\n")
        print("The guide is docs/GUIDE.md, and outputs/uk_food_beverage/"
              "report.md is a\nfinished run you can read without running "
              "anything.\n")
        print("Every option:\n")
        ap.print_help()
        return 2

    if args.offline and args.refresh:
        print("--offline and --refresh contradict each other: one forbids the "
              "network, the other requires it.", file=sys.stderr)
        return 2

    # `--plan` runs BEFORE load_config, and that ordering is the whole point:
    # a workbook load_config cannot read is exactly the workbook --plan exists
    # for. Nothing here computes, fetches or writes.
    if args.plan:
        from quadrium.config import plan_workbook
        return _plan(plan_workbook(args.config), args.json)

    try:
        cfg = load_config(args.config, offline=args.offline,
                          refresh=args.refresh)
    except ConfigError as exc:
        print(f"Configuration problem in {args.config}:\n\n{exc}\n",
              file=sys.stderr)
        return 1

    # A workbook can describe a regionalisation instead of a split, and then
    # everything below -- _describe, the substance warnings, splits, keys,
    # scenarios -- has nothing to act on. Dispatched BEFORE them, because
    # _describe reads cfg["splits"] and a regionalisation has none.
    if cfg.get("kind") == "regionalise":
        from . import diagnostics
        from .regionalise import regionalise
        A_nat = np.nan_to_num(
            diagnostics.technical_coefficients(cfg["table"].Z, cfg["table"].X))
        try:
            res = regionalise(A_nat, cfg["Q_region"], cfg["Q_national"],
                              method=cfg["method"], delta=cfg["delta"],
                              X_region=cfg["Q_region"]
                              if cfg["national_activity_from"] == "table output"
                              else None)
        except ValueError as exc:
            print(f"The method refused:\n\n  {exc}\n", file=sys.stderr)
            return 2
        if args.check:
            print(f"Table   : {cfg['table'].table_id} — {cfg['table'].n} sectors")
            print(f"Method  : {res.method}"
                  + (f", delta = {res.delta:g}" if res.delta is not None else ""))
            print(f"Region  : {cfg['Q_region'].sum() / cfg['Q_national'].sum() * 100:.2f} %"
                  f" of the national total\n")
            print(res.report())
            return 0
        print(f"Table   : {cfg['table'].table_id} — {cfg['table'].n} sectors")
        return _write_regionalisation(
            res, cfg["table"], args.outputs, cfg["project_id"],
            Path(cfg["source_file"]).name, Path(cfg["activity_file"]).name,
            cfg["national_activity_from"] == "file",
            cfg["Q_region"], cfg["Q_national"])

    # The fourth job, dispatched here for the same reason: `_describe` reads
    # cfg["splits"] and a CHARM run has none. `build_charm` has already made
    # every refusal this needs, including the two about the table itself, so
    # by here the run is known to be one the method admits.
    if cfg.get("kind") == "charm":
        from . import diagnostics
        from .charm import charm
        table = cfg["table"]
        A_X = np.nan_to_num(
            diagnostics.technical_coefficients(table.Z, table.X))
        E, M, D = table.trade_vectors()
        try:
            res = charm(A_X=A_X, X_national=table.X,
                        Z_S_national=table.Z.sum(axis=1), D_national=D,
                        E_national=E, M_national=M,
                        L_region=cfg["Q_region"], L_national=cfg["Q_national"],
                        indirect_allocation=table.trade.indirect_allocation)
        except ValueError as exc:
            print(f"The method refused:\n\n  {exc}\n", file=sys.stderr)
            return 2
        if args.check:
            print(f"Table   : {table.table_id} — {table.n} products, "
                  f"total flow")
            print(f"Declared: {table.trade.declared_by}")
            print(f"Region  : {res.employment_share * 100:.2f} % of national "
                  f"employment\n")
            print(res.report())
            return 0
        print(f"Table   : {table.table_id} — {table.n} products, total flow")
        return _write_charm(
            res, table, args.outputs, cfg["project_id"],
            Path(cfg["source_file"]).name, Path(cfg["activity_file"]).name)

    # The FIFTH job, and the first that does not build a table: it asks a
    # question about one. `build_mixed` has already refused every scenario the
    # sheet can state wrongly, so by here the run is one the model admits.
    if cfg.get("kind") == "mixed":
        from .mixed import MixedModelError, mixed_model_from_table
        table = cfg["table"]
        try:
            res = mixed_model_from_table(
                table, cfg["exogenous"],
                delta_x=cfg["delta_x"] or None,
                delta_f=cfg["delta_f"] or None)
        except (MixedModelError, ValueError) as exc:
            print(f"The model refused:\n\n  {exc}\n", file=sys.stderr)
            return 2
        if args.check:
            print(f"Table   : {table.table_id} — {table.n} sectors, "
                  f"{table.unit}")
            print(_mixed_report(res, cfg, table, check=True))
            return 0
        print(f"Table   : {table.table_id} — {table.n} sectors, {table.unit}")
        return _write_mixed(res, cfg, table, args.outputs)

    _describe(cfg)
    # Printed on BOTH paths. Warning only under --check would mean the run that
    # actually produces numbers is the quieter of the two.
    _warn_about_substance(cfg)

    if args.check:
        print("\nConfiguration and table are valid. Nothing was run "
              "(--check).")
        return 0

    project = IOProject(
        project_id=cfg["project_id"], table=cfg["table"], splits=cfg["splits"],
        scenarios=cfg["scenarios"], keys=cfg["keys"], ledger=cfg["ledger"],
        title=cfg["title"], source_file=cfg["source_file"], root=args.outputs,
        preamble=cfg["notes"] or "")
    try:
        project.run(key_alternatives=(args.key_alternatives
                                      or cfg.get("key_alternatives", False))).write()
    except ScenarioInfeasible as exc:
        print(f"\nEvery scenario was rejected.\n\n{exc.detail}\n",
              file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"\n{exc}\n", file=sys.stderr)
        return 1

    print()
    print(project.summary())
    print(f"\nReport : {project.dir / 'report.md'}")
    print(f"Folder : {project.dir}")
    rejected = project.meta.get("infeasible", [])
    if rejected:
        # Not a malfunction, and the report says so -- but not a clean run
        # either, and the exit code is what a script reads. Counting only
        # `results` returned 0 for a run that produced one table out of two.
        print(f"\n{len(rejected)} scenario(s) were REJECTED before they could "
              f"be balanced: {', '.join(r['scenario_id'] for r in rejected)}. "
              f"The numbers you gave them describe an economy that cannot "
              f"exist; the report says which figure is the problem, under "
              f"'Scenarios that were rejected'.", file=sys.stderr)
    ok = (all(r.report.passed for r in project.results) and not rejected)
    if not all(r.report.passed for r in project.results):
        print("\nAt least one scenario FAILED validation. Read the report "
              "before using any number from it.", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())


def _write_regionalisation(res, table, out_root, name, national_name,
                           activity_name, has_nat, q_reg, q_nat) -> int:
    """Write a regionalisation, whichever door asked for it.

    Both the flags and the `regionalise` sheet arrive here, so a result cannot
    depend on how it was requested and the measured cost cannot be printed by
    one route and not the other.
    """
    import numpy as np

    from .export import write_json

    out = Path(out_root) / (name or f"regionalised_{res.method.lower()}")
    out.mkdir(parents=True, exist_ok=True)
    np.savetxt(out / "coefficients.csv", res.A, delimiter=",",
               header=",".join(table.sector_codes), comments="# A^rr, ")
    # The region as a TABLE, in the format --national-kind interchange reads.
    # Without this the command produced a matrix and stopped: nothing
    # downstream could diagnose the region, split a sector of it, or export it.
    from .export import write_interchange_xlsx
    regional = res.to_table(
        sector_codes=table.sector_codes, sector_labels=table.sector_labels,
        country=f"{table.country} — region", year=table.year, unit=table.unit,
        classification=table.classification,
        source=f"regionalised from {national_name} with "
               f"{res.method}" + (f", delta={res.delta:g}"
                                  if res.delta is not None else ""),
        # The national table, so its satellite accounts can come down to the
        # region scaled rather than vanish, and so what CANNOT come -- the type
        # II closure -- is said rather than left to be noticed.
        national=table)
    wrote_table = write_interchange_xlsx(
        regional, out / "regional_table.xlsx",
        derived_from=f"Quadrium regionalisation with {res.method}"
                     + (f", delta = {res.delta:g}" if res.delta is not None
                        else "") + ". Estimated, not observed:")

    with (out / "implicit_imports.csv").open("w") as fh:
        fh.write("# interregional imports the scaling implies, CORE_039 p. 292\n")
        fh.write("sector_code,implicit_imports\n")
        for c, v in zip(table.sector_codes, res.implicit_imports):
            fh.write(f"{c},{v:.6f}\n")

    lines = [
        f"# Regionalised with {res.method}"
        + (f", delta = {res.delta:g}" if res.delta is not None else ""),
        "",
        f"From `{national_name}` ({table.country} {table.year}, "
        f"{table.n} sectors, {table.unit}).",
        f"Regional activity from `{activity_name}`"
        + ("" if has_nat else ", against the table's own output")
        + f", a {q_reg.sum() / q_nat.sum() * 100:.2f} % share of the national "
          f"total.",
        "",
        "## What this is known to get wrong",
        "",
        "*Printed because the method has measured limitations and a number "
        "without them invites more confidence than it has earned. "
        "`CORE_036` p. 35.*",
        "",
    ] + [f"- {c.lstrip('- ')}" if c.startswith("  - ") else c
         for c in res.caveats] + [
        "",
        "## What was written",
        "",
        "- `coefficients.csv` — the regional domestic coefficients.",
        "- `implicit_imports.csv` — the interregional imports the scaling "
        "implies, by product. This is the quantity that makes the method's "
        "trade assumption inspectable rather than implicit.",
        ("- `regional_table.xlsx` — the region as a table, in the format this "
         "engine reads back. Run it through `--check`, split a sector of it, "
         "or point `--national` at it. Its final demand is one column and its "
         "value added one row, because a location quotient says nothing about "
         "how either divides."
         if wrote_table else
         "- (no `regional_table.xlsx`: openpyxl is not installed)"),
        "",
        f"Scaling touched {int((res.q < 1.0).sum()):,} of "
        f"{res.q.size:,} cells; {int((res.slq >= 1.0).sum())} sectors were "
        f"at or above a location quotient of 1 and were left alone.",
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    write_json({"method": res.method, "delta": res.delta, "lambda": res.lam,
                "national_table": str(national_name),
                "activity_file": str(activity_name),
                "national_activity_from": "file" if has_nat else "table output",
                "regional_share_pct": float(q_reg.sum() / q_nat.sum() * 100),
                "caveats": res.caveats},
               out / "assumption_ledger.json")

    print("\n".join(lines))
    print(f"\nWritten to {out}")
    return 0


def _load_total_flow(kind, path):
    """The TOTAL-FLOW table, which is the opposite of what `--regionalise` loads.

    `_load_national` above names each loader with the variant that gives the
    DOMESTIC table, because that is what a location quotient needs. CHARM needs
    the other one: `M-075`'s DOMESTIC_IMPORT_TREATMENT says the two give
    different multipliers -- domestic output against supply -- and are not
    interchangeable, so choosing between `--regionalise` and `--charm` is
    choosing which multiplier you want and not merely which estimator.

    Two kinds REFUSE BY NAME rather than falling through to something close
    enough. A fall-through is how an analyst gets a plausible wrong answer with
    no error, which is the failure this whole route is arranged to prevent.
    """
    from .io_loader import LoaderError, load_io_table
    if kind == "ine":
        from .io_loader import load_ine_tio
        return load_ine_tio(path, variant="total")
    if kind == "eurostat":
        from .eurostat import load_iot
        return load_iot(path, variant="total")
    if kind == "interchange":
        return load_io_table(path)
    if kind == "uk":
        raise LoaderError(
            "the ONS publishes its analytical table at DOMESTIC use, with "
            "imports as a value-added row read along the industry axis. The "
            "file carries no total-flow variant and no imports by product, so "
            "CHARM has nothing to form a commodity balance from. This is a "
            "property of the publication and not of the loader.")
    if kind == "idescat":
        raise LoaderError(
            "the Catalan workbook's intermediate matrix is the 'ts Cat' sheet, "
            "which is DOMESTIC origin: its imports by product sit outside `Z`, "
            "in the supply identity. CHARM needs them distributed inside it. "
            "The workbook is also already a two-region table, so a "
            "single-region estimate of its trade is not what it is for.")
    raise LoaderError(f"--national-kind {kind!r} has no total-flow variant.")


def _charm(args) -> int:
    """Estimate a region's GROSS two-way trade, and print what it costs.

    Every other non-survey method here estimates NET trade and puts it on one
    side. CHARM keeps the balance and estimates the volume separately, so both
    directions of a product's trade can be positive at once -- which is what
    the commodity balance cannot represent, and what `OQ-R-01` measured at
    28.3 % of Catalonia's interregional trade.

    It is its own job and not a fifth `--method`: it takes a different table
    and it produces different objects. There is no `A^rr` here and no regional
    table to write.
    """
    import numpy as np

    from . import diagnostics
    from .charm import charm
    from .io_loader import LoaderError

    try:
        table = _load_total_flow(args.national_kind, args.national)
    except (LoaderError, FileNotFoundError, ValueError, KeyError) as exc:
        print(f"Could not read {args.national} as a "
              f"{args.national_kind} TOTAL-FLOW national table:\n\n  "
              f"{str(exc).splitlines()[0]}\n\n"
              f"CHARM needs the table whose intermediate matrix includes "
              f"imported inputs — the opposite of the one --regionalise needs. "
              f"Use --national-kind to say where the file came from.",
              file=sys.stderr)
        return 2

    # WHAT THE TABLE ITSELF SAYS, and the two refusals that cannot be argued
    # with by a flag. `indirect_allocation` is the loader's declaration because
    # a user cannot assert a convention about a table they did not compile.
    if table.trade is None:
        print(f"{args.national} was read by a route that does not say which of "
              f"its final-demand columns are exports or where its imports by "
              f"product are, so a commodity balance cannot be formed from it. "
              f"That is NOT SPECIFIED rather than zero.\n\n"
              f"  --national-kind ine and eurostat declare it. A file in this "
              f"engine's own format carries the declaration in its `metadata` "
              f"sheet when it was written from a table that had one.",
              file=sys.stderr)
        return 2
    if not table.trade.indirect_allocation:
        print(f"{args.national} is a DOMESTIC table: its intermediate matrix "
              f"holds home-produced flows only.\n\n"
              f"  Declared by: {table.trade.declared_by}\n\n"
              f"  CHARM's technical coefficients are z_ij / X_j on a table "
              f"where imported inputs are distributed across `Z` — the "
              f"indirect-allocation convention, STE_14 p. 12. Run on a "
              f"domestic table it would return numbers, and they would be the "
              f"wrong multipliers rather than an error, which is why this "
              f"refuses instead.",
              file=sys.stderr)
        return 2

    from .config import ConfigError as _CfgError
    from .config import read_activity
    try:
        L_reg, L_nat, national_from = read_activity(args.charm, table)
    except _CfgError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    # AND THE ONE PLACE THIS ROUTE CANNOT REUSE `read_activity`'s DEFAULT.
    #
    # With no third column it fills the national side with the table's own
    # OUTPUT, which is the right default for a location quotient. Eq. (30)
    # reads this pair as EMPLOYMENT, so taking output there would silently
    # assume every sector's labour productivity equals its output share --
    # which is not the source's assumption and is not any assumption anybody
    # chose.
    if national_from != "file":
        print(f"{args.charm} carries no `national` column, and for CHARM that "
              f"cannot be defaulted.\n\n"
              f"  eq. (30) reads this pair as EMPLOYMENT, regional over "
              f"national, sector by sector. With the column absent the engine "
              f"would substitute the table's own output, which assumes a "
              f"thing nobody chose. Add a third column, `national`, with the "
              f"country's employment by sector.",
              file=sys.stderr)
        return 2

    # z_ij / X_j, eq. (15) -- correct here PRECISELY BECAUSE this `Z` is the
    # total-flow one, the mirror image of the care _regionalise takes in the
    # other direction.
    A_X = np.nan_to_num(diagnostics.technical_coefficients(table.Z, table.X))
    E, M, D = table.trade_vectors()
    try:
        res = charm(A_X=A_X, X_national=table.X,
                    Z_S_national=table.Z.sum(axis=1), D_national=D,
                    E_national=E, M_national=M,
                    L_region=L_reg, L_national=L_nat,
                    indirect_allocation=table.trade.indirect_allocation)
    except ValueError as exc:
        print(f"The method refused:\n\n  {exc}\n", file=sys.stderr)
        return 2

    return _write_charm(res, table, args.outputs, args.name,
                        Path(args.national).name, Path(args.charm).name)


def _mixed_report(res, cfg, table, check: bool = False) -> str:
    """The report of a mixed run, one function so both doors say the same.

    `--check` prints it and writes nothing; a real run writes it to
    `report.md`. The text is identical, which is the point: a dry run that
    described the result differently would be a different dry run.
    """
    import numpy as np

    codes = list(table.sector_codes)
    X = np.asarray(table.X, float).ravel()
    exo = list(cfg["exogenous"])
    pct = cfg["pct_asked"]
    fixed_total = float(res.x[res.exogenous].sum())
    knock_on = float(res.x[res.endogenous].sum())
    total = fixed_total + knock_on

    lines = [f"# {cfg['title']}", ""]
    if not exo:
        lines += [
            "**No sector's output was fixed on the `mixed` sheet, so this is "
            "the ordinary Leontief answer to a change in final demand.** That "
            "is a legitimate question and the model spans both ends, but it "
            "is not the mixed model: nothing here was held at a given output.",
            ""]
    lines += [
        f"From `{Path(str(cfg['source_file'])).name}` "
        f"({table.country} {table.year}, {table.n} sectors, {table.unit}).",
        "",
        "## What was fixed, and what it did",
        "",
    ]
    if exo:
        lines += [f"| sector | output, {table.unit} | output fixed to change by "
                  f"| as % of its own output |", "|---|---:|---:|---:|"]
        for c in exo:
            i = codes.index(c)
            share = (res.x[i] / X[i] * 100) if X[i] else float("nan")
            asked = (f"{pct[c]:+.4g} % (asked)" if c in pct
                     else f"{share:+.4g} %")
            lines.append(f"| `{c}` | {X[i]:,.1f} | {res.x[i]:+,.1f} | {asked} |")
        lines += ["",
                  f"Those {len(exo)} sector(s) move by **{fixed_total:+,.1f} "
                  f"{table.unit}** between them, which is the figure you gave, "
                  f"not a result.",
                  "",
                  f"**The result is the other {table.n - len(exo)} sectors: "
                  f"{knock_on:+,.1f} {table.unit}.** Total change in output "
                  f"across the table, {total:+,.1f} {table.unit}"
                  + (f", or {total / fixed_total:,.3f} per unit of the output "
                     f"you fixed." if fixed_total else ".")]
    else:
        lines += [f"Final demand was moved for "
                  f"{len(cfg['delta_f'])} sector(s), by "
                  f"{sum(float(v) for v in cfg['delta_f'].values()):+,.1f} "
                  f"{table.unit} in all.",
                  "",
                  f"**Output across the table changes by {total:+,.1f} "
                  f"{table.unit}.**"]

    # THE DEMAND SHOCKS, WHICH THE FIRST VERSION OF THIS REPORT DROPPED.
    # A sheet may fix some outputs AND move some final demands in the same
    # scenario, which is the normal case: a quota on one industry while
    # another's orders rise. The report named only the fixed sectors, so a
    # figure the user had typed in did not appear anywhere in the document
    # describing the run. Caught on the first real run, 2026-11-12.
    if exo and cfg["delta_f"]:
        lines += ["", "## And final demand you moved yourself", "",
                  "Given on the sheet, alongside the fixed outputs. These are "
                  "figures you gave, not results.", ""]
        for c, v in cfg["delta_f"].items():
            i = codes.index(c)
            lines.append(f"- `{c}` — final demand {float(v):+,.1f} "
                         f"{table.unit}, and its output is solved for like "
                         f"any other: {res.x[i]:+,.1f}")

    # The consistent final demand of the fixed sectors. This is the quantity
    # the mixed model exists to produce and the one a Leontief run cannot
    # give, so it is named rather than left in the CSV.
    if exo:
        lines += ["", "## What final demand has to do for that to hold", "",
                  "Fixing a sector's output does not leave its final demand "
                  "free: the model returns the change in final demand that is "
                  "consistent with the output you fixed. This is a "
                  "consequence of the scenario, `DERIVED`, not a figure "
                  "anybody observed.", ""]
        for c in exo:
            i = codes.index(c)
            lines.append(f"- `{c}` — final demand {res.f[i]:+,.1f} "
                         f"{table.unit}")

    lines += ["", "## What this is known to get wrong", "",
              "*Printed because the method has a measured limitation and a "
              "number without it invites more confidence than it has earned. "
              "`M-073`, `CORE_085` p. 59.*", ""]
    if exo:
        lines += [
            "**Backward linkages only.** `CORE_085` p. 59: the forward "
            "effects on the production of sectors that use the exogenized "
            "outputs as inputs \"are not explicitly considered\". Cut a "
            "sector's output and the firms that BUY from it are left short of "
            "an input; this model does not see that, by construction. The "
            "source says the approach \"is most suitable for modeling "
            "capacity constraint scenarios where there are limited purchases "
            "of the exogenized sector(s) outputs by the other endogenous "
            "sectors\".",
            "",
            "How much that matters here, sector by sector — the share of each "
            "fixed sector's output that other sectors buy as an input:",
            ""]
        for c in exo:
            s = res.forward_share.get(c)
            if s is None:
                continue
            verdict = ("small, so the limitation is mild for this sector"
                       if s < 0.10 else
                       "LARGE: most of this sector's output is an input to "
                       "others, and that channel is the one the model does "
                       "not see" if s >= 0.40 else
                       "material; read the result with it in mind")
            lines.append(f"- `{c}` — {s * 100:.1f} % of its output is bought "
                         f"as an input by other sectors. {verdict}.")
        lines += ["",
                  "This is a warning and not a refusal, because the model is "
                  "correct about what it computes. `M-073`."]
    else:
        lines += ["Nothing was exogenized, so the forward-linkage limitation "
                  "does not apply to this run. The ordinary caveats of a "
                  "Leontief answer do: fixed coefficients, no capacity "
                  "limits, no price response."]

    if res.condition_number > 1e10:
        lines += ["", f"⚠ **The system is ill-conditioned** (condition number "
                      f"{res.condition_number:.3g}). The arithmetic is at the "
                      f"edge of what the numbers can carry; treat the last "
                      f"digits as noise and check whether a fixed sector is "
                      f"nearly a linear combination of others."]

    accounts = dict(getattr(table, "satellites", None) or {})
    if accounts:
        lines += ["", "## Satellite accounts", "",
                  "Each account's change is its value per unit of output "
                  "times the change in output, sector by sector. The per-unit "
                  "figure is `DERIVED` from the account and the table's "
                  "output; the account itself is whatever its own source says.",
                  ""]
        for name, acc in sorted(accounts.items()):
            v = np.asarray(getattr(acc, "values", acc), float).ravel()
            if v.shape != X.shape:
                continue
            with np.errstate(divide="ignore", invalid="ignore"):
                c = np.where(X > 0, v / np.where(X > 0, X, 1.0), 0.0)
            eff = res.effect(c)
            unit = getattr(acc, "unit", "") or ""
            lines.append(f"- **{name}** — {eff.sum():+,.2f} {unit}, of which "
                         f"{eff[res.endogenous].sum():+,.2f} in the sectors "
                         f"whose output was not fixed")
    if not check:
        lines += ["", "## What was written", "",
                  "- `mixed.csv` — every sector's output and final demand "
                  "change, and which side of the model it was on. This file "
                  "IS the result.",
                  "- `multipliers.csv` — how much each unknown moves per unit "
                  "of each value you gave. Column order is the table's.",
                  ]
        if accounts:
            lines.append("- `effects.csv` — the change in each satellite "
                         "account, by sector.")
    return "\n".join(lines) + "\n"


def _write_mixed(res, cfg, table, out_root) -> int:
    """Write a mixed run: the result, the multipliers, the accounts, the report.

    EVERY CSV HERE IS WRITTEN WITH THE `csv` MODULE, NOT WITH f-STRINGS, and
    that is not a style preference. The UK 2023 table has a sector whose CODE
    CONTAINS A COMMA -- `F41, F42  & F43` -- so pasting the code and a comma
    together produces a file with one extra column on that row, silently. The
    first version of this function did exactly that and the validator caught it
    on its first run, 2026-11-12, while reading back a file it had just
    written. Codes come from an office's spreadsheet and the engine does not
    get to assume what is in them.
    """
    import csv

    import numpy as np

    codes = list(table.sector_codes)
    X = np.asarray(table.X, float).ravel()
    out = Path(out_root) / (cfg["project_id"] or "mixed")
    out.mkdir(parents=True, exist_ok=True)

    with (out / "mixed.csv").open("w", newline="") as fh:
        fh.write("# The mixed exogenous/endogenous model, M-073, from "
                 "CORE_085 (Steinback 2004).\n")
        fh.write("# `side` says which: 'output fixed' is a figure you GAVE, "
                 "'solved' is a result.\n")
        w = csv.writer(fh)
        w.writerow(["sector_code", "X", "delta_x", "delta_x_pct", "delta_f",
                    "side"])
        for i, c in enumerate(codes):
            pct = (res.x[i] / X[i] * 100) if X[i] else float("nan")
            w.writerow([c, f"{X[i]:.6f}", f"{res.x[i]:.6f}", f"{pct:.6f}",
                        f"{res.f[i]:.6f}",
                        "solved" if res.endogenous[i] else "output fixed"])

    with (out / "multipliers.csv").open("w", newline="") as fh:
        fh.write("# M^-1 N: row i, column j is how much unknown i moves per "
                 "unit of the known value given for j.\n")
        w = csv.writer(fh)
        w.writerow(["sector_code"] + codes)
        for i, c in enumerate(codes):
            w.writerow([c] + [f"{v:.9f}" for v in res.multipliers[i]])

    accounts = dict(getattr(table, "satellites", None) or {})
    wrote_effects = False
    if accounts:
        rows = {}
        for name, acc in sorted(accounts.items()):
            v = np.asarray(getattr(acc, "values", acc), float).ravel()
            if v.shape != X.shape:
                continue
            with np.errstate(divide="ignore", invalid="ignore"):
                coef = np.where(X > 0, v / np.where(X > 0, X, 1.0), 0.0)
            rows[name] = res.effect(coef)
        if rows:
            wrote_effects = True
            with (out / "effects.csv").open("w", newline="") as fh:
                fh.write("# Change in each satellite account: its value per "
                         "unit of output times the change in output.\n")
                fh.write("# The per-unit figure is DERIVED from the account "
                         "and the table's output.\n")
                w = csv.writer(fh)
                w.writerow(["sector_code"] + list(rows))
                for i, c in enumerate(codes):
                    w.writerow([c] + [f"{rows[k][i]:.6f}" for k in rows])

    (out / "report.md").write_text(_mixed_report(res, cfg, table))
    print(f"Written : {out}/")
    print("          mixed.csv · multipliers.csv"
          + (" · effects.csv" if wrote_effects else "") + " · report.md")
    return 0


def _write_charm(res, table, out_root, name, national_name,
                 activity_name) -> int:
    """Write a CHARM run, whichever door asked for it.

    There is no `to_table()` here and that is deliberate, not missing. CHARM
    returns five vectors by commodity; the regional `Z` they would imply is
    `A^X @ diag(X^R)`, which is the nation's technology BY ASSUMPTION and not
    something CHARM estimates. And an `IOTable` with one residual final-demand
    column -- which is what `Regionalisation.to_table()` honestly produces --
    would net `E` against `M` and destroy the one quantity this method exists
    to compute.
    """
    import numpy as np

    from .export import write_json

    out = Path(out_root) / (name or "charm")
    out.mkdir(parents=True, exist_ok=True)

    with (out / "trade.csv").open("w") as fh:
        fh.write("# CHARM, M-075, from STE_14 (Kronenberg 2007). E and M are "
                 "GROSS and both can be positive.\n")
        fh.write("sector_code,X,Z_S,D,B,V,E,M,CH,eps\n")
        for i, c in enumerate(table.sector_codes):
            fh.write(f"{c},{res.X[i]:.6f},{res.Z_S[i]:.6f},{res.D[i]:.6f},"
                     f"{res.B[i]:.6f},{res.V[i]:.6f},{res.E[i]:.6f},"
                     f"{res.M[i]:.6f},{res.CH[i]:.6f},{res.eps[i]:.6f}\n")

    # SEPARATE FROM trade.csv ON PURPOSE. Merged into one file a reader comes
    # to believe `eps` was measured for the region. It was measured for the
    # NATION and carried across, which is the method's central assumption and
    # the thing all four caveats exist to keep in view.
    E_n, M_n, D_n = table.trade_vectors()
    V_n, B_n = E_n + M_n, E_n - M_n
    with (out / "heterogeneity.csv").open("w") as fh:
        fh.write("# the NATIONAL heterogeneity, which this run transported to "
                 "the region unchanged.\n")
        fh.write("sector_code,eps,V,B,CH,scale\n")
        scale = table.X + table.Z.sum(axis=1) + D_n
        for i, c in enumerate(table.sector_codes):
            fh.write(f"{c},{res.eps[i]:.6f},{V_n[i]:.6f},{B_n[i]:.6f},"
                     f"{V_n[i] - abs(B_n[i]):.6f},{scale[i]:.6f}\n")

    resid = res.market_clearing_residue
    ch_share = (float(res.CH.sum() / res.V.sum() * 100)
                if res.V.sum() else float("nan"))
    lines = [
        "# A region's gross two-way trade, estimated with CHARM",
        "",
        f"From `{national_name}` ({table.country} {table.year}, "
        f"{table.n} products, {table.unit}), the TOTAL-FLOW table.",
        f"Declared by: {table.trade.declared_by}",
        f"Regional employment from `{activity_name}`, "
        f"a {res.employment_share * 100:.2f} % share of the national total.",
        "",
        "## What this is known to get wrong",
        "",
        "*Printed because the method has measured limitations and a number "
        "without them invites more confidence than it has earned. "
        "`CORE_036` p. 35.*",
        "",
    ] + [f"- {c.lstrip('- ')}" if c.startswith("  - ") else c
         for c in res.caveats] + ([""] + res.flags if res.flags else []) + [
        "",
        "## What was written",
        "",
        "- `trade.csv` — output, intermediate sales, domestic final use, the "
        "balance, the volume, exports, imports, cross-hauling and the "
        "heterogeneity, by product. This file IS the result.",
        "- `heterogeneity.csv` — the same quantities for the NATION, which is "
        "where `eps` was measured. Kept separate so nothing reads as though "
        "it had been measured for the region.",
        "",
        "There is no `regional_table.xlsx`, no `coefficients.csv` and no "
        "`implicit_imports.csv` here, and that is not an omission. CHARM "
        "estimates trade, not a technology: the regional coefficient matrix it "
        "would imply is the nation's by assumption, and a table with one "
        "residual final-demand column would net exports against imports and "
        "destroy the one thing this method computes. Use `--regionalise` for a "
        "regional table.",
        "",
        f"Cross-hauling is {ch_share:.1f} % of estimated trade volume. The "
        f"market-clearing residue of eq. (13) is at most "
        f"{float(np.abs(resid).max()):,.6f} across {table.n} products — the "
        f"source's own consistency check, and this run's arithmetic rather "
        f"than its assumptions.",
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    write_json({"method": "CHARM",
                "national_table": str(national_name),
                "table_kind_declared_by": table.trade.declared_by,
                "indirect_allocation": bool(table.trade.indirect_allocation),
                "activity_file": str(activity_name),
                "employment_share": float(res.employment_share),
                "eps_source": "national, transported",
                "cross_hauling_share_pct": ch_share,
                "market_clearing_residue_max": float(np.abs(resid).max()),
                "caveats": res.caveats, "flags": res.flags},
               out / "assumption_ledger.json")

    print("\n".join(lines))
    print(f"\nWritten to {out}")
    return 0


def _regionalise(args) -> int:
    """Regionalise a national table, and print what it costs to have done so.

    `OQ-R-01` asked whether to implement the location quotient family knowing
    that it does not reproduce cross-hauling, or to wait for a source that
    handles it. The owner chose to implement it with the cost stated beside the
    result, on 2026-09-01. This is that: the method runs, and every run says in
    its own output what is known to be wrong with it.

    That is `CORE_036` p. 35's position — the responsibility for a table is the
    analyst's and there is no refuge in mechanically produced figures — turned
    into something the engine does rather than something a document says.
    """
    import numpy as np

    from . import diagnostics
    from .export import write_json
    from .io_loader import LoaderError, load_io_table
    from .regionalise import regionalise

    # Each loader is named with the variant that gives the DOMESTIC table,
    # because that is what the method needs and no file announces which of its
    # blocks that is. M-070's DOMESTIC_IMPORT_TREATMENT is the failure that
    # produces a plausible wrong answer instead of an error.
    def _load_national(kind, path):
        if kind == "interchange":
            return load_io_table(path)
        if kind == "ine":
            from .io_loader import load_ine_tio
            return load_ine_tio(path, variant="interior")
        if kind == "idescat":
            from .io_loader import load_idescat_mioc
            return load_idescat_mioc(path)
        if kind == "uk":
            from .io_loader import load_uk_analytical_iot
            return load_uk_analytical_iot(path)
        from .eurostat import load_iot
        return load_iot(path, variant="domestic")

    try:
        table = _load_national(args.national_kind, args.national)
    except (LoaderError, FileNotFoundError, ValueError, KeyError) as exc:
        print(f"Could not read {args.national} as a "
              f"{args.national_kind} national table:\n\n  "
              f"{str(exc).splitlines()[0]}\n\n"
              f"The table must be the DOMESTIC one — a location quotient scales "
              f"local sourcing down, so handing it a total-flow table "
              f"regionalises the country's imports as though they were "
              f"domestic supply, and nothing downstream catches that. Use "
              f"--national-kind to say where the file came from.",
              file=sys.stderr)
        return 2

    # The SAME reader the workbook route uses, so one mistake cannot get two
    # different refusals depending on which door the analyst came through.
    from .config import ConfigError as _CfgError
    from .config import read_activity
    try:
        q_reg, q_nat, national_from = read_activity(args.regionalise, table)
    except _CfgError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    has_nat = national_from == "file"

    A_nat = diagnostics.technical_coefficients(table.Z, table.X)
    A_nat = np.nan_to_num(A_nat)
    try:
        res = regionalise(A_nat, q_reg, q_nat, method=args.method,
                          delta=args.delta, X_region=q_reg if not has_nat else None)
    except ValueError as exc:
        print(f"The method refused:\n\n  {exc}\n", file=sys.stderr)
        return 2

    return _write_regionalisation(
        res, table, args.outputs, args.name, Path(args.national).name,
        Path(args.regionalise).name, has_nat, q_reg, q_nat)

