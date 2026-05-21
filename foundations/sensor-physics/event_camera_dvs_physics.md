# Event Camera (DVS) Physics for Embodied AI (事件相机物理 — 异步像素 / HDR / 10us 时间分辨率)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — async pixel principle / HDR / latency / motion-or-nothing
> **核心定位**：the "no global frame, no exposure, no shutter" sensor — the academic press kit hides that **static scenes return zero data** and that's the load-bearing constraint, not 10 µs latency

**Status:** v1 — opinionated draft, written to AGENTS.md 14-item dissection template 2026-05-21. Datasheet numbers marked `UNVERIFIED` need spec-sheet cross-check.
**Wedge tier:** sensor-physics expansion (5 of 5 sibling docs)

### X-Ray opening

Event cameras (Dynamic Vision Sensors, DVS) replace global-shutter exposure with *per-pixel asynchronous threshold triggers*: each pixel independently emits an "event" (x, y, polarity, timestamp) whenever its log-intensity changes by ±θ. 10 µs timestamp resolution beats 30 Hz frames by 3000×. 120 dB intrinsic HDR beats a 60 dB CMOS by 60 dB. But the same architecture means **a static, well-lit scene returns zero bits** — there is no "frame" to capture. For sensor engineers: event cameras are not "better cameras" — they're a different sensing modality that wins on motion + HDR and loses everywhere else.

### 📍 研究全景时间线 (Research Landscape Timeline)

```
2008 ── Lichtsteiner DVS128 (ETH Zurich Tobi Delbruck) ── first viable async pixel
2014 ── DAVIS (active + DVS hybrid, iniVation) ── frames AND events together
2017 ── Prophesee (Chronocam) founded ── commercial focus
2019 ── Prophesee Gen3 VGA ── 640×480, automotive interest
2020 ── Sony IMX636 (Sony + Prophesee partnership, 1280×720)
2021 ── UZH RPG drone racing (DVS-only quad navigation) ── high-speed validation
2023 ── Prophesee EVK4 ── developer kit standard
2024 ── Sony IMX661 / hybrid event-frame sensors emerge
202? ── ?  next: hybrid event-frame-depth single die / spiking-NN co-processor
```

This document sits at the "event vs frame" sensor-modality fork — the only sensor in the lineup that doesn't produce frames.

---

## 1 · Async pixel principle

📌 **Napkin Formula**: `event_rate ≈ N_pixels × motion_in_pixels_per_sec × (avg_contrast / θ)`. Everything in §2 reads against this — DVS data volume is bounded by scene motion, not pixel count × frame rate.

**(a) The pixel circuit.** Each pixel contains:
1. A photoreceptor (logarithmic, not linear — this is where HDR comes from).
2. A change amplifier comparing current log-intensity to a memorized value.
3. Two threshold comparators (positive and negative direction).
4. A reset signal that latches the new value once an event is emitted.

When `|log(I_now) - log(I_last_event)| > θ` (typically 10–25% intensity change), the pixel emits an event `(x, y, t, polarity)` to the chip-level arbiter. The arbiter outputs events serially over an AER (Address-Event Representation) bus at 100M–1G events/s peak `UNVERIFIED`.

**(b) Logarithmic photoreceptor → 120 dB HDR.** Conventional CMOS has linear photoreceptor + ADC bit depth → ~60 dB. Logarithmic compression in DVS pixel gives intrinsic 120 dB `UNVERIFIED` — sun + shadow in same frame without saturation, because pixels at different intensities operate on independent logarithmic scales.

**(c) 10 µs timestamping.** Pixel asynchrony + chip-level timestamp counter → events are timestamped to ~1–10 µs `UNVERIFIED`. There is no "frame" — temporal resolution is bounded by readout bandwidth, not exposure time.

**(d) Polarity per event.** Only direction of change (brighter / darker), not magnitude. To recover intensity you'd need to integrate events or use a hybrid sensor (DAVIS, Prophesee Gen4 hybrid).

⚡ **Eureka Moment.** Event cameras *replace the shutter with a threshold*. There is no notion of exposure time. Static scene = zero events. Fast motion = ms-scale per-pixel response. This is not "high speed" — it's *event-driven*. The CMOS framing assumption is gone.

---

## 2 · DVS vs frame camera comparison

