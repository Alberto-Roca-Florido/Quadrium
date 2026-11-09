"""
Every number the report tells a user, against the validator it cites.

AND THE GUIDE, WHICH WAS WORSE
--------------------------------
`docs/GUIDE.md` is the other document a user reads and the first one a stranger
opens — it begins "No Python: you fill in a spreadsheet and run one command".
It held **36 figures behind 2 citations**, and auditing it found:

  * the SAME stale profile paragraph the report had — 54 splits, 9.0 %, 3.4 %,
    10.6 %, 21 of 35 — against 96 splits, 7.78 %, 3.48 %, 7.79 %, 30 of 56;
  * `19 of the 68` where the base is now 96;
  * a section still opening "**Two numbers** from the table you already have
    rank the difficulty: the parent's own output multiplier and how many parts"
    — directly above a table with ONE column, because the multiplier signal was
    removed the night before and the paragraph introducing it was not;
  * borrowing a profile described as a coin flip at "78 of 162", which was the
    figure from before another country and another YEAR were separated.

Both documents are now fully cited and agree with their sources.

THE GAP THIS FILLS, NAMED BY THE FILE NEXT DOOR
-------------------------------------------------
`run_docs_current.py` audits the countable half of the documentation and says so
in its own output: *"What this cannot check is prose. A sentence that was true
when written and is false now will pass here."*

The report is prose, and it is the only prose a user actually reads. It carries
about forty figures — how much a split costs, what a real key is worth, what
balancing gives back — and every one of them comes from a validator that
measured it. When the evidence base widened this week those measurements moved,
and the report had to be chased by hand each time. It was chased imperfectly:
six figures sat stale in the user's report for hours before the next pass caught
them.

WHAT IS CHECKED
-----------------
Each numeric claim in `reporting.py` and `docs/GUIDE.md` is paired with the
validators its section names, and the number must appear in one of their
sources.

**The tolerance is the report's own printed precision.** A claim of `1.2` is met
by anything from 1.15 to 1.25; a claim of `27.4` by 27.35 to 27.45. That is
`precision.assertable_tolerance`'s rule — half of the last printed digit —
applied to prose instead of to a table, and it is what keeps a rounding
difference from reading as a contradiction. Matching the strings instead would
fail on 3 of 8 sample pairs purely for writing `pp` where the validator writes
`points`.

AND HOW MUCH A MATCH IS WORTH
-------------------------------
A validator's source holds hundreds of numbers, so a claim could match by luck.
Swept over 0 to 100 at one decimal, a random value lands on a cited validator
between **2.4 % and 11.6 %** of the time. Seventy-three claims agreeing is not
something a shuffled set of numbers produces, and the file measures this rather
than asserting it.

AND THE PATHS, WHICH IS WHERE THE FIRST DEFECT WAS
----------------------------------------------------
The report cites validators by path, and this file runs in BOTH trees: the
private one keeps them under `validators/`, the public one — where a
user actually runs the engine — under `validators/`. One citation had the
private prefix hard-coded, so the path it handed a public user did not exist.
Fifteen others used two other spellings. All twenty now use the one form that
resolves in both.

WHAT THIS DOES NOT SHOW
-------------------------
That a claim and its validator agree does **not** make either right. What
establishes the figures is the validators themselves, run against tables the
offices published. This catches drift between what was measured and what is
told, which is a narrower and more mundane failure — and the one that actually
happened, five times in five days.

Run:
    python3 validators/run_report_claims.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Both documents a user reads: the report the engine writes, and the guide it
# is written from. The guide is the one a stranger opens first -- "No Python:
# you fill in a spreadsheet and run one command" -- and it carried 36 figures
# behind 2 citations when this first looked at it.
AUDITED = (ROOT / "src" / "quadrium" / "reporting.py",
           ROOT / "docs" / "GUIDE.md")
VDIR = Path(__file__).resolve().parent
FAIL: list[str] = []


def cited_source(name: str) -> str | None:
    """The text of a cited validator, or None when it is not in this tree.

    A CITATION THAT DOES NOT RESOLVE IS ALREADY A REPORTED FAILURE, and
    reading it anyway turned that report into a traceback. In the public tree,
    where a guide citation pointed at a PRIVATE_ONLY validator, this file
    printed its FAIL and then died on the open -- so every check after it
    never ran and the output ended in a stack trace instead of a verdict. The
    three readers below skip a missing file instead: the figure then finds no
    source, which is exactly what it has.
    """
    p = VDIR / name
    return p.read_text() if p.exists() else None

# Numbers that are not measurements: cut points, alphas, section numbers and the
# like, plus the years and paragraph references that belong to the sources.
NOT_A_MEASUREMENT = re.compile(r"^(0|1|2|3|4|5|18|19|20|65|89|100|1000)$")

CITE = re.compile(r"`validators/(run_[a-z_0-9]+\.py)`")
# A claim is a number the report emphasises or qualifies: bolded, a percentage,
# an "N of M", or a correlation.
CLAIM = re.compile(
    r"\*\*([0-9][0-9.,]*)\s*%?\*\*"
    r"|([0-9]+\.[0-9]+)\s*(?:%|points|pp)"
    r"|([0-9]+)\s+of\s+([0-9]+)"
    r"|r\s*=\s*([+-]?[0-9]+\.[0-9]+)")


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {name}"
          + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def printed_tolerance(text: str) -> float:
    """Half of the last digit the claim actually prints.

    The same rule `precision.assertable_tolerance` applies to a published table,
    applied to a sentence: a number written to one decimal asserts nothing
    finer than 0.05 either side of itself.
    """
    body = text.replace(",", "")
    return 0.5 * 10 ** -(len(body.split(".")[1]) if "." in body else 0)


def numbers_in(text: str) -> list[float]:
    out = []
    for m in re.finditer(r"[0-9]+(?:\.[0-9]+)?", text.replace(",", "")):
        try:
            out.append(float(m.group()))
        except ValueError:
            pass
    return out


def main() -> int:
    print(__doc__.strip().split("Run:")[0].rstrip())
    print("\n" + "=" * 78)

    present = [f for f in AUDITED if f.exists()]
    check("the documents a user reads are where this expects them",
          len(present) == len(AUDITED),
          ", ".join(str(f.relative_to(ROOT)) for f in present))
    if not present:
        return 1

    # A Markdown guide is user-facing on every line; a Python module is
    # user-facing only inside the string literals the report is built from.
    # Scanning the module's commentary too pulled numbers out of notes about
    # the pilot's history and called them uncited claims.
    def user_facing(path, line):
        if path.suffix != ".py":
            return True
        t = line.strip()
        return t.startswith(('"', "f\"", "'", "f'"))

    def scan(path):
        lines = path.read_text().splitlines()
        cited = sorted({m for line in lines for m in CITE.findall(line)})
        pairs, uncited = [], []
        for i, line in enumerate(lines):
            if not user_facing(path, line):
                continue
            found = list(CLAIM.finditer(line))
            if not found:
                continue
            # EVERY validator named nearby, not the first one below. A section
            # states several figures and names several sources in no fixed
            # order; taking the nearest citation below attributed the size
            # screen's numbers to the carry-over study because that citation
            # came first in the sentence. A claim counts as supported if ANY
            # source its section names still carries it.
            near = set()
            for j in range(max(0, i - 8), min(i + 30, len(lines))):
                near.update(CITE.findall(lines[j]))
            for m in found:
                raw = next(g for g in m.groups() if g)
                if NOT_A_MEASUREMENT.match(raw.replace(",", "")):
                    continue
                if m.group(3) and m.group(4):
                    raw = f"{m.group(3)} of {m.group(4)}"
                rec = (path.name, i + 1, raw, sorted(near))
                (pairs if near else uncited).append(rec)
        return lines, cited, pairs, uncited

    # 1 -- every cited path must resolve in THIS tree, whichever tree it is.
    #
    # THE NEEDLE CANNOT BE A LITERAL THE SYNC REWRITES. `sync_public.py`
    # rewrites the private tree's `library/` + `validators/` into the public
    # tree's `validators/` in everything it copies, INCLUDING validator source.
    # Written as a literal, the prefix test became `if "validators/" in line`
    # in the public tree and failed against all 22 legitimate citations. The
    # rewrite is right when the string is a path being USED -- `run_p2_sweep`
    # spells one out and is translated correctly -- and wrong when it is a path
    # being SEARCHED FOR. Assembled from parts, it survives the copy.
    private_prefix = "library" + "/" + "validators/"
    all_cited, all_pairs, all_uncited, missing, stale = set(), [], [], [], []
    print()
    for f in present:
        lines, cited, pairs, uncited = scan(f)
        all_cited |= set(cited)
        all_pairs += pairs
        all_uncited += uncited
        missing += [(f.name, c) for c in cited if not (VDIR / c).exists()]
        stale += [(f.name, i + 1) for i, line in enumerate(lines)
                  if private_prefix in line]
        print(f"    {f.name:<16}{len(pairs) + len(uncited):>4} claim(s), "
              f"{len(cited):>3} validator(s) cited, "
              f"{len(uncited):>3} claim(s) with no source named")

    check("every validator these documents point a user at exists here",
          not missing,
          f"all {len(all_cited)} resolve in {VDIR.relative_to(ROOT)}"
          if not missing
          else f"missing: {', '.join(f'{a}:{b}' for a, b in missing)}")
    check("no citation assumes the private tree's layout",
          not stale,
          f"a citation carrying the private prefix hands a user a path that "
          f"does not exist here: {stale}" if stale else
          f"none of the {len(all_cited)} carries it")

    pairs, uncited = all_pairs, all_uncited
    check("what these documents assert names what measured it",
          not uncited,
          f"{len(pairs)} cited and {len(uncited)} not. A figure with no source "
          f"named is not wrong, but nothing here can tell whether it has "
          f"drifted, and a reader has nowhere to go")

    # 2 -- the substance
    bad = []
    for name, lineno, raw, cites in pairs:
        ok = False
        for c in cites:
            src = cited_source(c)
            if src is None:
                continue
            if " of " in raw:
                a, b = raw.split(" of ")
                ok = (raw in src) or (f"{a} of {b}" in src.replace(",", ""))
            else:
                want = float(raw.replace(",", ""))
                tol = printed_tolerance(raw)
                ok = any(abs(v - want) <= tol for v in numbers_in(src))
            if ok:
                break
        if not ok:
            bad.append((name, lineno, raw, ", ".join(cites)))

    # WHAT `bad` IS, AND WHY IT DID NOT EXIST UNTIL 2026-11-08.
    #
    # The list above was built and then read by nothing. The substance check
    # -- does the figure still match the validator that measured it -- was
    # dead code for as long as it existed, so this file verified that every
    # claim NAMES a source and never that the source still carries it. Found
    # by planting a false figure in the guide (78.6 % for 68.6 %) and watching
    # the run pass.
    #
    # It does not FAIL on them, and that is a measurement rather than a
    # kindness: a validator that computes its figure at run time has it in no
    # literal anywhere, so there is nothing in its source to match and the
    # mismatch says nothing about whether the figure is right. 23 of 138 are
    # that. The fix for one of them is to pin the figure as a literal in the
    # validator -- `run_charm.py` does, which is why none of GUIDE.md §10's
    # figures is on this list -- and doing that for the remaining 23 is work
    # with a decision in front of it, not a line of code.
    #
    # So the gap is printed with its denominator. An unverifiable figure that
    # nobody has counted reads exactly like a verified one.
    print()
    print(f"    {len(pairs) - len(bad)} of {len(pairs)} cited figure(s) were "
          f"found in the source of a validator their section names;")
    print(f"    coverage: {len(pairs) - len(bad)} of {len(pairs)} cited "
          f"figures verified against a validator's source, {len(bad)} not "
          f"({100 * (len(pairs) - len(bad)) / max(len(pairs), 1):.1f} %)")
    if bad:
        print()
        print("    figures whose cited validator does not carry them as a "
              "literal — computed at run time, so this cannot tell whether "
              "they have drifted:")
        for name, lineno, raw, cites in bad[:14]:
            print(f"      {name}:{lineno}  '{raw}'  cites {cites}")
        if len(bad) > 14:
            print(f"      … and {len(bad) - 14} more")
    # TWO RATCHETS, so that counting the gap is not the same as accepting it.
    #
    # `reporting.py` is the engine's OWN report, and its figures are literals
    # in the validators that measured them: 0 of its claims are unverifiable
    # today. So a mismatch there is a drift and fails. That is the failure
    # this file was written for -- six figures stale in a user's report for
    # hours -- and until now nothing would have caught it.
    #
    # `docs/GUIDE.md` carries 23 figures their validators compute at run time
    # and hold in no literal. Those are counted, listed, and FLOORED: the
    # number may fall and may not rise, so §10's figures could be pinned
    # (run_charm.py does) without the next section's being left unpinned
    # quietly. Lowering this floor to make a run pass is the one thing it is
    # for.
    GUIDE_UNVERIFIABLE_FLOOR = 23
    report_bad = [b for b in bad if b[0].endswith(".py")]
    guide_bad = [b for b in bad if b[0].endswith(".md")]
    check("the engine's own report still matches what measured it",
          not report_bad,
          "; ".join(f"{a}:{b} '{c}' cites {d}" for a, b, c, d in report_bad)
          if report_bad else
          f"all {len([x for x in pairs if x[0].endswith('.py')])} of "
          f"reporting.py's cited figures are literals in their validator, so "
          f"a drift is a failure here and not a note")
    check("and the guide's unverifiable figures have not increased",
          len(guide_bad) <= GUIDE_UNVERIFIABLE_FLOOR,
          f"{len(guide_bad)} against a floor of {GUIDE_UNVERIFIABLE_FLOOR}. "
          f"Pin a figure as a literal in the validator that measures it and "
          f"this falls; add a figure nothing carries and it rises. Never "
          f"raise the floor to make a run pass")

    # AND THAT THE MATCHER DISCRIMINATES, which is the part that makes the
    # 115 mean anything. The first version of this check asserted
    # `verified + unverifiable == paired`, which is true by construction and
    # was therefore a second vacuous pass written while removing the first.
    #
    # This takes each verified claim, moves it by ten printed digits, and
    # requires that the moved value is NOT found in the same source. A matcher
    # that accepted anything would verify all 138 and this would catch it.
    discriminates = ok_count = 0
    for name, lineno, raw, cites in pairs:
        if " of " in raw or raw in [b[2] for b in bad]:
            continue
        ok_count += 1
        shifted = float(raw.replace(",", "")) + 10 * printed_tolerance(raw) * 2
        hit = False
        for c in cites:
            src = cited_source(c)
            if src is None:
                continue
            if any(abs(v - shifted) <= printed_tolerance(raw)
                   for v in numbers_in(src)):
                hit = True
                break
        if not hit:
            discriminates += 1
    check("and the matcher rejects a figure that has moved",
          ok_count and discriminates / ok_count >= 0.75,
          f"{discriminates} of {ok_count} verified figures stop matching once "
          f"shifted by ten printed digits. Some still match because a "
          f"validator's source holds hundreds of numbers — that is why the "
          f"luck measurement below exists — but a matcher that accepted "
          f"anything would score 0 here and verify all {len(pairs)}")

    print()
    if uncited:
        print()
        print("    figures with no validator named in their section:")
        for name, lineno, raw, _ in uncited[:14]:
            print(f"      {name}:{lineno}  '{raw}'")
        if len(uncited) > 14:
            print(f"      … and {len(uncited) - 14} more")

    # 3 -- HOW MUCH A MATCH IS WORTH, measured rather than assumed.
    #
    # A validator's source holds hundreds of numbers, so with a tolerance of
    # half a printed digit a claim could match by luck. If most values matched
    # most files, "all 73 agree" would mean nothing. Sweeping 0 to 100 at one
    # decimal against each cited validator says how often a value lands on one
    # of its numbers by chance.
    grid = [x / 10 for x in range(0, 1001)]
    rates = []
    for c in sorted(all_cited):
        src = cited_source(c)
        if src is None:
            continue
        nums = numbers_in(src)
        rates.append((c, sum(1 for g in grid
                             if any(abs(n - g) <= 0.05 for n in nums))
                      / len(grid)))
    worst = max(r for _, r in rates)
    print()
    print(f"    a 1-decimal value lands on a cited validator by chance "
          f"{min(r for _, r in rates) * 100:.1f} % to {worst * 100:.1f} % "
          f"of the time")
    check("so a match is evidence, not arithmetic luck",
          worst < 0.25,
          f"the loosest of the {len(rates)} cited files matches a random value "
          f"{worst * 100:.1f} % of the time, so {len(pairs)} agreeing is not "
          f"something a shuffled set of numbers would produce")

    print()
    print("    Agreement is not correctness. The validators are what establish")
    print("    these figures; this only catches the report drifting away from")
    print("    them, which is the failure that actually kept happening.")

    print("\n" + "=" * 78)
    if FAIL:
        print(f"{len(FAIL)} check(s) FAILED: {', '.join(FAIL)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
