"""CHARM -- the Cross-Hauling Adjusted Regionalization Method.

The method is `library/specs/B_method_cards/M-075_charm.md`, which is the
contract this module implements. The source is `STE_14` (Kronenberg, *How Can
Regionalization Methods Deal With Cross-Hauling?*, STE Preprint 14,
Forschungszentrum Juelich, 2007), section IV, pp. 24-28 -- the author's own
account of the method the journal article `CORE_037` later published.

WHAT CHARM IS FOR, IN ONE PARAGRAPH
-------------------------------------
Every other non-survey method this engine ships estimates *net* trade. The
commodity balance gives `B = E - M` and then assumes one side of it is zero
(`STE_14` p. 19, citing Moore and Petersen). The location quotient family
nets the same thing out through a scaling rule. Both therefore understate
trade and overstate multipliers, which this project has measured: SLQ
overstates local output multipliers by 6.9 % to 20.0 %. CHARM keeps `B` and
estimates the *volume* `V = E + M` separately, so both sides can be positive
at once. The gap `V - |B|` is cross-hauling, and this project measures it at
28.3 % of Catalonia's trade with the rest of Spain -- a quantity no member of
the quotient family aims at.

WHAT IT DOES NOT FIX
----------------------
CHARM transports one number from the nation to the region: the heterogeneity
`eps`. `run_charm_heterogeneity.py` measured that transport on the one pair
where both tables exist, and it **carries the ordering but not the level**:
rank correlation 0.886 between Spain and Catalonia, but Catalonia's mean
heterogeneity is 1.40x Spain's and the national value under-predicts in 47 of
63 products. The reason is structural rather than the one the literature
alleges -- on international trade alone Catalonia averages 0.85 of Spain, and
only its trade with the rest of Spain carries it above. A region trades more
than its country because what is internal to the country is external to the
region, and that does not shrink with a better classification. Every run
prints this, unasked, the way `regionalise()` prints its own costs.

THE TABLE THIS NEEDS
----------------------
An **indirect allocation** table (`STE_14` pp. 11-12, ESA 95's standard
input-output table). Under direct allocation the imports of commodity `i` are
lumped into the importing sector's input row, so there is no commodity balance
to compute and `A^X` cannot be formed at all -- the source says so outright on
p. 12. This module cannot detect the convention from an array, so it is the
caller's declaration, and `charm()` requires it explicitly rather than
defaulting.

TWO DEFECTS IN THE SOURCE'S OWN PRINTING
------------------------------------------
Both were found by reading the rendered pages, not the text layer, and both
are recorded in `A_core_accounting_spec.md` section A.9.3.

1. **Equation (25), p. 26, prints `E = (V - B)/2`** -- identical to equation
   (24) for `M` on the same page. It cannot be: (22) gives `V = E + M` and
   (23) gives `B = E - M`, so `E = (V + B)/2`. Implemented as the identity
   requires. The arithmetic is checked rather than trusted: `E - M == B` and
   `E + M == V` are asserted on every run.

2. **Equation (23), p. 26, prints `B = X - Z^P - D`**, where equation (3),
   p. 6 defines `Z^P` as interindustry *purchases*, the COLUMN sums. The
   commodity balance needs the ROW sums, `Z^S`. Three things say so: the
   paper's own demand identity (10) with market clearing (13) gives
   `E - M = X - D - Z^S` as algebra; equations (27), (28) and (29) all print
   `Z^S` in the same expression; and the prose of section III.1.2, p. 18
   calls the row totals "the regional intermediate use of the individual
   commodities". Equation (23) is alone against all three. Implemented as
   `Z^S`.

Neither is a transcription error of this project's. They are what the preprint
prints.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

# `run_charm_heterogeneity.py`, Spain against Catalonia on the INE/IDESCAT
# pair, bridged by `run_es_cat_bridge.py`. Measured, not quoted.
MEASURED_TRANSPORT = {
    "rank_correlation": 0.886,
    "mean_heterogeneity_national": 0.217,
    "mean_heterogeneity_regional": 0.303,
    "regional_over_national": 1.40,
    "under_predicted_products": 47,
    "products": 63,
    "mean_absolute_error": 0.117,
    "international_only_ratio": 0.85,
}


def _caveats() -> list[str]:
    m = MEASURED_TRANSPORT
    return [
        "- eps is transported from the nation to the region unchanged. Measured "
        "on Spain against Catalonia, that transport carries the ORDERING "
        f"(rank correlation {m['rank_correlation']}) and not the LEVEL: the "
        f"region's mean heterogeneity is {m['regional_over_national']:.2f}x the "
        f"nation's and the national value under-predicts in "
        f"{m['under_predicted_products']} of {m['products']} products, mean "
        f"absolute error {m['mean_absolute_error']:.3f} against a national mean "
        f"of {m['mean_heterogeneity_national']:.3f}",
        "- the cause is structural, not a classification defect: on "
        f"INTERNATIONAL trade alone the region averages "
        f"{m['international_only_ratio']:.2f} of the nation. The excess comes "
        "from trade with the rest of the country, which is internal to the "
        "nation and external to the region. A finer product classification does "
        "not reduce it",
        "- CHARM estimates a region's trade with EVERYWHERE ELSE as one flow. "
        "It does not split that into trade with the rest of the country and "
        "trade abroad, and interregional cross-hauling between two named "
        "regions is outside it entirely",
        "- regional final use is assumed proportional to the region's share of "
        "national employment (eq. 32). The source names this as the method's "
        "weakest input and says a hybrid approach should replace it with "
        "surveyed household consumption (p. 28)",
    ]


@dataclass
class Heterogeneity:
    """The national heterogeneity `eps`, and the quantities it came from."""

    eps: np.ndarray                 # eq. (29), by commodity
    V: np.ndarray                   # eq. (22), gross trade volume
    B: np.ndarray                   # eq. (23), trade balance
    CH: np.ndarray                  # eq. (26), cross-hauling
    scale: np.ndarray               # X + Z^S + D, eq. (29)'s denominator
    balance_residue: np.ndarray     # (E - M) - (X - Z^S - D), should be ~0
    flags: list[str] = field(default_factory=list)

    @property
    def cross_hauling_share(self) -> float:
        """Cross-hauling as a share of gross trade, the headline quantity."""
        v = self.V.sum()
        return float(self.CH.sum() / v) if v else float("nan")


@dataclass
class Charm:
    """A region's estimated trade pattern, and what the caller should know."""

    X: np.ndarray                   # regional output, eq. (30)
    Z_S: np.ndarray                 # regional intermediate sales, eq. (31)
    D: np.ndarray                   # regional domestic final use, eq. (32)
    B: np.ndarray                   # regional trade balance, eq. (23)
    V: np.ndarray                   # regional trade volume, eq. (28)
    E: np.ndarray                   # regional exports, eq. (25) corrected
    M: np.ndarray                   # regional imports, eq. (24)
    CH: np.ndarray                  # regional cross-hauling, V - |B|
    eps: np.ndarray                 # the heterogeneity transported
    employment_share: float
    caveats: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    @property
    def supply(self) -> np.ndarray:
        """S^R = X^R + M^R, eq. (4)."""
        return self.X + self.M

    @property
    def use(self) -> np.ndarray:
        """U^R = Z^SR + D^R + E^R, eq. (10)."""
        return self.Z_S + self.D + self.E

    @property
    def market_clearing_residue(self) -> np.ndarray:
        """S^R - U^R, eq. (13). The source names this the consistency check."""
        return self.supply - self.use

    def report(self) -> str:
        """The costs, as a block a caller prints beside the numbers."""
        lines = list(self.caveats)
        if self.flags:
            lines.append("")
            lines.extend(self.flags)
        return "\n".join(lines)


