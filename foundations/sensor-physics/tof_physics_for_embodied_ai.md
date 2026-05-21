# Time-of-Flight Physics for Embodied AI (具身 AI 飞行时间传感器物理拆解)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — phase vs pulsed ToF / modulation wrap-around / SPAD vs APD / multipath
> **核心定位**：the wrap-around-and-multipath story vendor datasheets bury in fine print — modulation frequency is the load-bearing knob, not "depth accuracy"

**Status:** v1 — opinionated draft, written to AGENTS.md 14-item dissection template 2026-05-21. Datasheet numbers marked `UNVERIFIED` need spec-sheet cross-check.
**Wedge tier:** sensor-physics expansion (2 of 5 sibling docs)

### X-Ray opening

Every ToF vendor picks between two physical regimes — **phase-detection CW** (Kinect v2, iPhone front-cam, Microsoft Azure) and **pulsed dToF** (iPhone rear LiDAR, automotive flash LiDAR). Reading the datasheet's "range up to X m" misses the actual trade: CW gives sub-cm precision but wraps at `c / (2·f_mod)`; pulsed gives unambiguous range but timing jitter floors precision at a few cm. The vendor's modulation-frequency choice silently picks which failure mode you inherit. For sensor engineers: "ToF accuracy" is meaningless without naming the regime.

### 📍 研究全景时间线 (Research Landscape Timeline)

```
2010 ── PMD Technologies CamCube — CW-ToF reaches consumer-adjacent
2013 ── Kinect v2 (Microsoft, 850nm CW-ToF, ~30 MHz) ── living-room scale CW
2017 ── Sony IMX556 ToF sensor ── back-illuminated CW-ToF on phones
2020 ── iPhone 12 Pro rear LiDAR (Sony dToF SPAD, 940nm pulsed) ── consumer dToF
2022 ── ams/AMS-OSRAM TMF8828 multi-zone dToF ── proximity-grade SPAD modules
2023-25 ── Automotive flash LiDAR (Ouster DF, Innoviz, 1550nm InGaAs SPAD)
2024 ── iPhone front Face ID supplement (940nm CW-ToF for face-distance)
202? ── ?  next: gated SPAD imagers, FMCW per-pixel coherent ToF
```

This document sits at the CW-vs-pulsed fork — the choice that determines wrap-around behavior, multipath sensitivity, and BoM tier.

---

## 1 · ToF regimes — two physical principles, one label

📌 **Napkin Formula**: `range_unambig = c / (2 · f_mod)` for CW; `range_floor = c · σ_jitter / 2` for pulsed. Everything in §2 reads against these two equations — CW trades range for precision via `f_mod`, pulsed trades precision for range via detector jitter.

**(a) Phase-detection CW (Continuous Wave).** Modulate illuminator amplitude at `f_mod` (10–100 MHz). Per-pixel demodulator (typically 4-tap quadrature) measures phase delay `φ` of returned light → depth `d = c·φ / (4π·f_mod)`. Sub-cm precision at indoor range. **Wrap-around**: phase wraps at `2π`, so range repeats every `c/(2·f_mod)` — at 30 MHz that's 5 m, at 100 MHz only 1.5 m. Multi-frequency unwrapping (Kinect v2 uses 3 frequencies `UNVERIFIED`) extends this but doubles integration time.

**(b) Pulsed dToF (direct ToF).** Fire ~ns laser pulse, time the photon return per-pixel with a SPAD + TDC (Time-to-Digital Converter). Depth `d = c·Δt/2`. No wrap-around (each pulse independently timed). Precision floored by jitter of SPAD+TDC chain — typically 100–500 ps `UNVERIFIED` → 1.5–7.5 cm at one-pulse SNR. Histogramming N pulses recovers `1/√N`. iPhone LiDAR fires ~thousands of pulses per frame.

**(c) Detectors — SPAD vs APD.**
- **SPAD** (Single-Photon Avalanche Diode): reverse-biased *above breakdown*, single photon triggers macroscopic avalanche. Binary output, ~50 ps timing resolution `UNVERIFIED`. Dead time 10–100 ns limits pile-up at high flux. Mass-producible in CMOS (Sony IMX591 family `UNVERIFIED`).
- **APD** (Avalanche Photodiode): below-breakdown linear gain (×10–100). Analog output, demodulation-friendly for CW. Worse single-photon sensitivity, no dead-time pile-up.

CW-ToF systems historically use APD-like demodulating pixels (charge separation per phase tap). Pulsed systems use SPAD. The detector picks the regime — not the other way around.

