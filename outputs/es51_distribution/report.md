# Catalonia's distribution sector, divided, on a table that holds the rest of Spain and the rest of Europe
Generated 2026-09-27 12:35 UTC · Quadrium 0.2.0

**Read the assumption ledger before quoting any number.** The sizes are Eurostat's own for Catalonia at this table's own year; the table they divide is an estimate whose identities do not close, and the two published indicators that could drive the split disagree by 7.8 points on accommodation and food.

**2 scenario(s)** · 1 sector(s) divided: `G-I` into G, H, I

---

## Original table

- **Source:** Huang, S. & Koutroumpis, P. (2023), European multi regional input output data for 2008-2018, Scientific Data 10, 218, doi:10.1038/s41597-023-02117-y; Zenodo record 7875024, CC BY 4.0 (MRIO_2018_272regions.xlsx, Final_demand_2018.xlsx, TAXSUB_VA_2018.xlsx)
- **Reference year:** 2018 · **Unit:** million US dollars: Huang & Koutroumpis (2023) state it, and the archive's own country totals are Eurostat's value added converted at each year's euro-dollar rate, which no other currency fits (`run_mrio_scale.py`); price basis not stated · **Classification:** 10 sectors, NACE Rev. 2 sections grouped as the archive groups them, in three blocks; NUTS-2 as coded in the archive
- **What the loader decided when reading this file:** THREE BLOCKS THAT COVER THE ARCHIVE: ES51, the rest of ES (18 regions) and the rest of the archive (253 regions). Every cell is the archive's own flows added up, and this region's own block is the one-region table's cell for cell. Because the three cover the archive, the trade between regions is intermediate demand here rather than a final-demand column: what a one-region table omits -- 16.4 % of this region's output multipliers, nearly all of it output set off in the other two blocks rather than a return to this one -- is inside these multipliers. What it costs is that the other two blocks are aggregates, whose technology is a mix of the regions inside them. NEITHER IDENTITY CLOSES IN THIS ARCHIVE: the row residue is 15.5 % of output and the column residue 7.4 %, both carried in a labelled RESIDUAL column and row computed here. NPISH is identical to GGFC on every row of the final-demand file and was dropped rather than counted twice. A sector code names THIS region's block: the three blocks carry the same ten codes, as an interregional table must, and this region goes first, so a split of `G-I` divides ES51's G-I and not an aggregate's. Every cell is ESTIMATED, as the whole archive is, and the unit is the archive's.
- ⚠️ **The input table is not a publication.** It is itself a product of this engine: **900 of its 900 intermediate cells (100.0 %) were already estimates before this run began**, and every figure below inherits them. What was done to it, oldest first:
  1. (not recorded)

### What this table holds that a one-region table cannot

Three blocks — `ES51`, the rest of its country (18 regions) and the rest of the archive (253 regions) — which between them cover the archive. So what an impulse sets off in the other two — which a one-region table cannot hold — is **inside the multipliers below**, and the trade between regions is intermediate demand rather than a final-demand column. A table of `ES51` alone would omit **16.4 %** of its output multipliers; across the archive the median is 11.7 %.

What it costs: the other two blocks are aggregates, and an aggregate's technology is a mix of the regions inside it. This table answers what this region's demand sets off everywhere, not what each other region does. A sector code names `ES51`'s own block, which is what a split divides.

**How much of this stays here is the archive's answer, and it is drawn in favour of here.** The archive records about a quarter of the purchases a region makes from the rest of its country, against the surveys that can check it. Give nine surveyed regions the purchases their own surveys record and the total an impulse sets off barely moves — a median -0.1 % — while the share of it that stays in the region falls from a median 88.9 % to 72.7 %. So trust the total; read the split as a bound (`run_wide_against_surveys.py`).

Where an impulse lands, by the sector it starts in — the share of the output one unit of demand sets off that is produced in each block. The last column is the same quantity measured on all 2,720 units of the archive rather than on these three, so it and the first column should add to a hundred; over 7 regions they differ by a median 0.05 points and at most 1.7 (`run_eu_mrio_wide.py`). These are 2018's: across the deposit's 11 years the share that stays in a region moves a median 4.0 points between its highest and lowest year, at most 4.6.

| sector | stays in `ES51` | `ES_REST` | `REST` | a one-region table omits |
|---|---:|---:|---:|---:|
| `A` | 46.2 % | 44.4 % | 9.4 % | 53.9 % |
| `B-E` | 92.6 % | 6.2 % | 1.2 % | 7.5 % |
| `F` | 70.5 % | 25.9 % | 3.6 % | 29.6 % |
| `G-I` | 96.3 % | 3.2 % | 0.5 % | 3.7 % |
| `J` | 96.8 % | 2.8 % | 0.5 % | 3.2 % |
| `K` | 85.4 % | 12.7 % | 1.8 % | 14.6 % |
| `L` | 93.9 % | 5.5 % | 0.6 % | 6.1 % |
| `M_N` | 97.1 % | 2.5 % | 0.4 % | 2.9 % |
| `O-Q` | 91.2 % | 7.8 % | 0.9 % | 8.8 % |
| `R-U` | 92.3 % | 6.5 % | 1.1 % | 7.7 % |

**Scenario `__original__`** — PASSED

