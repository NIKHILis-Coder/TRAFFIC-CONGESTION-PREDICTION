# Dataset Selection

Evaluation of publicly available datasets for **network congestion prediction +
adaptive routing**, and the reasoning behind the final choice.

All availability checks and measurements in this document were performed on
**2026-07-28** against the live sources.

---

## 1. What this project actually requires

The project predicts congestion on **network links** and then reroutes traffic with
Dijkstra + dynamic edge costs to reduce peak link utilisation. That imposes three
hard requirements that eliminate most "network traffic" datasets:

| # | Requirement | Why it's non-negotiable |
|---|---|---|
| R1 | **A topology** — nodes + links | Without a graph there is nothing to run Dijkstra on |
| R2 | **Link capacities** | Utilisation = load / capacity. No capacity ⇒ no congestion ground truth |
| R3 | **Time-series demand** (traffic matrices over time) | Congestion *prediction* needs a temporal signal, not one snapshot |

A fourth is strongly desirable:

| R4 | **Baseline routing / IGP weights** | Gives a legitimate "before" baseline to measure rerouting improvement against |

The common failure mode is datasets that satisfy R3 richly but have no R1/R2 at all
(packet traces), or satisfy R1/R2 but ship only a single static demand matrix
(network-design libraries).

---

## 2. Datasets evaluated

### 2.1 Abilene traffic matrices — Yin Zhang, UT Austin ✅ **SELECTED (primary)**

- **What it is:** Measured origin–destination traffic matrices from the Internet2
  Abilene backbone (US research network), derived from Netflow + BGP + IGP data.
  Ships with the topology, real link capacities, OSPF weights, and the routing matrix.
- **Source:** <https://www.cs.utexas.edu/~yzhang/research/AbileneTM/>
- **Size / timespan:** 24 weekly files (`X01.gz`–`X24.gz`), ~7.3 MB each,
  **164 MB total** compressed (~488 MB uncompressed).
  **2004-03-01 → 2004-09-04**, ~6 months.
  **5-minute** granularity → 2,016 matrices/week, **48,384 traffic matrices** total.
- **Topology:** 12 nodes, **30 directed backbone links**, 144 OD pairs.
- **Capacities:** ✅ **Real and documented** — 9,920,000 kbps (OC-192) on 28 links,
  2,480,000 kbps (OC-48) on the ATLA↔IPLS pair. Sourced from an Internet2
  presentation dated 2003-04-10, cited inside the topology file.
- **Baseline routing:** ✅ Real **OSPF weights** per link (e.g. NYCM↔WASH = 233,
  DNVR↔STTL = 2095) plus a precomputed routing matrix `A`.
- **R1 R2 R3 R4:** ✅ ✅ ✅ ✅ — the only candidate that satisfies all four.
- **License / attribution:** Research dataset published for community use, no explicit
  license file. Standard citation:
  > Y. Zhang, M. Roughan, C. Lund, D. Donoho. *An Information-Theoretic Approach to
  > Traffic Matrix Estimation.* ACM SIGCOMM 2003.
  > Y. Zhang et al. *Network Anomography.* ACM IMC 2005.
- **Data format caveat:** each row holds 720 values = 144 OD pairs × 5 estimates
  (`realOD`, `simpleGravity`, `simpleTomogravity`, `generalGravity`,
  `generalTomogravity`). **Only column 1 of each group of 5 is the measured value** —
  the other four are estimation-algorithm outputs and must be discarded, or the model
  would be trained on synthetic estimates. Units are `100 bytes / 5 min`
  (100 = packet sampling rate), so kbps = value × 100 × 8 / 300 / 1000.

### 2.2 GÉANT traffic matrices — TOTEM project, Uni. Liège ✅ **SELECTED (secondary)**

- **What it is:** Intradomain traffic matrices for GÉANT, the pan-European research
  network, built from full IGP + sampled Netflow + BGP data.
- **Source:** <https://totem.run.montefiore.uliege.be/files/data/traffic-matrices-anonymized-v2.tar.bz2>
- **Size / timespan:** 17.9 MB bz2. **2005-01-01 → 2005-04-29** (~4 months),
  **15-minute** granularity, **10,772 traffic matrices** (XML, kbps).
- **Topology:** 23 nodes, 74 directed links, included as `topology-anonymised.xml`.
- **Capacities:** ❌ **Absent.** The anonymised topology declares a `kbps` bandwidth
  unit but the `<link>` elements carry only `<from>`/`<to>` — no capacity attribute.
  Node IDs are anonymised integers with lat/long zeroed, so they **cannot be joined**
  to the named SNDlib GÉANT nodes (`at1.at`, `de1.de`, …) to borrow capacities.