⚡ **Eureka Moment.** The CW-vs-pulsed split is not about *range* — it's about whether your modulation frequency wraps inside your workspace. Kinect v2 living room (3 m) at 30 MHz fits in one wrap. Automotive 200 m at 100 MHz wraps 26 times — unrecoverable; you must go pulsed.

---

## 2 · CW vs pulsed comparison (vendors don't publish side-by-side)

| Property | CW phase ToF | Pulsed dToF |
|---|---|---|
| Typical illuminator | LED / VCSEL, 10–300 mW avg | VCSEL / EEL, kW peak / mW avg |
| Modulation | sinusoidal 10–100 MHz | <5 ns pulse, 10–100 kHz rep rate |
| Detector | demodulating CMOS pixel (4-tap) | SPAD + TDC per pixel |
| Wrap-around | yes, `c/(2·f_mod)` | no (per-pulse) |
| Precision (typical) | sub-cm | 1–10 cm |
| Range (typical) | 0.3–8 m | 0.5–200+ m |
| Multipath sensitivity | high (phase mixes) | moderate (first-return / histogram) |
| Ambient rejection | needs modulated illuminator >> ambient at `f_mod` | gating + BPF; SPAD dark count limits |
| Cost (sensor) | $5–50 | $20–500+ (SPAD array) |
| Power | continuous 1–10 W | bursty, avg <1 W |
| Typical use | **Kinect v2, Face ID, Azure Kinect** | **iPhone LiDAR, automotive flash LiDAR** |

Rule predicting vendor choice: if workspace fits one wrap at a tractable `f_mod` (≤30 MHz for 5 m) → CW (cheap pixel, dense depth); if range > 10 m or wrap-unwrap budget can't pay → pulsed (SPAD).

---

## 3 · Worked example — 100 MHz CW-ToF: how far before wrap-around?

Back-of-envelope (numbers `UNVERIFIED`, for engineering intuition):

```
Source:     850 nm VCSEL, 200 mW avg, sinusoidal 100 MHz amplitude modulation
Detector:   Sony-class 4-tap demod pixel, 320×240
Integration: 30 ms/frame, 30 Hz
```

- **Wrap range:** `c / (2 · f_mod) = 3e8 / 2e8 = 1.5 m`. A scene point at 2.0 m phase-aliases to 0.5 m. Whole rooms broken.
- **Drop to 30 MHz:** wrap = 5 m, but phase precision degrades ~3.3× (phase noise is fixed σ_φ; depth = `σ_φ·c/(4π·f_mod)`). 100 MHz precision ~3 mm `UNVERIFIED` → at 30 MHz ~10 mm.
- **Multi-frequency unwrap:** run 100 MHz + 30 MHz interleaved; CRT-like unwrap recovers true range up to LCM-bound while keeping 100 MHz precision. Cost: 2× integration time → halved frame rate, or doubled illuminator duty.
- **Pulsed alternative:** 500 ps jitter SPAD → 7.5 cm single-pulse precision; histogram 1000 pulses → `1/√1000 ≈ 30×` reduction → 2.5 mm @ 30 Hz, with no wrap up to (rep period · c / 2). 100 kHz rep → 1.5 km unambiguous.

Confirms §1 → §2: CW is the right pick if and only if your workspace ≤ wrap range at a frequency that hits your precision spec. Above ~10 m or where multipath dominates, pulsed wins despite higher BoM.

---

## 4 · ToF vs structured light vs active stereo (siblings)

| Method | Depth signal | Strength | Failure mode |
|---|---|---|---|
| **Structured light** | triangulation of dot pattern displacement | dense at short range, cheap | sun saturates, fails outdoors, single point of failure |
| **CW-ToF** | phase delay of modulated illuminator | dense, textureless OK, sub-cm | multipath, wrap-around, power |
| **Pulsed dToF** | direct photon round-trip timing | long range, unambig, fast | SPAD cost, sparse for low-cost arrays |
| **Active stereo** (sibling 850nm doc) | stereo correspondence + non-informative texture projector | graceful degradation, outdoor-OK | baseline-vs-range trade |

ToF's **textureless surface** advantage is what sells it for face auth and bin-picking white-on-white. Structured light needs *some* contrast across dots; ToF doesn't. ToF's curse — multipath — is what active stereo's "the world supplies the signal" approach sidesteps.

---

## 5 · Multipath — ToF's defining failure

A wall + a corner reflector both return light to the same pixel. Phase-ToF measures *the vector sum* of the two phasors → reports a fictional in-between depth. In corners, on glossy floors, against retroreflective tape — ToF lies systematically. Mitigations:

- **Multi-frequency** — different `f_mod` produce different mixing; solve jointly. Kinect v2 approach.
- **Frequency-modulated CW** (chirp) — coherent ToF separates returns by Doppler/range. Aeva FMCW LiDAR. Expensive.
- **Pulsed first-return** — only count the first photon per pulse; ignores secondary bounces. Standard automotive practice.
- **Geometric priors** — flag pixels near specular reflectors as low-confidence.

Pulsed systems suffer less because the first-return gate temporally isolates the direct path. CW systems suffer most because phase has no temporal handle once the photons hit the pixel.

---

## 6 · Hidden Assumptions — what ToF silently bets on

The "ToF gives depth" assumption is only stable while these hold. Watch this list when something breaks:

- **Modulation rate >> ambient flicker rate.** Sun is DC; 100 MHz modulation rejects it as common-mode. But **fluorescent / PWM-LED ambient** at 100–1000 Hz can beat against `f_mod` and inject ghost depth `UNVERIFIED`.
- **Scene is mostly single-bounce.** Multipath fraction <10% — corners, glossy floors, retroreflective tape break this.
- **No competing ToF source.** Two phones doing dToF in the same room rarely sync; SPAD dark counts climb, histograms muddy. Multi-sensor coordination protocol assumed absent.
- **SPAD pile-up < detector rate.** High-flux scenes (sun on chrome) saturate SPAD dead-time, biasing histograms early. Pulsed assumes photon rate << 1/dead-time.
- **Illuminator power within IEC 60825-1 Class 1** at use distance. Pulsed kW peak only works because pulse <5 ns and duty <0.1% — see sibling `active_nir_850nm_for_embodied_ai.md` §3.
- **Pixel charge well not saturated** by ambient. Outdoors, ambient can fill the integration well before `f_mod` even resolves; need shorter integration or narrower BPF.

---

## 7 · ToF vs active stereo — when to pick which

| Question | Pick |
|---|---|
| Textureless surfaces (white wall, sheet metal)? | **ToF** |
| Outdoor / direct-sun? | **active stereo** (graceful degradation) |
| Range >5 m at consumer BOM? | **pulsed ToF** |
| Range <2 m, dense, cheap? | CW-ToF |
| Tolerate single-point-of-failure? | ToF (any) |
| Want soft floor (projector fails → passive stereo)? | active stereo |
| Multi-robot coexistence? | active stereo (less inter-sensor interference) |

⚡ Rule: ToF gives you depth where active stereo can't (textureless), at the cost of multipath and modulation-aware integration. Active stereo gives you outdoor + graceful degradation, at the cost of textured surface dependence.

**🎙️ Interview Tip.** Asked "ToF or active stereo for our robot?" — first question back is *"workspace range, ambient class, and surface texture?"* Below 2 m textureless indoor → ToF. Outdoor / dust / variable surface → active stereo. Above 10 m → pulsed dToF or LiDAR; CW is out.

---

## 8 · For the reader

- **Manipulation** — short range, textureless parts → CW-ToF where workspace ≤ 1.5 m and ambient is controlled; otherwise active stereo (850 nm).
- **Drone** — pulsed dToF altimeter <5 m (TMF8828-class proximity), then leave depth to passive stereo + VIO.
- **Headset / AR** — CW-ToF for hand-tracking workspace (0.3–1 m); textureless skin makes it the right pick.
- **Automotive long-range** — pulsed dToF SPAD, 1550 nm to clear Class 1 at kW peak (see sibling LiDAR doc).

---

## References

- IEC 60825-1 — laser product safety classification
- Sony IMX591 / IMX556 ToF datasheets, `UNVERIFIED`
- ams-OSRAM TMF8828 datasheet, `UNVERIFIED`
- Microsoft Azure Kinect DK technical specs, `UNVERIFIED`
- Apple iPhone Pro LiDAR teardowns (iFixit / TechInsights), `UNVERIFIED, no DOI`
- Empirical: maintainer's sensor-stack work on Autel platforms

## Boundary

- `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md` — band selection / Class 1 (sibling)
- `foundations/sensor-physics/lidar_physics_905_vs_1550.md` — long-range pulsed regime (sibling)
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — cross-embodiment SWaP-C application
- `embodiments/aerial/sensor-stack/` — drone-specific deployment (CW-ToF rare; pulsed altimeter common)
- Per-embodiment integration + calibration live under `embodiments/<x>/sensor-stack/`; this doc covers physics only.

*2026-05-21. v1 first version, satisfies 14-item gate. UNVERIFIED → datasheet cites in v1.1.*

---
[← Back to sensor-physics README](./README.md)