- `OK  ` **check_original_balance** — row balance max dev 0 against 1e-06, column balance max dev 0 against 1e-06 — derived from float64 accumulation over the terms summed — this source does not round  
  <sub>ID-11 / ID-02, A_core_accounting_spec.md §A.6; D_open_questions.md OQ-B-02</sub>
- `OK  ` **check_sign_structure** — 71 negative cell(s): Z=20, Y=22, VA=29. Negatives are legitimate and select GRAS over RAS; they are not an error.  
  <sub>A_core_accounting_spec.md §A.8.1; CORE_012 ¶11.66, pp. 333–334</sub>
- `OK  ` **check_zero_output** — all sectors have non-zero output
- `OK  ` **check_leontief_productive** — spectral radius of A = 0.550822 (must be < 1), largest column sum 0.7814. Below 1 the Neumann series converges, the inverse is non-negative and a multiplier means what it says; at or above it the economy consumes at least as much as it makes and the multipliers are not large but undefined  
  <sub>ID-12, CORE_005 ¶36.36–36.39, pp. 1015–1016</sub>
- `OK  ` **check_leontief_identity** — max |Ax + y − x| = 1.86e-09 against 1e-06; the same statement through the inverse, max |Ly − x| = 1.86e-09 against 5.96e-06, which is that bound amplified by ‖L‖∞ = 5.96. Both are accounting, bounded by this source's own printed precision and by how far its books were already out  
  <sub>ID-12, CORE_005 ¶36.36, p. 1015</sub>
- `OK  ` **check_leontief_nonnegative** — every cell of the Leontief inverse is non-negative, so each multiplier is a sum of same-signed terms  
  <sub>ID-12</sub>
- `OK  ` **check_leontief_inverse** — ‖(I−A)L − I‖ = 6.66e-16 against 6.76e-13 for a matrix with condition number 3. This one is arithmetic and nothing else: it asks whether the inverse was computed, not whether the table adds up. An ill-conditioned system loses digits no source precision can restore  
  <sub>ID-12, CORE_005 ¶36.37, p. 1015</sub>

> Solver convergence is necessary but **not sufficient** for statistical validity (CORE_006 ¶9.51, p. 288; CORE_012 ¶11.105, pp. 342–343).

---

## Scenario `S1_wages`

### Balancing

- **Method: GRAS** — 56 negative cell(s) in the expanded table; RAS is undefined there (CORE_012 Box 11.3, p. 345)
- Converged: True; iterations by split: G-I 1
- Max deviation from target row / column totals: 9.31e-10 / 2.33e-10
- Negatives: 56 in the seed, 56 in the result, **0 sign changes**

### `G-I` — Distribution

| Block | Key | Chosen? | Strength | Year | vs table | Weights |
|---|---|---|---|---|---|---|
| output | `key_wages_sbs_2018` | chosen | medium | 2018 | same year | 0.627, 0.200, 0.174 |
| final_demand | `key_wages_sbs_2018` | inherited | medium | 2018 | same year | 0.627, 0.200, 0.174 |
| value_added | `key_wages_sbs_2018` | inherited | medium | 2018 | same year | 0.627, 0.200, 0.174 |
| intermediate_rows | `key_wages_sbs_2018` | inherited | medium | 2018 | same year | 0.627, 0.200, 0.174 |
| intermediate_cols | `key_wages_sbs_2018` | inherited | medium | 2018 | same year | 0.627, 0.200, 0.174 |

**How wrong will each subsector's SIZE be?**

| Subsector | share of the parent | typical | p90 |
|---|---:|---:|---:|
| `G` | 62.7% | 12 % | 44 % |
| `H` | 20.0% | 37 % | 137 % |
| `I` | 17.4% | 42 % | 158 % |

> A proportional split gives each part `share x parent output`, so an error of *e* **points** in a share is an error of `e / share` in that part's own size. The two columns put the median and p90 error of a real downloadable key — 7.3 and 27.4 points (`validators/run_real_key.py`) — through that division. Measured on 1,583 subsector-and-proxy pairs, the typical column runs about 0.65 of the truth and the p90 column contains it **92 %** of the time, holding at 88.7 to 92.9 % with each country held out.
>
> **A small part is where this bites.** A few points of key error is the whole of a 5 % subsector. If your key came from the office's own published split for another year rather than from a proxy, use 1.2 points instead of 7.3 (`validators/run_key_carryover.py`) and these numbers fall by six. See `validators/run_size_screen.py`.


- `key_wages_sbs_2018` — Eurostat, Structural business statistics by NUTS 2 region and NACE Rev. 2 (sbs_r_nuts06_r2), Catalonia, 2018, wages and salaries (V13320), million euro

*inherited* — no key was named for that block, so it took the output key. That is a default, not a decision by the analyst, and it means the block carries whatever the output proxy implies rather than a measurement of its own.

| Subsector | Output | Intermediate sales | Final demand | Value added | Output multiplier |
|---|---:|---:|---:|---:|---:|
| G | 71,879.2 | 34,822.8 | 37,056.4 | 40,131.5 | 1.922 |
| H | 22,880.3 | 11,084.6 | 11,795.6 | 12,774.5 | 1.922 |
| I | 19,896.1 | 9,638.9 | 10,257.2 | 11,108.3 | 1.922 |

*Corroboration against `key_headcount_sbs_2018` (medium, 2018), which did **not** drive this split:*

