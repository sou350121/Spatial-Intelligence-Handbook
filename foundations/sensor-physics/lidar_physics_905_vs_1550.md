# LiDAR Physics: 905 nm vs 1550 nm (LiDAR 物理 — 905nm 与 1550nm 路线之争)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — Si SPAD vs InGaAs SPAD / eye safety / mechanical vs solid-state / FMCW
> **核心定位**：the eye-safety arithmetic vendor pitches gloss over — 1550 nm doesn't beat 905 nm on physics, it beats it on the IEC 60825-1 MPE ceiling by ~1000×, which is the whole story

**Status:** v1 — opinionated draft, written to AGENTS.md 14-item dissection template 2026-05-21. Datasheet numbers marked `UNVERIFIED` need spec-sheet cross-check.
**Wedge tier:** sensor-physics expansion (3 of 5 sibling docs)

### X-Ray opening

The 905-vs-1550 LiDAR split is decided by one number: the IEC 60825-1 Class 1 Maximum Permissible Exposure (MPE) at the laser wavelength. At 905 nm, the cornea + lens *transmit* the beam onto the retina → MPE caps peak power to single-digit mW. At 1550 nm, the cornea + lens *absorb* nearly all the energy before it reaches the retina → MPE jumps ~1000× → kilowatt peak pulses become Class 1. For sensor engineers: this is why Luminar / Aeva / Hesai-FT pay the InGaAs cost premium — they're buying eye-safety headroom, not better photons.

### 📍 研究全景时间线 (Research Landscape Timeline)

```
2007 ── Velodyne HDL-64 (905nm, mechanical) ── KITTI era, $80k/13kg
2014 ── Quanergy / Ouster (905nm Si SPAD) ── solid-state era begins
2017 ── Luminar founded (1550nm InGaAs SPAD, kW peak) ── eye-safety arbitrage
2019 ── Aeva announces FMCW LiDAR (1550nm coherent detection)
2020 ── Hesai Pandar128 (905nm, automotive validation)
2022 ── Innoviz One (905nm MEMS-mirror solid-state, kW-equivalent via duty)
2023 ── Hesai AT128 / AT512 (905nm, half-solid-state, $1-4k tier)
2024 ── Aeva Atlas (FMCW production) / Luminar Halo
2025 ── Livox Mid-360 (905nm, 250g) ── enters sub-3kg drone tier
202? ── ?  next: silicon-photonics OPA (no moving parts), $500 1550nm
```

This document sits at the 905 nm Si / 1550 nm InGaAs fork — the only contested physics question in mass-market AD LiDAR.

---

## 1 · Wavelength physics primer

📌 **Napkin Formula**: `max_class1_peak ≈ MPE(λ) × eye_pupil_area / pulse_duration`. Everything in §2 reads against this — 905 nm hits MPE at ~5 mW peak; 1550 nm hits it at ~5 W average / kW peak. That's the whole route.

**(a) Detector physics.**
- **905 nm + Si SPAD.** Silicon bandgap 1.12 eV — 905 nm photon (1.37 eV) is detectable. Si SPAD QE ~30% at 905 nm `UNVERIFIED`. Mass-produced CMOS process; arrays of 100k+ pixels at automotive cost. Hesai / Innoviz / Ouster route.
- **1550 nm + InGaAs SPAD.** Silicon transparent past ~1100 nm. Need InGaAs (In₀.₅₃Ga₀.₄₇As, bandgap 0.74 eV). Hybrid CMOS+InGaAs ROIC. QE ~20–30% `UNVERIFIED`. Per-pixel cost 50–100× Si SPAD. Luminar / Aeva / Hesai-FT route.

