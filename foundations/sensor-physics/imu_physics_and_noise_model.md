# IMU Physics & Noise Model (IMU 物理与噪声模型 — MEMS vs FOG / Allan 方差 / 漂移预算)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — MEMS vs FOG sensing principles / Allan variance / bias instability / temperature
> **核心定位**：the drift-budget arithmetic VIO papers assume away — `$3 BMI270` vs `$15k KVH 1750` is a 5000× cost step and a 10000× bias-instability step, and the choice is dictated by mission duration

**Status:** v1 — opinionated draft, written to AGENTS.md 14-item dissection template 2026-05-21. Datasheet numbers marked `UNVERIFIED` need spec-sheet cross-check.
**Wedge tier:** sensor-physics expansion (4 of 5 sibling docs)

### X-Ray opening

Every embodiment ships at least one IMU; the only real question is *which physics*. MEMS gyros (vibrating mass, Coriolis readout) cost $3 and have bias instability ~0.5°/s — fine for drones with GNSS, fatal for AUVs without GNSS. FOG (Fiber-Optic Gyro, Sagnac effect on a coiled fiber) costs $5k–50k and has bias instability ~0.05°/hr — overkill for drones, mandatory for long-duration autonomous undersea or tunnel driving. For sensor engineers: the IMU choice collapses to one question — *how long does the platform have to dead-reckon without an aiding signal?*

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1985 ── First fiber-optic gyros (Honeywell, KVH) ── inertial nav era begins
2007 ── Apple iPhone 4 InvenSense MPU-6050 ── consumer MEMS IMU goes mass-market
2014 ── Bosch BMI160 / BMI270 lineage ── $3 9-DoF IMU
2015 ── DJI Phantom 3 MEMS+GPS fusion ── consumer drone era
2018 ── Honeywell HG4930 tactical MEMS (~$5k) ── mid-tier
2020 ── KVH 1750 / 1775 FOG widely adopted in AUV / surveying
2022 ── Apple AirPods Pro 2 9-DoF MEMS in earbud ── ~$1 cost floor `UNVERIFIED`
2024 ── Anello Photonics SiPh gyro <$1k targets ── photonic mid-tier emerging
202? ── ?  next: chip-scale atomic gyro / cold-atom interferometer (lab today)
```

This document sits at the MEMS-vs-FOG fork — the only real choice once "use an IMU" is decided.

---

## 1 · Sensing principles — two physical regimes

📌 **Napkin Formula**: `dead_reckon_drift = bias_instability × t + ARW × √t + scale_factor_error × Δθ`. Everything in §2 reads against this — MEMS drifts meters/minute, FOG drifts meters/hour, by 4 orders of magnitude on bias instability.

**(a) MEMS Coriolis gyro.** Micromachined vibrating mass (silicon, 100 µm scale) driven at resonance. Rotation about the sensitive axis injects a Coriolis force perpendicular to drive motion → capacitive pickoff measures it. Gyro-on-a-chip: 3 axes + 3 accelerometers + temperature + magnetometer in a 3×3 mm BGA. Bosch BMI270 (~$3 `UNVERIFIED`, 0.5°/s bias instability, 0.007°/√Hz ARW `UNVERIFIED`). InvenSense ICM-42688 sibling.

**(b) FOG (Fiber-Optic Gyro).** Sagnac effect: a beam split into two counter-propagating paths around a fiber coil. Rotation about the coil axis causes a path-length difference → phase shift at the recombination interferometer. Resolution scales with coil area × number of turns — KVH 1750 typical 200 m fiber. KVH 1750 ($15k `UNVERIFIED`, 0.05°/hr bias instability, 0.012°/√hr ARW `UNVERIFIED`). Honeywell GG1320 / iXBlue counterparts.

**(c) RLG (Ring Laser Gyro).** Same Sagnac principle, but with a laser cavity instead of fiber. Aircraft inertial navigation (Honeywell HG9900). Higher performance than FOG, larger and more expensive ($50k+). Out of scope for embodied AI at consumer cost.

**(d) Accelerometers.** Always MEMS at every tier — vibrating beam or pendulous mass, capacitive readout. Bias instability and noise scale similarly to gyros but accelerometer drift contributes via *double* integration to position, so the gyro number dominates orientation while the accelerometer dominates position drift once orientation is locked.

⚡ **Eureka Moment.** MEMS-vs-FOG is **not** a quality ladder — it's a mission-duration fork. MEMS is fine if you're aided every few seconds (GNSS, vision, wheel odometry). FOG only matters when you must coast unaided for minutes-to-hours. The cost step is 5000× because the physics step (vibrating silicon vs km-long coiled fiber) is fundamentally different.

---

## 2 · MEMS vs FOG comparison

| Property | MEMS (BMI270 class) | FOG (KVH 1750 class) |
|---|---|---|
| Sensing principle | Coriolis on vibrating mass | Sagnac on fiber coil |
| Cost | ~$3 | ~$15k |
| Weight | <1 g | 500–1000 g |
| Power | <10 mW | 5–15 W |
| Bias instability (gyro) | 0.5°/s `UNVERIFIED` | 0.05°/hr `UNVERIFIED` |
| ARW (angle random walk) | 0.007°/√Hz | 0.012°/√hr |
| Scale-factor stability | ~0.1% | ~5 ppm |
| Temperature sensitivity | ~0.05°/s/°C `UNVERIFIED` | ~0.001°/hr/°C `UNVERIFIED` |
| Operating range | -40 to +85 °C consumer | -40 to +85 °C industrial |
| Typical use | **BMI270 → drones, phones, AGVs** | **KVH 1750 → AUVs, L4 AD tunnels, surveying** |

Mid-tier "tactical-grade MEMS" (Honeywell HG4930, ~$5k `UNVERIFIED`) sits in between — 0.05°/hr bias *temporarily*, but drifts faster than FOG over hours due to remaining MEMS instability mechanisms.

---

## 3 · Allan variance — the canonical noise model

Plot σ(τ) of a stationary IMU on log-log: averaging time τ on x-axis, deviation σ on y-axis.

```
log σ
  ^
  |    \         /
  |     \  ARW  /
  |      \    /
  |       \  /  ← bias instability floor
  |        \/______
  |        /
  |       / RRW (rate random walk)
  |      /
  +-----+---------------------> log τ
        τ at minimum = bias instability time constant