| Subsector | implied by the split | measured | gap |
|---|---:|---:|---:|
| G | 0.6269 | 0.5791 | +8.2% |
| H | 0.1996 | 0.1684 | +18.5% |
| I | 0.1735 | 0.2525 | -31.3% |

Largest disagreement **31.3%**, against the `output` weights. Every other check in this report asks whether the arithmetic is self-consistent and would pass on any key; this one asks whether an independent measurement agrees. Source: Eurostat, Structural business statistics by NUTS 2 region and NACE Rev. 2 (sbs_r_nuts06_r2), Catalonia, 2018, persons employed (V16110), number

*Classification:* G-I -> G, H, I: codes are not in a recognised classification, so the hierarchy was not checked

*Headroom:* the tightest subsector still has 2,358.00 of internal trade left, 17.4 % of this sector's own diagonal of 13,588.5. That margin is the budget any differentiated input structure has to fit inside — a sector that barely trades with itself leaves little room to claim its subsectors buy differently.

*Input structures:* these subsectors buy the **same mix** in different amounts — cosine distance -0.00000, effectively zero. Each is a scaled copy of the parent's input structure, so any difference in their multipliers is an artefact of the internal block, not a finding. Supply `input_profiles` to give them genuinely different purchasing patterns.

> **What a profile is worth, measured.** On 96 splits where the office publishes both the parent and its parts, giving the engine the parts' TRUE input profile moves the SEED's multiplier error from a median 7.78 % to 3.48 %. **The balancer then gives all of that back**: the delivered table is a median 7.79 % against 7.78 % for using no profile at all, and it beats doing nothing in 30 of 56. Balancing adjusts the internal block only — correct when a split is proportional, since nothing else moves — so a profiled column pushes the whole adjustment into the least reliable part of the table. The engine also refuses the profiled scenario outright in 19 of 54.
>
> **Borrowing one from a country that publishes your split is a coin flip** — 162 borrowings, better in 78 and worse in 84, helping by a median 4.2 points and hurting by 3.1. It helps where the split was going badly anyway and hurts where it was fine (r = +0.42 against the baseline error), which is only knowable afterwards; the ex-ante screen does not predict it (r = +0.17 for the parent multiplier, -0.22 for the number of parts). See `validators/run_input_profiles_backtest.py`.

The estimated **internal block** for this sector is 0.08 % of the absolute value of the intermediate matrix. It has no direct observation behind it: the original table held a single diagonal cell of 13,588.5, and the split assumes the propensity to trade internally is proportional to each subsector's weight (MVP_0.1 §6.3).

> **It is the weakest assumption here, and the result does not rest on it.** Measured on 96 splits where the office publishes both the parent and its parts, this block misses the published one by a median of **60 %** — the worst-estimated part of a split, against 42 % for the touched block as a whole. But how wrong it is does not predict how wrong the subsectors' multipliers are: correlation **+0.03**. Raising `internal_block_alpha` to the 1.5 that real blocks show makes the multipliers worse, not better, on 37 of those 68. See `validators/run_internal_block_backtest.py`.

> One caution about the percentage above: it is the block over the **whole** intermediate matrix, which is why it reads small. Over this subsector's own input column the same block runs from nothing to 56 %, and that is the share with anything to do with its multiplier.

### Cell provenance

| Provenance | Cells | Share | Data status (§A.1) |
|---|---:|---:|---|
| observed | 0 | 0.0 % | OBSERVED |
| proxy_estimated | 1024 | 100.0 % | **ESTIMATED** |
| balanced_adjustment | 0 | 0.0 % | **BALANCED** |
| user_constraint | 0 | 0.0 % | OBSERVED (analyst-pinned) |

> **This is a map of what was estimated, not a warning about your multipliers.** Measured on 68 real splits where the office publishes both the parent and its parts, the share of the table a split had to estimate has **no relationship** to how far the subsectors' multipliers land from the published truth — correlation −0.01. A split can be 112 % out cell by cell and still put its multipliers inside 4 %, or be tidy in the cells and 40 % out in the multipliers. What the multiplier error does track, at +0.92, is how UNLIKE the parts are: the worst error is about two thirds of the spread between their true multipliers, because proportional splitting hands every part the parent's average structure. See `validators/run_split_backtest.py`.

### Validation

**Scenario `S1_wages`** — PASSED

Method: **GRAS** — 56 negative cell(s) in the expanded table; RAS is undefined there (CORE_012 Box 11.3, p. 345)

- `OK  ` **check_proxy_coverage** — every subsector of every split has a positive proxy in every block (1 split(s))
- `OK  ` **check_key_vintage** — all 5 key(s) and profile(s) are measured in 2018, the table's own reference year
- `OK  ` **check_solver_convergence** — GRAS converged in 1 iterations (step 6.66e-16, tolerance 1e-09, PROJECT CHOICE)  
  <sub>CORE_006 ¶9.51, p. 288 — convergence is necessary, not sufficient</sub>
- `OK  ` **check_margins_attained** — max deviation from target row/column totals 9.31e-10 against a tolerance of 0.00609; margin imbalance sum(rows)-sum(cols) = 3.73e-09 — the targets are inconsistent, so no table satisfies both and part of that deviation cannot be solved away  
  <sub>OQ-B-02 v1.57; quadrium.precision.infeasibility_floor</sub>
