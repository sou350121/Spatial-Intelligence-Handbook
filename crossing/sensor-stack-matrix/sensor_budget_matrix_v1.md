# Sensor Budget Matrix v1

**Status:** v1 — opinionated draft. Datasheet numbers marked `UNVERIFIED` need spec-sheet cross-check.
**Wedge tier:** W2 (one of 5 launch docs)
**TL;DR:** Each embodiment picks its sensor stack on a binding SWaP-C constraint (Size / Weight / Power / Cost) academic surveys never write down. Drones bound by grams and watts, AD by range and integration miles, manipulation by cost-per-cell, marine by physics. A Velodyne VLP-16 at **580g/~8W** `UNVERIFIED` is unremarkable on a Waymo van, fatal on a 250g racing drone, over-budget by 4× on a $5k AGV. Same sensor, three verdicts. That is the whole game.

---
## 1 · SWaP-C axes per embodiment

Manipulation: cost-per-cell, ~5% of $25–50k arm. Humanoid: head weight + thermal, 3–8%. Ground (AGV): cost + cert, 10–20% of $5–30k. Driving (L4): range + integration miles, $50k+ on $80k vehicle. Aerial (<3kg): **weight + power**, 20–40% by weight. Marine (AUV): pressure + acoustic, 30–50% of $50k–1M.
## 2 · The matrix, expanded

Cells: **status** · *reason* · number.

|  | RGB mono | Stereo | RGBD | LiDAR | IMU | NIR | Event | Acoustic |
|---|---|---|---|---|---|---|---|---|
| **Manipulation** | sometimes · *wrist fallback* | **core** · *5–10cm baseline* | **core** · *D435 default; 5–80cm matches workspace, 70g/$300* | **rare** · *adds nothing sub-1m* | **core** · *BMI270 ~$3* | sometimes · *shiny parts* | rare | rare |
| **Humanoid** | **core** · *peripheral* | **core** · *only metric primitive fitting the head* | sometimes · *torso, not face* | sometimes · *H1 ships one; 500g tolerated* | **core** · *>12 IMUs typical* | rare · *head thermal* | research | rare |
| **Ground (AGV)** | **core** · *cheapest primitive, $30* | **core** · *ZED-class <$500* | sometimes · *indoor only* | **core outdoor** · *Hokuyo $1.5k cert; Velodyne 580g/8W `UNVERIFIED`* | **core** · *only dead-reckoning under shelves* | rare | rare | sometimes · *ultrasonic <$5* |
| **Driving (AD)** | **core** · *lights/signs/lanes* | sometimes · *Tesla yes; Waymo no* | **rare** · *breaks past 5m; target 50–200m* | **core Waymo / never Tesla** · *128-beam $8–80k, 1–3kg/15–30W `UNVERIFIED`* | **core** · *auto-grade $50–500; +FOG $5–20k tunnels* | rare | research | rare · *parking only* |
| **Aerial (<3kg)** | **core** · *FPV = platform's eyes, 5–15g* | sometimes · *Skydio yes; racing no* | **rare** · *active illum = power suicide; §3.1* | sometimes · *Livox 500g/10W flies on 3kg+ only* | **core** · *only >100Hz path <1g cost; BMI270 0.5g/<5mW* | rare | research · *UZH RPG* | sometimes · *altimeter <5m* |
| **Marine (AUV)** | sometimes · *<5m visibility* | sometimes · *photogrammetry* | rare · *NIR absorbed <1m* | rare · *blue-green $200k+* | **core** · *FOG mandatory; KVH 1750 $15k/700g `UNVERIFIED`* | rare · *physics forbids* | rare | **core** · *DVL+multibeam+side-scan = the whole stack; AURELION ACOSTRA `UNVERIFIED, no DOI`* |

---
## 3 · The three counterintuitive cells

### 3.1 Why drones almost never use RGBD

A D435 is 70g/3W. On a Skydio 2+ (800g) that's tolerable; on a 250g cinewhoop it's 28% of all-up weight and >10% of battery — *before* the projector helps you, because **outdoor sunlight saturates the 850nm pattern within 2m** (see `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md`). You pay weight indoors and get nothing outdoors.

The deeper number: on a 3kg quad, every 100g costs 30–60s of hover `UNVERIFIED`. A 500g active-illumination rig = ~2 min lost on a 12-min mission — 17% of mission, for a sensor that only works in the 0.5–3m band drones rarely operate in. Drones fly 5–50m space; RGBD is built for 0.5–5m. The Venn diagram is empty. Dominant pattern: **mono RGB + IMU + ultrasonic <5m + (optional) downward stereo**. Active depth reserved for indoor inspection drones over 1.5kg. See `embodiments/aerial/sensor-stack/`.

