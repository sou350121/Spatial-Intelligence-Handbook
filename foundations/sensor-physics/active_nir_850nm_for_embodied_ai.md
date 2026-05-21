# Active NIR (850 nm) for Embodied AI (具身 AI 主动近红外 850nm 选型)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — band selection / laser safety / cost
> **核心定位**：the upstream story vendor surveys treat as "a given" — Si QE × solar dip × Class 1 safety × cost is the load-bearing optimization

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item dissection template 2026-05-21. Spec numbers marked `UNVERIFIED` still need datasheet check.
**Wedge tier:** W1 (1 of 5 launch docs)
### X-Ray opening

Every embodied-AI vendor shipping active sensing converges on 850 nm — the unique point where silicon QE, the solar dip, and IEC 60825-1 Class 1 eye-safety all clear at a price the BOM absorbs. For sensor engineers: "940 nm because Apple" is a category error — Apple optimizes for *continuous* eye exposure, robotics optimizes for *ambient rejection*. Reading band choice as a performance ranking misses what's actually being traded.

### 📍 研究全景时间线 (Research Landscape Timeline)

```
2010 ── Kinect v1 (PrimeSense, 850 nm structured light) ── NIR active goes consumer
2013 ── Kinect v2 (850 nm CW ToF)
2017 ── iPhone X Face ID (940 nm) ── on-skin continuous → band shift
2018 ── Intel RealSense D-series (850 nm active stereo) ── robotics outdoor
2023-25 ─ Automotive 1550 nm SPAD wave (Luminar, Innoviz, Hesai-FT) ── InGaAs kW-pulse
2024 ── Apple Vision Pro (940 nm eye-tracking) ── continuous-on re-confirms 940
202? ── ?  next candidates: 1380 nm SWIR for AD short-range, 905→940 SPAD migration
```

This wedge lives at the 850-vs-940 fork — the only contested point in mass-market embodied AI.

---

## 1 · Spectral physics primer (Overview)

Three curves govern the choice; reading one alone is how vendors land at 940 nm "because Apple" and can't hit range.

📌 **Napkin Formula**: `band_value = (Si_QE × ambient_rejection × safety_budget) / cost`. Read every cell in §2 against this — 850 nm wins for pulsed robotics; 940 nm for continuous on-face; 1550 nm only when BOM accepts InGaAs.

**(a) Silicon QE.** FSI CMOS peaks ~550 nm, falls off past 1000 nm (photon energy < Si indirect bandgap). Datasheets `UNVERIFIED`: ~35–50% at 850 nm, ~15–25% at 940 nm, zero past 1100 nm. BSI gains ~1.5×; NIR-enhanced (STARVIS-2) pushes 850 nm toward 60% `UNVERIFIED`. Past 1100 nm = InGaAs = 50–100× cost.

**(b) Solar irradiance (AM1.5).** Atmosphere chews dips at 760 nm (O₂), 940 nm (H₂O), 1380 nm (H₂O). 850 nm is *shallow* (~30% below NIR baseline `UNVERIFIED`); 940 nm is a *deeper* trough — long-exposure consumer products favor it.

**(c) Eye safety — IEC 60825-1.** MPE rises sharply past 700 nm; cornea+lens transmit and blink reflex stops triggering. At 850 nm, 100 ms exposure, Class 1 caps ~1 mW/cm² time-averaged `UNVERIFIED`; 940 nm ~2× looser; 1550 nm ~1000× looser (cornea+lens absorb almost everything) — that's why 1550 nm LiDAR can punch kilowatts.

⚡ **Eureka Moment.** The 850-vs-940 vendor split is *exposure-duration*, not performance — pulse <10 ms occasional viewer = 850 nm, continuous-on viewer = 940 nm. Every other axis is downstream of that one choice.

---

## 2 · Band comparison (vendors don't publish this side-by-side)