- `OK  ` **check_reaggregation_untouched** — cells involving no split sector reproduce the original to 0 (must be ~0: they were copied, not estimated)
- `OK  ` **check_reaggregation** — max reaggregation error 1.69e-14 % against a tolerance of 1e-06 % (PROJECT CHOICE); grand total off by 0
- `OK  ` **check_leontief_productive** — spectral radius of A = 0.550822 (must be < 1), largest column sum 0.7814. Below 1 the Neumann series converges, the inverse is non-negative and a multiplier means what it says; at or above it the economy consumes at least as much as it makes and the multipliers are not large but undefined  
  <sub>ID-12, CORE_005 ¶36.36–36.39, pp. 1015–1016</sub>
- `OK  ` **check_leontief_identity** — max |Ax + y − x| = 1.86e-09 against 1e-06; the same statement through the inverse, max |Ly − x| = 1.86e-09 against 6.04e-06, which is that bound amplified by ‖L‖∞ = 6.04. Both are accounting, bounded by this source's own printed precision and by how far its books were already out  
  <sub>ID-12, CORE_005 ¶36.36, p. 1015</sub>
- `OK  ` **check_leontief_nonnegative** — every cell of the Leontief inverse is non-negative, so each multiplier is a sum of same-signed terms  
  <sub>ID-12</sub>
- `OK  ` **check_leontief_inverse** — ‖(I−A)L − I‖ = 4.44e-16 against 7.22e-13 for a matrix with condition number 3. This one is arithmetic and nothing else: it asks whether the inverse was computed, not whether the table adds up. An ill-conditioned system loses digits no source precision can restore  
  <sub>ID-12, CORE_005 ¶36.37, p. 1015</sub>
- `OK  ` **check_sign_preserved** — 0 cell(s) changed sign during balancing; 56 negative(s) in the result against 56 in the seed  
  <sub>UNH_18 ¶18.35, p. 558 — GRAS is sign preserving</sub>
- `OK  ` **check_extreme_coefficients** — 0 technical coefficient(s) above 1 (PROJECT CHOICE); max = 0.41, min = -8.97e-17
- `OK  ` **check_internal_block_share** — estimated internal block(s) as a share of the absolute value of the whole intermediate matrix: G-I 0.08 %. This is the least certain part of the result and is labelled PROXY_ESTIMATED throughout  
  <sub>MVP_0.1 §6.3 — double-proportionality hypothesis</sub>
- `OK  ` **check_zero_row_col** — 0 zero row/column(s) created by balancing. Zero means below 6.544e-07, which is what this source's own precision can distinguish from it
- `OK  ` **check_user_constraints_held** — every analyst-pinned cell still holds the value it was given  
  <sub>UNH_18 ¶18.81, p. 569 — GRAS accepts row and column totals only</sub>
- `OK  ` **check_provenance_complete** — 0 observed, 1024 proxy-estimated, 0 balanced-adjustment, 0 user-constrained, of 1024 cells  
  <sub>MVP_0.1 §2.6; A_core_accounting_spec.md §A.1</sub>

> Solver convergence is necessary but **not sufficient** for statistical validity (CORE_006 ¶9.51, p. 288; CORE_012 ¶11.105, pp. 342–343).

---

## Scenario `S2_headcount`

### Balancing

- **Method: GRAS** — 56 negative cell(s) in the expanded table; RAS is undefined there (CORE_012 Box 11.3, p. 345)
- Converged: True; iterations by split: G-I 1
- Max deviation from target row / column totals: 9.31e-10 / 2.33e-10
- Negatives: 56 in the seed, 56 in the result, **0 sign changes**

### `G-I` — Distribution

| Block | Key | Chosen? | Strength | Year | vs table | Weights |
|---|---|---|---|---|---|---|
| output | `key_headcount_sbs_2018` | chosen | medium | 2018 | same year | 0.579, 0.168, 0.252 |
| final_demand | `key_headcount_sbs_2018` | inherited | medium | 2018 | same year | 0.579, 0.168, 0.252 |
| value_added | `key_headcount_sbs_2018` | inherited | medium | 2018 | same year | 0.579, 0.168, 0.252 |
| intermediate_rows | `key_headcount_sbs_2018` | inherited | medium | 2018 | same year | 0.579, 0.168, 0.252 |
| intermediate_cols | `key_headcount_sbs_2018` | inherited | medium | 2018 | same year | 0.579, 0.168, 0.252 |

**How wrong will each subsector's SIZE be?**

| Subsector | share of the parent | typical | p90 |
|---|---:|---:|---:|
| `G` | 57.9% | 13 % | 47 % |
| `H` | 16.8% | 43 % | 163 % |
| `I` | 25.2% | 29 % | 109 % |

> A proportional split gives each part `share x parent output`, so an error of *e* **points** in a share is an error of `e / share` in that part's own size. The two columns put the median and p90 error of a real downloadable key — 7.3 and 27.4 points (`validators/run_real_key.py`) — through that division. Measured on 1,583 subsector-and-proxy pairs, the typical column runs about 0.65 of the truth and the p90 column contains it **92 %** of the time, holding at 88.7 to 92.9 % with each country held out.
>
> **A small part is where this bites.** A few points of key error is the whole of a 5 % subsector. If your key came from the office's own published split for another year rather than from a proxy, use 1.2 points instead of 7.3 (`validators/run_key_carryover.py`) and these numbers fall by six. See `validators/run_size_screen.py`.