def _as_vector(name: str, value, n: Optional[int] = None) -> np.ndarray:
    arr = np.asarray(value, float).ravel()
    if n is not None and len(arr) != n:
        raise ValueError(f"{name} has {len(arr)} sectors against {n}; align the "
                         f"classifications first, do not pad")
    if not np.isfinite(arr).all():
        raise ValueError(f"{name} carries non-finite entries")
    return arr


def national_heterogeneity(X: np.ndarray,
                           Z_S: np.ndarray,
                           D: np.ndarray,
                           E: np.ndarray,
                           M: np.ndarray,
                           *,
                           balance_tolerance: float = 1e-9) -> Heterogeneity:
    """Estimate product heterogeneity from a national table. `STE_14` eq. (29).

        eps = (V - |B|) / (X + Z^S + D)

    with `V = E + M` (22) and `B = E - M` (23). Every argument is a vector
    indexed by **commodity**, from an indirect-allocation table:

        X     domestic production
        Z_S   intermediate SALES of each commodity -- the ROW sums of Z, which
              is `A S` in eq. (2.A). Not the column sums; see this module's
              docstring for why the source's eq. (23) says otherwise
        D     domestic final use, exports excluded
        E     exports
        M     imports

    `B` is computed from `E - M` rather than from `X - Z^S - D` because the
    two are the same quantity by the source's own identity (10) with (13), and
    computing it the first way leaves the second as a check. The residue is
    returned, not swallowed: a table whose supply and use do not balance
    produces an `eps` that absorbs the imbalance, and the caller is entitled to
    see it.
    """
    X = _as_vector("X", X)
    n = len(X)
    Z_S = _as_vector("Z_S", Z_S, n)
    D = _as_vector("D", D, n)
    E = _as_vector("E", E, n)
    M = _as_vector("M", M, n)

    flags: list[str] = []
    for name, arr in (("E", E), ("M", M)):
        bad = np.flatnonzero(arr < 0)
        if bad.size:
            raise ValueError(
                f"{name} is negative in {bad.size} commodit(ies), first at "
                f"index {int(bad[0])} ({arr[bad[0]]:.6g}). CHARM's eq. (26) "
                f"reads V - |B| as cross-hauling, which is only a volume if "
                f"both sides of the trade are non-negative. This project knows "
                f"negatives are legitimate elsewhere in a table; here they are "
                f"not representable, so this refuses rather than returning a "
                f"negative heterogeneity")

    V = E + M                                               # (22)
    B = E - M                                               # (23)
    CH = V - np.abs(B)                                      # (26)
    scale = X + Z_S + D                                     # (29) denominator

    balance_residue = B - (X - Z_S - D)
    worst = float(np.max(np.abs(balance_residue))) if n else 0.0
    span = float(np.max(np.abs(scale))) if n else 0.0
    if span and worst > balance_tolerance * max(span, 1.0):
        flags.append(
            f"! supply and use do not balance: (E - M) differs from "
            f"(X - Z^S - D) by at most {worst:.6g} across {n} commodities. "
            f"eq. (23) states they are the same quantity, so eps absorbs the "
            f"difference")

    zero = np.flatnonzero(scale <= 0)
    if zero.size:
        raise ValueError(
            f"eq. (29)'s denominator X + Z^S + D is non-positive in "
            f"{zero.size} commodit(ies), first at index {int(zero[0])}. "
            f"Heterogeneity is undefined there and substituting a value would "
            f"be inventing one")

    eps = CH / scale                                        # (29)

    high = np.flatnonzero(eps > 1.0)
    if high.size:
        flags.append(
            f"- eps exceeds 1 in {high.size} of {n} commodities (max "
            f"{float(eps.max()):.3f}). That is not an error: eq. (27) makes "
            f"eps a scale factor on X + Z^S + D, not a share of anything, and "
            f"a commodity re-exported more than it is produced and used will "
            f"exceed 1. Recorded because an earlier reading of this formula "
            f"through a secondary source treated the exceedance as a sign the "
            f"denominator was wrong")

    return Heterogeneity(eps=eps, V=V, B=B, CH=CH, scale=scale,
                         balance_residue=balance_residue, flags=flags)


