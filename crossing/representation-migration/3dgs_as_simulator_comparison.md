# 3DGS-as-Simulator: Manipulation vs Drone vs AD

**Status:** v1 — opinionated draft. Compute / latency / asset-size numbers marked `UNVERIFIED` need rig-side validation.
**Wedge tier:** W1
**TL;DR:** Three communities are calling the same idea "3DGS-as-simulator" while building three very different things. Splat-Sim (manipulation) trades hours-per-scene fit for grasp-loop fidelity. Aerial Gym-lineage drone sim2real trades fidelity for *millions of parallel rollouts*. NVIDIA Cosmos / AD scene reconstruction trades both for *editable counterfactuals*. **The fidelity-vs-controllability trade-off resolves in opposite directions per embodiment — and the first product-ready 3DGS-sim will not be the most photorealistic one.**

---

## 1 · Why this comparison is overdue

In the last 18 months, every embodiment community discovered that **3DGS reconstructs a scene faithfully enough to render synthetic training data**. Three independent waves landed:

- **Manipulation** — Splat-Sim (Qureshi et al. 2024), RoboGS, GaussianGrasper — fit a scene from a few minutes of phone capture, drop in articulated robot URDFs, train policies via domain randomization on top.
- **Drone / aerial** — Aerial Gym lineage (ETH Zürich / NVIDIA), Splat-Nav (Chen et al. 2024), GS-Splatter sim — fit an outdoor environment, fly a quadrotor through it in massively parallel sims, transfer policies to real flight.
- **AD** — NVIDIA Cosmos, Waymo's "Block-NeRF → 3DGS" lineage, UniSim, MARS — reconstruct logged driving scenes, *edit* them (add traffic, change weather), use as a closed-loop validation environment.

Looked at separately, each looks like the same paper rewritten with different keywords. Looked at together, **the architectures, compute budgets, fidelity targets, and product paths are different enough that they will not converge in 2026**. That's the crossing question.

---

## 2 · The three teams side by side

| | Manipulation (Splat-Sim lineage) | Drone (Aerial Gym lineage) | AD (Cosmos / UniSim) |
|---|---|---|---|
| Scene scale | 1–3 m³ tabletop / cabinet | 100–10000 m² outdoor | 100m–km driving log |
| Capture | 2–5 min phone video | drone pre-flight or aerial photogrammetry | sensor-rig log (camera + LiDAR + GNSS) |
| Fit time `UNVERIFIED` | 5–30 min per scene | 30 min–4 hr | hours–days per log |
| Render rate target | 30 Hz for grasp servo | **1k+ Hz across parallel envs** | 10 Hz for closed-loop eval |
| Fidelity target | photometric + contact geometry | flyable obstacles, sky, no perfect ground | drivable + dynamic agents editable |
| Domain randomization style | textures, lighting, object poses | wind, lighting, sensor noise | traffic, weather, agent behavior |
| Asset count per scene | 1 scene + N objects (URDFs) | 1 scene + 1 ego model | 1 scene + 10s of dynamic agents |
| Real-robot in the loop? | yes (grasp validation) | yes (zero-shot transfer) | rarely (validation env, not training env) |
| Today's primary use | policy training | RL training + sim2real | safety case + regression testing |
| Compute per training run `UNVERIFIED` | 1 GPU × hours | 8 GPUs × days (massive parallel) | 64+ GPUs × days |

The shape of this table is what `crossing/` exists to show. *Same representation, three orthogonal optimization targets.*

---

## 3 · Why fidelity-vs-controllability resolves differently per embodiment

Every simulator faces the same triangle:

```
              fidelity
              /\
             /  \
            /    \
           /      \
          /        \
   speed ─────── controllability
        (parallel)   (editable)
```

You can pick two. The interesting part is *which two each embodiment picks*:

