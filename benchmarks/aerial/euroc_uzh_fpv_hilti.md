# EuRoC vs UZH-FPV vs Hilti — Three Aerial VIO Benchmarks, Three Different Stories (三大空中 VIO 基准)

> **发布时间**: EuRoC IJRR 2016 / UZH-FPV ICRA 2019 / Hilti 2021–
> **基准名**: EuRoC MAV · UZH-FPV Drone Racing · Hilti SLAM Challenge
> **核心定位**: 一句话回答三个不同的 VIO 失败模式 — EuRoC 测室内基线、UZH-FPV 测高动态、Hilti 测工地真实部署；缺一即缺一条 deployment claim。

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item dissection template 2026-05-21. Saturation claims `UNVERIFIED` where based on leaderboard skim.
**TL;DR:** EuRoC is fully saturated by 2026 and tells you nothing about deployment; UZH-FPV stresses the *dynamics* envelope (high-speed racing); Hilti stresses the *appearance + scale* envelope (construction-site outdoor). A VIO paper that reports only EuRoC is hiding either dynamics weakness, scale weakness, or both.

### X-Ray (non-expert friendly)

(a) Aerial visual-inertial odometry (VIO) lets a drone know where it is from cameras + IMU; three orthogonal failure modes (slow indoor / aggressive dynamics / outdoor real-site) each have a canonical benchmark. (b) EuRoC saturated by 2026, UZH-FPV stresses 15 m/s racing dynamics, Hilti stresses construction-grade lighting + texture-poor scale. (c) For aerial spatial-AI engineers: pick benchmarks by failure mode you claim to solve — reporting only EuRoC in 2026 is a methods-paper signal, not a deployment claim.

### 📍 Benchmark Evolution Timeline

```
KITTI 2012 ─► EuRoC 2016 ─► TUM-VI 2018 ─► ★ UZH-FPV 2019 ─► ★ Hilti 2021 ─► event-camera successor 2027?
   │            │                              │                  │
   │            └── indoor lab (saturated 2026) │                  └── construction-grade deployment GT
   │                                            └── racing dynamics (open)
   └── outdoor automotive — different envelope
```

EuRoC anchored the field for a decade; UZH-FPV and Hilti opened the dynamics / deployment axes that EuRoC can't measure.

### ⚡ Eureka Moment

**No single benchmark covers aerial VIO's three orthogonal failure modes.** Indoor-lab + racing-dynamics + construction-deployment are not interchangeable axes — a method can saturate EuRoC and *fail to initialize* on UZH-FPV. The diagnostic isn't which one a paper reports; it's which two it omits.

### 📌 Napkin Formula

```
Aerial VIO deployment-readiness ⇔ (EuRoC sub-10cm ATE) ∧ (UZH-FPV init-without-tuning) ∧ (Hilti lighting-transition survival)
                                                      ─ all three required, not OR ─
```

---

## 1 · Why three, not one

Aerial VIO has at least three orthogonal failure modes:

- **Benign slow indoor** — well-lit, low motion blur, repeatable trajectories
- **Aggressive dynamics** — 15+ m/s, high angular rates, motion blur dominates
- **Outdoor construction-grade scale + appearance** — long sequences, lighting changes, weak texture, GNSS-denied

No single benchmark covers all three. The three below were designed for one each. Cite all three or admit your scope.

See `crossing/slam-vio-migration/vggt_vs_drone_vio.md` for the broader argument about why aerial VIO is the strictest spatial-intelligence test case.

---

## 2 · EuRoC MAV (Burri et al. *IJRR 2016*)

**Rig.** ASL MAV with Aptina global-shutter stereo + ADIS16448 IMU, indoor at ETH's Vicon room. GT from Vicon / laser tracker. 11 sequences, easy/medium/difficult, max ~2 m/s, ~20 min cumulative.

**Why everyone reports it.** First good indoor stereo-inertial benchmark with reliable GT. Every VIO paper from VINS-Mono (2018) onward reports EuRoC.

**Saturation 2026.** Fully saturated `UNVERIFIED — leaderboard skim`. Top tightly-coupled methods (OpenVINS, ORB-SLAM3 inertial, VINS-Fusion patches) score sub-10 cm ATE on every sequence including "difficult". Differences between top methods are below the GT noise floor.