def charm(*,
          A_X: np.ndarray,
          X_national: np.ndarray,
          Z_S_national: np.ndarray,
          D_national: np.ndarray,
          E_national: np.ndarray,
          M_national: np.ndarray,
          L_region: np.ndarray,
          L_national: np.ndarray,
          indirect_allocation: bool,
          eps: Optional[np.ndarray] = None) -> Charm:
    """Estimate a region's trade pattern. `STE_14` section IV.3, pp. 27-28.

    `A_X` is the technical coefficient matrix of eq. (15), `a^X_ij = z_ij / X_j`
    -- divided by domestic **production**, not by total supply. The matrix
    `A = z_ij / S_j` of eq. (1) is a different one and feeding it here scales
    the region's intermediate use by the wrong denominator in every column.
    Equation (15) is computable only from an indirect-allocation table; eq. (31)
    uses it.

    `L_region` and `L_national` are sectoral employment. Equation (30) uses
    them sector by sector for output; equation (32) uses the **aggregate**
    ratio for final use, which is the source's own asymmetry and not a slip --
    see p. 27, where (30) carries the subscript `i` and (32) does not.

    `eps` defaults to the national heterogeneity estimated from the national
    arguments, which is the method. Passing one explicitly is for a caller who
    has measured the region's own, and the measurement this project has says
    the national value under-predicts in 47 of 63 products.

    `indirect_allocation` must be stated. It cannot be inferred from an array,
    and the method does not apply without it.
    """
    if not indirect_allocation:
        raise ValueError(
            "CHARM requires a table with INDIRECT allocation of imports. "
            "`STE_14` p. 12: technical coefficients cannot be calculated from "
            "a direct-allocation table at all, because the imports are lumped "
            "into one row and it is impossible to tell which commodity they "
            "are. Pass indirect_allocation=True only if that is what the table "
            "is")

    A_X = np.asarray(A_X, float)
    X_national = _as_vector("X_national", X_national)
    n = len(X_national)
    if A_X.shape != (n, n):
        raise ValueError(f"A_X must be {n}x{n} to match the {n} commodities of "
                         f"X_national, got {A_X.shape}")
    if not np.isfinite(A_X).all():
        raise ValueError("A_X carries non-finite entries")
    Z_S_national = _as_vector("Z_S_national", Z_S_national, n)
    D_national = _as_vector("D_national", D_national, n)
    E_national = _as_vector("E_national", E_national, n)
    M_national = _as_vector("M_national", M_national, n)
    L_region = _as_vector("L_region", L_region, n)
    L_national = _as_vector("L_national", L_national, n)

    if (L_region < 0).any() or (L_national < 0).any():
        raise ValueError("employment cannot be negative")
    if L_national.sum() <= 0:
        raise ValueError("national employment must be positive")
    bad = np.flatnonzero((L_national <= 0) & (L_region > 0))
    if bad.size:
        raise ValueError(
            f"sector {int(bad[0])} has regional employment and none "
            f"nationally, so eq. (30)'s ratio is undefined. That is a "
            f"classification error upstream, not a value to substitute")

    national = national_heterogeneity(X_national, Z_S_national, D_national,
                                      E_national, M_national)
    if eps is None:
        eps = national.eps
    else:
        eps = _as_vector("eps", eps, n)
    neg = np.flatnonzero(eps < 0)
    if neg.size:
        raise ValueError(
            f"eps is negative in {neg.size} commodit(ies), first at index "
            f"{int(neg[0])}. eq. (28) would then give V < |B| and eq. (24) a "
            f"negative import")

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(L_national > 0, L_region / L_national, 0.0)
    X_r = ratio * X_national                                # (30)
    Z_S_r = A_X @ X_r                                       # (31)
    share = float(L_region.sum() / L_national.sum())
    D_r = share * D_national                                # (32)

    B_r = X_r - Z_S_r - D_r                                 # (23)
    scale_r = X_r + Z_S_r + D_r
    V_r = np.abs(B_r) + eps * scale_r                       # (28)
    M_r = (V_r - B_r) / 2.0                                 # (24)
    E_r = (V_r + B_r) / 2.0                                 # (25), corrected
    CH_r = V_r - np.abs(B_r)

    # The two identities the corrected (25) is there to satisfy. If either
    # fails the arithmetic is wrong, not the data, so this is an assertion and
    # not a flag.
    scale_B = max(1.0, float(np.max(np.abs(B_r)))) if n else 1.0
    scale_V = max(1.0, float(np.max(np.abs(V_r)))) if n else 1.0
    assert np.allclose(E_r - M_r, B_r, rtol=0, atol=1e-9 * scale_B), "E - M != B"
    assert np.allclose(E_r + M_r, V_r, rtol=0, atol=1e-9 * scale_V), "E + M != V"

    flags = list(national.flags)
    for name, arr in (("exports", E_r), ("imports", M_r)):
        bad = np.flatnonzero(arr < 0)
        if bad.size:
            flags.append(
                f"! regional {name} came out negative in {bad.size} "
                f"commodit(ies), worst {float(arr.min()):.6g}. With eps >= 0 "
                f"eq. (28) cannot produce that, so the cause is upstream")
    if share > 1.0:
        flags.append(
            f"! the region's employment is {share:.3f} of the nation's, which "
            f"is more than all of it")

    return Charm(X=X_r, Z_S=Z_S_r, D=D_r, B=B_r, V=V_r, E=E_r, M=M_r, CH=CH_r,
                 eps=np.asarray(eps, float), employment_share=share,
                 caveats=_caveats(), flags=flags)


def commodity_balance(X: np.ndarray,
                      Z_S: np.ndarray,
                      D: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The classical CB approach, for comparison. `STE_14` p. 19.

    Moore and Petersen's rule: if the balance is positive it is all exports and
    imports are zero; if negative, the other way round. Returns `(E, M)`.

    This is exactly `charm()` with `eps = 0`, and the source says so on p. 26
    -- which makes it the degenerate case a test should pin, not a separate
    method. The difference between the two is the whole of what CHARM adds.
    """
    X = _as_vector("X", X)
    n = len(X)
    Z_S = _as_vector("Z_S", Z_S, n)
    D = _as_vector("D", D, n)
    B = X - Z_S - D
    return np.maximum(B, 0.0), np.maximum(-B, 0.0)