- **Manipulation picks fidelity + controllability.** Why: contact dynamics is the bottleneck, and you need to spawn random object poses but render them photorealistically (because the policy is a VLM consuming RGB). Speed is sacrificed because one robot needs one rollout at a time, not 4096 of them. *Splat-Sim's 30 min fit is fine.*
- **Drone picks speed + fidelity.** Why: drone RL training takes *millions* of episodes; sim must run on a GPU at 1000+ Hz. Editability is sacrificed because the agent flies the same wind/obstacle scene over and over. *Aerial Gym does not need to add traffic to your park.*
- **AD picks controllability + fidelity.** Why: the value is in counterfactuals ("would the policy have hit this cyclist if we shifted them 1.5 m left?"). Speed is sacrificed because each "rerun" is one drive log, not 10000 parallel episodes — the validation question is sequential, not statistical. *Cosmos renders 10 fps and that's fine for the safety case.*

**No two embodiments pick the same two corners.** This is why a "universal 3DGS simulator" is the wrong product. Whoever tries to build it ships something that's mediocre at all three.

---

## 4 · The compute budget reality

The hidden axis is per-embodiment economics:

- **Manipulation** can afford 30 minutes of scene fit because a teleop demo costs an operator a similar amount of human time. Fit-once-train-many amortizes well.
- **Drone** *cannot* afford 4 hours of scene fit per environment because the training pipeline wants 1000s of distinct environments per RL curriculum. Aerial Gym's answer is parametric / procedural environments with 3DGS-style appearance baked on top — not full per-scene fits.
- **AD** can afford days of fit per log because logs are precious (millions of miles of fleet data, the company already owns them). Per-log fit is a one-time cost amortized over years of regression testing.

Number to anchor: a 3DGS scene of moderate size (~500k Gaussians) fits in 5–10 min on an RTX 4090 `UNVERIFIED`. Same scene at AD-grade (10M+ Gaussians, dynamic agents, weather conditioning) is hours–days on an 8×H100. **That gap is two orders of magnitude.** No single rendering stack survives it.

---

## 5 · When 3DGS-as-sim beats traditional sim — and when it doesn't

Traditional simulators (Isaac Sim, AirSim, CARLA, MuJoCo) have a 10-year head start on contact dynamics, parallelism, and editability. 3DGS-as-sim wins specifically when:

- **Photometric realism is the bottleneck** — VLM-based manipulation policies, end-to-end driving from camera. Splat-Sim and Cosmos win here because mesh-based PBR is still uncanny at close range.
- **Real-scene transfer is the bottleneck** — "I want to test my policy on *this exact warehouse*". 3DGS fits the warehouse in 30 min; building a CAD model of the warehouse takes weeks.
- **Counterfactuals on logged data** — "what if the pedestrian had been wearing a yellow jacket?". Editing a 3DGS scene is easier than editing a CAD scene because the representation is point-cloud-native.

It *loses* when:

- **Contact dynamics matter** — 3DGS gives you appearance, not friction or compliance. Splat-Sim still uses MuJoCo / PhysX under the hood; the 3DGS only renders. Pure 3DGS does not simulate grasping.
- **Massive parallelism matters** — Isaac Sim runs 4096 envs on one GPU. 3DGS at 1000 Hz across 4096 envs is research-stage; the Aerial Gym work has shown one piece of this but not the full stack.
- **Generalization across scenes matters** — A policy trained in one fitted scene overfits. You still need procedural / parametric environments for breadth.

The pattern: **3DGS-as-sim is the appearance backend; the physics, parallelism, and editability backends are still being filled in per embodiment**.

---

## 6 · The product paths in 2026

```
   Manipulation (Splat-Sim)             Drone (Aerial Gym)              AD (Cosmos / UniSim)
   ─────────────────────────             ──────────────────              ────────────────────
   capture warehouse cell                fly recon over field            fleet log (camera+LiDAR)
          │                                     │                                │
          ▼                                     ▼                                ▼
   fit 3DGS (30 min)                     fit 3DGS (hours)                fit 3DGS + agents (days)
          │                                     │                                │
          ▼                                     ▼                                ▼
   spawn URDF robot,                     load into Aerial Gym,           edit scene (add agents,
   randomize objects + texture           run 10M RL rollouts             change weather)
          │                                     │                                │
          ▼                                     ▼                                ▼
   train VLM policy                      transfer policy to real         closed-loop policy eval
          │                                     │                                │
          ▼                                     ▼                                ▼
   deploy on real robot                  flight test                     safety case + ship update
```