| Band | Si QE | Ambient rejection | Eye-safety | Cost | Typical use |
|---|---|---|---|---|---|
| **760 nm** | ~55% | good (O₂ dip) | tightest NIR | cheap | rare — visible red leak |
| **808 nm** | ~50% | poor | tight | cheap | laser pumping, not sensing |
| **850 nm** | ~40–50% | moderate | workable, pulsed | cheap | **RealSense, Kinect, Skydio** |
| **940 nm** | ~20% | strong (H₂O dip) | ~2× looser | cheap | **Face ID, Vision Pro** |
| **1380 nm** | ~0% Si | strongest dip | very loose | InGaAs | atmospheric, not depth |
| **1550 nm** | 0% Si | strong | ~1000× looser | InGaAs 50–100× | **automotive flash LiDAR** |

Rule predicting vendor choice: pulse <10 ms occasionally-on-user → 850 nm (recover QE); continuously on user's eyes → 940 nm (pay QE tax for cumulative dose). **Apple picked 940 nm because the safety budget compounds over continuous wear, not for performance.**

---

## 3 · Worked example — 100 mW peak, 850 nm, 10 ms pulse: Class 1 at 30 cm? at 5 cm?

Back-of-envelope (numbers `UNVERIFIED`, for engineering intuition):

```
Source:  100 mW peak, 10 ms pulse, 1 Hz repetition (~1% duty)
Beam:    20° × 20° flood at 850 nm (VCSEL + diffuser)
Aperture stop: 7 mm (IEC pupil model)
```

- **30 cm:** flood spreads to ~10×10 cm² → ~1 mW/cm² peak, 1% duty → ~10 µW/cm² time-avg. Class 1 limit ~1 mW/cm² order `UNVERIFIED`. **Margin ~100×, Class 1.**
- **5 cm (user pokes nose in):** projector aperture fills the 7 mm pupil → ~100 mW/cm² instantaneous, ~1 mW/cm² time-avg. **Hits the Class 1 edge.**
- **940 nm** buys ~2× looser MPE → 5 cm ships with margin. **1550 nm** buys ~1000× → 100 W peak still Class 1 (but InGaAs at 50–100× cost).

Confirms §1(c) → §2: 30 cm robotics is Class-1-easy at 850 nm; on-face continuous is not, and that's exactly where vendors shift to 940 nm.

---

## 4 · Hardware archetypes in the wild

**Structured light.** VCSEL projects a pseudo-random dot pattern; one camera reads deformation. Kinect v1 (PrimeSense, 850 nm), Face ID (940 nm, ~30k dots). Dense depth, no temporal aliasing. Outdoors dies fast, range capped <4 m at realistic projector power.

**ToF.** Modulated illuminator + demodulating pixel measures phase delay. Kinect v2 (850 nm CW), iPhone LiDAR (940 nm pulsed SPAD), automotive flash LiDAR (1550 nm InGaAs SPAD, kW peak). Works on textureless surfaces. Multipath, modulation wraparound, power-hungry.

**Active stereo.** Two cameras + a *non-informative* IR speckle projector that creates texture for stereo matching. Intel RealSense D-series (D435/D455 — 850 nm); Skydio's obstacle sensing is in this family. Degrades gracefully — projector dies, you still have passive stereo. Standard baseline-vs-range trade.

The graceful-degradation property is why active stereo dominates robotics. Structured light and ToF have *single points of failure*; active stereo has a soft floor.

---

## 5 · Embedded BPF — quietly the most important part

Every production active sensor has a narrow BPF glued in front. A 10 nm FWHM BPF at 850 nm rejects ~95% of ambient solar power `UNVERIFIED` — what makes outdoor active sensing tractable.

- **20 nm FWHM:** $1–2, ~85% rejection. Forgiving of VCSEL drift.
- **10 nm FWHM:** $3–6, ~95%. Standard for outdoor robotics.
- **5 nm FWHM:** $10+ and you fight VCSEL thermal drift — see §6.

The BPF must be angle-of-incidence stable; rays into a wide-FOV lens hit up to 30° and cheap BPFs blue-shift at angle. High-end modules use telecentric optics or angle-tuned stacks.

---

## 6 · Failure modes you only learn the hard way

**Cross-talk between two 850 nm projectors.** Two RealSense devices facing each other inject each other's patterns into the wrong correspondence search. Mitigations: time-domain multiplexing, spatial pattern uniqueness, or turn one off. Multi-robot needs a coordination protocol — empirical from Autel work.

