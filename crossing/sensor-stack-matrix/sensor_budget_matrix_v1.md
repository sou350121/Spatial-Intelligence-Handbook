# Sensor Budget Matrix v1 (传感器预算矩阵 — 跨 embodiment SWaP-C 对照)

> **发布时间**：2026-05-21
> **适用范围**：6 embodiments × 8 sensor classes (manipulation/humanoid/ground/driving/aerial/marine)
> **核心定位**：industry's missing SWaP-C account — academic surveys never write it down, internal BoMs always do.

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item dissection template 2026-05-21. Datasheet numbers marked `UNVERIFIED` need spec-sheet cross-check.
**Wedge tier:** W2 (one of 5 launch docs)
**TL;DR:** Each embodiment picks its sensor stack on a binding SWaP-C constraint academic surveys never write down. Drones bound by grams+watts, AD by range, manipulation by cost-per-cell, marine by physics. A Velodyne VLP-16 at **580g/~8W** `UNVERIFIED` is unremarkable on a Waymo van, fatal on a 250g racing drone, over-budget by 4× on a $5k AGV. Same sensor, three verdicts.

### X-Ray opening (non-expert friendly)

(a) The **same** VLP-16 is mandatory on Waymo's van, fatal on a 250g racer, over-budget by 4× on a $5k AGV — one datasheet, three verdicts. (b) Each embodiment binds on a different constraint: weight+power (drones), range (AD), cost-per-cell (manipulation), physics (marine). (c) For sensor-hardware engineers, this is the BoM-level table usually rebuilt internally from scratch — academic surveys stop at "we used a RealSense D435."

### 📍 研究全景时间线 (where this matrix sits)

```
2010 ── Velodyne HDL-64 era (KITTI). LiDAR == AD. $80k/13kg normal.
2013 ── Kinect v1 / Xtion. Indoor RGBD unlocks manipulation papers.
2015 ── MEMS IMU revolution (Bosch BMI / InvenSense). $3 IMUs unlock drones.
2017 ── 850nm RealSense D400 lineage. RGBD = "default" indoor; sun saturation
        ignored by most academic benchmarks.
2020 ── Apple iPad/iPhone Pro LiDAR (Sony dToF). Consumer SPAD normalized.
2023 ── 1550nm InGaAs SPAD wave (Hesai AT128, Innoviz, Aeva).
2025 ── Livox Mid-360 (~250g) brings LiDAR within reach of 3kg+ drones.
        ── you are here (2026) ──
?    ── Solid-state automotive LiDAR <100g? Underwater LiDAR <$50k? Open.
```

---

## 1 · SWaP-C axes per embodiment

📌 **Napkin Formula** (X-Ray):

```
verdict = sensor_cost / (embodiment_total_budget × workspace_relevance)
```

SWaP-C decisions are **ratios, not absolute prices**. A $4k LiDAR is "cheap" on an $80k AD car at 200m; "infinite" on a $300 hobby drone at 5m. Workspace relevance is the multiplier most surveys silently drop.

| Embodiment | Binding constraint | Sensor share of budget |
|---|---|---|
| Manipulation | cost-per-cell | ~5% of $25–50k arm |
| Humanoid | head weight + thermal | 3–8% |
| Ground (AGV) | cost + cert | 10–20% of $5–30k |
| Driving (L4) | range + integration miles | $50k+ on $80k vehicle |
| Aerial (&lt;3kg) | **weight + power** | 20–40% by weight |
| Marine (AUV) | pressure + acoustic | 30–50% of $50k–1M |

## 2 · The matrix, expanded

Cells: **status** · *reason* · number.