The three pipelines look superficially identical and architecturally diverge at every stage past "fit 3DGS".

---

## 7 · 2-year outlook + falsifiable prediction

What's actually shipping by 2027:

1. **Manipulation** — Splat-Sim-style pipelines integrated into Isaac Sim / NVIDIA GR00T workflow. Photoreal cell scanning at consumer phone capture quality. *Most product-ready first.*
2. **Drone** — Aerial Gym + 3DGS appearance for racing / inspection RL. Sim2real gap narrows but doesn't close; outdoor wind and lighting still bite.
3. **AD** — Cosmos and equivalents (Waymo / Tesla internal) become safety-case standard. Public-facing 3DGS-as-AD-sim ships as a benchmark / leaderboard, not a training environment.

**Falsifiable prediction:** before 2027-12, a manipulation-policy stack will ship a commercial product (likely Physical Intelligence π0-class or Skild AI) that uses Splat-Sim-style 3DGS rendering as a *training-time* simulator and ships a successful real-world VLA policy on top. **No equivalent product will ship in drone or AD by the same date** — both stay in research / internal-validation use through 2027. Bet against any AD vendor claiming "trained in 3DGS sim" before 2028.

---

## For the reader

- **Manipulation engineer** — Splat-Sim is your near-term win. Don't expect it to fix your contact dynamics; pair it with MuJoCo / PhysX. Watch the GR00T / Cosmos integration story.
- **Drone engineer** — Aerial Gym + 3DGS is the cheapest sim2real path for outdoor inspection. Don't expect 1000-Hz photoreal rendering on a single GPU yet. Watch the ETH / NVIDIA collab.
- **AD engineer** — Cosmos-class tooling is a validation environment, not a training environment, for at least 2 more years. Use it to *score* policies, not train them.
- **Researcher** — the open lane is *editable + parallel + photoreal*. Nobody owns all three. Whoever closes that triangle wins the next two NeurIPS cycles.

---

## References

- Splat-Sim — Qureshi et al. 2024. https://arxiv.org/abs/2409.10161 `UNVERIFIED ID`
- Aerial Gym — Kulkarni et al. *IROS 2023* / NVIDIA. https://arxiv.org/abs/2305.16510
- Splat-Nav — Chen et al. 2024. https://arxiv.org/abs/2403.02751 `UNVERIFIED ID`
- NVIDIA Cosmos — https://www.nvidia.com/en-us/ai/cosmos/ (product page; technical report TBD)
- UniSim — Yang et al. *CVPR 2023*. https://arxiv.org/abs/2308.01898 `UNVERIFIED ID`
- Block-NeRF — Tancik et al. *CVPR 2022*. https://arxiv.org/abs/2202.05263
- 3DGS — Kerbl et al. *SIGGRAPH 2023*. https://arxiv.org/abs/2308.04079
- Isaac Sim — NVIDIA. https://developer.nvidia.com/isaac-sim
- CARLA — Dosovitskiy et al. *CoRL 2017*. https://arxiv.org/abs/1711.03938

## Boundary

This doc compares *use-cases* of 3DGS-as-simulator across embodiments. It does **not** dissect 3DGS internals (that's `foundations/3dgs/3dgs_siggraph2023_dissection.md`), nor Splat-Sim implementation (`embodiments/manipulation/sim/`), nor Cosmos data engineering (`embodiments/driving/sim/`). The per-embodiment scene-scale and sensor-stack details live in `crossing/scale-comparison/` and `crossing/sensor-stack-matrix/`.

---

*Last opinion update: 2026-05-21. §7 prediction will be scored at 2027-12.*