**(b) Eye safety — IEC 60825-1 MPE.** Eye absorption at the corneal surface determines retinal hazard:
- **905 nm:** cornea + lens *transmit* ~70% to retina; 1.37 eV photons photochemically damage retina. MPE for 100 ns pulse: ~`UNVERIFIED` 1 µJ/cm². Continuous: ~1 mW/cm².
- **1550 nm:** water in cornea (~3 mm thick) and lens absorbs >99% of 1550 nm before retina. Photon energy (0.80 eV) too low for photochemical damage even if it got through. MPE jumps ~1000× — kW peak pulses become Class 1.

This is *the* arbitrage. Photon-for-photon, 1550 nm is a worse choice (InGaAs more expensive, somewhat worse QE in cheap modules); MPE-for-MPE, it wins by 1000×.

**(c) Atmospheric / weather.**
- **Fog / rain / snow** — Mie scattering dominates at both wavelengths; 1550 nm slightly better penetration in dense fog `UNVERIFIED` but not the 1000× headroom of MPE. *Most* of 1550 nm's all-weather marketing is actually about peak-power headroom, not differential atmospheric loss.
- **Sun ambient** — solar irradiance at 1550 nm is in an H₂O absorption dip → ~3–5× lower ambient than 905 nm `UNVERIFIED`. Modest help, not the load-bearing factor.

⚡ **Eureka Moment.** The 905-vs-1550 choice is the eye-safety MPE ceiling, *not* better photons or better weather. Every other axis is downstream of the 1000× MPE step. Luminar's pitch "see further in rain" is half-true; the real story is "we can punch kilowatts you can't."

---

## 2 · 905 nm vs 1550 nm comparison

| Property | 905 nm Si SPAD | 1550 nm InGaAs SPAD |
|---|---|---|
| Detector cost / pixel | ~$0.01–0.10 (CMOS) | ~$1–10 (hybrid InGaAs) |
| QE at λ | ~30% `UNVERIFIED` | ~20–30% `UNVERIFIED` |
| Class 1 peak (10 ns pulse) | ~5 mW `UNVERIFIED` | ~5 W (~1000×) |
| Class 1 average | ~1 mW/cm² | ~100 mW/cm² + |
| Range (Class 1, automotive) | 100–200 m | 250–500+ m |
| Solar ambient at λ | baseline | ~3–5× lower `UNVERIFIED` |
| Fog penetration | baseline | marginally better |
| BoM tier (full sensor) | $500–4k | $5k–80k |
| Mass-production maturity | very high | growing |
| Typical vendors | Velodyne, Ouster, Hesai, Innoviz, Livox | Luminar, Aeva, Hesai-FT |

Rule predicting vendor choice: if range target ≤200 m and BoM ceiling ≤$4k → 905 nm; if range target >250 m or platform tolerates premium BoM → 1550 nm.

---

## 3 · Mechanical vs solid-state vs FMCW (architectures)

**(a) Mechanical spinning.** Velodyne HDL/VLP, Hesai Pandar64. 64–128 individual laser+detector pairs on a rotating gimbal, 5–20 Hz. Pros: mature, 360° native, well-understood. Cons: mechanical wear, ~500–13000 g, integration ugly. *905 nm dominant* — InGaAs price multiplied by N=64 channels is prohibitive.

**(b) Solid-state — MEMS mirror.** Innoviz One, Hesai AT128/AT512. One (or few) laser, beam-steered by ~5×5 mm MEMS mirror. Pros: no macroscopic moving parts, automotive-grade. Cons: limited FOV (typically 60–120°), MEMS reliability under shock.

**(c) Solid-state — flash.** Ouster DF, Continental HFL110. No scanning; illuminate the whole scene at once, 2D SPAD array reads timing per pixel. Pros: no scanning artifacts (rolling-shutter on dynamic scenes vanishes), simple optics. Cons: optical power budget — flashing 200 m × 60° wide is energy-intensive → 1550 nm gets used here.

**(d) Solid-state — OPA (optical phased array).** Quanergy attempted, silicon-photonics research today. No moving parts, electronic beam steering. Pros: chip-scale potential. Cons: still maturity-gated.

