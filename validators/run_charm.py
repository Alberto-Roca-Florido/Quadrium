"""CHARM against its source, its degenerate case, and Catalonia's real trade.

The method is `M-075`, implemented in `src/quadrium/charm.py` from `STE_14`
(Kronenberg, *How Can Regionalization Methods Deal With Cross-Hauling?*, STE
Preprint 14, Forschungszentrum Juelich, 2007), section IV, pp. 24-28.

WHY THIS VALIDATOR LOOKS DIFFERENT FROM THE OTHERS, AND SAYS SO
-----------------------------------------------------------------
`run_gras_austria.py` and `run_sut_ras_austria.py` verify an implementation
against the printed intermediates of the source's own worked example. That is
this project's rule, written into `CLAUDE.md` after Box 18.3 printed a final
table that did not follow from its own iterations.

**`STE_14` prints no worked example at all.** There are no numbers to check
against: section IV derives the method and section IV.4 discusses how to embed
it, and the chapter ends. The journal article `CORE_037` applies CHARM to North
Rhine-Westphalia, and `CORE_037` is still held as a DOI link only. So the rule
cannot be followed here, and pretending otherwise by checking the code against
itself would be exactly the vacuous pass this project keeps catching.

What is done instead is stated plainly, in three parts:

  1. **Identities the source states**, each a test the implementation can fail.
     The sharpest is the round trip: estimate `eps` from a table, then hand the
     method that same table as its own "region". It must return that table's
     own exports and imports, to machine precision. It does so only if (28)
     and (29) are mutual inverses AND equation (25) is the corrected form --
     the preprint's own printed (25) fails this test by the whole of `B`.
  2. **The degenerate case the source names**: p. 26 says that with no
     cross-hauling CHARM "becomes equivalent to the classical CB approach".
     Set `eps = 0` and it must reproduce Moore and Petersen's rule exactly.
  3. **A measurement against published truth.** Spain's table and Catalonia's
     both exist. CHARM is given Catalonia's TRUE output and Spain's technology
     and asked for Catalonia's trade; the answer is compared with Catalonia's
     published trade, against the commodity balance as the baseline. Giving it
     the true output removes the employment proxy from the test, so what is
     measured is the trade formula alone -- and so the error found is a FLOOR,
     not an estimate of what a real application would suffer.

Exit 0 pass, 1 fail, 3 checked nothing.

Run:
    python3 validators/run_charm.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

ES = ROOT / "data" / "ine" / "cne_tio_21.xlsx"
CAT = ROOT / "data" / "idescat" / "mioc2021ts64.xlsx"

FAIL = 0
RAN = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global FAIL, RAN
    RAN += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if detail:
        for line in detail.splitlines():
            print(f"         {line}")
    if not ok:
        FAIL += 1


def refuses(name: str, fn, fragment: str) -> None:
    """A refusal is a feature only if it refuses for the stated reason."""
    try:
        fn()
    except Exception as exc:                                # noqa: BLE001
        got = str(exc)
        check(name, fragment.lower() in got.lower(),
              "" if fragment.lower() in got.lower()
              else f"refused, but for {got.splitlines()[0][:70]!r}")
    else:
        check(name, False, "did not refuse")


def toy():
    """A small consistent indirect-allocation table, built to satisfy (13).

    Not a fixture from the source -- the source has none. It exists so the
    identity tests run even with no data files on disk, and it is built so
    supply equals use by construction rather than by adjustment.
    """
    rng = np.random.default_rng(20261107)
    n = 6
    Z = rng.uniform(1.0, 40.0, (n, n))
    X = rng.uniform(200.0, 600.0, n)
    M = rng.uniform(10.0, 120.0, n)
    S = X + M
    Z_S = Z.sum(1)
    E = rng.uniform(5.0, 90.0, n)
    D = S - Z_S - E                       # (13): S = Z^S + D + E
    A_X = Z / X[None, :]                  # (15)
    return dict(Z=Z, X=X, M=M, E=E, D=D, Z_S=Z_S, A_X=A_X, n=n)


def main() -> int:
    warnings.filterwarnings("ignore")
    from quadrium.charm import (charm, commodity_balance,
                                national_heterogeneity)

    print(__doc__.strip().split("Run:")[0].rstrip())
    print("\n" + "=" * 78)
    print("\n  THE SOURCE'S IDENTITIES, ON A CONSISTENT TABLE")
    t = toy()
    n = t["n"]

    h = national_heterogeneity(t["X"], t["Z_S"], t["D"], t["E"], t["M"])

    check("eq. (22) and (23): V = E + M and B = E - M",
          np.allclose(h.V, t["E"] + t["M"]) and np.allclose(h.B, t["E"] - t["M"]))

    # The column sums are what eq. (23) PRINTS. Computing the residue both
    # ways is how the project establishes which superscript the source meant,
    # rather than asserting it.
    Z_P = t["Z"].sum(0)
    res_S = np.max(np.abs((t["E"] - t["M"]) - (t["X"] - t["Z_S"] - t["D"])))
    res_P = np.max(np.abs((t["E"] - t["M"]) - (t["X"] - Z_P - t["D"])))
    check("eq. (23) holds with the ROW sums Z^S and fails with the column "
          "sums Z^P it prints",
          res_S < 1e-9 and res_P > 1.0,
          f"worst residue {res_S:.3e} with Z^S against {res_P:,.1f} with Z^P. "
          f"The source's eqs. (27), (28) and (29) all print Z^S, and its own "
          f"identities (10) and (13) give E - M = X - D - Z^S as algebra. "
          f"Equation (23) is alone against all three")
    check("eq. (26): V = |B| + CH, so CH = 2 min(E, M)",
          np.allclose(h.CH, 2.0 * np.minimum(t["E"], t["M"])),
          "this is why the secondary rendering in CORE_039 p. 299 and the "
          "primary agree: (e + m - |e - m|) IS V - |B|")
    check("eq. (29)'s denominator is X + Z^S + D, as the primary prints it",
          np.allclose(h.scale, t["X"] + t["Z_S"] + t["D"]),
          "CORE_039 p. 299 renders the same denominator. The primary confirms "
          "the secondary this project had been relying on")
    check("the headline share summarises the vectors it is derived from",
          abs(h.cross_hauling_share - float(h.CH.sum() / h.V.sum())) < 1e-15
          and 0.0 <= h.cross_hauling_share <= 1.0,
          f"cross-hauling is {h.cross_hauling_share * 100:.1f} % of gross trade "
          f"on this table. It is the same quantity "
          f"run_regionalisation_crosshauling.py measures at 28.3 % for "
          f"Catalonia against the rest of Spain")

    print("\n  THE ROUND TRIP -- the test the source's printed eq. (25) fails")
    L = np.full(n, 1000.0)
    r = charm(A_X=t["A_X"], X_national=t["X"], Z_S_national=t["Z_S"],
              D_national=t["D"], E_national=t["E"], M_national=t["M"],
              L_region=L, L_national=L, indirect_allocation=True)
    worst_e = float(np.max(np.abs(r.E - t["E"])))
    worst_m = float(np.max(np.abs(r.M - t["M"])))
    check("a region identical to the nation gets the nation's own trade back",
          worst_e < 1e-9 and worst_m < 1e-9,
          f"exports out by at most {worst_e:.3e}, imports {worst_m:.3e}")

    # What the source's printed (25) would have given, computed here rather
    # than described, so the claim that it is wrong is a measurement.
    E_as_printed = (r.V - r.B) / 2.0
    gap = float(np.max(np.abs(E_as_printed - t["E"])))
    check("and the preprint's printed eq. (25) would have got it wrong by B",
          gap > 1e-6 and np.allclose(E_as_printed - r.E, -r.B),
          f"E = (V - B)/2 as printed on p. 26 misses by up to {gap:,.2f}, "
          f"which is exactly the trade balance. It is identical to eq. (24) "
          f"for M on the same page, so it cannot be right")

    check("eq. (24)/(25) keep E - M = B and E + M = V",
          np.allclose(r.E - r.M, r.B) and np.allclose(r.E + r.M, r.V))
    check("eq. (13): the region's supply clears against its use",
          float(np.max(np.abs(r.market_clearing_residue))) < 1e-9,
          f"worst {float(np.max(np.abs(r.market_clearing_residue))):.3e} -- "
          f"the source names this its consistency check, p. 28")
    check("exports and imports are both non-negative",
          bool((r.E >= 0).all() and (r.M >= 0).all()))

    print("\n  THE DEGENERATE CASE THE SOURCE NAMES (p. 26)")
    half = np.full(n, 500.0)
    z = charm(A_X=t["A_X"], X_national=t["X"], Z_S_national=t["Z_S"],
              D_national=t["D"], E_national=t["E"], M_national=t["M"],
              L_region=half, L_national=L, indirect_allocation=True,
              eps=np.zeros(n))
    cb_e, cb_m = commodity_balance(z.X, z.Z_S, z.D)
    check("with eps = 0 CHARM is exactly the commodity balance",
          np.allclose(z.E, cb_e) and np.allclose(z.M, cb_m),
          "p. 26: 'our approach becomes equivalent to the classical CB "
          "approach outlined above'")
    check("and one side of every commodity's trade is then zero",
          bool(np.all(np.minimum(z.E, z.M) < 1e-12)),
          "which is the defect CHARM exists to remove")

    live = charm(A_X=t["A_X"], X_national=t["X"], Z_S_national=t["Z_S"],
                 D_national=t["D"], E_national=t["E"], M_national=t["M"],
                 L_region=half, L_national=L, indirect_allocation=True)
    check("with the estimated eps, trade volume is larger than the CB's",
          float(live.V.sum()) > float(z.V.sum()),
          f"{live.V.sum():,.1f} against {z.V.sum():,.1f}. p. 28 predicts this "
          f"and says it is why CHARM's multipliers come out smaller")
    check("and the two agree on the balance, which neither is free to move",
          np.allclose(live.B, z.B),
          "CHARM changes the VOLUME of trade, never its net. Any method that "
          "moved B would be changing the regional accounts, not estimating "
          "trade")

    print("\n  WHAT IT REFUSES")
    base = dict(A_X=t["A_X"], X_national=t["X"], Z_S_national=t["Z_S"],
                D_national=t["D"], E_national=t["E"], M_national=t["M"],
                L_region=L, L_national=L)
    refuses("a direct-allocation table, which has no commodity balance at all",
            lambda: charm(**base, indirect_allocation=False),
            "INDIRECT allocation")
    refuses("a negative export, which makes V - |B| not a volume",
            lambda: national_heterogeneity(t["X"], t["Z_S"], t["D"],
                                           np.r_[-1.0, t["E"][1:]], t["M"]),
            "negative")
    refuses("a negative eps, which would give a negative import",
            lambda: charm(**base, indirect_allocation=True,
                          eps=np.r_[-0.1, np.zeros(n - 1)]),
            "negative")
    refuses("regional employment in a sector the nation does not have",
            lambda: charm(**{**base, "L_national": np.r_[0.0, L[1:]]},
                          indirect_allocation=True),
            "undefined")
    refuses("a classification that does not line up",
            lambda: charm(**{**base, "L_region": L[:-1]},
                          indirect_allocation=True),
            "do not pad")

    print("\n" + "=" * 78)
    print("  AGAINST PUBLISHED TRUTH: Catalonia's trade, from Spain's table")

    if not (ES.exists() and CAT.exists()):
        print("\n  The measurement needs both tables and at least one is "
              "absent:")
        for p in (ES, CAT):
            print(f"    {'present' if p.exists() else 'ABSENT '}  {p}")
        print("\n  The identity and refusal checks above did run. The "
              "measurement did not,")
        print("  and a run that checked only the arithmetic is not a run that "
              "checked the method.")
        if FAIL == 0:
            # The line check.sh parses, so the suite can name the reason
            # instead of printing the skip with a blank beside it.
            print("Nothing was checked: the measurement needs both published "
                  "tables.")
        return 3 if FAIL == 0 else 1

    from run_es_cat_bridge import to_catalan_products as fold

    from quadrium.io_loader import load_idescat_mioc, load_ine_tio

    es = load_ine_tio(ES, variant="total")
    cat = load_idescat_mioc(CAT)

    # The three vectors come off the loader's own declaration now. Until
    # 2026-11-08 they were `Y[:, 5] + Y[:, 6]`, `-Y[:, 7]` and `Y[:, 0:5]`
    # written in here, one set of column numbers per country, and the Catalan
    # imports came from a derivation held in a sibling validator that does not
    # travel to the public tree. run_trade_block.py checks that the
    # declaration reproduces those indices to zero.
    E_es, M_es, D_es = es.trade_vectors()
    e_es, m_es, d_es = fold(E_es), fold(M_es), fold(D_es)
    x_es = fold(es.X)
    z_es = fold(es.Z.sum(1))

    e_ca = cat.exports_by_product()
    m_ca = cat.imports_by_product()
    x_ca = cat.X

    check("both tables loaded and fold onto the same 63 products",
          len(x_es) == len(x_ca) == 63,
          f"Spain {len(x_es)}, Catalonia {len(x_ca)} after the bridge of "
          f"run_es_cat_bridge.py")

    # Spain's technical coefficients, eq. (15). The fold is applied to both
    # axes of Z before dividing, so the matrix and the output vector are on
    # the same 63 products.
    Z_es = fold(fold(es.Z).T).T
    with np.errstate(divide="ignore", invalid="ignore"):
        A_X_es = np.nan_to_num(Z_es / np.where(x_es > 0, x_es, np.nan)[None, :])

    # The employment proxy is REMOVED from this test on purpose: L^R/L^N is
    # set to Catalonia's true output share, so eq. (30) returns Catalonia's
    # published output exactly and what is measured is the trade formula.
    with np.errstate(divide="ignore", invalid="ignore"):
        share = np.where(x_es > 0, x_ca / x_es, 0.0)
    L_nat = np.ones(len(x_es))

    res = charm(A_X=A_X_es, X_national=x_es, Z_S_national=z_es,
                D_national=d_es, E_national=e_es, M_national=m_es,
                L_region=share, L_national=L_nat, indirect_allocation=True)
    check("eq. (30) returns Catalonia's published output, as the test intends",
          float(np.max(np.abs(res.X - x_ca))) < 1e-6,
          f"worst {float(np.max(np.abs(res.X - x_ca))):.3e} -- the employment "
          f"proxy is out of this measurement, so the error below is CHARM's "
          f"trade formula alone and is a FLOOR")

    # The same property on the two PUBLISHED economies, which is the figure
    # this project has quoted since v1.77 and had never computed through the
    # engine's own object.
    h_es = national_heterogeneity(x_es, z_es, d_es, e_es, m_es)
    h_ca = national_heterogeneity(x_ca, cat.Z.sum(1), cat.Y[:, 0:4].sum(1),
                                  e_ca, m_ca)
    # WHERE THE 1.40x IN eps ACTUALLY COMES FROM.
    # This check was first written the other way round -- "Catalonia
    # cross-hauls a larger share of its trade than Spain" -- and FAILED. The
    # measurement is the finding: the two shares are nearly equal, so the
    # heterogeneity gap of v1.78 is not a difference in how much of its trade
    # a region doubles back. It is a difference in how much it trades.
    #   eps = CH / (X + Z^S + D) = (CH / V) . (V / (X + Z^S + D))
    # The left factor is the same in both economies; the right one is not.
    i_es = float(h_es.V.sum() / h_es.scale.sum())
    i_ca = float(h_ca.V.sum() / h_ca.scale.sum())
    check("the heterogeneity gap is trade INTENSITY, not a propensity to "
          "cross-haul",
          abs(h_ca.cross_hauling_share - h_es.cross_hauling_share) < 0.05
          and i_ca / i_es > 1.2,
          f"cross-hauling as a share of gross trade: Spain "
          f"{h_es.cross_hauling_share * 100:.1f} %, Catalonia "
          f"{h_ca.cross_hauling_share * 100:.1f} % -- the same within "
          f"{abs(h_ca.cross_hauling_share - h_es.cross_hauling_share) * 100:.1f} "
          f"points. Trade as a share of X + Z^S + D: Spain "
          f"{i_es * 100:.1f} %, Catalonia {i_ca * 100:.1f} % -- "
          f"{i_ca / i_es:.2f}x. Aggregate eps is the product of the two, "
          f"{h_ca.CH.sum() / h_ca.scale.sum() / (h_es.CH.sum() / h_es.scale.sum()):.2f}x, "
          f"and ALL of it is the second factor. Two numbers here are NOT the "
          f"ones OQ-R-01 quotes and must not be read as them: its 1.40x is a "
          f"mean of per-product eps on the total-supply denominator, and its "
          f"28.3 % is min(E, M) over gross on Catalonia's trade with the rest "
          f"of Spain alone. Both are different quantities on different bases. "
          f"What carries across is the DIRECTION, and this decomposition says "
          f"where it comes from")

    cb_e, cb_m = commodity_balance(res.X, res.Z_S, res.D)

    def err(est, truth):
        tot = float(truth.sum())
        return (abs(float(est.sum()) - tot) / tot * 100.0,
                float(np.abs(est - truth).sum()) / tot * 100.0)

    print()
    print(f"    {'':<24}{'total err %':>13}{'by-product err %':>19}")
    for label, e_hat, m_hat in (("commodity balance", cb_e, cb_m),
                                ("CHARM", res.E, res.M)):
        te, pe = err(e_hat, e_ca)
        tm, pm = err(m_hat, m_ca)
        print(f"    {label + ', exports':<24}{te:>13.1f}{pe:>19.1f}")
        print(f"    {label + ', imports':<24}{tm:>13.1f}{pm:>19.1f}")

    cb_vol = float(cb_e.sum() + cb_m.sum())
    ch_vol = float(res.E.sum() + res.M.sum())
    true_vol = float(e_ca.sum() + m_ca.sum())
    check("the commodity balance understates Catalonia's trade, as the whole "
          "literature says",
          cb_vol < true_vol,
          f"CB estimates {cb_vol:,.0f} against a published {true_vol:,.0f} -- "
          f"{(1 - cb_vol / true_vol) * 100:.1f} % short")
    check("CHARM closes part of that gap",
          ch_vol > cb_vol,
          f"CHARM {ch_vol:,.0f}, CB {cb_vol:,.0f}, published {true_vol:,.0f} "
          f"-- CHARM recovers "
          f"{(ch_vol - cb_vol) / max(true_vol - cb_vol, 1e-9) * 100:.1f} % of "
          f"the shortfall the CB leaves")

    cross_true = float(np.minimum(e_ca, m_ca).sum())
    cross_charm = float(np.minimum(res.E, res.M).sum())
    check("and it produces cross-hauling where the CB produces none at all",
          cross_charm > 0 and float(np.minimum(cb_e, cb_m).sum()) == 0.0,
          f"CHARM {cross_charm:,.0f} against a published {cross_true:,.0f} "
          f"({cross_charm / cross_true * 100:.1f} % of it). The CB's is zero "
          f"by construction, in 63 of 63 products")

    # THE HEADLINE FIGURES, PINNED AS LITERALS, and that is the point of
    # writing them out again rather than only printing them.
    #
    # `docs/GUIDE.md` §10 quotes these to a reader choosing between this and
    # the location quotient family, and `run_report_claims.py` checks a guide
    # figure by looking for it IN THE SOURCE of the validator its section
    # names. A figure this file only ever computed at run time could not be
    # found there, so the guide's copy of it was unverifiable -- it would have
    # drifted in silence, which is the exact failure that validator exists
    # against. Written here, a measurement that moves fails this check and the
    # guide is what gets corrected.
    short_pct = (1 - cb_vol / true_vol) * 100
    recovered_pct = (ch_vol - cb_vol) / max(true_vol - cb_vol, 1e-9) * 100
    cross_pct = cross_charm / cross_true * 100
    for label, got, want in (
            ("the CB is 64.8 % short of the published total", short_pct, 64.8),
            ("CHARM recovers 68.6 % of that shortfall", recovered_pct, 68.6),
            ("and produces 65.1 % of the published cross-hauling",
             cross_pct, 65.1),
            ("CHARM itself is still 20.4 % short of the published total",
             (1 - ch_vol / true_vol) * 100, 20.4)):
        check(label, abs(got - want) <= 0.05,
              f"{got:.1f} % against the {want} % the guide quotes — half the "
              f"last printed digit, the same rule run_report_claims.py "
              f"applies to a sentence")
    check("the published total and both estimates are these",
          abs(true_vol - 275062) < 1 and abs(cb_vol - 96954) < 1
          and abs(ch_vol - 219056) < 1,
          f"published {true_vol:,.0f}, CB {cb_vol:,.0f}, CHARM {ch_vol:,.0f} "
          f"million EUR — pinned so the guide's table cannot outlive them")

    print("\n  WHAT THE RUN PRINTS WITHOUT BEING ASKED")
    print(res.report())
    check("the measured cost of the transported eps is printed, unasked",
          "0.886" in res.report() and "1.40" in res.report()
          and "47 of 63" in res.report() and "0.117" in res.report(),
          "M-075 and regionalise.py follow the same rule: CORE_036 p. 35, no "
          "refuge in a mechanically produced figure — and the guide quotes all "
          "four, so they are asserted here rather than merely printed")

    print("\n" + "=" * 78)
    print(f"  {RAN} checks, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:                                # noqa: BLE001
        print(f"\n  CHECKED NOTHING: {type(exc).__name__}: {exc}")
        sys.exit(3)
