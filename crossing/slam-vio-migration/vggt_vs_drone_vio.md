# Can VGGT Replace Drone VIO?

**Status:** DRAFT v0.1 — scaffold only, content pending
**Wedge tier:** W1 (one of 5 launch docs) — **handbook's flagship piece**
**Why this doc exists:** The question — "feed-forward 3D replaces classical VIO?" — is the cleanest test of the handbook's cross-embodiment claim. On a desktop scanner the answer is yes today. On a 30 m/s racing drone the answer is no even by 2026. *Why the answer flips when you change embodiment* is the whole point.

---

## Thesis

VGGT delivers correct geometry but neither the latency budget nor the scale resolution that aerial VIO requires. Where VINS-Mono / OpenVINS / DROID-SLAM survive on aerial platforms, they survive because IMU pre-integration and metric scale are baked in; VGGT outputs un-metric pointmaps and runs at ~5–10 Hz on Jetson Orin even after distillation. The path forward is hybrid (VGGT as a low-rate global anchor, classical VIO for high-rate dead-reckoning) — not replacement.

---

## Outline

1. **What aerial VIO requires** (the non-negotiables)
   - ≥ 100 Hz state estimate (control loop bandwidth)
   - Metric scale (controllers care about meters)
   - Sub-10 ms latency from sensor to estimate
   - Robust to IMU spectrum aliasing under prop vibration
2. **What VGGT delivers**
   - ~5–10 Hz on Jetson Orin (with FP16 + token reduction)
   - Un-metric pointmap (scale ambiguity from monocular)
   - 100–300 ms latency end-to-end
3. **Gap matrix** (rate × scale × latency × vibration tolerance)
4. **Hybrid architectures**
   - VIO front, VGGT loop closure
   - VGGT scaffold + visual-inertial filter
   - Tightly coupled VGGT pointmap into MSCKF
5. **What changes per embodiment**
   - Manipulation: VGGT wins because rate < 30 Hz acceptable
   - Ground mobile: VGGT acceptable with GNSS fusion
   - Aerial racing: VIO essential
   - Aerial inspection: hybrid viable today
   - Marine: neither solves the core problem (visual degradation)
6. **2-year outlook** — what would need to change in VGGT-class models for the aerial answer to flip.

---

## Starter references

- VGGT (CVPR 2025) — see `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`
- VINS-Fusion / OpenVINS — HKUST / UDel
- DROID-SLAM — Princeton
- π³ / streaming feed-forward variants
- UZH RPG racing drone papers — latency budgets
- Skydio engineering blog — autonomy at altitude
- Maintainer's own drone deployment notes

---

## Boundary note

This is a *crossing* piece. Per-method dissections live in `foundations/`. Per-embodiment stacks (e.g. UZH-style racing) live in `embodiments/aerial/vio/`. This doc links to both rather than duplicating.