|  | RGB mono | Stereo | RGBD | LiDAR | IMU | NIR | Event | Acoustic |
|---|---|---|---|---|---|---|---|---|
| **Manipulation** | sometimes · *wrist fallback* | **core** · *5–10cm baseline* | **core** · *D435 default; 5–80cm matches workspace, 70g/$300* | **rare** · *adds nothing sub-1m* | **core** · *BMI270 ~$3* | sometimes · *shiny parts* | rare | rare |
| **Humanoid** | **core** · *peripheral* | **core** · *only metric primitive fitting the head* | sometimes · *torso, not face* | sometimes · *H1 ships one; 500g tolerated* | **core** · *>12 IMUs typical* | rare · *head thermal* | research | rare |
| **Ground (AGV)** | **core** · *cheapest primitive, $30* | **core** · *ZED-class &lt;$500* | sometimes · *indoor only* | **core outdoor** · *Hokuyo $1.5k cert; Velodyne 580g/8W `UNVERIFIED`* | **core** · *only dead-reckoning under shelves* | rare | rare | sometimes · *ultrasonic &lt;$5* |
| **Driving (AD)** | **core** · *lights/signs/lanes* | sometimes · *Tesla yes; Waymo no* | **rare** · *breaks past 5m; target 50–200m* | **core Waymo / never Tesla** · *128-beam $8–80k, 1–3kg/15–30W `UNVERIFIED`* | **core** · *auto-grade $50–500; +FOG $5–20k tunnels* | rare | research | rare · *parking only* |
| **Aerial (&lt;3kg)** | **core** · *FPV = platform's eyes, 5–15g* | sometimes · *Skydio yes; racing no* | **rare** · *active illum = power suicide; §3.1* | sometimes · *Livox 500g/10W flies on 3kg+ only* | **core** · *only >100Hz path &lt;1g cost; BMI270 0.5g/&lt;5mW* | rare | research · *UZH RPG* | sometimes · *altimeter &lt;5m* |
| **Marine (AUV)** | sometimes · *&lt;5m visibility* | sometimes · *photogrammetry* | rare · *NIR absorbed &lt;1m* | rare · *blue-green $200k+* | **core** · *FOG mandatory; KVH 1750 $15k/700g `UNVERIFIED`* | rare · *physics forbids* | rare | **core** · *DVL+multibeam+side-scan = the whole stack; AURELION ACOSTRA `UNVERIFIED, no DOI`* |

---

## 3 · The three counterintuitive cells

### 3.1 Why drones almost never use RGBD

A D435 is 70g/3W. On a Skydio 2+ (800g) tolerable; on a 250g cinewhoop it's 28% of all-up weight and >10% of battery — *before* the projector helps, because **outdoor sunlight saturates the 850nm pattern within 2m** (see `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md`). Pay weight indoors, get nothing outdoors.

Deeper: on a 3kg quad, every 100g costs 30–60s of hover `UNVERIFIED`. A 500g active-illumination rig = ~2 min lost on a 12-min mission, for a sensor working only in 0.5–3m — drones fly 5–50m. The Venn diagram is empty. Pattern: **mono RGB + IMU + ultrasonic &lt;5m + (optional) downward stereo**. Active depth reserved for indoor inspection drones >1.5kg.

### 3.2 Why AD almost never uses RGBD

Highway AD design range is 150–250m. RGBD breaks past 5m (structured light) or ~20m (ToF) because returned NIR falls as 1/r² against a 1kW/m² sunlight floor `UNVERIFIED`. To match LiDAR at 200m, active RGBD needs *kilowatts* — which is why pulsed LiDAR exists. RGBD and LiDAR aren't competitors at AD range; they're the same physics scaled by 100× optical power. AD depth = **stereo + LiDAR + radar**, RGBD only in parking-assist. Mobileye: stereo+radar+mono-ML. Waymo: LiDAR-primary.

### 3.3 Why manipulation almost never uses LiDAR

VLP-16: $4k/580g `UNVERIFIED`. D435: $300/70g. Manipulation workspace is a 1m³ cube. Inside it, LiDAR's 0.1–0.4° angular resolution gives sub-cm depth — same as a $300 RGBD. Outside, you don't care. LiDAR offers **no resolution advantage in the relevant volume** at 13× cost and 8× weight. Exception: mobile manipulation where base amortizes 2D LiDAR for safety — wrist stays RGBD. LiDAR's value scales with range; manipulation's range doesn't.

---

## 4 · Cross-cutting patterns

- **IMU is always core.** Only question: FOG vs MEMS, decided by mission duration vs allowable drift. BMI270 (~$3, 0.5°/s bias `UNVERIFIED`) covers drones/AGVs; KVH 1750 FOG (~$15k, 0.05°/hr `UNVERIFIED`) covers AUVs and L4 AD.
- **At least one camera is always core.** Mono vs stereo is $200 + sync complexity, not physics.
- ⚡ **Eureka Moment — Sensor #3 splits embodiments.** IMU is universal, ≥1 camera is universal, and **the third sensor (RGBD / LiDAR / sonar / nothing) is where the embodiment identity is written**. Everything else follows.