**Sun reflection off chrome / wet asphalt / bumpers.** A specular reflector returns a sun-tinted blob that saturates regardless of BPF — the in-band component of full sun on a mirror still exceeds the projector. Only HDR pixels (Sony IMX490 lineage `UNVERIFIED`) and dynamic exposure help.

**VCSEL center-wavelength thermal drift.** ~0.06 nm/°C `UNVERIFIED`. Over 60°C that's ~4 nm. With a 5 nm BPF you lose half your photons at hot edge. Keep BPF ≥10 nm FWHM, thermally regulate the VCSEL, or accept duty-cycle penalty.

**Projector-dot blooming.** Cheap rolling-shutter sensors smear bright returns into vertical ghost lines. Global-shutter or BSI-anti-blooming fixes it.

### Hidden Assumptions — what the 850 nm pick silently bets on

The 850 nm convergence is only stable while these all hold. Watch this list when something breaks:

- **Si-sensor availability.** Commodity CMOS with ≥35% QE at 850 nm stays in production. Supply shock pushes BOM toward InGaAs.
- **BPF angle stability.** Wide-FOV lenses (≤60° HFOV) with BPFs that don't blue-shift > a few nm at 30° AOI. Fisheye breaks this.
- **VCSEL thermal envelope.** Housing keeps emitter <60°C; outdoor sun-baked this fails and BPF / VCSEL drift de-align.
- **Multi-robot non-coordination is rare.** No 5 RealSense robots in one room; once false, cross-talk dominates.
- **Solar baseline.** AM1.5 outdoor; high-altitude or snow-field albedo can double ambient.
- **Optical components in supply.** Narrow BPFs + 850 nm VCSELs stay commodity; supply shock migrates products to 808 nm or 940 nm.

---

## 7 · Comparison across embodiments + interview tip

| Embodiment | Band pick | Why this band (one driver) | Why not the others |
|---|---|---|---|
| **Manipulation (tabletop)** | 850 nm active stereo | <2 m workspace, BOM tolerates projector, indoor ambient | 940 nm wastes QE; 1550 nm BOM impossible |
| **Drone** | usually passive (no active) | 1–3 W projector tax kills 250 g power budget | 850 nm only justified indoor / dusk (Skydio) |
| **AR / VR headset** | 940 nm eye-tracking | continuous-on dose budget compounds | 850 nm Class 1 margin too tight at 5 cm |
| **Phone face auth** | 940 nm structured light | on-skin continuous; <30 cm range | 850 nm needs lower power → fewer dots |
| **Automotive long-range** | 1550 nm SPAD | kW-peak still Class 1; >200 m range | 905 nm Class 3R at bumper, 850 nm range-limited |

Lesson: in headsets *exposure duration* dominates; in robots *ambient rejection* dominates.

**🎙️ Interview Tip.** Asked "why not 1550 nm for everything"? — 1550 nm needs InGaAs (50–100× cost); only the kW-pulse automotive use case can pay for it.

---

## 8 · For the reader

- **Manipulation** — active stereo 850 nm; knob is BPF FWHM vs VCSEL thermal envelope.
- **Drone** — passive stereo + VIO. Active 850 nm only for indoor/dusk; 1–3 W tax.
- **Headset / on-face** — 940 nm. Don't argue with the dose budget.
- **AD / long-range** — 1550 nm if BOM tolerates InGaAs; 905 nm for short-range cost tier.

---

## References

- IEC 60825-1 — laser product safety classification
- Hamamatsu / Sony / OmniVision CMOS QE datasheets; Lumentum / II-VI VCSEL primers
- Intel RealSense D400 whitepapers
- Empirical: maintainer's Autel sensor-stack work

## Boundary

- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — power/cost/range trades
- `embodiments/aerial/sensor-stack/` — why drones skip 850 nm
- `deployment/hardware-selection/` — BOM reasoning
- Module integration + calibration live under `embodiments/<x>/sensor-stack/`

*2026-05-21. v1.1 backfill. UNVERIFIED → datasheet cites in v1.2.*

---
[← Back to sensor-physics README](./README.md)
