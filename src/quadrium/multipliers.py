"""One complete multiplier table per run: output, income, employment, anything.

WHY THIS MODULE EXISTS
------------------------
The arithmetic was already here and already verified. `diagnostics.py` holds
the Leontief inverse, the output multipliers and the satellite effects;
`run_multipliers.py` checks them against the ONS's own published `Multipliers`
and `Effects` sheets -- **7 variables x 103 industries, 1,434 published figures,
worst error 7.11e-15.** `M-067` states the two formulas as fact on that basis.

What did not exist was a DELIVERABLE. The multipliers reached a user as prose
inside one job's report and as keys inside a diagnostics JSON; the
regionalisation, CHARM and projection jobs emitted nothing multiplier-shaped at
all, and no file anywhere held the table a consultancy report actually prints.
This module builds that table, once, so both doors write the same object.

THE TWO FORMULAS, VERBATIM FROM `M-067`
-----------------------------------------
With `x` industry output, `L = (I - A)^-1`, and `v` ANY row of the table --- a
value-added component, a satellite account, imports, taxes, or output itself:

    direct      d = v / x              what one unit of own output uses
    effect      e = d^T L              what it and its whole supply chain use
    multiplier  m = e / d              total over direct

`UNH_20` para. 20.90 eq. (45) makes the output multiplier the column sum of
`L`, which is the special case `v = x` where `d = 1` and `m = e`. Para. 20.94
eq. (46) gives `Z = B(I - A)^-1` for a satellite. One formula, three uses.

THREE RULES THIS TABLE MAY NOT BREAK
--------------------------------------
They are not style. Each was written down after something went wrong.

1. **Nothing here is called a "multiplier" without its type.** `M-067`:
   "Any output of this project that says 'multiplier' without saying 'type I'
   is making the larger claim silently, and understating by more than half."
   On the UK 2023 table type II is 1.573x type I. Every field name carries
   `_type_i` or `_type_ii`, and `write_multiplier_table` refuses a header that
   does not.

2. **A type II column is a level, not a ranking.** `OQ-T-05` closed on the
   measurement: closed three defensible ways the economy-wide uplift barely
   moves (1.573 / 1.614 / 1.612) while the inter-industry spread nearly halves
   (1.02-3.10 against 1.20-2.31). The Handbook does not say what to divide the
   consumption column by, so an industry league table rests on a choice nobody
   made. The closure used travels with the numbers in `closure`, and the
   writer prints it under them.

3. **A multiplier that should not be published is left EMPTY with its reason.**
   The ONS publishes no multiplier for L68A, Owner-Occupiers' Housing, output
   GBP 260,111 million: imputed rent has no transaction, no employment and no
   supply chain, so a multiplier for it is an artefact of the imputation. The
   engine computes one happily. `exclude` carries the same refusal, and the
   reason is a required argument rather than an optional note, because a blank
   cell with no reason is indistinguishable from a bug.

   Separately, where the direct coefficient is zero there IS no multiplier --
   `m = e / 0`. That comes back NaN and is counted, never replaced with zero.
   And a NEGATIVE multiplier is meaningful on a table with negative
   coefficients (`M-067`: "Do not clamp"), so nothing here clamps.

WHAT THE TABLE CANNOT TELL YOU ABOUT ITSELF
---------------------------------------------
`IOTable` has no price-basis field, and the guide is blunt about why: "Basic
prices and purchasers' prices give different multipliers, and nothing in the
numbers tells you which you have." So `provenance()` QUOTES what the table says
about itself -- its unit, source, classification and lineage -- and writes
`NOT SPECIFIED` where the table is silent, rather than inferring a price basis
from the figures. `M-028` is the reason this matters enough to print: "A
multiplier is meaningless without knowing which of Models A-D generated its
table", and the model, when there was one, is in the lineage.

Cards: `M-067` (the formulas), `M-028` (the inverse and its preconditions),
`M-074` (auditing somebody else's published multipliers with them).
Validator: `library/validators/run_multiplier_table.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

from . import diagnostics


class MultiplierError(ValueError):
    """A multiplier table was asked for in terms this table cannot answer.

    Registered in `TYPES` in `library/tools/sweep_refusals.py` and
    `library/validators/run_refusal_coverage.py` in the same change that
    defined it. That is the rule, and it exists because it was broken:
    `MixedModelError`'s thirteen refusals were invisible to the refusal census
    from the day the mixed model shipped, and `ProxyValueError`'s six had been
    invisible for longer.
    """


# The suffix every multiplier field carries, and the reason rule 1 above can be
# checked rather than trusted. A header that holds the word `multiplier` and
# none of these is a silent type II claim.
TYPE_TAGS = ("_type_i", "_type_ii")


@dataclass
class RowMultipliers:
    """One quantity's direct coefficient, total effect and multiplier.

    `values` are the TOTALS the quantity takes per sector -- the whole wage
    bill, the whole headcount, the whole tonnage -- never the coefficient. The
    coefficient is derived here, which is the same division `Satellite`
    documents and for the same reason: a total is what an office publishes and
    what a split has to divide.
    """
    name: str
    unit: str
    kind: str                     # "output" | "value_added" | "satellite"
    values: np.ndarray            # totals, per sector
    direct: np.ndarray            # v / x; NaN where output is zero
    effect: np.ndarray            # d^T L
    multiplier: np.ndarray        # e / d; NaN where the direct coefficient is 0
    source: str = ""
    labels_summed: list = field(default_factory=list)
    data_status: str = "DERIVED"

    @property
    def undefined(self) -> int:
        """How many sectors have no multiplier, because their direct
        coefficient is zero. A count, so a report can say so instead of
        printing a column of blanks nobody explains."""
        return int(np.isnan(self.multiplier).sum())

    @property
    def indirect_share(self) -> np.ndarray:
        """What fraction of the total effect is NOT the sector's own use.

        `1 - d/e`. NaN where the effect is zero, and it can be negative on a
        table with negative coefficients, which is not an error.
        """
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(self.effect != 0,
                            1.0 - self.direct / np.where(self.effect == 0,
                                                         1.0, self.effect),
                            np.nan)


@dataclass
class MultiplierTable:
    """The deliverable: one row per sector, every multiplier the run can state.

    `suppressed` maps a sector code to the reason its multipliers are not
    published. Those sectors keep their row -- they are still sectors -- and
    every multiplier value in it is NaN.
    """
    table_id: str
    codes: list
    labels: list
    output: RowMultipliers                       # type I, always present
    rows: dict                                   # name -> RowMultipliers
    leontief: dict                               # condition number, negatives…
    provenance: dict                             # what the table says of itself
    output_type_ii: Optional[np.ndarray] = None
    induced_uplift: Optional[np.ndarray] = None
    closure: Optional[dict] = None
    suppressed: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.codes)

    def column_names(self) -> list:
        """Every numeric column this table will write, in order.

        Named here rather than in the writer so the validator can assert rule 1
        against the names themselves, with no file involved.
        """
        out = ["output_multiplier_type_i"]
        if self.output_type_ii is not None:
            out += ["output_multiplier_type_ii",
                    "induced_uplift_type_ii_over_type_i"]
        for name in self.rows:
            out += [f"{name}__direct", f"{name}__effect",
                    f"{name}__multiplier_type_i", f"{name}__indirect_share"]
        return out


def _rowvalues(table, what: str):
    """Resolve one `what` into (values, kind, unit, labels_summed, source).

    A value-added row is named by its own label, and SEVERAL may be summed with
    `;` -- the separator `type_ii_income_rows` already uses, so a workbook does
    not learn two conventions for one idea. Gross value added is three rows on
    the UK table and one on others, which is exactly why this is the user's
    statement about their table and not a name this module knows.
    """
    want = [w.strip() for w in str(what).split(";") if w.strip()]
    if not want:
        raise MultiplierError("nothing was named")

    if len(want) == 1 and want[0].lower() == "output":
        return (np.asarray(table.X, float), "output", table.unit, [], "")

    sats = dict(getattr(table, "satellites", {}) or {})
    if len(want) == 1 and want[0] in sats:
        s = sats[want[0]]
        return (np.asarray(s.values, float), "satellite", s.unit, [],
                f"{s.source} ({s.source_year})")

    va = list(table.VA_labels)
    missing = [w for w in want if w not in va]
    if missing:
        # EVERYTHING THIS TABLE CAN ANSWER, in the refusal itself. A label that
        # is nearly right -- a trailing space, a different dash -- is the
        # common case, and a refusal that only says "no" sends the user to the
        # source workbook to guess.
        raise MultiplierError(
            f"{', '.join(repr(m) for m in missing)} is not a row of "
            f"{table.table_id}. Its value-added rows are: {'; '.join(va)}. "
            f"Its satellite accounts are: "
            f"{'; '.join(sats) if sats else 'none'}. "
            f"Or write `output` for the output multiplier.")
    idx = [va.index(w) for w in want]
    values = np.asarray(table.VA, float)[idx, :].sum(axis=0)
    return (values, "value_added", table.unit, want, table.source)


def multiplier_table(table, *, rows: Optional[Sequence] = None,
                     names: Optional[dict] = None,
                     exclude: Optional[dict] = None) -> MultiplierTable:
    """Build the whole multiplier table for `table`.

    `rows` names the quantities wanted, each one a `what` as `_rowvalues`
    describes it; `None` means every value-added row and every satellite
    account, each on its own. `names` optionally renames a `what` for the
    column header -- `{"Compensation of employees": "wages"}`.

    `exclude` maps a sector code to the REASON its multipliers must not be
    published. The reason is not optional: see rule 3 in this module's header.
    """
    codes = list(table.sector_codes)
    X = np.asarray(table.X, float)
    Z = np.asarray(table.Z, float)
    n = len(codes)

    exclude = dict(exclude or {})
    unknown = [c for c in exclude if c not in codes]
    if unknown:
        raise MultiplierError(
            f"{', '.join(repr(c) for c in unknown)} cannot be excluded from "
            f"{table.table_id}: it is not one of its {n} sectors.")
    blank = [c for c, why in exclude.items() if not str(why or "").strip()]
    if blank:
        raise MultiplierError(
            f"{', '.join(repr(c) for c in blank)} is excluded with no reason. "
            f"A blank cell with no reason beside it cannot be told apart from "
            f"a bug, and the exclusion that makes this feature honest -- the "
            f"ONS's refusal to publish a multiplier for imputed rent -- is "
            f"worth nothing unless the sheet says why.")

    A = diagnostics.technical_coefficients(Z, X)
    L, info = diagnostics.leontief_inverse(A)

    # The negative census and the spectral radius come back from
    # `leontief_inverse`; `n_negative_inverse` is about L itself, which is what
    # `check_leontief_nonnegative` judges and what a user quoting a column sum
    # is actually standing on.
    leontief = dict(info)
    leontief["n_negative_inverse"] = int((L < -1e-9).sum())
    leontief["negative_inverse_columns"] = [
        codes[j] for j in range(n) if (L[:, j] < -1e-9).any()]

    want = list(rows) if rows is not None else (
        list(table.VA_labels) + list(getattr(table, "satellites", {}) or {}))
    names = dict(names or {})

    def build(what: str) -> RowMultipliers:
        values, kind, unit, summed, source = _rowvalues(table, what)
        if values.shape != (n,):
            raise MultiplierError(
                f"{what!r} gives {values.shape[0]} values for {n} sectors")
        with np.errstate(divide="ignore", invalid="ignore"):
            direct = np.where(X != 0, values / np.where(X == 0, 1.0, X),
                              np.nan)
        effect = np.nan_to_num(direct, nan=0.0) @ L
        with np.errstate(divide="ignore", invalid="ignore"):
            mult = np.divide(effect, direct, out=np.full(n, np.nan),
                             where=np.nan_to_num(direct, nan=0.0) != 0)
        return RowMultipliers(
            name=names.get(what, what), unit=unit, kind=kind, values=values,
            direct=direct, effect=effect, multiplier=mult, source=source,
            labels_summed=summed)

    out = build("output")
    out.name = "output"
    built = {}
    for what in want:
        r = build(what)
        if r.name in built:
            raise MultiplierError(
                f"two quantities would both be called {r.name!r}. Give one of "
                f"them its own name, or the two columns cannot be told apart "
                f"in the file.")
        built[r.name] = r

    # ---- type II, only if the workbook declared the closure ---------------
    m2 = uplift = closure = None
    spec = dict(getattr(table, "type_ii", {}) or {})
    if spec:
        va = list(table.VA_labels)
        idx = [va.index(r) for r in spec["income_rows"] if r in va]
        if len(idx) != len(spec["income_rows"]):
            raise MultiplierError(
                f"the type II closure names income rows this table does not "
                f"have: {spec['income_rows']} against {va}")
        if spec["household"] not in list(table.Y_labels):
            raise MultiplierError(
                f"the type II closure names household column "
                f"{spec['household']!r}, and this table's final-demand "
                f"columns are {list(table.Y_labels)}")
        income = np.asarray(table.VA, float)[idx, :].sum(axis=0)
        y = np.asarray(table.Y, float)[:, list(table.Y_labels).index(
            spec["household"])]
        t2 = diagnostics.type_ii_multipliers(A, income, y, X)
        m2 = np.asarray(t2["multipliers"], float)
        with np.errstate(divide="ignore", invalid="ignore"):
            uplift = np.where(out.multiplier != 0, m2 / out.multiplier, np.nan)
        closure = {
            "income_rows": list(spec["income_rows"]),
            "household": spec["household"],
            "propensity": t2["propensity"],
            "income_total": t2["income_total"],
            "household_total": t2["household_total"],
            # THE SENTENCE THE NUMBERS TRAVEL WITH. `OQ-T-05` is closed as
            # NOT SPECIFIED, so this is not a caveat the writer may drop.
            "read_the_uplift_not_the_order":
                "Closed three defensible ways the economy-wide uplift barely "
                "moves (1.573 / 1.614 / 1.612) while the spread between "
                "industries nearly halves (1.02-3.10 against 1.20-2.31). The "
                "Handbook does not say what to divide the consumption column "
                "by, so ranking industries by their type II multiplier rests "
                "on a choice nobody made. Read the uplift; do not read the "
                "order. OQ-T-05, M-067.",
        }

    mt = MultiplierTable(
        table_id=table.table_id, codes=codes,
        labels=list(table.sector_labels), output=out, rows=built,
        leontief=leontief, provenance=provenance(table),
        output_type_ii=m2, induced_uplift=uplift, closure=closure,
        suppressed={c: str(w).strip() for c, w in exclude.items()})

    # Suppression is applied LAST and to the built arrays, not by skipping the
    # sector: the arithmetic is the same for everybody and only the publication
    # is withheld. Doing it earlier would change the inverse, which would make
    # the OTHER sectors' multipliers depend on an editorial decision.
    for code in mt.suppressed:
        j = codes.index(code)
        for r in [out] + list(built.values()):
            r.direct[j] = np.nan
            r.effect[j] = np.nan
            r.multiplier[j] = np.nan
        if m2 is not None:
            m2[j] = np.nan
            uplift[j] = np.nan
    return mt


def known_wrong(prov: dict) -> list:
    """What is measured to be wrong with the multipliers of THIS table.

    Read out of the table's own lineage, not out of the job that is running:
    this is asked of tables some earlier run wrote, and the warning belongs to
    the table rather than to the session. Returns plain sentences.

    ONE SOURCE, because the report and the CSV travel separately. The first
    version computed these in the report alone while a code comment claimed
    the file carried them too -- so the user who opened the file and not the
    report had the silent copy, which is the worse half of the pair.
    """
    lin = " ".join(prov.get("lineage") or []).lower()
    out = []
    if "->" in lin and "::" in lin:
        out.append(
            "THIS TABLE WAS DISAGGREGATED BY THIS ENGINE. If the split was "
            "driven by an allocation key alone, with no input profile, every "
            "subsector carries the SAME multiplier as its parent: the weight "
            "cancels in a_ij = Z_ij / X_j. That is arithmetic, not economics. "
            "Measured: with the key exactly right the subsectors' multipliers "
            "still land a median 7.3 % from the published truth, and 19 of 96 "
            "are out by more than 15 % (run_split_backtest.py).")
    if "region" in lin or "flq" in lin or "slq" in lin or "cilq" in lin:
        out.append(
            "THIS TABLE WAS REGIONALISED BY A LOCATION QUOTIENT. The whole "
            "quotient family overstates local output multipliers, and a blind "
            "delta costs a mean 2.2 points of multiplier bias, worst 6.8. The "
            "run's own report prints the figures and what else the estimate "
            "leaves out (run_flq_delta.py, run_regional_truth_survey.py).")
    if "project" in lin or "sut-ras" in lin or "sut_ras" in lin \
            or "sut-euro" in lin or "sut_euro" in lin:
        out.append(
            "THIS TABLE WAS PROJECTED TO ANOTHER YEAR. Its cells are "
            "ESTIMATED from targets, so these multipliers are an estimate of "
            "a future or past year's multipliers and not a measurement of "
            "one.")
    return out


def provenance(table) -> dict:
    """What the table says about itself, quoted, with `NOT SPECIFIED` where it
    says nothing.

    A multiplier is only comparable with another one computed on the same price
    basis, the same domestic/total treatment and the same transformation model.
    `IOTable` carries no field for the first two, so this does NOT infer them:
    it reports the table's own words and the lineage, and says plainly when the
    table is silent. `M-028`, `M-067` `PRICE_BASIS`.
    """
    text = " ".join(str(x) for x in (
        getattr(table, "unit", ""), getattr(table, "source", ""),
        getattr(table, "notes", "") or "", getattr(table, "table_id", ""),
        " ".join(getattr(table, "lineage", []) or []))).lower()

    if "purchasers" in text and "basic price" not in text:
        basis = "purchasers' prices (from the table's own description)"
    elif "basic price" in text and "purchasers" not in text:
        basis = "basic prices (from the table's own description)"
    else:
        basis = ("NOT SPECIFIED — this table does not say, and the numbers do "
                 "not tell you. Multipliers at basic prices and at "
                 "purchasers' prices are different quantities and must not be "
                 "presented together")

    lineage = list(getattr(table, "lineage", []) or [])
    model = [ln for ln in lineage if "model" in ln.lower()]
    return {
        "table_id": table.table_id,
        "country": getattr(table, "country", ""),
        "year": getattr(table, "year", ""),
        "unit": getattr(table, "unit", ""),
        "classification": getattr(table, "classification", ""),
        "source": getattr(table, "source", ""),
        "price_basis": basis,
        "transformation": (model[-1] if model else
                           "NOT SPECIFIED — no transformation is recorded in "
                           "this table's lineage, so it was read as published "
                           "or built without one. A multiplier is meaningless "
                           "without knowing which of CORE_013's models A–D "
                           "produced its table (M-028)"),
        "lineage": lineage,
        "inherited_residue": float(getattr(table, "inherited_residue", 0.0)),
        # DERIVED is the status of the arithmetic, not of the inputs. A split
        # or regionalised table's cells are ESTIMATED and its multipliers are
        # no firmer than that; the status below says which, from the table's
        # own provenance array rather than from the caller's word.
        "data_status": ("DERIVED from OBSERVED inputs"
                        if getattr(table, "provenance", None) is None else
                        "DERIVED from a table this engine built: its cells "
                        "carry their own ESTIMATED/BALANCED labels and these "
                        "multipliers are no firmer than they are"),
    }