- **R1 R2 R3 R4:** ✅ ❌ ✅ ❌
- **License / attribution:** Public, anonymised. Citation **required** by the provider:
  > S. Uhlig, B. Quoitin, S. Balon, J. Lepropre. *Providing public intradomain traffic
  > matrices to the research community.* ACM SIGCOMM CCR, 36(1), January 2006.
- **Verdict:** Cannot be the primary dataset — no capacities means no absolute
  congestion ground truth. **But** it is an excellent *second network*: it lets the
  project show the pipeline generalises to a different topology, at a different
  granularity, on a different continent. Percentile-based labelling (§4) is
  capacity-free, so it transfers cleanly.

### 2.3 SNDlib — Survivable Network Design Library ✅ **SELECTED (supporting)**

- **What it is:** Canonical reference network topologies used across the network-design
  literature. 26 networks including `abilene`, `geant`, `nobel-us`, `germany50`.
- **Source:** <https://sndlib.put.poznan.pl/download/sndlib-networks-xml.zip> (793 KB)
  *(the historical `sndlib.zib.de` host now 302-redirects here)*
- **Topology / capacities:** `geant.xml` — 22 nodes, 36 links, ✅ capacities present
  (e.g. 40,000 with costs). `abilene.xml` — 12 nodes, 15 links, ❌ **no** capacity
  elements.
- **Demand:** ❌ **Single static demand matrix only** (462 demands for GÉANT, 132 for
  Abilene). There is no time dimension.
- **R1 R2 R3 R4:** ✅ ⚠️ ❌ ❌
- **License / attribution:** Free for research and education; cite
  > S. Orlowski, M. Pióro, A. Tomaszewski, R. Wessäly. *SNDlib 1.0 — Survivable
  > Network Design Library.* Networks 55(3), 2010.
- **Verdict:** Disqualified as a primary source — **one demand matrix cannot support
  time-series prediction**. Kept as a cross-reference to sanity-check our parsed
  topologies against the canonical published versions, and as extra graphs for
  stress-testing the routing code.

### 2.4 Abilene via YATES (Cornell Netlab) ❌ **rejected — already tried and failed**

- **What it is:** The same underlying Abilene measurements, redistributed inside the
  YATES traffic-engineering tool (LGPL-3.0).
- **Size / timespan:** 200 hourly traffic-matrix snapshots, 12 nodes / 30 links.
- **Capacities:** ⚠️ Present but **wrong for this purpose** — the topology declares
  **1 Gbps** links, a Mininet testbed-scale figure, not Abilene's real ~10 Gbps OC-192.
- **Why rejected:** documented in the project decision log. The testbed capacities
  combined with real demand pinned link utilisation **below 1% on every link across
  all 200 timesteps**, leaving no dynamic range to define congestion classes.
  It is also **242× less data** than §2.1 (200 hourly vs 48,384 five-minute matrices).
  §2.1 is strictly better on every axis: same network, real capacities, real OSPF
  weights, far more samples, finer granularity.

### 2.5 Waikato / WITS internet traffic traces ❌ **rejected — no topology, and offline**

- **What it is:** Passive packet header traces (ERF format) from the University of
  Waikato, via the WAND group.
- **Availability:** ❌ `wand.net.nz/wits/` returned **HTTP 503 / no response** on
  2026-07-28. The archive appears to be down.
- **R1 R2 R3 R4:** ❌ ❌ ✅ ❌ — packet traces from a single measurement point.
  There is **no topology and no link capacities**, so there is nothing to route over.
- **Verdict:** Rejected on fundamentals (a single-link packet trace cannot support
  graph rerouting) before availability even becomes the issue.

### 2.6 CAIDA passive traces ❌ **rejected — access-gated and no topology**

- **Source:** <https://www.caida.org/catalog/datasets/passive_dataset/> (page reachable)
- **Access:** ❌ Requires a formal request with institutional affiliation and a signed
  Acceptable Use Policy; approval is not immediate and redistribution is prohibited.
- **R1 R2 R3 R4:** ❌ ❌ ✅ ❌ — anonymised backbone-link packet traces. Again a
  single vantage point, no graph, no capacities.
- **Verdict:** Rejected. Even with access granted, the data answers a different
  question (per-packet/flow characterisation), and the AUP forbids committing the data
  to a public portfolio repo — which defeats the purpose of a reviewable project.