**(e) FMCW (Frequency-Modulated Continuous Wave).** Aeva, SiLC, Mobileye Chauffeur LiDAR. Coherent detection: emit chirped CW, mix return with local oscillator, beat frequency encodes range *and* Doppler velocity per pixel. Pros: per-pixel velocity (huge for prediction), interference rejection (only matches own chirp), eye-safety friendly. Cons: complex optics, expensive lasers (1550 nm tunable). *1550 nm dominant* — coherent detection needs narrow linewidth + InGaAs detectors.

Most pulsed LiDARs (905 or 1550) are *ToF* — distance only. FMCW is *coherent* — distance + velocity, fundamentally different.

---

## 4 · Worked example — 905 nm vs 1550 nm at 200 m SNR

Back-of-envelope (numbers `UNVERIFIED`, for engineering intuition):

```
Target:     10% diffuse Lambertian reflector, 200 m
Receiver:   25 mm aperture, 10 nm BPF
Ambient:    AM1.5 daylight (1 kW/m² broadband)
Pulse:      10 ns (limited by Class 1 peak)
```

- **905 nm path.** Class 1 cap → 5 mW peak → 0.05 nJ/pulse. Returned photons per pulse at 200 m: `0.05 nJ × (10% × π·(0.025/2)² / (4π·200²)) × QE / hν` ≈ ~5 photons `UNVERIFIED`. SPAD dark count ~10 cps `UNVERIFIED`, BPF reduces ambient to ~1k cps. Need histogram ~100 pulses → 30 Hz frame at 3 kHz rep rate. Pixel cost low, system cost moderate.
- **1550 nm path.** Class 1 cap → 5 W peak (1000×) → 50 nJ/pulse. Returned photons → ~5000 photons/pulse `UNVERIFIED`. Single-pulse SNR at 200 m: 100× better than 905 nm. Net: hit 250–500 m at same frame rate, or hit 200 m at 30 Hz with 1 pulse/pixel and no histogramming → simpler timing, lower per-pixel cost amortized.

The 1000× MPE step isn't a marginal gain — it's a fundamentally different signal regime. At 200 m, 905 nm survives via histogramming; 1550 nm doesn't need to. This is why Luminar markets "single-pulse confidence."

Confirms §1 → §2: 905 nm is range-limited by Class 1, not by physics. 1550 nm spends BoM to lift the ceiling.

---

## 5 · Hardware archetypes in the wild

**Velodyne / Ouster lineage.** 905 nm Si SPAD, mechanical or solid-state. Range 100–200 m typical, $1k–10k tier. Workhorse of L4 development fleets; everywhere in research.

**Hesai AT128 / AT512.** 905 nm MEMS-solid-state. ~$1–4k. Half-solid-state era; range 200 m at ≥10% reflectivity `UNVERIFIED`. Dominant in Chinese AD passenger cars 2024-26.

**Luminar Iris / Halo.** 1550 nm InGaAs SPAD, pulsed. $1k+ target, $5k+ today. Volvo EX90 lineage. Pitched at 250 m highway.

**Aeva Atlas.** 1550 nm FMCW. Velocity per pixel. Mobileye Chauffeur partnership. Higher BoM, premium tier.

**Innoviz One / Two.** 905 nm MEMS. Audi A8 era → Volkswagen production. Range 200 m, BMW-ID 905 nm Si SPAD route.

**Livox Mid-360.** 905 nm, ~$1k retail, 265 g. Brings LiDAR into the sub-3 kg drone tier (see `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` §7).

---

## 6 · Hidden Assumptions — what each route silently bets on

The 905-vs-1550 picks are stable only while these hold:

- **IEC 60825-1 stays Class 1.** Regulatory tightening (e.g., new pediatric eye-safety amendment) could erase the 1000× headroom; both routes recalculate.
- **InGaAs supply.** 1550 nm requires InGaAs; supply shock (telecom upcycle, geopolitical) lengthens lead times. 905 nm tied to CMOS supply (much deeper).
- **Class 3R/3B not acceptable.** Industrial LiDAR (warehouse, mining) sometimes ships Class 3R — there 905 nm gets kW-equivalent via duty cycling, no need for 1550 nm. Passenger cars require Class 1 at the bumper.
- **Sun stays AM1.5.** Snow albedo, high-altitude UV, equatorial midday all push ambient up — 905 nm in-band ambient can saturate cheap SPADs.
- **Fog / rain numbers are population-tail, not median.** Heavy fog defeats both; 1550 nm's "all-weather" advantage is marketing tail-end.
- **No competing in-band sources.** Multiple 905 nm LiDARs on a busy highway interfere; coded pulse sequences mitigate but don't eliminate. FMCW (1550) sidesteps via coherent detection.

---

## 7 · Comparison across embodiments + interview tip

| Embodiment | LiDAR pick (if any) | Why |
|---|---|---|
| **AD passenger car L2+** | 905 nm MEMS (Hesai AT128 / Innoviz) | $1–4k BoM ceiling; 200 m enough at highway |
| **AD passenger car L3+** | 1550 nm (Luminar Iris / Aeva) | 250 m + single-pulse confidence justifies premium |
| **Robotaxi L4** | 905 nm mechanical (Velodyne) historically; mixing 1550 in fleet | redundancy via diverse sensors; mature stack |
| **Drone (≥3 kg)** | 905 nm solid-state (Livox Mid-360) | 250 g / 10 W fits payload; range 100 m enough |
| **AGV / mining** | 905 nm Class 3R short range | indoor / fenced → Class 1 not mandatory |
| **Manipulation** | none | workspace 1 m³; LiDAR offers no resolution advantage (see crossing/sensor-stack-matrix) |

Lesson: in **L3+ passenger AD**, 1550 nm wins on the MPE ceiling. Everywhere else, 905 nm's BoM win is decisive.

**🎙️ Interview Tip.** Asked "why does Luminar use 1550 nm?" — say **eye-safety MPE 1000× headroom enables kW peak pulses, enabling 250 m at Class 1.** Anyone answering "better weather" or "longer wavelength = longer range" has read marketing, not physics.

---

## 8 · For the reader

- **AD engineer** — 905 nm for ≤200 m / BoM-bounded; 1550 nm only when 250 m+ is contractual. FMCW only when per-pixel velocity is load-bearing for prediction.
- **Aerial engineer** — Livox Mid-360 class 905 nm; 1550 nm not in drone tier yet.
- **Manipulation engineer** — skip LiDAR entirely; this fork doesn't apply to your workspace.
- **Marine engineer** — neither wavelength survives >1 m of water; ignore LiDAR, use multibeam sonar.

---

## References

- IEC 60825-1 — laser product safety classification
- Velodyne HDL/VLP, Hesai AT128/AT512, Innoviz One/Two product specs `UNVERIFIED`
- Luminar Iris / Halo whitepapers `UNVERIFIED, no DOI`
- Aeva Atlas FMCW technical brief `UNVERIFIED, no DOI`
- Livox Mid-360 datasheet `UNVERIFIED`
- Empirical: maintainer's exposure to automotive LiDAR vendor pitches at trade shows

## Boundary

- `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md` — short-range 850 nm sibling (active stereo / structured light)
- `foundations/sensor-physics/tof_physics_for_embodied_ai.md` — ToF regime (sibling; pulsed LiDAR is the long-range branch of pulsed ToF)
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — cross-embodiment SWaP-C: when LiDAR makes sense at all
- `embodiments/aerial/sensor-stack/` — Livox-class deployment on drones
- Per-embodiment integration + calibration (extrinsics, time-sync) live under `embodiments/<x>/sensor-stack/`; this doc covers wavelength + eye-safety + detector physics only.

*2026-05-21. v1 first version, satisfies 14-item gate. UNVERIFIED → datasheet cites in v1.1.*

---
[← Back to sensor-physics README](./README.md)