```

Three regimes:
1. **ARW (angle random walk)** — short τ, slope -1/2 in log-log. Thermal / shot noise of the readout. Averages down as `1/√τ`. Improves with longer integration; sets short-term performance.
2. **Bias instability** — minimum of curve, slope 0. The *floor* of the IMU — averaging more doesn't help past this τ. Caused by mechanical / electronic 1/f noise. **The single number quoted on datasheets.**
3. **RRW (rate random walk)** — long τ, slope +1/2. Bias itself drifts. Dominates long-duration unaided integration.

For VIO / VINS-Fusion / OpenVINS papers, ARW + bias instability set the IMU pre-integration noise covariance. RRW is usually modeled as a slow random-walk bias state — and gets *worse* than papers assume on long flights because of unmodeled temperature transients.

---

## 4 · Worked example — 1 minute unaided flight: MEMS vs FOG position drift

Back-of-envelope (numbers `UNVERIFIED`, for engineering intuition):

```
Scenario:   GNSS-denied tunnel, no visual aid (smoke / dark)
Platform:   drone or robocar, dead-reckoning on IMU only
Duration:   t = 60 s
```

- **MEMS BMI270 path.**
  - Orientation drift from bias instability: `0.5°/s × 60 s = 30°`. Catastrophic by itself.
  - More realistic with calibration: residual bias post-calibration ~0.05°/s `UNVERIFIED` → 3° over 60 s.
  - Accelerometer bias ~0.01 m/s² `UNVERIFIED` → position drift `(1/2)·b·t² = 0.5·0.01·3600 = 18 m`.
  - **Total position uncertainty after 60 s of unaided flight: ~20 m.** Unusable for tunnel driving; barely tolerable for short GNSS gap.

- **FOG KVH 1750 path.**
  - Orientation drift: `0.05°/hr × (60/3600) = 0.0008°`. Effectively zero.
  - Accelerometer (still MEMS in IMU package — FOG only replaces gyro): same ~0.01 m/s² → 18 m position drift.
  - **Total position uncertainty after 60 s: ~18 m**, dominated entirely by the accelerometer.
  - But over 1 hour, MEMS position drift balloons to ~`O(km)` while FOG-aided estimator holds tens of meters.

Confirms §1 → §2: at 60 s, accelerometer bias dominates either way. FOG advantage shows up at *minutes-to-hours*. 5000× cost step is justified only when mission unaided duration exceeds ~5 minutes.

---

## 5 · Sources of error you only learn the hard way

**Temperature transients.** Most MEMS specs are *at* a calibrated temperature. Cold-start a drone outdoors → IMU runs through a 30 °C swing in 10 minutes → uncalibrated bias drift dominates everything else. Mitigations: thermal hood, embedded calibration LUT, soft-start delay.

**Vibration aliasing.** Drone motor 1F at ~100–500 Hz; IMU sampled at 1 kHz can alias 600 Hz vibration into the low-frequency band where the navigation filter sits. The IMU isn't *broken* — the sampling is. Mitigations: mechanical isolation, anti-alias LPF before ADC, oversample-and-decimate.

**Magnetometer corruption.** Magnetic-driven heading aid breaks near batteries, motors, ferromagnetic cargo. Always treat mag as soft-aid not hard-aid.

**G-sensitivity (gyro response to linear acceleration).** Cheap MEMS gyros pick up `O(0.01°/s/g)` bias under sustained g. Aggressive drone maneuvers inject false rotation.

**Coupling between axes.** Cross-axis sensitivity ~0.5% for cheap MEMS; calibration matrix matters.

---

## 6 · Hidden Assumptions — what the IMU choice silently bets on

The MEMS-vs-FOG decision is only stable while these hold:

- **Vibration spectrum does not exceed sampling anti-alias bandwidth.** Drone motors at 5–10 kRPM (200–500 Hz 1F) under 1 kHz IMU sampling → must filter. High-RPM micro-drone breaks this assumption.
- **Operating temperature stays within calibration envelope.** -40 to +85 °C industrial; -20 to +60 °C consumer. Outside, bias jumps multiples beyond datasheet.
- **Mission duration is correctly estimated.** Drones nominally GNSS-aided every 100 ms — MEMS fine. AUVs without GNSS for hours — FOG mandatory. Wrong estimate → wrong IMU class.
- **Aiding sources reliable.** Vision-aided VIO fails in dark, dust, fog → IMU coasts unaided → the *aided* assumption that justified MEMS evaporates. Same hardware, different verdict.
- **Calibration kept current.** MEMS bias drifts batch-to-batch and over years; OEM factory cal often sufficient for short missions, fails for long-duration. Long-duration platforms run self-calibration during stationary periods.
- **Accelerometer is the bottleneck in 1-minute drift, not the gyro.** Past 5–10 minutes unaided, the gyro takes over. Picking the FOG gyro doesn't help if you keep a cheap accelerometer.

---

## 7 · Comparison across embodiments + interview tip

| Embodiment | IMU pick | Why |
|---|---|---|
| **Manipulation** | MEMS BMI270 ($3) | static base; visual feedback dominates; <10 s unaided periods |
| **Humanoid** | multiple MEMS (>12 typical) | per-joint sensing; aggregate via kinematic chain |
| **Ground AGV** | MEMS + wheel odometry | wheel encoders aid every meter; MEMS sufficient |
| **Drone (consumer)** | MEMS + GNSS + visual | every aid available; MEMS fine; FOG weight prohibitive |
| **AD passenger car** | auto-grade MEMS ($50–500) | GNSS + visual aid; tunnels handled by short MEMS dead-reckon |
| **AD L4 + tunnels >5 min** | MEMS + occasional tactical-grade or FOG hybrid | unaided tunnel duration matters |
| **AUV** | **FOG mandatory (KVH 1750)** | hours unaided underwater; physics forbids GNSS, vision limited to <5 m |
| **Aerospace inertial nav** | RLG ($50k+) | hours-to-days unaided, beyond FOG envelope |

Lesson: pick IMU class by **unaided mission duration**, not by "quality." Drones don't need FOG; AUVs do.

**🎙️ Interview Tip.** Asked "do we need a FOG for this drone?" — first question back is *"longest unaided segment in seconds?"* If <30 s of GNSS gap, MEMS + good VIO is overkill-killer. If you can't bound it (mining tunnel, AUV mission), FOG. Anyone answering "FOG always better" is selling FOG.

---

## 8 · For the reader

- **Manipulation** — MEMS ($3), don't think about it.
- **Drone** — MEMS BMI270 / ICM-42688 + GNSS + VIO. FOG only if mission spec contains >5 min unaided segments.
- **AD** — auto-grade MEMS for L2; tactical-grade MEMS for L4 with tunnels; FOG only if mission includes long tunnel + no map prior.
- **Marine** — FOG mandatory (KVH 1750 or equivalent); no substitute.

---

## References

- Bosch BMI270 datasheet `UNVERIFIED`
- InvenSense ICM-42688 datasheet `UNVERIFIED`
- KVH 1750 / 1775 IMU technical brief `UNVERIFIED, no DOI`
- Honeywell HG4930 tactical MEMS spec `UNVERIFIED, no DOI`
- IEEE 952-1997 — IMU specification format (Allan variance terminology)
- Empirical: maintainer's drone calibration / temperature-soak experience

## Boundary

- `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md` — visual sensing sibling
- `foundations/sensor-physics/tof_physics_for_embodied_ai.md` — depth sensing sibling
- `foundations/sensor-physics/lidar_physics_905_vs_1550.md` — long-range sibling
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — IMU is universal-core across all embodiments; matrix shows when FOG enters
- `embodiments/aerial/sensor-stack/` — drone IMU integration / vibration isolation
- VIO / VINS pre-integration math: `foundations/slam-vio/` (TBD) — IMU model *consumption*. This doc covers the sensor physics generating the noise; the filter math living under SLAM-VIO consumes it.

*2026-05-21. v1 first version, satisfies 14-item gate. UNVERIFIED → datasheet cites in v1.1.*

---
[← Back to sensor-physics README](./README.md)