## 5 · Hidden Assumptions

Where this matrix would break:

- **Embodiment classes are fixed.** Hybrid duty cycles (teleop humanoid indoor + walking outdoor) collapse here; re-classify if needed.
- **Payload class dominates compute class.** Sub-100g nano drones flip this — compute weight rivals sensor weight.
- **Vendor SKU prices stable.** Hesai/Innoviz moved 3× downward in 24 months; "$8–80k LiDAR" is a 2026 snapshot, not a law.
- **Underwater visibility physics holds.** Turbid coastal vs clear blue shifts "&lt;5m visibility" by an order of magnitude.
- **AD long range is a hard requirement.** Geofenced low-speed AD (campus shuttle, mining truck) unlocks cheaper RGBD-class stacks.
- **`UNVERIFIED` numbers within 2×.** Order-of-magnitude is load-bearing; 5×-off vendor spec may flip individual verdicts — the *pattern* (Sensor #3 splits embodiments) does not.

## 6 · "Always" / "Never" per embodiment

Manipulation: RGBD wrist / never LiDAR. Humanoid: stereo head + multi-IMU / never active NIR on head. Ground: 2D safety LiDAR + wheel IMU / never FOG. Driving: front mono + radar + IMU / never RGBD. Aerial &lt;3kg: IMU + mono FPV / never RGBD. Marine: FOG IMU + DVL / never RGB-only.

## 7 · Decision tree — embodiment + budget → starter stack

**$500 indoor AGV** → D435 ($300) + BMI270 ($3) + ultrasonic ($5) + RPi. Skip LiDAR; depth as virtual 2D scan. Ships in a weekend; won't pass SEMI S2.

**$5k outdoor drone (1.5kg)** → Mono global-shutter ($200) + BMI270 ($3) + GPS/RTK ($300) + downward stereo ($400) + Livox Mid-360 *only if* payload >2kg (~$1k/250g `UNVERIFIED`). For a 250g racer: mono + IMU + baro. VLP-16 at $4k/580g is a non-starter.

**$50k AD demo car** → Auto IMU ($500) + 4–6× mono ($2k) + front stereo ($1k) + 128-beam LiDAR ($15–25k, Hesai AT128 `UNVERIFIED`) + 4× corner radar ($2k) + front long-range radar ($1.5k). LiDAR alone = half the BoM; "Tesla or Waymo school?" reduces to "spend half the budget on one device?"

## 8 · Falsifiable 2-year prediction

**By 2028-05-21**, ≥1 commercial sub-3kg drone will ship with an integrated &lt;100g solid-state automotive-derived LiDAR (Hesai/Innoviz/Aeva lineage) at &lt;$2k retail, flipping the aerial "LiDAR rare" cell to "sometimes" for the 1–3kg class. Falsified if no such SKU exists at that date.

## 9 · For the reader (per-persona)

- **Manipulation engineer:** stop benchmarking LiDAR; RGBD wrist + IMU is your stack — argue resolution, not range.
- **Aerial engineer:** every 100g = 30–60s of hover; reject active-NIR on outdoor sub-3kg platforms.
- **AD engineer:** RGBD is not "cheap LiDAR" — different range regime. Stereo+radar+mono-ML (Tesla) vs LiDAR-primary (Waymo).
- **Marine engineer:** acoustic (DVL + multibeam) is *the* stack; treat RGB/NIR as &lt;5m clear-water special cases.

## 10 · Interview Tip

If asked *"why doesn't drone X use RGBD?"* — say **weight + sun saturation + range mismatch**. Always SWaP-C, never "unproven technology."

---

## Cross-references

`foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md` · `embodiments/aerial/sensor-stack/` · `embodiments/marine/` · `deployment/hardware-selection/`.

## References

Sony IMX900 · Velodyne VLP-16 / Hesai AT128 / Innoviz One · Bosch BMI270 · KVH 1750 FOG · Intel RealSense D435 · AURELION ACOSTRA — all `UNVERIFIED, no DOI`. Skydio blog. Tesla AI Day.

## Boundary

Compares sensor classes across embodiments at BoM level. Per-sensor physics: `foundations/sensor-physics/`. Per-embodiment integration: `embodiments/*/sensor-stack/`.

*2026-05-21. v1.1 backfill — datasheets verified in v1.2.*