### 2.7 Kaggle "network traffic" datasets ❌ **rejected — wrong problem or synthetic**

- **What's actually there:** the popular network datasets on Kaggle are
  **intrusion-detection** corpora — CICIDS2017, UNSW-NB15, KDD-Cup-99, NSL-KDD. These
  are per-flow records labelled *attack vs benign*, not link loads over a topology.
- **R1 R2 R3 R4:** ❌ ❌ ⚠️ ❌
- **Verdict:** Rejected on all counts. They have no topology and no link capacities,
  their label is a security label rather than a congestion label, and the handful that
  do advertise "congestion" are **synthetically generated** with unstated generators —
  which would undermine the whole point of using real measurements. Provenance is also
  frequently unclear or unlicensed, which is a liability in a portfolio piece.

---

## 3. Comparison summary

| Dataset | Topology | Real capacities | Time-series demand | Baseline routing | Samples | Verdict |
|---|:--:|:--:|:--:|:--:|---|---|
| **Abilene (UT Austin)** | ✅ 12n/30l | ✅ OC-192/OC-48 | ✅ 5-min, 6 mo | ✅ OSPF + matrix | **48,384** | **Primary** |
| **GÉANT (TOTEM)** | ✅ 23n/74l | ❌ | ✅ 15-min, 4 mo | ❌ | **10,772** | **Secondary** |
| **SNDlib** | ✅ 26 nets | ⚠️ some | ❌ single matrix | ❌ | 1 | **Supporting** |
| Abilene / YATES | ✅ 12n/30l | ⚠️ testbed 1 Gbps | ✅ hourly | ⚠️ | 200 | Rejected |
| Waikato / WITS | ❌ | ❌ | ✅ packets | ❌ | — | Rejected (also offline) |
| CAIDA | ❌ | ❌ | ✅ packets | ❌ | — | Rejected (gated) |
| Kaggle IDS sets | ❌ | ❌ | ⚠️ flows | ❌ | — | Rejected |

---

## 4. Recommendation

**Primary: Abilene traffic matrices (UT Austin).
Secondary: GÉANT (TOTEM) as a cross-network generalisation test.
Supporting: SNDlib for topology cross-validation.**

### Why Abilene wins

It is the **only** evaluated dataset that satisfies all four requirements at once.
Every rejected alternative fails on a structural axis, not a cosmetic one: packet
traces (Waikato, CAIDA) have no graph to route over; design libraries (SNDlib) have no
time axis; Kaggle sets solve a different problem; and the YATES variant of Abilene has
capacities that are simply wrong for this purpose.

### Verification — this was measured, not assumed

The previous attempt died on a capacity/scale mismatch, so the fix was verified
directly against the new data before committing to it. Using the dataset's **own**
routing matrix `A`, the real OC-192/OC-48 capacities, and the measured `realOD` column
over week 1 (2,016 timesteps):

| Metric | YATES attempt | **This dataset** |
|---|---|---|
| Max link utilisation | < 1% | **32.09%** |
| Network-wide mean | ~0% | 2.73% |
| Network-wide p95 | ~0% | 7.10% |
| Mean per-timestep peak-link utilisation | — | 7.38% |

**The capacity-mismatch problem is resolved.** Utilisation now spans a usable range
instead of being pinned at zero.

More importantly, the data shows a **real routing imbalance**, which is exactly what
gives the adaptive-routing half of the project something genuine to fix:

| Link | Capacity | Mean util | Max util |
|---|---|---|---|
| CHIN→IPLS | 9.92 Gbps | 5.44% | **32.09%** |
| IPLS→KSCY | 9.92 Gbps | 5.10% | 31.98% |
| KSCY→DNVR | 9.92 Gbps | 4.35% | 31.08% |
| … | | | |
| STTL→SNVA | 9.92 Gbps | 0.42% | **0.86%** ← lowest *inter-city* link |
| ATLA-M5→ATLA | 9.92 Gbps | 0.10% | 0.25% ← lowest overall (intra-PoP) |

> **Correction (2026-07-28).** An earlier summary described STTL→SNVA as "the link
> that idles lowest" at 0.86%. The value is right but the superlative was not:
> ATLA-M5→ATLAng is lower at 0.25%. `ATLA-M5` and `ATLAng` share identical
> coordinates (33.75, −84.3833) — they are two routers *inside the same Atlanta PoP*,
> so that link is intra-PoP rather than inter-city backbone. STTL→SNVA is the lowest
> **inter-city** link. Both figures are visible in the link summary table in
> `notebooks/01_data_and_utilization.ipynb`.

