# The TRD Failure Atlas: Transparent, Reflective, Deformable

**Status:** v1 — opinionated draft. Sensor / latency / cost numbers marked `UNVERIFIED` need rig-side validation.
**Wedge tier:** W1
**TL;DR:** Three failure modes — transparent objects, reflective surfaces, deformable bodies — break *every* spatial intelligence stack, but they break each embodiment differently and each embodiment's dominant mitigation **does not generalize**. The manipulation answer (polarization + tactile) won't fly on a drone; the AD answer (radar redundancy) won't dive on an AUV; the AUV answer (sonar) won't grasp a wine glass. **TRD is the cleanest crossing axis after scale.**

---

## 1 · Why "transparent / reflective / deformable" is one failure mode, not three

From a sensor-physics standpoint, all three break the same assumption: **that surface appearance is a one-to-one function of surface geometry and surface BRDF**.

- **Transparent** — the light returning to the camera came from *behind* the surface. Geometry estimator localizes the *background*, not the surface.
- **Reflective** — the light returning to the camera came from *somewhere else in the scene*. Geometry estimator localizes a *virtual* surface behind the mirror.
- **Deformable** — the surface *did exist* at last frame but is not where it was. Geometry estimator's prior (rigid body) is wrong; tracking and reconstruction both diverge.

Different physics, but the same downstream symptom: **the depth map lies, and the policy that consumes it acts on a lie**. Which is why every embodiment community has rediscovered this problem independently and named it three different things.

The interesting part is **the mitigation strategy is forced by the embodiment's sensor budget and latency envelope, and those forces push different embodiments toward incompatible answers**. That's the crossing story.

---

## 2 · The TRD breakage table

| | Transparent | Reflective | Deformable |
|---|---|---|---|
| **Manipulation** | Wine glass / clear plastic bag — RealSense / stereo see the table behind it; grasp planner aims at nothing | Chrome teapot / stainless cookware — IR projector pattern flares; reads as a hole | Cloth folding / cable manipulation — geometry valid only at instant t; planner replans every frame |
| **Humanoid** | Glass door / glass divider — opens-up trajectory collides with closed glass | Polished hospital floor / mirror — VIO loop-closes to a virtual ghost room | Carrying a soft bag / opening a curtain — payload geometry shifts mid-trajectory |
| **Ground AGV** | Glass office partition — robot drives into it; LiDAR sees behind | Wet floor / polished concrete — LiDAR intensity inversion; depth cam confused | Plastic curtain / chain mat — robot can pass but path planner sees obstacle |
| **Drone** | Glass facade on commercial building — collision; cameras see through, LiDAR sees a weak return | Wet roof / solar panel / car windshield — visual SLAM reads as sky; stereo NaN | Tree canopy in wind / power line in sway — feature tracker loses lock |
| **AD** | Glass storefront / windshield of stopped car — LiDAR weak return, radar invisible | Wet asphalt / chrome bumper / Cybertruck-class panel — radar gets multipath; cameras get glare | Tarp on a truck / loose load / pedestrian carrying a sheet — classifier fails |
| **Marine AUV** | Jellyfish / clear plankton bloom — sonar weak return; vehicle hits gelatinous mass | Surface ceiling (air-water from below) — sonar reflects back; visual sees mirror | Kelp forest / fishing net / seagrass — propeller entanglement risk |

Notice: same three columns, six embodiments, eighteen distinct failure scenarios that no single sensor stack fully handles.

---

## 3 · The dominant mitigation per embodiment — and why it doesn't transfer