- `key_headcount_sbs_2018` — Eurostat, Structural business statistics by NUTS 2 region and NACE Rev. 2 (sbs_r_nuts06_r2), Catalonia, 2018, persons employed (V16110), number

*inherited* — no key was named for that block, so it took the output key. That is a default, not a decision by the analyst, and it means the block carries whatever the output proxy implies rather than a measurement of its own.

| Subsector | Output | Intermediate sales | Final demand | Value added | Output multiplier |
|---|---:|---:|---:|---:|---:|
| G | 66,402.4 | 32,169.5 | 34,232.9 | 37,073.7 | 1.922 |
| H | 19,305.3 | 9,352.7 | 9,952.6 | 10,778.5 | 1.922 |
| I | 28,947.9 | 14,024.2 | 14,923.7 | 16,162.1 | 1.922 |

*Corroboration against `key_wages_sbs_2018` (medium, 2018), which did **not** drive this split:*

| Subsector | implied by the split | measured | gap |
|---|---:|---:|---:|
| G | 0.5791 | 0.6269 | -7.6% |
| H | 0.1684 | 0.1996 | -15.6% |
| I | 0.2525 | 0.1735 | +45.5% |

Largest disagreement **45.5%**, against the `output` weights. Every other check in this report asks whether the arithmetic is self-consistent and would pass on any key; this one asks whether an independent measurement agrees. Source: Eurostat, Structural business statistics by NUTS 2 region and NACE Rev. 2 (sbs_r_nuts06_r2), Catalonia, 2018, wages and salaries (V13320), million euro

*Classification:* G-I -> G, H, I: codes are not in a recognised classification, so the hierarchy was not checked

*Headroom:* the tightest subsector still has 2,287.98 of internal trade left, 16.8 % of this sector's own diagonal of 13,588.5. That margin is the budget any differentiated input structure has to fit inside — a sector that barely trades with itself leaves little room to claim its subsectors buy differently.

*Input structures:* these subsectors buy the **same mix** in different amounts — cosine distance -0.00000, effectively zero. Each is a scaled copy of the parent's input structure, so any difference in their multipliers is an artefact of the internal block, not a finding. Supply `input_profiles` to give them genuinely different purchasing patterns.

> **What a profile is worth, measured.** On 96 splits where the office publishes both the parent and its parts, giving the engine the parts' TRUE input profile moves the SEED's multiplier error from a median 7.78 % to 3.48 %. **The balancer then gives all of that back**: the delivered table is a median 7.79 % against 7.78 % for using no profile at all, and it beats doing nothing in 30 of 56. Balancing adjusts the internal block only — correct when a split is proportional, since nothing else moves — so a profiled column pushes the whole adjustment into the least reliable part of the table. The engine also refuses the profiled scenario outright in 19 of 54.
>
> **Borrowing one from a country that publishes your split is a coin flip** — 162 borrowings, better in 78 and worse in 84, helping by a median 4.2 points and hurting by 3.1. It helps where the split was going badly anyway and hurts where it was fine (r = +0.42 against the baseline error), which is only knowable afterwards; the ex-ante screen does not predict it (r = +0.17 for the parent multiplier, -0.22 for the number of parts). See `validators/run_input_profiles_backtest.py`.

The estimated **internal block** for this sector is 0.08 % of the absolute value of the intermediate matrix. It has no direct observation behind it: the original table held a single diagonal cell of 13,588.5, and the split assumes the propensity to trade internally is proportional to each subsector's weight (MVP_0.1 §6.3).

> **It is the weakest assumption here, and the result does not rest on it.** Measured on 96 splits where the office publishes both the parent and its parts, this block misses the published one by a median of **60 %** — the worst-estimated part of a split, against 42 % for the touched block as a whole. But how wrong it is does not predict how wrong the subsectors' multipliers are: correlation **+0.03**. Raising `internal_block_alpha` to the 1.5 that real blocks show makes the multipliers worse, not better, on 37 of those 68. See `validators/run_internal_block_backtest.py`.

> One caution about the percentage above: it is the block over the **whole** intermediate matrix, which is why it reads small. Over this subsector's own input column the same block runs from nothing to 56 %, and that is the share with anything to do with its multiplier.

### Cell provenance

| Provenance | Cells | Share | Data status (§A.1) |
|---|---:|---:|---|
| observed | 0 | 0.0 % | OBSERVED |
| proxy_estimated | 1024 | 100.0 % | **ESTIMATED** |
| balanced_adjustment | 0 | 0.0 % | **BALANCED** |
| user_constraint | 0 | 0.0 % | OBSERVED (analyst-pinned) |

> **This is a map of what was estimated, not a warning about your multipliers.** Measured on 68 real splits where the office publishes both the parent and its parts, the share of the table a split had to estimate has **no relationship** to how far the subsectors' multipliers land from the published truth — correlation −0.01. A split can be 112 % out cell by cell and still put its multipliers inside 4 %, or be tidy in the cells and 40 % out in the multipliers. What the multiplier error does track, at +0.92, is how UNLIKE the parts are: the worst error is about two thirds of the spread between their true multipliers, because proportional splitting hands every part the parent's average structure. See `validators/run_split_backtest.py`.

