# Active NIR (850 nm) for Embodied AI

**Status:** v1 — opinionated draft. Spec numbers marked `UNVERIFIED` need datasheet check.
**Wedge tier:** W1 (1 of 5 launch docs)
**TL;DR:** Every embodied-AI vendor shipping active sensing converges on 850 nm — the unique point where silicon QE, the solar irradiance dip, and Class 1 eye-safety all clear at a price the BOM absorbs. Surveys treat the illuminator as a given; the interesting story is upstream. Why 850 — and what flips at 940 or 1550 — is the prerequisite to honest sensor selection.

---

## 1 · Spectral physics primer

Three curves govern the choice; reading one in isolation is how vendors land at 940 nm "because Apple" and then can't hit range.

**(a) Silicon QE.** FSI CMOS peaks ~550 nm and falls off a cliff past 1000 nm — photon energy drops below silicon's indirect-bandgap absorption. Sony IMX / OmniVision datasheets `UNVERIFIED`: ~35–50% QE at 850 nm, ~15–25% at 940 nm, zero past 1100 nm. BSI gains ~1.5×; NIR-enhanced (Sony STARVIS-2) pushes 850 nm toward 60% `UNVERIFIED`. Past 1100 nm you leave silicon for InGaAs — 50–100× sensor cost.

**(b) Solar irradiance (AM1.5).** Atmosphere chews dips at 760 nm (O₂), 940 nm (H₂O), 1150/1380 nm (H₂O), 1880 nm (H₂O). 850 nm is a *shallow* dip — ambient ~30% below broad NIR baseline `UNVERIFIED`. 940 nm is a *deeper* trough; long-exposure consumer products favor it.

**(c) Eye safety — IEC 60825-1.** MPE for collimated NIR rises sharply past 700 nm — cornea+lens absorb less and the blink reflex stops triggering, so the full dose lands invisibly. At 850 nm, 100 ms exposure, Class 1 caps time-averaged irradiance at ~1 mW/cm² order `UNVERIFIED`; 940 nm is ~2× looser; 1550 nm jumps ~1000× because cornea+lens absorb almost everything. This is why 1550 nm LiDAR can punch kilowatts.

Optimization: maximize (Si QE × ambient rejection × safety) / cost. 850 nm wins pulsed <10 ms. 940 nm wins continuous-on. 1550 nm wins long-range automotive where InGaAs cost is acceptable.

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

The 850-vs-940 line is the only contested one in mass-market embodied AI. The rule that predicts vendor choice: pulse <10 ms and only occasionally on a user → 850 nm, recover QE. Continuously illuminating a user's eyes (Face ID auth; Vision Pro whenever worn) → 940 nm, pay the QE tax to stay inside cumulative dose. **Apple picked 940 nm not for performance but because Face ID is on-skin and Vision Pro is on-eye continuous — the safety budget compounds.**

---

## 3 · Hardware archetypes in the wild

**Structured light.** VCSEL projects a pseudo-random dot pattern; one camera reads deformation. Kinect v1 (PrimeSense, 850 nm), Face ID (940 nm, ~30k dots). Dense depth, no temporal aliasing. Outdoors dies fast, range capped <4 m at realistic projector power.

**ToF.** Modulated illuminator + demodulating pixel measures phase delay. Kinect v2 (850 nm CW), iPhone LiDAR (940 nm pulsed SPAD), automotive flash LiDAR (1550 nm InGaAs SPAD, kW peak). Works on textureless surfaces. Multipath, modulation wraparound, power-hungry.

**Active stereo.** Two cameras + a *non-informative* IR speckle projector that creates texture for stereo matching. Intel RealSense D-series (D435/D455 — 850 nm); Skydio's obstacle sensing is in this family. Degrades gracefully — projector dies, you still have passive stereo. Standard baseline-vs-range trade.

The graceful-degradation property is why active stereo dominates robotics. Structured light and ToF have *single points of failure*; active stereo has a soft floor.

---

## 4 · Embedded BPF — quietly the most important part

