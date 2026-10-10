# Catalonia's distribution sector, divided

*A finished run, published verbatim. Regenerate it with
`python3 examples/es51_distribution.py`, which needs the archive's 2018 workbook
in `data/mrio/` — `data/mrio/README.md` says where it comes from.*

**What was divided.** `G-I`, Eurostat's A10 grouping of NACE sections G, H and
I, in Catalonia (ES51) in 2018, into trade, transport and hospitality. Driven by
wages, the three come out at **71,879.2**, **22,880.3** and **19,896.1** million.

**On a table that holds more than Catalonia.** The table is the European
multiregional archive loaded with `mrio_scope: with_rest`: thirty sectors in
three blocks — ES51, the rest of its country (**18** regions) and the rest of the
archive (**253**). So the report can answer what a one-region table cannot ask,
which is where an impulse lands: of the output an impulse in `G-I` sets off,
**96.3 %** is produced in Catalonia, **3.2 %** in the rest of Spain and **0.5 %**
further away. A table of ES51 alone would omit **16.4 %** of its output
multipliers.

Read that split as a bound rather than a measurement: the archive keeps trade at
home, and the report says so beside the figures.

## What is real here, and what is not

**Real, and at the table's own year.** The sizes are Eurostat's regional
structural business statistics for Catalonia in 2018 — `sbs_r_nuts06_r2`, which
publishes sections G, H and I separately. No interpolation, no borrowing from
another region, and no vintage gap, which no other example here has had.

**Not real: neither published indicator is output.** The regional statistics
carry local units, wages and persons employed at NUTS-2, and neither turnover nor
value added. The closest available proxy to output is therefore a cost. Wages
drive the split; persons employed is registered and not used, so the engine can
measure the disagreement:

| share of `G-I` given to | by wages | by persons employed |
|---|---:|---:|
| G trade | 62.7 % | 57.9 % |
| H transport | 20.0 % | 16.8 % |
| I hospitality | **17.4 %** | **25.2 %** |

**7.8 points on hospitality.** That is the equal-productivity assumption made
visible: a waiter and a wholesaler do not carry the same output per head, and
whichever key is chosen imposes one ratio. The report prints the gap and does
not rank the two — this project measured, on splits where the office publishes
both the parent and its parts, that least disagreement with your other proxies
does not mean closest to the truth.

**And the table is an estimate.** Every cell of the archive is modelled, and
neither of its accounting identities closes: the row residue is **15.5 %** of
output and the column residue **7.4 %**, both carried in a labelled RESIDUAL row
and column rather than balanced away.

## What the report tells you that a split alone would not

- the three subsectors share the parent's output multiplier, **1.922**, because
  one key splits every block and the weight cancels in `a_ij = Z_ij / X_j`. The
  report says so rather than printing three numbers that look different;
- how risky a split into three parts is, measured on real splits where the
  office publishes both the parent and its parts: a median error of **10.6 %**
  and a worst of **49.2 %** on comparable splits;
- four registered assumptions, including one the engine asked for: `check_split`
  accepts `G-I -> G, H, I` and states that it could not verify the tiling,
  because it does not parse the A10 grouping. That the three sections tile it is
  read from Eurostat's documentation, not derived here.

## Every figure above is in `report.md`

That is checked rather than claimed: `validators/run_public_docs.py` reads this
page, takes every number in it, and fails if one of them is not in the report it
narrates.