### Validation

**Scenario `S2_headcount`** — PASSED

Method: **GRAS** — 56 negative cell(s) in the expanded table; RAS is undefined there (CORE_012 Box 11.3, p. 345)

- `OK  ` **check_proxy_coverage** — every subsector of every split has a positive proxy in every block (1 split(s))
- `OK  ` **check_key_vintage** — all 5 key(s) and profile(s) are measured in 2018, the table's own reference year
- `OK  ` **check_solver_convergence** — GRAS converged in 1 iterations (step 8.88e-16, tolerance 1e-09, PROJECT CHOICE)  
  <sub>CORE_006 ¶9.51, p. 288 — convergence is necessary, not sufficient</sub>
- `OK  ` **check_margins_attained** — max deviation from target row/column totals 9.31e-10 against a tolerance of 0.00609; margin imbalance sum(rows)-sum(cols) = 0  
  <sub>OQ-B-02 v1.57; quadrium.precision.infeasibility_floor</sub>
- `OK  ` **check_reaggregation_untouched** — cells involving no split sector reproduce the original to 0 (must be ~0: they were copied, not estimated)
- `OK  ` **check_reaggregation** — max reaggregation error 5.35e-14 % against a tolerance of 1e-06 % (PROJECT CHOICE); grand total off by 0
- `OK  ` **check_leontief_productive** — spectral radius of A = 0.550822 (must be < 1), largest column sum 0.7814. Below 1 the Neumann series converges, the inverse is non-negative and a multiplier means what it says; at or above it the economy consumes at least as much as it makes and the multipliers are not large but undefined  
  <sub>ID-12, CORE_005 ¶36.36–36.39, pp. 1015–1016</sub>
- `OK  ` **check_leontief_identity** — max |Ax + y − x| = 1.86e-09 against 1e-06; the same statement through the inverse, max |Ly − x| = 1.86e-09 against 6.04e-06, which is that bound amplified by ‖L‖∞ = 6.04. Both are accounting, bounded by this source's own printed precision and by how far its books were already out  
  <sub>ID-12, CORE_005 ¶36.36, p. 1015</sub>
- `OK  ` **check_leontief_nonnegative** — every cell of the Leontief inverse is non-negative, so each multiplier is a sum of same-signed terms  
  <sub>ID-12</sub>
- `OK  ` **check_leontief_inverse** — ‖(I−A)L − I‖ = 8.88e-16 against 7.22e-13 for a matrix with condition number 3. This one is arithmetic and nothing else: it asks whether the inverse was computed, not whether the table adds up. An ill-conditioned system loses digits no source precision can restore  
  <sub>ID-12, CORE_005 ¶36.37, p. 1015</sub>
- `OK  ` **check_sign_preserved** — 0 cell(s) changed sign during balancing; 56 negative(s) in the result against 56 in the seed  
  <sub>UNH_18 ¶18.35, p. 558 — GRAS is sign preserving</sub>
- `OK  ` **check_extreme_coefficients** — 0 technical coefficient(s) above 1 (PROJECT CHOICE); max = 0.41, min = -8.97e-17
- `OK  ` **check_internal_block_share** — estimated internal block(s) as a share of the absolute value of the whole intermediate matrix: G-I 0.08 %. This is the least certain part of the result and is labelled PROXY_ESTIMATED throughout  
  <sub>MVP_0.1 §6.3 — double-proportionality hypothesis</sub>
- `OK  ` **check_zero_row_col** — 0 zero row/column(s) created by balancing. Zero means below 6.544e-07, which is what this source's own precision can distinguish from it
- `OK  ` **check_user_constraints_held** — every analyst-pinned cell still holds the value it was given  
  <sub>UNH_18 ¶18.81, p. 569 — GRAS accepts row and column totals only</sub>
- `OK  ` **check_provenance_complete** — 0 observed, 1024 proxy-estimated, 0 balanced-adjustment, 0 user-constrained, of 1024 cells  
  <sub>MVP_0.1 §2.6; A_core_accounting_spec.md §A.1</sub>

> Solver convergence is necessary but **not sufficient** for statistical validity (CORE_006 ¶9.51, p. 288; CORE_012 ¶11.105, pp. 342–343).

---

## Scenario comparison

Output multipliers by subsector. The range is the honest measure of how much the proxy choice matters — of how much it matters, not of how wrong the answer is; see the note under *How far the outside evidence disagrees*.

| Subsector | S1_wages | S2_headcount | Range | Range % |
|---|---|---|---|---|
| G | 1.922 | 1.922 | 0.000 | 0.0 % |
| H | 1.922 | 1.922 | 0.000 | 0.0 % |
| I | 1.922 | 1.922 | 0.000 | 0.0 % |

**Main driver of variation:** the cell `I -> B-E`, which spans 2,367.8 across scenarios. This is the crude measure of MVP_0.1 §10 — the widest cell, not a sensitivity analysis.

### How far the outside evidence disagrees

Each scenario compared against the allocation keys that were registered and then **not** used to drive it. The spread between the closest and the furthest is the uncertainty this report can actually support.

| Scenario | driven by | closest key | furthest key | keys compared |
|---|---|---|---|---:|
| `S1_wages` | `key_wages_sbs_2018` | `key_headcount_sbs_2018` 31.3% | `key_headcount_sbs_2018` 31.3% | 1 |
| `S2_headcount` | `key_headcount_sbs_2018` | `key_wages_sbs_2018` 45.5% | `key_wages_sbs_2018` 45.5% | 1 |