OSPF routing concentrates load on the Chicago–Indianapolis–Kansas City–Denver
corridor at **~37× the utilisation** of the idle Seattle–Sunnyvale inter-city link.
That imbalance is a real, measurable target: *reducing peak link utilisation* means
pushing traffic off that corridor onto demonstrably idle capacity.

### Full-dataset figures (all 24 weeks)

The table above is week 1 only. Across the full deduplicated 48,096-timestep series:

| Metric | Week 1 (X01) | **All 24 weeks** |
|---|---|---|
| Max link utilisation | 32.09% (CHIN→IPLS) | **75.36%** (KSCY→IPLS, 2004-09-01 05:45) |
| Mean utilisation | 2.73% | 2.69% |
| p95 utilisation | 7.10% | 6.28% |
| Mean per-timestep peak-link util | 7.38% | 7.76% |

The 24-week maximum is **more than double** the week-1 maximum — a longer observation
window contains larger extremes. This materially helps the project: peak utilisation
reaching 75% is a genuinely congested link, not a rounding artefact, which
strengthens the case for congestion classification and gives rerouting a real
hotspot to relieve.

### Known limitation, stated honestly

Absolute utilisation is **low** (mean 2.73%). This is not a data defect — the Abilene
backbone was genuinely and famously over-provisioned in 2004. The consequence is that
congestion **cannot** be defined by absolute thresholds like ">80% of capacity",
because that class would be empty.

Congestion is therefore defined **per-link, relative to that link's own utilisation
distribution** (percentile-based: Low ≤ p50, Medium p50–p80, High p80–p95, Critical
> p95) — the standard approach in traffic-classification research when literal
provisioned-capacity ground truth is unavailable or non-binding. Measured dynamic
range supports this: the median across links of p95/p50 is **1.46×**, and peak/median
reaches ~6× on the hot corridor links.

This choice has a bonus: percentile labelling is **capacity-free**, which is precisely
why the same pipeline can run unmodified on GÉANT despite its missing capacities.

### Why the combination beats Abilene alone

- **Generalisation evidence.** Training on Abilene and evaluating the same pipeline on
  GÉANT demonstrates the approach isn't overfitted to one 12-node topology — a
  materially stronger claim for a portfolio project than single-network results.
- **Two granularities.** 5-minute (Abilene) and 15-minute (GÉANT) test whether the
  temporal features hold up under a different sampling rate.
- **Scale range.** 12 nodes / 144 OD pairs vs 23 nodes / 529 OD pairs exercises the
  routing code at two graph sizes.
- **Independent topology validation.** SNDlib's published `geant.xml` / `abilene.xml`
  give a canonical reference to check our parsers against, so a silent parsing error
  in the topology can't quietly corrupt every downstream utilisation number.

---

## 5. Open decision — raw data is 188 MB

`data/raw/` totals **188 MB**. **No individual file exceeds 50 MB** (largest is
`X01.gz` at 7.3 MB), so nothing is near GitHub's 100 MB hard per-file limit — but the
aggregate is well past what belongs in a normal git repo.

Current state: **`.gitignore` excludes `data/raw/`**, and `scripts/fetch_data.py`
restores it from source. This is reversible and is **not** a final decision — the
Git LFS vs fetch-script choice is still open, per the project owner.

| Option | Pros | Cons |
|---|---|---|
| **Fetch script** (current) | Repo stays ~1 MB; clean clone; no LFS quota | Depends on upstream hosts staying up |
| **Git LFS** | Data travels with the repo; immune to link rot | Consumes LFS quota (1 GB free); needs `git lfs install` |
| **Hybrid** | Commit the 1.7 MB of topology/metadata + GÉANT (18 MB); fetch the 164 MB of Abilene matrices | Slightly more moving parts |

The **hybrid** is worth considering: the small, hard-to-replace topology files
(`topo-2003-04-10.txt`, `links`, `demands`, `A` — 28 KB total) are the pieces whose
loss would actually break the project, and they cost nothing to commit.

---

## 6. Sources

- Abilene TM — <https://www.cs.utexas.edu/~yzhang/research/AbileneTM/>
- GÉANT / TOTEM — <https://totem.info.ucl.ac.be/dataset.html>
- SNDlib — <https://sndlib.put.poznan.pl/>
- CAIDA passive datasets — <https://www.caida.org/catalog/datasets/passive_dataset/>
- WITS / WAND — <https://wand.net.nz/wits/> *(unreachable 2026-07-28)*