| Property | Global-shutter CMOS (Sony IMX900) | Event camera (Prophesee EVK4) |
|---|---|---|
| Output | dense frames at fixed Hz | sparse events (x, y, t, ±) |
| Temporal resolution | 1–10 ms (frame period) | 1–10 µs (per-pixel) `UNVERIFIED` |
| Dynamic range | ~60 dB (linear) | ~120 dB (log) `UNVERIFIED` |
| Static scene output | full frame every period | ~zero (only noise events) |
| Motion blur | yes, exposure-bound | none (no exposure) |
| Data volume | constant (W × H × Hz × bits) | scene-dependent, can be 10–1000× less or more |
| Sensor cost | $5–500 | $200–3000 |
| Resolution (typical) | 1080p–4K | VGA–HD (1280×720 max today `UNVERIFIED`) |
| Latency to first event | ~33 ms (one frame) | ~10 µs `UNVERIFIED` |
| Power | 0.1–5 W | 0.01–0.5 W (scene-dependent) |
| Typical vendors | Sony, OmniVision | **Prophesee, iniVation, Samsung research** |

Rule predicting when DVS wins: scene motion ≫ static content **and** latency / HDR matters. Static surveillance loses to frames; high-speed obstacle avoidance wins with DVS.

---

## 3 · Prophesee vs iniVation — sensor lineage

**Prophesee (formerly Chronocam).** French startup, commercial focus. Partnership with Sony → IMX636 (1280×720) and IMX669 (HD hybrid event+frame). Higher resolution, automotive-grade ambitions, EVK4 developer kit. SDK + OpenEB stack mature. Cost tier: $1k–3k per sensor + lens `UNVERIFIED`.

**iniVation (Tobi Delbruck's ETH spin-out).** Research focus, DAVIS sensors (240×180 DVS + APS frame). Smaller resolution, more sophisticated APS hybrid (you get *both* events and conventional frames out of the same array). Cost tier: $3k+ as research kit `UNVERIFIED`.

**Samsung / academic prototypes.** Larger arrays (640×480 to 1.28 MP), not commercially available outside research collabs.

For drone work — Prophesee Gen3/Gen4 sensors. For perception research where you want a comparison baseline with conventional imagery — DAVIS. For long-tail edge deployment (cost-sensitive) — wait for IMX636 to drop into automotive supply at $200 tier (not there yet 2026).

---

## 4 · Worked example — DVS at 6 m/s flight: signal rate vs global-shutter

Back-of-envelope (numbers `UNVERIFIED`, for engineering intuition):

```
Drone:       6 m/s forward, racing through gate course
Camera:      640×480 DVS at HFOV 90°, focal_length ~ 320 px
Scene:       textured wall 3 m ahead
```

- **Apparent motion at sensor.** At 3 m range, 6 m/s lateral parallax → angular motion ~2 rad/s → ~640 px/s across sensor.
- **Event rate per pixel.** At ~640 px/s motion across pixel, with typical scene contrast above threshold → ~200 events/s/px in textured regions; ~0 in plain regions. Assume ~10% pixels active → `0.10 × 640×480 × 200 = 6.1M events/s`. Per event ~64 bits → ~50 MB/s. Tractable on USB-3.
- **Same trajectory, global-shutter frame camera at 30 fps.** Motion 640 px/s × 33 ms exposure → 21 px motion blur per frame. Feature matching catastrophically degraded. Need 1 ms exposure → 1/1000 light → SNR collapses, or use HDR illumination.
- **At 100 fps with sub-ms exposure** the frame camera matches in temporal terms but throws 99% of bandwidth at static background and burns 10× the power.

DVS doesn't *win on resolution* (it's VGA vs 4K). It wins on **latency-to-first-event** for obstacle avoidance and on **no-motion-blur** for high-speed tracking. The 50 MB/s is allocated to the parts of the scene that *changed* — which is the parts that matter for control.

Confirms §1 → §2: DVS shines for drone racing (every photon is signal), drowns for cinematography (static frames are the product).

---

## 5 · Where DVS lives and dies

**Where it lives.**
- **High-speed obstacle avoidance** — UZH RPG drone racing demos.
- **HDR perception** — driving out of tunnels, welding-spark robotics, sun-shadow transitions.
- **Low-power always-on** — drones / wearables where static-scene zero-event keeps power < 100 mW.
- **Motion-only tasks** — gesture, vibration analysis, particle tracking, eye-tracking saccades.
- **Spiking-NN front-ends** — neuromorphic chips (Loihi, Akida) consume events natively.

**Where it dies.**
- **Static scene capture** — security camera of an empty parking lot returns nothing; intruder triggers a burst but you have no "before."
- **Color / texture** — DVS is monochrome and gives only change polarity. Hybrid DAVIS / IMX636 mitigate via APS path.
- **Low-light textureless** — if change events are below threshold or the scene has no spatial contrast, DVS is blind. No "long exposure" rescue.
- **Compute downstream is unfamiliar.** Most CV pipelines assume frames. Treating events as artificial frames (binning into a tensor every N µs) discards most of DVS's advantage.

---

## 6 · Hidden Assumptions — what DVS silently bets on

The DVS pick is stable only while these hold:

- **Scene contains motion OR illumination change.** A perfectly static, perfectly flat-lit scene returns zero events — DVS is *blind* to it. Mitigations: combine with frame APS (DAVIS) or rely on ego-motion to generate change.
- **Spatial contrast exists in the scene.** No texture → no edges → motion produces no log-intensity threshold crossings → still zero events. White wall + perfect lighting = invisible.
- **Threshold θ tuned to scene illumination.** Too tight = noise floods events; too loose = important changes missed. Per-pixel threshold drift over temperature complicates this.
- **AER bus not saturated.** Strobe lights, fast-moving textured scenes can produce >100M events/s and saturate the readout — events drop, timestamps skew. Hard to debug because the *symptom* is missing data.
- **Algorithm consumes events natively.** Binning DVS into frame tensors → re-imposes the framing assumption DVS removed → throws away the latency win. Only event-native algorithms (event-based VIO, spiking NN) extract full advantage.
- **Synchronization with other sensors.** AER timestamps are sensor-clock; aligning with IMU / frame camera needs hardware sync or post-hoc registration. Easy to get wrong.
- **Resolution sufficient for task.** VGA–HD vs frame camera 4K — DVS loses by 8× on pixel count. For fine-grained classification, you need APS frames.

---

## 7 · Comparison across embodiments + interview tip

| Embodiment | DVS suitable? | Why |
|---|---|---|
| **Drone racing** | **yes — primary case** | high speed + low latency + HDR (UZH RPG demos) |
| **Drone cinematography** | **no** | static or slow scenes; viewer wants frames; 4K matters |
| **Manipulation** | research-grade | mostly static; benefits if scene has fast disturbances |
| **Humanoid** | research | head + eye saccade tracking interesting; whole-body not yet |
| **AD perception** | **no for primary** | resolution + color + classification — frame camera wins |
| **AD perception (HDR transition)** | **maybe as supplement** | tunnel exit / oncoming-headlight; complements frames |
| **Marine** | rare | static murky water gives little change signal |
| **AR / VR eye tracking** | yes | saccade tracking 10 µs latency + low power |

Lesson: DVS earns its slot on **motion + latency + HDR**. Cinematography / classification / static-scene workloads are still global-shutter CMOS territory.

**🎙️ Interview Tip.** Asked "should our drone use an event camera?" — separate **racing / collision avoidance** (DVS plausible primary) from **cinematography / mapping** (DVS supplement at best). For drone-racing latency benchmark, point to UZH RPG papers. For Hollywood drone, DVS is the wrong tool — frames are the product.

---

## 8 · For the reader

- **Manipulation engineer** — global-shutter CMOS (RGBD) remains primary; DVS interesting if you have a fast-moving target or strobe-light environment.
- **Aerial engineer (racing)** — **yes** — Prophesee EVK4 or IMX636-based platform; latency + HDR + power profile fit drone racing precisely.
- **Aerial engineer (cinematography)** — **no** — viewer wants 4K frames; DVS provides nothing the global-shutter doesn't.
- **AD engineer** — supplement only, for HDR transitions; primary perception stays on frames.
- **Marine engineer** — skip; acoustic stack dominates.

---

## References

- Lichtsteiner et al. "A 128×128 120 dB 15 µs Latency Asynchronous Temporal Contrast Vision Sensor" IEEE JSSC 2008
- Prophesee EVK4 / IMX636 datasheets `UNVERIFIED`
- iniVation DAVIS346 spec sheet `UNVERIFIED, no DOI`
- UZH Robotics & Perception Group — drone racing with event cameras (Mueggler, Gehrig, Scaramuzza)
- Gallego et al. "Event-based Vision: A Survey" PAMI 2020
- IEC 60825-1 (laser safety — irrelevant for passive DVS, included for cross-reference to active sibling docs)

## Boundary

- `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md` — active NIR (passive DVS is opposite end of spectrum)
- `foundations/sensor-physics/tof_physics_for_embodied_ai.md` — depth sibling (event-based ToF research exists, not commercial)
- `foundations/sensor-physics/lidar_physics_905_vs_1550.md` — long-range pulsed sibling
- `foundations/sensor-physics/imu_physics_and_noise_model.md` — IMU sibling (DVS+IMU is the standard fusion stack)
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — cross-embodiment SWaP-C: when DVS earns its slot (drone racing primary)
- `embodiments/aerial/event-camera/` — per-embodiment deployment, drone-racing case study
- Event-based VIO / SLAM algorithms: `foundations/slam-vio/` (TBD) — algorithm consumes physics; this doc is physics only.

*2026-05-21. v1 first version, satisfies 14-item gate. UNVERIFIED → datasheet cites in v1.1.*

---
[← Back to sensor-physics README](./README.md)
