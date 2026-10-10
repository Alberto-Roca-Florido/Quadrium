"""The mixed exogenous/endogenous model: some sectors' OUTPUT is given.

The method is `library/specs/B_method_cards/M-073_mixed_exogenous_endogenous.md`,
which is the contract this module implements. Source: `CORE_085` (Steinback
2004, *The Review of Regional Studies* 34(1): 57-71), eqs. (2)-(4) and the
3 x 3 example of its appendix, which `run_mixed_model.py` reproduces.

WHY LEONTIEF IS NOT ENOUGH
----------------------------
`x = (I - A)^-1 f` takes final demand as given and solves for output. When a
quota, a closure or a plant's capacity fixes a sector's output instead, feeding
that output change in as if it were final demand overstates the effect, because
the sector's own column of the inverse counts again the output it sells to the
others -- `CORE_085` p. 61: "the economy-wide effects would be overestimated".
The mixed model moves the given outputs to the right-hand side and solves for
the rest.

THE ALGEBRA, IN THE FORM THIS MODULE USES
-------------------------------------------
`CORE_085` writes eq. (2) for two sectors with the rows reordered and says the
procedure "is the same for any square set of linear equations" (p. 62). Here the
order is never changed. A switch vector `e` (1 endogenous, 0 exogenous) builds
`E = diag(e)` and

    M = (I - A) E - (I - E)        N = E - (I - A)(I - E)        M z = N v

with `v` holding the known values -- Delta f for endogenous sectors, Delta x for
exogenous ones -- and `z` the unknowns in the same positions: Delta x for
endogenous sectors and, for exogenous ones, the change in final demand that is
consistent with the output fixed for them. Column by column, `M` and `N` are
exactly the matrices of eq. (2): an endogenous column of `M` is that column of
`(I - A)`, an exogenous one is `-e_j`. The switch form is a PROJECT CONVENTION
(no reordering, so results come back in table order); it is the same system.

AND THE CHECK THAT COMES FREE
-------------------------------
`CORE_085` eq. (4) gives a second route to the same answer: set the exogenous
sectors' ROWS of `A` to zero (nobody buys from them inside the model), invert,
and feed the output changes in as final demand. The paper proves the two agree
(pp. 64-66). `output_based_inverse` implements eq. (4) and the validator holds
the two routes to each other on real tables.

WHAT THE MODEL CANNOT SAY
---------------------------
Forward linkages. A fishing quota cut leaves the processors that buy the fish
short of an input; this model does not see that, by construction -- `CORE_085`
p. 59: the approach "is most suitable for modeling capacity constraint scenarios
where there are limited purchases of the exogenized sector(s) outputs by the
other endogenous sectors". `mixed_model_from_table` reports, for every
exogenous sector, the share of its output that other sectors buy as an input,
so a reader can see how much that limitation matters for the case in hand.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np


class MixedModelError(ValueError):
    """The request cannot be solved as stated; the message says why."""


@dataclass
class MixedResult:
    """The solution of `M z = N v`, unpacked into the quantities people use.

    `x` is the change in output of EVERY sector: solved for the endogenous ones,
    the given value for the exogenous ones. `f` is the change in final demand
    of every sector: given for the endogenous ones, the consistent residual for
    the exogenous ones. `z` is the raw solution vector in the source's sense.
    `multipliers` is `M^-1 N`: column j says how much each unknown moves per
    unit of the j-th known value.
    """
    endogenous: np.ndarray
    x: np.ndarray
    f: np.ndarray
    z: np.ndarray
    multipliers: np.ndarray
    condition_number: float
    codes: Optional[list[str]] = None
    forward_share: dict = field(default_factory=dict)

    @property
    def exogenous(self) -> np.ndarray:
        return ~self.endogenous

    def effect(self, coefficients) -> np.ndarray:
        """Sector by sector, `c_j * Delta x_j` for a coefficient per unit of output.

        Jobs, emissions, wages or value added per unit of output: the change in
        that quantity is the coefficient times the change in output, in every
        sector, exogenous ones included -- their output moved by the amount
        given, and that movement has its own direct effect.
        """
        c = np.asarray(coefficients, float).ravel()
        if c.shape != self.x.shape:
            raise MixedModelError(
                f"{c.shape[0]} coefficients for {self.x.shape[0]} sectors")
        return c * self.x


def _switches(n: int, exogenous, codes: Optional[Sequence[str]]) -> np.ndarray:
    """A boolean 'endogenous' mask from a mask, a list of positions or of codes."""
    ex = np.zeros(n, bool)
    items = list(exogenous)
    if len(items) == n and all(isinstance(v, (bool, np.bool_)) for v in items):
        return ~np.asarray(items, bool)
    for item in items:
        if isinstance(item, str):
            if codes is None:
                raise MixedModelError(
                    f"exogenous sector {item!r} named by code, but no codes "
                    f"were given to look it up in")
            if item not in codes:
                raise MixedModelError(
                    f"exogenous sector {item!r} is not a code of this table")
            ex[list(codes).index(item)] = True
        else:
            i = int(item)
            if not 0 <= i < n:
                raise MixedModelError(f"exogenous position {i} outside 0..{n - 1}")
            ex[i] = True
    return ~ex


def _vector(values, n: int, codes, what: str) -> np.ndarray:
    """A length-n vector from an array, or from a {code or position: value} map."""
    if values is None:
        return np.zeros(n)
    if isinstance(values, dict):
        out = np.zeros(n)
        for k, v in values.items():
            if isinstance(k, str):
                if codes is None or k not in codes:
                    raise MixedModelError(f"{what}: {k!r} is not a code of this table")
                out[list(codes).index(k)] = float(v)
            else:
                out[int(k)] = float(v)
        return out
    out = np.asarray(values, float).ravel()
    if out.shape != (n,):
        raise MixedModelError(f"{what} has {out.shape[0]} values for {n} sectors")
    return out


def mixed_model(A, exogenous, delta_x=None, delta_f=None, *,
                codes: Optional[Sequence[str]] = None) -> MixedResult:
    """Solve the mixed model for given outputs and given final demands.

    `A` is any square coefficient matrix -- domestic, regional, or closed with
    a household row and column for type II effects. `exogenous` names the
    sectors whose output is given: a boolean mask, positions, or codes (with
    `codes`). `delta_x` holds the given output changes and may only be non-zero
    for exogenous sectors; `delta_f` holds the final-demand changes of the
    endogenous ones and may only be non-zero for those. Either can be an array
    of length n or a {code or position: value} map. A value on the wrong side
    is refused rather than ignored: it is a request the model cannot honour,
    and silently dropping it would answer a different question.

    With no exogenous sector this IS Leontief, `x = (I - A)^-1 f`, and with every
    sector exogenous it is the accounting identity `f = (I - A) x`; both are
    allowed because they are the two ends of the same model, and the tests use
    them.
    """
    A = np.asarray(A, float)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise MixedModelError(f"A must be square, got shape {A.shape}")
    if not np.isfinite(A).all():
        raise MixedModelError("A has non-finite entries")
    n = A.shape[0]
    if codes is not None and len(codes) != n:
        raise MixedModelError(f"{len(codes)} codes for {n} sectors")

    endo = _switches(n, exogenous, codes)
    dx = _vector(delta_x, n, codes, "delta_x")
    df = _vector(delta_f, n, codes, "delta_f")

    wrong_x = np.flatnonzero(endo & (dx != 0))
    if wrong_x.size:
        raise MixedModelError(
            f"delta_x gives an output change for {wrong_x.size} endogenous "
            f"sector(s) (first: {_name(wrong_x[0], codes)}). An endogenous "
            f"sector's output is what the model solves for; to fix it, make "
            f"the sector exogenous.")
    wrong_f = np.flatnonzero(~endo & (df != 0))
    if wrong_f.size:
        raise MixedModelError(
            f"delta_f gives a final-demand change for {wrong_f.size} exogenous "
            f"sector(s) (first: {_name(wrong_f[0], codes)}). An exogenous "
            f"sector's final demand is the residual the model returns, so it "
            f"cannot also be given.")

    E = np.diag(endo.astype(float))
    I = np.eye(n)
    IA = I - A
    M = IA @ E - (I - E)
    N = E - IA @ (I - E)
    v = np.where(endo, df, dx)

    cond = float(np.linalg.cond(M))
    if not np.isfinite(cond) or cond > 1e14:
        raise MixedModelError(
            f"M is singular or nearly so (condition number {cond:.3g}). The "
            f"endogenous block (I - A_nn) cannot be inverted: some group of "
            f"endogenous sectors buys from itself as much as it produces.")

    MN = np.linalg.solve(M, N)
    z = MN @ v
    x = np.where(endo, z, dx)
    f = np.where(endo, df, z)
    return MixedResult(endogenous=endo, x=x, f=f, z=z, multipliers=MN,
                       condition_number=cond,
                       codes=list(codes) if codes is not None else None)


def output_based_inverse(A, exogenous, *,
                         codes: Optional[Sequence[str]] = None) -> np.ndarray:
    """`CORE_085` eq. (4): the Leontief inverse with exogenous ROWS of A at zero.

    Its exogenous columns are "output-to-output" multipliers: column j says how
    much each sector's output changes when sector j's output is fixed to change
    by one unit, with a 1 on the diagonal and zeros in the other exogenous
    rows. Multiplying it by a vector of given output changes reproduces the
    mixed model's outputs when the endogenous final demands do not change.
    """
    A = np.asarray(A, float)
    n = A.shape[0]
    endo = _switches(n, exogenous, codes)
    At = A.copy()
    At[~endo, :] = 0.0
    return np.linalg.inv(np.eye(n) - At)


def mixed_model_from_table(table, exogenous: Sequence[str], delta_x=None,
                           delta_f=None) -> MixedResult:
    """The mixed model on an `IOTable`, by sector code.

    Builds `A = Z diag(X)^-1` (a sector with no output has no coefficients and
    is refused if named exogenous, since a given change in nothing is not a
    request) and adds, for each exogenous sector, the share of its output that
    other sectors buy as an intermediate input -- the forward linkage this
    model leaves out (`CORE_085` p. 59).
    """
    codes = list(table.sector_codes)
    Z = np.asarray(table.Z, float)
    X = np.asarray(table.X, float).ravel()
    with np.errstate(divide="ignore", invalid="ignore"):
        A = np.where(X > 0, Z / np.where(X > 0, X, 1.0), 0.0)
    for c in exogenous:
        if c in codes and X[codes.index(c)] <= 0:
            raise MixedModelError(
                f"{c!r} has no output in this table, so a given change in its "
                f"output has nothing to scale")
    res = mixed_model(A, exogenous, delta_x, delta_f, codes=codes)
    for k in np.flatnonzero(res.exogenous):
        others = [j for j in range(len(codes)) if j != k]
        res.forward_share[codes[k]] = float(Z[k, others].sum() / X[k])
    return res


def _name(i: int, codes) -> str:
    return codes[i] if codes is not None else f"position {i}"