### 3.2 Why AD almost never uses RGBD

Design range for highway AD is 150–250m forward, 50–80m side. RGBD breaks past 5m (structured light) or ~20m (indoor ToF) because returned NIR falls as 1/r² and ambient sunlight is a 1kW/m² floor `UNVERIFIED`. To match LiDAR at 200m, active RGBD would need *kilowatts* of illumination — which is exactly why pulsed LiDAR exists. RGBD and LiDAR aren't competitors at AD range; they're the same physics scaled by 100× optical power and a different detector (SPAD vs ToF imager). The AD depth question is **stereo + LiDAR + radar**, with RGBD only in parking-assist (<5m, low speed). Mobileye-class: stereo + radar + mono ML depth. Waymo-class: LiDAR-primary. RGBD never reaches the highway stack.

### 3.3 Why manipulation almost never uses LiDAR

VLP-16: $4k/580g `UNVERIFIED`. D435: $300/70g. Manipulation workspace is a 1m³ cube. Inside that cube, LiDAR's 0.1–0.4° angular resolution gives sub-cm depth — same as a $300 RGBD. Outside the cube you don't care. LiDAR offers **no resolution advantage in the relevant volume** while costing 13× and weighing 8× more. Exception: mobile manipulation (Stretch, Fetch) where the base already amortizes a 2D LiDAR for safety — but even there the wrist sensor is RGBD. LiDAR's value scales with range; manipulation's range doesn't. The trades never cross.

---
## 4 · Cross-cutting patterns

- **IMU is always core.** Every embodiment lists it. Only real question: FOG vs MEMS, decided by mission duration vs allowable drift. BMI270 (MEMS, ~$3, 0.5°/s bias `UNVERIFIED`) covers drones/AGVs. KVH 1750 FOG (~$15k, 0.05°/hr `UNVERIFIED`) covers AUVs and L4 AD.
- **At least one camera is always core.** Mono vs stereo is a $200 + sync-complexity decision, not physics.
- **Sensor #3 splits embodiments.** RGBD for manipulation/indoor. LiDAR for outdoor ground + AD. Sonar for marine. Nothing for sub-1kg aerial. This is the cell where a Velodyne datasheet number lives or dies.

---
## 5 · "Always" / "Never" per embodiment

Manipulation: RGBD wrist / never LiDAR. Humanoid: stereo head + multi-IMU / never active NIR on head (thermal). Ground: 2D safety LiDAR + wheel IMU / never FOG (overkill). Driving: front mono + radar + IMU / never RGBD (range). Aerial <3kg: IMU + mono FPV / never RGBD (weight + sun). Marine: FOG IMU + DVL / never RGB-only stacks.

---
## 6 · Decision tree — embodiment + budget → starter stack

**$500 indoor AGV** → D435 ($300) + BMI270 ($3) + ultrasonic ($5) + RPi compute. Skip LiDAR; use depth as virtual 2D scan. Ships in a weekend; won't pass SEMI S2.

**$5,000 outdoor drone (1.5kg)** → Mono global-shutter ($200) + BMI270 ($3) + GPS/RTK ($300) + downward stereo ($400) + Livox Mid-360 *only if* payload >2kg (~$1k/250g `UNVERIFIED`). For a 250g racer: mono + IMU + baro. VLP-16 at $4k/580g is a non-starter; the LiDAR question only matters above 3kg.

**$50,000 AD demo car** → Auto IMU ($500) + 4–6× mono ($2k) + front stereo ($1k) + 128-beam LiDAR ($15–25k, Hesai AT128 `UNVERIFIED`) + 4× corner radar ($2k) + front long-range radar ($1.5k). LiDAR alone is half the BoM; "Tesla or Waymo school?" reduces to "spend half the budget on one device?" — the rest follows.

---
## Cross-references

`foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md` (why 850nm RGBD breaks outdoors) · `embodiments/aerial/sensor-stack/` (drone payload class table) · `embodiments/marine/` (DVL+FOG+sonar) · `deployment/hardware-selection/` (BoM templates).

## References (datasheet-dominant)

Sony IMX900 · Velodyne VLP-16 / Hesai AT128 / Innoviz One · Bosch BMI270 · KVH 1750 FOG · Intel RealSense D435 · AURELION ACOSTRA sonar — all `UNVERIFIED, no DOI`. Skydio engineering blog. Tesla AI Day archives.

## Boundary

Compares sensor classes across embodiments at BoM level. Per-sensor physics: `foundations/sensor-physics/`. Per-embodiment integration: `embodiments/*/sensor-stack/`. Cite from there when the cross-embodiment SWaP-C trade is what's argued.

*2026-05-21. Datasheets verified in v1.1.*