```
  Manipulation:  polarization camera + tactile + multi-view
                 ─────────────────────────────────────────
                 cost ~$3k `UNVERIFIED`, weight 200 g, range 0.1–1 m
                 transfer to drone? NO — too heavy, too slow, wrong range
                 transfer to AD? NO — wrong scale, polarization unreliable outdoors

  Drone:         redundancy + plan-the-safe-side + radar
                 ────────────────────────────────────────
                 cost ~$800 radar, weight 200 g, range 0.5–30 m
                 transfer to manipulation? NO — radar resolution too coarse at 0.3 m
                 transfer to AD? PARTIAL — different radar class (77 GHz vs drone 60 GHz)

  AD:            radar primary + LiDAR + camera fusion + map prior
                 ──────────────────────────────────────────────
                 cost >$10k full stack, weight 5+ kg, range 5–200 m
                 transfer to drone? NO — too heavy, SWaP-C explodes
                 transfer to humanoid? NO — radar lobes too broad for room-scale

  AUV:           multibeam sonar primary + DVL + acoustic doppler
                 ───────────────────────────────────────────────
                 cost >$30k, weight 3+ kg, range 0.5–30 m underwater
                 transfer to anything in air? NO — acoustic doesn't propagate
```

Read this as: **every embodiment has a winning answer, and none of them generalize.** The "spatial intelligence" pretense that one perception stack will run on all robots fundamentally breaks here, before it even gets to the model architecture conversation.

---

## 4 · Three breakage close-ups

### 4a · Chrome teapot in a manipulation cell

Active-IR-projector depth cameras (RealSense D435/D455) flood the scene with a structured IR pattern and triangulate. On chrome, the pattern reflects to *somewhere else* (the ceiling, a wall) and the camera sees no pattern *on* the chrome — it reads as a hole. The naive grasp planner aims for the *background table*.

The 2026 fix is **polarization** (Lucid Vision Phoenix Polar-class) which exploits the fact that reflected light is partially polarized. Cost ~$3k, weight ~200 g `UNVERIFIED`. Works at 0.1–1 m range, fails at >2 m. **Won't fit on a drone budget at all.**

A second fix is **tactile-after-vision** — let the visual system aim approximately, then close the loop with a F/T sensor or skin sensor when the gripper makes contact. Cheap and slow, fine for a tabletop, dead for highway speeds.

### 4b · Wet asphalt at AD highway speeds

Wet asphalt acts as a partial mirror. The lane line is faint; oncoming headlights smear; LiDAR intensity becomes ambiguous (the return is *bright* not because the surface is bright, but because the geometry is specular). Camera-based lane detection has reported 5–20× error spikes on wet vs dry runs `UNVERIFIED`.

The 2026 fix is **radar primary at long range** (radar ignores wet asphalt) + **map prior** (we know the lanes are there from HD map) + **degraded-mode policy** (slow down, increase following distance). All three are layered. **None of those transfer to drone** — drones have no HD-map prior and no equivalent of "slow down on the freeway".

### 4c · Cloth folding in manipulation vs power-line in wind for drone

Two deformable-object stories that look superficially similar and are completely different problems.

- **Cloth folding** — geometry is high-dimensional but **slow**. The cloth is at rest 95% of the time. The policy can re-perceive at each step.
- **Power-line in wind** — geometry is low-dimensional (1D curve) but **fast**. The line oscillates at 1–3 Hz. The policy has to *predict* where it will be, not just see where it is.

The manipulation answer: dense visual tracking + replan-each-step. Works at 30 Hz on a Jetson. The drone answer: detect the line as a *class*, predict its swept-volume bounding region, give it 2× safety margin. **The manipulation stack is useless on the drone**: its predictions are not fast enough, and the line moves between frames.

---

## 5 · The cross-embodiment matrix that drives sensor-stack-matrix

The TRD failures push each embodiment toward a sensor stack that wouldn't be its first choice on other axes:

| Sensor added because of TRD | Manipulation | Humanoid | Ground AGV | Drone | AD | Marine |
|---|---|---|---|---|---|---|
| Polarization camera | ✅ (transparent / reflective) | optional | optional | ❌ SWaP | ❌ outdoor unreliable | ❌ underwater optics fight |
| Tactile / force | ✅ | ✅ | rarely | ❌ | ❌ | ❌ |
| Radar | ❌ resolution | optional | ✅ | ✅ | ✅ primary | ❌ underwater |
| Sonar / acoustic | ❌ in-air | ❌ | rarely | ❌ | ❌ | ✅ primary |
| Map prior | ❌ | optional | ✅ | partial (geofencing) | ✅ HD map | ✅ bathymetric |
| Multi-view / parallax | ✅ | ✅ | ✅ | ✅ | ✅ | partial |

