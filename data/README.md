# Data — Provenance & Layout

Raw data is **not committed to git** (~188 MB, all publicly re-downloadable).
Restore it with:

```bash
python scripts/fetch_data.py          # fetch everything
python scripts/fetch_data.py --check  # report what's present
```

Full evaluation of why these datasets were chosen: [`docs/dataset_selection.md`](../docs/dataset_selection.md).

---

## Layout

```
data/
├── raw/                                  # immutable source data — never edit by hand
│   ├── abilene/                          # PRIMARY dataset
│   │   ├── topo-2003-04-10.txt           # 12 nodes; link capacities (kbps) + OSPF weights
│   │   ├── links                         # link name -> link index (1..54)
│   │   ├── demands                       # OD pair name -> demand index (1..144)
│   │   ├── A                             # routing matrix: (link_idx, dmd_idx, fraction)
│   │   ├── readme.txt                    # upstream format documentation
│   │   └── traffic-matrices/X01.gz … X24.gz   # 24 weeks of 5-min traffic matrices
│   ├── geant/                            # SECONDARY dataset
│   │   └── traffic-matrices-anonymized-v2.tar.bz2   # topology + 10,772 TMs (XML)
│   └── sndlib/                           # SUPPORTING reference topologies
│       ├── sndlib-networks-xml.zip       # all 26 SNDlib networks
│       ├── geant.xml  abilene.xml  nobel-us.xml
└── processed/                            # derived artefacts — regenerate, don't commit
    ├── abilene_link_utilization.parquet       # tidy long: 1,442,880 rows x 7 cols
    ├── abilene_link_utilization_wide.parquet  # wide: 48,096 timesteps x 30 links
    ├── abilene_features.parquet               # labels + 16 features, 1,442,880 rows
    └── abilene_congestion_thresholds.csv      # per-link p50/p80/p95
```

Regenerate the processed tables with:

Run the two notebooks in order:

1. `notebooks/01_data_and_utilization.ipynb` — topology + traffic matrices → utilisation
2. `notebooks/02_labeling_and_features.ipynb` — labels + gap-aware features

**Long format** — one row per (timestamp, link): `timestamp`, `link`, `src`, `dst`,
`capacity_kbps`, `load_kbps`, `utilization_pct`.
**Wide format** — timestamp index, one column per link, values are utilisation %.
**Features** — `timestamp`, `link`, `utilization_pct`, `congestion` (ordered
categorical), 6 lags, 6 rolling mean/std, 4 cyclical time encodings.

### ⚠️ Features are gap-aware — do not rebuild them positionally

Because the series is irregular, lags and rolling windows are computed on a
**complete 5-minute grid** spanning 2004-03-01 → 2004-09-10 (55,872 slots, of which
7,776 are absent). A lag reaching across a gap lands on an absent slot and yields
NaN structurally.

A naive `shift()` would instead have filled **37,440 (link, timestep, lag) cells**
with values pulled across a gap — e.g. presenting a reading from 18 days earlier as
"the previous 5-minute sample". NaNs are **retained, not dropped**, so the modelling
step picks its own policy (XGBoost handles NaN natively).

Congestion labels use per-link percentile thresholds. **The 50/30/15/5 class split is
definitional, not empirical** — percentile labelling imposes it by construction.
Thresholds are persisted to `abilene_congestion_thresholds.csv`; they are currently
fit on the full series and **must be refit on the training window alone** before any
temporal train/test split, or the label definition will have seen future data.

---

## 1. Abilene traffic matrices — PRIMARY

| | |
|---|---|
| **Source** | <https://www.cs.utexas.edu/~yzhang/research/AbileneTM/> |
| **Network** | Internet2 Abilene, US research backbone |
| **Timespan** | 2004-03-01 → 2004-09-04 (~6 months, 24 weekly files) |
| **Granularity** | 5 minutes → 2,016 matrices/week, **48,384 total** |
| **Topology** | 12 nodes, 30 directed links, 144 OD pairs |
| **Capacities** | 9,920,000 kbps (OC-192); 2,480,000 kbps (OC-48) on ATLA↔IPLS |
| **Size** | 164 MB compressed (~488 MB uncompressed) |
| **License** | Research dataset, no explicit license file — cite the papers below |

**Attribution:**
> Y. Zhang, M. Roughan, C. Lund, D. Donoho. *An Information-Theoretic Approach to
> Traffic Matrix Estimation.* ACM SIGCOMM, 2003.
>
> Y. Zhang, Z. Ge, A. Greenberg, M. Roughan. *Network Anomography.* ACM IMC, 2005.

### ⚠️ Two format traps

**1. Only 1 in 5 columns is real data.** Each row of `X*.gz` has
**720 values = 144 OD pairs × 5**, ordered per OD pair as:

```
realOD | simpleGravity | simpleTomogravity | generalGravity | generalTomogravity
```

Only `realOD` (**column index 0, 5, 10, … — i.e. `[:, 0::5]`**) is the measured
value. The other four are outputs of traffic-matrix *estimation algorithms*. Training
on them would mean training on synthetic estimates, not measurements.

