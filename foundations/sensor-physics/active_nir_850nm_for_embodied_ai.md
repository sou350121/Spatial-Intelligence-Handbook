# Active NIR (850 nm) for Embodied AI

**Status:** DRAFT v0.1 — scaffold only, content pending
**Wedge tier:** W1 (one of 5 launch docs)
**Why this doc exists:** Industry deploys 850 nm active NIR illumination in production (Skydio's obstacle sensing, Apple Face ID, structured-light depth cameras), but academic surveys skip the physics. This is the handbook's "industry's missing axis" wedge.

---

## Thesis

850 nm sits at the sweet spot of (a) Si CMOS sensitivity, (b) ambient solar irradiance dip, (c) human eye safety class 1 budget at reasonable optical power. Every embodied-AI vendor that ships active sensing converges on this band. Understanding *why* — and what changes at 940 nm / 1550 nm — is a prerequisite for honest sensor selection.

---

## Outline

1. **Spectral physics primer** — quantum efficiency of Si vs InGaAs, solar irradiance curve (AM1.5), Class 1 / Class 1M laser safety MPE numbers.
2. **Why 850 nm specifically** — comparison table with 760 / 808 / 940 / 1380 / 1550 nm: QE, ambient rejection, eye safety budget, optical component cost.
3. **Hardware archetypes**
   - Structured light (Kinect v1 lineage, Apple Face ID)
   - ToF (Kinect v2, iPhone LiDAR, automotive flash LiDAR)
   - Active stereo (Intel RealSense D-series, Skydio)
4. **Embedded BPF design** — bandpass filter width vs cost vs out-of-band rejection. Why narrow BPF (10 nm FWHM) gains ambient rejection.
5. **Failure modes** — interference from other 850 nm projectors, sun reflections off chrome, thermal drift of VCSEL center wavelength.
6. **Embodiment-specific picks** — manipulation (active stereo wins), drone (passive stereo or VIO dominant — 850 nm power-hungry), AR/VR (Vision Pro uses 940 nm not 850 nm — write up why).

---

## Starter references

- Hamamatsu / Sony / OmniVision QE curves (datasheets)
- IEC 60825-1 (laser safety classification)
- Intel RealSense whitepapers (active stereo)
- VCSEL physics primers — Lumentum / II-VI
- Empirical experience from the maintainer's Autel work

---

## Boundary note

This doc covers spectrum + safety + cost. Embodiment-specific sensor stacks live under `embodiments/<x>/sensor-stack/`. Cross-embodiment matrix lives under `crossing/sensor-stack-matrix/`.