Every production active sensor has a narrow BPF glued in front. A 10 nm FWHM BPF at 850 nm rejects ~95% of ambient solar power `UNVERIFIED` — what makes outdoor active sensing tractable.

- **20 nm FWHM:** $1–2, ~85% rejection. Forgiving of VCSEL drift.
- **10 nm FWHM:** $3–6, ~95%. Standard for outdoor robotics.
- **5 nm FWHM:** $10+ and you fight VCSEL thermal drift — see §5.

The BPF must be angle-of-incidence stable; rays into a wide-FOV lens hit up to 30° and cheap BPFs blue-shift at angle. High-end modules use telecentric optics or angle-tuned stacks.

---

## 5 · Failure modes you only learn the hard way

**Cross-talk between two 850 nm projectors.** Two RealSense devices facing each other inject each other's patterns into the wrong correspondence search. Mitigations: time-domain multiplexing, spatial pattern uniqueness, or turn one off. Multi-robot needs a coordination protocol — empirical from Autel work.

**Sun reflection off chrome / wet asphalt / bumpers.** A specular reflector returns a sun-tinted blob that saturates regardless of BPF — the in-band component of full sun on a mirror still exceeds the projector. Only HDR pixels (Sony IMX490 lineage `UNVERIFIED`) and dynamic exposure help.

**VCSEL center-wavelength thermal drift.** ~0.06 nm/°C `UNVERIFIED`. Over 60°C that's ~4 nm. With a 5 nm BPF you lose half your photons at hot edge. Keep BPF ≥10 nm FWHM, thermally regulate the VCSEL, or accept duty-cycle penalty.

**Projector-dot blooming.** Cheap rolling-shutter sensors smear bright returns into vertical ghost lines. Global-shutter or BSI-anti-blooming fixes it.

---

## 6 · Embodiment-specific picks

**Manipulation (tabletop).** Active stereo 850 nm wins. Workspace <2 m, controlled lighting, BOM tolerates $200. RealSense D405/D435; Photoneo and Zivid for high-precision. ToF is rare — multipath off the gripper kills accuracy.

**Drones.** Active 850 nm is usually *skipped*. 250 g power budget is tight, projector draws 1–3 W continuous, outdoor sun overwhelms it. Skydio is the exception — indoor and dusk matter to their customers. DJI Mini, Autel Nano use passive stereo + VIO. See `embodiments/aerial/sensor-stack/`.

**AR/VR.** Vision Pro uses 940 nm for eye-tracking because illuminators are continuously on while worn. World-facing depth is a separate stack (ToF + passive). Lesson: in headsets *exposure duration* dominates; in robots *ambient rejection* dominates.

**Automotive.** 1550 nm dominates new long-range LiDAR for the eye-safety budget alone — kW-peak pulse is Class 1 at the bumper where 905 nm is Class 3R. Cost falls as InGaAs SPAD matures.

---

## 7 · For the reader

- **Manipulation** — active stereo 850 nm; only knob is BPF FWHM vs VCSEL thermal envelope.
- **Drone** — passive stereo + VIO by default. Active 850 nm only for indoor/dusk; 1–3 W tax.
- **Headset / on-face** — 940 nm. Don't argue with the dose budget.
- **AD / long-range** — 1550 nm if BOM tolerates InGaAs; 905 nm for short-range cost tier.

---

## References

- IEC 60825-1 — laser product safety classification.
- Hamamatsu / Sony / OmniVision CMOS QE datasheets.
- Intel RealSense D400 whitepapers; Lumentum / II-VI VCSEL primers.
- Empirical: maintainer's Autel sensor-stack work.

## Cross-refs / boundary

- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — power/cost/range trades
- `embodiments/aerial/sensor-stack/` — why drones skip 850 nm
- `deployment/hardware-selection/` — BOM reasoning

Spectrum + safety + cost only. Module integration and calibration live under `embodiments/<x>/sensor-stack/`.

*2026-05-21. UNVERIFIED → datasheet cites in v1.1.*