The cells where TRD forces a new sensor are *exactly* the cells where SWaP-C / cost blows up on the embodiment's primary axis. **TRD is the failure mode that breaks the SWaP-C budget**, which is why the answer in `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` always has a "TRD margin" line item.

---

## 6 · 2-year outlook + falsifiable prediction

What changes by 2027:

1. **Polarization cameras drop to &lt;$500** — would let humanoid and ground AGV adopt them as standard. Plausible by 2027.
2. **Imaging radar with cm-class resolution** — would let drone and AD handle TRD without the polarization workaround. Multiple vendors (Arbe, Mobileye, Texas Instruments) targeting this; 2027 ship date plausible.
3. **TRD-aware foundation depth models** — train on synthetic transparent/reflective/deformable data. The data does not exist at scale; ClearGrasp (Sajjan et al. 2020) and DexNerf are seeds.
4. **VLM understands "this is a window"** — semantic prior bypasses the perception problem. Today's VLMs (Gemini, GPT-4V) already do this with surprising reliability; integrating into the perception loop is the open problem.

**Falsifiable prediction:** before 2027-12, a manipulation policy will ship that handles glass / chrome / cloth with a single front-end (no per-object sensor swap), via VLM semantic prior + polarization + tactile fusion. **No equivalent will ship in drone or AD** — both keep TRD as known-limitation / degraded-mode through 2027. Bet against any AD vendor claiming "solved wet asphalt" without map prior.

---

## For the reader

- **Manipulation engineer** — polarization + tactile is your default. Don't generalize your success to "we solved TRD"; you solved it at 0.3 m, not at 30 m.
- **Humanoid engineer** — your hardest case is glass doors and polished floors. Borrow manipulation's polarization tooling; add an "is glass?" semantic prior from a VLM.
- **Drone engineer** — your TRD answer is *redundancy* (radar + visual + altimeter), not *resolution*. Don't try to make stereo see through glass; route around it.
- **AD engineer** — wet asphalt is your single hardest TRD case. The answer is degraded-mode + map prior + radar primary; don't expect any single sensor to fix it.
- **Marine engineer** — your TRD failures are jellyfish and kelp; the mitigation is acoustic primary + visual auxiliary. Don't trust visual SLAM near the surface (mirror ceiling).
- **Researcher** — TRD-aware depth foundation models (item 3) are the open lane. The data bottleneck is real and synthetic-only data won't close it.

---

## References

- ClearGrasp — Sajjan et al. *ICRA 2020*. https://arxiv.org/abs/1910.02550
- Dex-NeRF — Ichnowski et al. *CoRL 2021*. https://arxiv.org/abs/2110.14217
- Lucid Vision Phoenix Polar — product page. https://thinklucid.com `UNVERIFIED, no DOI`
- Polarization-based 3D imaging review — Kadambi et al. *ICCV 2015*. https://www.cs.ucla.edu/~achakrabarti/papers/kadambi_iccv15.pdf `UNVERIFIED`
- Imaging radar overview — Arbe, Mobileye, TI — vendor pages, no canonical paper.
- Sonar fundamentals — Lurton, *An Introduction to Underwater Acoustics* (2002). `UNVERIFIED, textbook`
- Cloth manipulation survey — Sanchez et al. *IJRR 2018*. https://arxiv.org/abs/1804.06934 `UNVERIFIED`

## Boundary

This doc lays out TRD failures *across embodiments* and the *dominant per-embodiment mitigation*. It does **not** dissect per-sensor physics (that's `foundations/sensor-physics/*.md`), nor manipulation-specific TRD pipelines (`embodiments/manipulation/perception/`), nor the SWaP-C math (`crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md`). Cross-link here when you need the "why doesn't X's answer work for Y" story.

---

*Last opinion update: 2026-05-21. §6 prediction will be scored at 2027-12.*