> **Nothing here says which end is right, and the ranking that used to sit in this space was removed for cause.** It marked the scenario that disagreed least as better supported. On the Spanish pilot the key that disagreed MOST — employment, by 58.8 % — turned out to be the closest to the truth once the INE's 110-product supply table settled it, while the driving key was 9.8 points out. Least disagreement measures resemblance to your own inputs, not accuracy. See `validators/run_key_bias.py`.
>
> **What a large disagreement is good for** is telling you where to go looking. In that case a better source existed and was one download away. See `D_open_questions.md` OQ-S-05 and OQ-S-06.
>
> **This spread is not a confidence interval, and it is not much of a floor either.** Measured on 65 splits across five country-years where the office publishes both the parent and its parts: the range contains the true share for 84.0 % of subsectors and for every subsector at once in **49 of 65 splits** — it misses one split in four. And where it does contain the answer it does so across a median **28 points of share**, which excludes almost nothing. Honest about being uncertain; nearly silent about where the answer is.
>
> **A narrow range is not a safer one.** The splits where the range misses are the WIDER ones (median 38.6 points against 27.8), so there is no flag here to act on. Nor is the verdict a property of the sector: of the 13 parents that appear in more than one country-year, the range agrees with itself in 7. Dropping the highest and lowest proxy does not rescue it — coverage falls to 59.7 % while the range is still 12 points wide. See `validators/run_key_spread.py`.
>
> One thing the spread does NOT do is lean reliably one way. Every available proxy sits on the same side of the answer for only **16.0 %** of subsectors. Spanish hospitality, where all seven of the pilot's keys overstate accommodation and the range misses by 0.6 points, is the unusual case and not the pattern — as it also was for the size of the error. See `validators/run_key_bias.py` and `validators/run_real_key.py`.

### How risky was this split, before you made it?

**How many parts you asked for** ranks a split's difficulty, measured on 96 real splits where the office publishes both the parent and its parts. Held out one country at a time it separates in the same direction in all four — BE 7.9 to 22.5 %, FR 8.2 to 11.2 %, HU 5.3 to 7.9 %, SK 4.4 to 19.7 %.

| Split | parent multiplier | parts | comparable splits: median error | worst |
|---|---:|---:|---:|---:|
| `G-I` | 1.922 | 3 | 10.6 % | 49.2 % |

> The error columns are what the subsectors' **multipliers** did in comparable splits. They are a band, not a prediction for your table: the screen ranks, and the spread inside each band is wide — the worst column is the worst of 96, not a bound on yours. The cut point is the median of the 96, two parts.
>
> **The parent multiplier column is printed and is no longer used to place you in a band.** Fitted on 68 splits it looked like a second, independent signal; on 96 it ranks at +0.24 and is NEGATIVE in France, and at few parts its two bands come out at 5.4 % and 5.3 % — no separation at all. An earlier version of this report split you four ways on it. See `validators/run_split_screen.py`.
>
> **The band does not depend on your key being right.** Without an input profile, no allocation key can move a subsector's multiplier — the share cancels out of the coefficients, so every key gives the same one. Measured on 638 real published proxies, identical to the answer's own multipliers in 636 of 638 — the two exceptions give a real subsector a share of exactly zero, and the engine refuses those. What the band measures is structure, and your key cannot add to it or subtract from it. See `validators/run_key_invariance.py`.
>
> **Your key sets the sizes, and that is where it costs you.** A share error of a few points is not a subsector a few percent out: the error is relative to a part that may be small, so it is amplified by a median factor of 3.8. Real downloadable proxies are out by a median 7.3 points of share, which leaves the worst subsector's output out by a median **32 %**, and only 77 of 638 put every subsector within 10 % of its true size. See `validators/run_real_key.py`.
>
> **If ANOTHER YEAR of your own table publishes the split, use it and ignore all of this.** The same parent a year earlier misses by **0.7 points**, against 2.8 for the band above and 5.7 for the same parent borrowed from another country. A split's difficulty is a property of the table it is in, not of the sector — which is why another COUNTRY's number is the worst of the three, and why `validators/run_key_carryover.py` finds the same thing from the key's side.
>
> **Asking for more parts does not make each part worse.** A single subsector's error barely moves with the number of parts (r = +0.17); the worst of them does (r = +0.36), because more parts is more draws. If you need one particular subsector, that costs you little. If you need all of them to hold, it costs you the maximum. See `validators/run_split_screen.py`.

### How wrong is this if your allocation key is wrong?

Exactly as wrong as the key, in the sizes — and not at all in the multipliers. The weight scales a subsector's output, value added and purchases together and cancels out of `a_ij = Z_ij / X_j`, so **one per cent of error in the key is one per cent of error in the size and zero in the multiplier**. That is arithmetic, not an estimate, and it needs no simulation.

Per 1 % your key is wrong, in million US dollars: Huang & Koutroumpis (2023) state it:

| Subsector | Output | Value added | Purchases | per 1 % of key |
|---|---:|---:|---:|---:|
| `G` | 71,879 | 40,131 | 31,748 | **719** |
| `H` | 22,880 | 12,774 | 10,106 | **229** |
| `I` | 19,896 | 11,108 | 8,788 | **199** |