**2. Units are `100 bytes / 5 minutes`,** where 100 is the packet sampling rate:

```
kbps = value × 100 × 8 / 300 / 1000
```

An earlier attempt on a different Abilene mirror applied a bytes→bits conversion that
the data did not need and produced ~0% utilisation everywhere. Check units before
trusting any utilisation number.

### ⚠️ The 24 weekly files are NOT contiguous

The week start dates in `readme.txt` are authoritative (the data files carry no
timestamps of their own), and they are **not** a clean 7-day sequence. Audited
2026-07-28:

| Join | Kind | Amount | Detail |
|---|---|---|---|
| X02 → X03 | **gap** | 18 days | 2004-03-15 → 2004-04-02 |
| X04 → X05 | **gap** | 6 days | 2004-04-16 → 2004-04-22 |
| X05 → X06 | **gap** | 2 days | 2004-04-29 → 2004-05-01 |
| X20 → X21 | **overlap** | 1 day | X21 starts 2004-08-13, inside X20's last day |
| X21 → X22 | **gap** | 1 day | 2004-08-20 → 2004-08-21 |

18 of 23 joins are contiguous. Net effect: **194 calendar days spanned, 167 days of
actual data (86.1%)**.

**The X20/X21 overlap is redundant, not conflicting.** X20's last 288 rows and X21's
first 288 rows were verified **byte-identical** (max difference exactly 0), so
dropping the second copy is lossless: 48,384 raw rows → **48,096 unique timesteps**.
`deduplicate()` re-verifies this on every run and **raises** if duplicated timestamps
ever disagree, rather than silently picking a winner.

Consequence for modelling: the series is **irregular**. Any lag/rolling feature must
respect the gaps — treating the array as evenly spaced would silently compare
2004-03-15 against 2004-04-02 as if they were five minutes apart.

### Topology file structure

`topo-2003-04-10.txt` has two sections, `router` then `link`:

```
router
#name    city          latitude   longitude
ATLAng   Atlanta_GA    33.750000  -84.383300
...
link
#x       y        capacity(kbps)  OSPF
ATLAng   HSTNng   9920000         1176
ATLAng   IPLSng   2480000         587
```

Capacities are cited upstream to an Internet2 presentation dated 2003-04-10; OSPF
weights to the Abilene IGP topology diagram of the same date.

---

## 2. GÉANT traffic matrices — SECONDARY

| | |
|---|---|
| **Source** | <https://totem.run.montefiore.uliege.be/files/data/traffic-matrices-anonymized-v2.tar.bz2> |
| **Project page** | <https://totem.info.ucl.ac.be/dataset.html> |
| **Network** | GÉANT, pan-European research backbone |
| **Timespan** | 2005-01-01 → 2005-04-29 (~4 months) |
| **Granularity** | 15 minutes → **10,772 traffic matrices** |
| **Topology** | 23 nodes, 74 directed links (`topology-anonymised.xml`) |
| **Capacities** | ❌ **none** — links carry only `<from>`/`<to>` |
| **Units** | kbps (declared in each XML `<info><units>` block) |
| **Size** | 17.9 MB bz2 |
| **License** | Public, anonymised. **Citation required by the provider.** |

**Attribution (required):**
> S. Uhlig, B. Quoitin, S. Balon, J. Lepropre. *Providing public intradomain traffic
> matrices to the research community.* ACM SIGCOMM Computer Communication Review,
> 36(1), January 2006.

**Anonymisation caveat:** router IDs are integers and lat/long are zeroed, so GÉANT
nodes **cannot** be joined to the named SNDlib GÉANT nodes (`at1.at`, `de1.de`, …) to
recover capacities. This is why GÉANT is secondary — and why the congestion labelling
must be percentile-based rather than capacity-based.

One matrix per file, `traffic-matrices/IntraTM-YYYY-MM-DD-HH-MM.xml`:

```xml
<IntraTM ASID="20965">
  <src id="12">
    <dst id="13">25871.3956</dst>
```

---

## 3. SNDlib reference topologies — SUPPORTING

| | |
|---|---|
| **Source** | <https://sndlib.put.poznan.pl/download/sndlib-networks-xml.zip> |
| **Contents** | 26 canonical research topologies |
| **Demand** | ❌ **single static matrix per network** — no time dimension |
| **Size** | 793 KB |
| **License** | Free for research and education |

**Attribution:**
> S. Orlowski, M. Pióro, A. Tomaszewski, R. Wessäly. *SNDlib 1.0 — Survivable Network
> Design Library.* Networks 55(3), 2010.

Used **only** to cross-validate parsed topologies against canonical published
versions, and as extra graphs for routing tests. `geant.xml` carries capacities;
`abilene.xml` does not.

*(The historical host `sndlib.zib.de` now redirects to the Poznań mirror above.)*

---

## Rules for this directory

1. **`data/raw/` is immutable.** Never edit in place — all cleaning writes to
   `data/processed/`.
2. **Nothing in here is committed.** Both `raw/` and `processed/` are gitignored;
   `fetch_data.py` is the reproducibility path.
3. **Cite GÉANT if results using it are published** — the provider requires it.