**What EuRoC does *not* test:** sustained high-speed flight (real cruise 5–15 m/s); outdoor lighting / sun-shadow transitions (the #1 real-world failure); sustained prop vibration; long sequences; GNSS-denied transitions. A paper reporting only EuRoC in 2026 is a methods paper, not a deployment claim.

---

## 3 · UZH-FPV Drone Racing (Delmerico et al. *ICRA 2019*)

**Rig.** Quadrotor with global-shutter forward + 45°-down cameras + onboard IMU, flown by professional racing pilots at UZH RPG. Leica laser tracker GT. Indoor + outdoor racing-line flights, speeds to ~14 m/s, IMU-saturating angular rates, motion blur, prop vibration.

**Tests:** motion blur at real exposure budgets, IMU saturation / prop aliasing, rapid scene-content change, aggressive turns. Many methods that win EuRoC fail to *initialize* on UZH-FPV without per-sequence tuning — that's the diagnostic value but makes the benchmark "ugly" for tables.

**Saturation 2026.** Far from saturated. Robust performance across all sequences without per-sequence tuning is still open `UNVERIFIED`. The UZH RPG racing line (Kaufmann et al. *Nature 2023*) bypasses this with a learned controller — different problem.

---

## 4 · Hilti SLAM Challenge (Helmberger et al., 2021–ongoing)

**Rig.** Multi-camera + IMU + LiDAR sensor head, hand-carried + vehicle-mounted on real construction sites. Total-station-anchored survey GT. Construction sites (indoor + outdoor + transitions), parking garages, multi-floor, real lighting, texture-poor walls.

**Tests that the other two don't:** texture-poor surfaces (concrete, drywall), indoor-outdoor lighting transitions, multi-sensor fusion (Cam + IMU + LiDAR), construction-grade scale, survey-grade GT at site scale.

**Why it's the closest thing to deployment.** Hilti's commercial product is laser-scanning at construction sites; the dataset was captured with the same operational envelope a real Hilti product survives. The only public benchmark where leaderboard wins plausibly map to shipping.

**Saturation 2026.** Open. Multi-sensor fusion methods lead; vision-only struggles on texture-poor sequences `UNVERIFIED — last winner table 2026-Q1`.

---

## 5 · Side-by-side comparison

| Axis | EuRoC | UZH-FPV | Hilti |
|---|---|---|---|
| Year | 2016 | 2019 | 2021– |
| Setting | Indoor lab | Indoor + outdoor racing | Construction sites |
| Max speed | ~2 m/s | ~14 m/s | walking + vehicle |
| Sensors | Stereo + IMU | Stereo + IMU | Multi-cam + IMU + LiDAR |
| GT source | Vicon + laser tracker | Leica laser tracker | Total-station survey |
| Saturation 2026 | ✅ saturated `UNVERIFIED` | ❌ open | ❌ open |
| Tests dynamics | weak | ✅ | weak |
| Tests scale | weak | weak | ✅ |
| Tests appearance | weak | medium | ✅ |
| Tests LiDAR fusion | ❌ | ❌ | ✅ |
| Deployment realism | low | medium (racing) | high |

---

## 5.5 · Worked example — auditing a VIO paper in 3 minutes

You see a 2026 VIO paper claiming "robust deployment-ready aerial autonomy":

1. **EuRoC** — sub-10 cm ATE on all 11 seqs? table-stakes; absent or per-seq-tuned = flag.
2. **UZH-FPV** — present without per-seq tuning? robust dynamics grounded; absent = "robust to fast motion" is rhetoric.
3. **Hilti** — present with texture-poor + lighting-transition seqs? real deployment paper; absent + "deployment-ready" = overclaim.
4. **Outdoor GNSS-denied** — none of the three test it; most papers paper over.
5. **Feed-forward 3D claims** — need rate / latency vs `crossing/slam-vio-migration/vggt_vs_drone_vio.md`.

Three minutes; the omissions tell the story.

---

## 6 · When a paper reports only EuRoC, what's hidden

The diagnostic that earns this doc its place:

1. **No dynamics claim possible.** EuRoC top speed is 2 m/s. "Robust to fast motion" without UZH-FPV is rhetoric.
2. **No outdoor claim possible.** All indoor. Sun + shadow transitions untested.
3. **No long-sequence claim possible.** Short sequences. Drift accumulation barely exercised.
4. **No texture-poor claim possible.** Plenty of texture. Concrete walls are not in the distribution.
5. **No multi-sensor fusion claim possible.** Camera + IMU only. LiDAR + Cam + IMU is the deployment reality.

If a paper makes any of those claims while reporting only EuRoC, demand UZH-FPV or Hilti.

---

## 7 · What to use when

- **VIO methods paper** → EuRoC (lingua franca) + at least one of UZH-FPV / Hilti
- **High-dynamics claim** → UZH-FPV mandatory
- **Deployment / construction-grade claim** → Hilti mandatory
- **Feed-forward 3D as VIO** → all three + cross-ref `crossing/slam-vio-migration/vggt_vs_drone_vio.md` for the rate / latency gap

---

## 7.5 · Hidden Assumptions

Assumptions that, when violated, make numbers misleading:

- **GT noise floor below methods** — fine on EuRoC, debatable on UZH-FPV Leica at racing speed.
- **Camera+IMU sync perfect** — small temporal offsets dominate sub-cm ATE; calibration drift invisible.
- **Single rig per benchmark** — cross-rig generalization rarely measured.
- **Static environment** — none stress dynamic agents (people, vehicles).
- **Daylight / repeatable lighting** — Hilti has lighting transitions but daylight-anchored.
- **No wind / no payload swing** — published flights only; gusts untested.
- **Western environments** — all European; dust / monsoon / snow / tropical absent.

---

## 7.6 · Interview Tip

When asked "what's the right benchmark for aerial VIO in 2026" — name **all three** and explain the failure mode each addresses (indoor saturated baseline / racing dynamics / construction deployment). Then point out that the *omissions* are the diagnostic — a paper reporting only EuRoC in 2026 cannot make any dynamics, outdoor, or multi-sensor claim. Bonus: mention that feed-forward 3D (VGGT-class) doesn't yet fit the latency budget any of these benchmarks implicitly assume (see `crossing/slam-vio-migration/vggt_vs_drone_vio.md`).

---

## 8 · 2-year outlook

EuRoC won't be replaced — historical results anchor it. By 2027 most serious aerial VIO papers will additionally report Hilti as the deployment-realism check. UZH-FPV may get superseded by an event-camera-primary successor; UZH RPG is the lab to watch.

**Falsifiable prediction:** before 2027-12 a top-tier aerial VIO paper will be desk-rejected or heavily criticized specifically for reporting only EuRoC.

---

## For the reader

- **VIO researcher** — pick benchmarks by the failure mode you solved, not by leaderboard tradition.
- **Drone engineer** — Hilti is the closest signal for site survival; UZH-FPV for racing / inspection cruise.
- **Reviewer** — "EuRoC only" is a flag, not a free pass.

---

## References

- EuRoC MAV — Burri et al. *IJRR 2016*. https://projects.asl.ethz.ch/datasets/doku.php?id=kmavvisualinertialdatasets
- UZH-FPV — Delmerico et al. *ICRA 2019*. https://fpv.ifi.uzh.ch/
- Hilti SLAM Challenge — Helmberger et al. 2021. https://hilti-challenge.com/ · https://arxiv.org/abs/2109.11316
- VINS-Mono — Qin et al. *T-RO 2018*. https://arxiv.org/abs/1708.03852
- OpenVINS — Geneva et al. *ICRA 2020*. https://arxiv.org/abs/1910.00298
- UZH RPG champion-level racing — Kaufmann et al. *Nature 2023*. https://www.nature.com/articles/s41586-023-06419-4
- Cross-ref: `crossing/slam-vio-migration/vggt_vs_drone_vio.md`

## Boundary

This doc compares three benchmarks at the protocol level. Per-method results (how OpenVINS performs on Hilti, how DROID-SLAM performs on UZH-FPV) belong in `embodiments/aerial/vio/`. Feed-forward 3D vs classical VIO is `crossing/slam-vio-migration/vggt_vs_drone_vio.md`.

---

*Last opinion update: 2026-05-21. v1.1 — backfilled to AGENTS.md 14-item template.*