So a key you believe to within 10 % gives a subsector size you believe to within 10 %, and a multiplier you believe exactly as much as you believe the parent sector's — no more and no less. **The uncertainty the key carries lands entirely on the levels.**

What moves a multiplier is the `profiles` sheet, and it moves it very little: on the project's own fixture, DOUBLING one supplier's intensity moves the multiplier by 0.35 %. If you need subsectors that differ as buyers, that is the lever — and it is a short one. See `validators/run_key_sensitivity.py`.

### Read this before quoting the multipliers

**Every subsector has the same output multiplier, and that is a property of the method, not a finding about the economy.**

Splitting a sector proportionally with a single allocation key gives each subsector a scaled copy of the parent's input structure. If output and intermediate purchases are split by the same weights, the technical coefficients `a_ij = Z_ij / X_j` come out identical for every subsector — the weight cancels — so the multipliers must be identical too. The arithmetic cannot produce anything else.

The disaggregation is still useful: each subsector gets its own output, value added and final demand, and the table stays balanced. But it adds **no information about how the subsectors differ as buyers**. Genuinely different multipliers require genuinely different input structures — a separate proxy for the intermediate columns, survey data on what each subsector actually purchases, or cells set by hand through `Scenario.user_constraints`.

Quoting these multipliers as evidence that hotels and restaurants have similar economic pull would be circular.

---

## How to read this

- Every value produced by the solver has data status `BALANCED`. It is **not** an observation and must never be relabelled as one.
- Solver convergence is **necessary but not sufficient** for statistical validity (CORE_006 ¶9.51, p. 288). A converged run that fails a plausibility check is a failed run.
- **No published source states a numerical tolerance for an accounting identity.** Six were searched and the question is settled: what a balance can be tested against is a property of the table, not of the method. So the floor applied here is derived from your own table's stated precision — an identity summing `n` cells published to `d` decimals cannot be checked more tightly than `0.5·10⁻ᵈ·n`, and below that line 'balanced' and 'not balanced' are the same observation. Every tolerance that remains a genuine choice is labelled `PROJECT CHOICE` where it is used.
- The method was **selected by the sign structure of the table**, not chosen by preference. RAS cannot be applied to a matrix with negative entries (CORE_012 Box 11.3, p. 345); GRAS can (UNH_18 ¶18.35, p. 558), and reduces to RAS when there are none.

---

## Assumption ledger

| ID | Assumption | Source | Confidence | Impact |
|---|---|---|---|---|
| `A-01` | The split rests on a COST proxy, not on output. The regional structural business statistics publish local units, wages and persons employed at NUTS-2, and neither turnover nor value added, so nothing published measures the three sections' output for Catalonia. S1 uses wages because they track value more closely than a headcount. | Eurostat, Structural business statistics by NUTS 2 region and NACE Rev. 2 (sbs_r_nuts06_r2), Catalonia, 2018 | medium | up to 7.9 points of the parent's output on one subsector; the report prints both scenarios rather than ranking them |
| `A-02` | Every subsector inherits the parent's input structure. With one allocation key the weight cancels in a_ij = Z_ij / X_j, so all three share `G-I`'s multiplier. Differentiating them would need purchasing profiles, and nothing published gives them for a NUTS-2 region. | Sizes: Eurostat, Structural business statistics by NUTS 2 region and NACE Rev. 2 (sbs_r_nuts06_r2), Catalonia, 2018 || Structures: NOT ESTIMATED | strong | the three subsectors' multipliers are the parent's and should be quoted as such |
| `A-03` | That sections G, H and I tile the archive's `G-I`. `G-I` is Eurostat's A10 grouping, which `check_split` does not parse, so the engine accepts the split and says it could not verify the tiling. The grouping is documented by Eurostat as G, H and I; it is read from there rather than derived here. | Eurostat, NACE Rev. 2 A*10 aggregation | strong | none on the arithmetic — the parts are scaled to the parent's own total either way — but a reader who believed the grouping were G and I alone would be reading transport into the wrong row |
| `A-04` | The table is an ESTIMATE, cell by cell: the archive is modelled from the OECD ICIO, Eurostat regional accounts and truck freight flows. Neither of its accounting identities closes, and the residue is carried in a labelled RESIDUAL row and column rather than balanced away. Against ten surveyed regions it records about a quarter of the purchases a region makes from the rest of its country, so the share of an impulse that stays in Catalonia is an upper bound. | Huang, S. & Koutroumpis, P. (2023), European multi regional input output data for 2008-2018, Scientific Data 10, 218 | weak | the split is exact arithmetic on estimated cells; the report sizes the residue and states the bound beside the figures |


---

*Not every reference here is one you can follow.* `A_core_accounting_spec.md`, `D_open_questions.md`, `OQ-B-02`, `MVP_0.1`, `OQ-S-05`, `OQ-S-06` point into this project's own research record — its open questions, its accounting specification and its method cards. That record is **not** distributed with the software, because it quotes copyrighted manuals at length; `PROVENANCE.md` says so and why. Everything cited as `CORE_nnn`, `UNH_nn` or `SNA_25` is a published source, given by paragraph and page, and every one of those page citations is verified against the source's own text before it ships. The identities `ID-nn` are defined in the public specification.