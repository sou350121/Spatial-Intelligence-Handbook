# Splat-Sim 与基于 3DGS 的操作数据工厂 (Splat-Sim and 3DGS-Powered Manipulation Data Factories)

> **发布时间**：Splat-Sim (Qureshi et al. 2024, arXiv:2405.02316); RoboGS family 2024; GaussianGrasper (arXiv:2403.09637)
> **核心定位**：用 3DGS 把"phone 拍 3 分钟 → 一万条 manipulation 训练 demo"的 sim2real 桥梁打通；它不是新仿真器，而是"以视觉真实度换接触保真度"的 data factory。

A diffusion policy needs thousands of photorealistic demonstrations per task. Teleoperation gives ~50 episodes a day per operator. Isaac Sim gives unlimited episodes that look like plastic. **Splat-Sim splits the difference: reconstruct a real scene as 3DGS in minutes, then render the same task from a thousand novel viewpoints — feeding a diffusion policy that has to consume real RGB at deployment.**

### X-Ray (non-expert friendly)

1. **The problem.** Imitation policies overfit to the exact camera pose and lighting of the teleop demos; they collapse the first time the kitchen looks slightly different.
2. **The trick.** Capture the scene once with 3DGS. Re-render the same demonstration from a thousand jittered camera poses, with the robot URDF overlaid synthetically — turning 100 real demos into 10000 photoreal samples without re-recording anything.
3. **Why a spatial-AI reader should care.** This is the first deployment of 3DGS where the *robotics customer is buying photorealism specifically as a sim2real lever* — not as a graphics property. It changes what "good enough 3DGS" means.

### Research Landscape Timeline (X-Ray)

```
  2017 ─── Domain randomization (OpenAI, To et al.)
  2020 ─── NeRF — but too slow per-scene for sim2real
  2023.07 ─ 3DGS (Kerbl et al. SIGGRAPH) — 100× faster, explicit
                              │
  ┌───────────────────────────┼───────────────────────────┐
  2024.05 Splat-Sim       2024.06 RoboGS         2024.09 GaussianGrasper
  Today: rigid-body only; contact dynamics still borrowed from teleop,
         deformables and contact-rich tasks remain open.
```

---

## 1 · System Overview

### 1.1 Component Comparison

| Module | Input | Output | Cost (per task, `UNVERIFIED`) |
|---|---|---|---|
| Scene capture | 2–5 min phone video | COLMAP poses + 3DGS scene (~1 GB) | 5–30 min |
| Robot overlay | URDF + joint trajectory | Robot rendered into 3DGS scene | ~30 ms / frame on RTX 4090 |
| Viewpoint aug | k demos + cam-pose distribution | k × N rendered demos | ~5 min for 1000 views |
| Policy training | Augmented demo set | Diffusion / ACT policy | Hours on A100 |
| Real-robot eval | Trained policy + arm | Success-rate Δ vs teleop-only | The only number that matters |

### 1.2 Key Mechanism

The Splat-Sim trick is to keep the *task* and *robot trajectory* fixed across all augmentations, varying only the rendered camera pose, the lighting (re-color SH coefficients), and optional distractor splats.

⚡ **Eureka Moment**: *The robot doesn't need to learn novel actions — it needs to learn to ignore irrelevant pixels. 3DGS rendering is the cheapest way to manufacture "same action, different pixels" pairs at scale.*

### 1.3 Pipeline Flow

```
  phone capture → COLMAP + 3DGS fit (~10 min)
       ↓
  3DGS scene primitives
       ↓ ← URDF + teleop trajectory
  Splat-Sim renderer (jitter cam, jitter SH lighting, splice distractors)
       ↓
  N rendered demo videos → diffusion policy training (real + splat mix)
```

---

## 2 · Math Core

📌 **Napkin Formula**:
```
  Loss_policy = E_{view, light}[ L(π(I_render(scene, view, light)), a_teleop) ]
```
*The policy's action target stays bolted to the original teleop action; only the rendered input varies.*

Splat-Sim does not modify the underlying gaussians per augmentation — it varies the *rendering function* arguments:

- **Camera pose `T_cw`**: sampled from Gaussian around the teleop camera (typical std `UNVERIFIED`: ±5 cm position, ±3° orientation).
- **Lighting via SH**: SH coefficients attenuated and re-tinted per gaussian (cheap proxy for relighting; no path tracing).
- **Distractor splat injection**: object-library gaussian clusters inserted at non-task positions.

> Variables: `I_render` is the differentiable rasterizer from the original 3DGS paper; `a_teleop` is the teleop action label; `π` is the policy network.

This is *not* a physics-aware augmentation. It does not relight by path tracing and does not change the robot's contact wrench when the policy nudges the cup. **The augmentation is photometric only; contact dynamics is borrowed unchanged from the original teleop trajectory.**

---

## 3 · Worked Example: 100 Demos → 10000 Demos

Task: "pick the red cup, place in the drawer." Start with 100 teleop demos.

1. **Capture the scene once.** Phone walks around the counter for 3 minutes (~150 frames). COLMAP + 3DGS produces ~600k gaussians.
2. **For each of the 100 demos**, sample 100 camera-pose perturbations from N(μ=teleop_cam, σ=±5cm/±3°). That's 10000 renderings.
3. **Render each under 3 lighting variants** (warm / cool / overcast SH). 30000 demos.
4. **Splice a random distractor** into 50% of the renderings at non-contact positions.
5. **Train diffusion policy** on (real_100 + splat_30000). Use ~50/50 sampling — *not* 100% splat (collapses).
6. **Validate on real arm.** Published deltas (`UNVERIFIED`): +15–30 pp success rate vs real-100-only, attributed to photometric robustness.

Total clock time added: capture 3 min + fit 10 min + render 30 min ≈ 45 min, fraction of one A100-hour.

---

## 4 · Engineering View: When Splat-Sim Beats Isaac

| Concern | Splat-Sim | Isaac Sim |
|---|---|---|
| Scene-author cost | 5 min phone capture | hours of artist work per asset |
| Photorealism | ★★★★ (real-world capture) | ★★ (depends on USD assets) |
| Contact dynamics | borrowed from real teleop (✅ correct) | physics engine (✅ controllable) |
| Novel motion (no teleop ref) | ❌ — needs a real demo | ✅ — RL from scratch works |
| Deformables, fluids | ❌ — gaussians are rigid | ✅ — FEM / SPH plugins |
| GPU cost / 1k demos `UNVERIFIED` | ~0.5 GPU-hour | ~2 GPU-hour |

**Decision rule**: if your manipulation task is failing on *appearance variation*, Splat-Sim is the cheapest fix. If it's failing on *novel contact* (insertion, slippery surfaces), Splat-Sim cannot help — you need Isaac or real data.

---

## 5 · Data & Eval Conventions

Splat-Sim papers typically report per-task success rate on physical robot (real-teleop-only vs real+splat mix), robustness curves under eval-time camera-pose perturbations, and distractor-injection robustness in real cluttered scenes.

What is **rarely** reported cleanly: contact-rich tasks (insertions, screwing) or how little real data the augmentation can survive on (it cannot run with zero real demos).

---

## 6 · Capabilities & Failure Modes

**Works well**: pick-and-place, push, slide on textured surfaces; mobile manipulation in real homes; appearance-bound tasks for a VLM consuming RGB.

**Fails or marginal**: insertion / peg-in-hole / screwing (wrong gap); deformable objects; articulated objects beyond captured state; tasks needing tactile or force supervision.

### 6.1 Hidden Assumptions

1. **Scene capture quality is sufficient.** Noisy COLMAP poses → 3DGS floaters → renders with artifacts → policy overfits to artifacts. Capture discipline is part of the method.
2. **Contact dynamics is not the bottleneck.** Splat-Sim renders pixels of the robot near a cup; it does not simulate the cup tipping when nudged. Augmentation varies what the policy sees, not what physically happened.
3. **Teleop action labels remain valid under viewpoint jitter.** True for end-effector-frame action policies; fragile for camera-frame ones.
4. **SH-attenuation lighting is "close enough."** No global illumination is recomputed. Specular materials and hard shadows do not respond correctly.
5. **Training-time only.** The deployed policy never queries Splat-Sim — this is the firewall against inference-time world-model failure modes.

---

## 7 · Comparison & Interview Tip

| | Splat-Sim | Isaac + DR | Cosmos-Transfer | Genie-style WM |
|---|---|---|---|---|
| Stage | training | training | training | inference |
| Photorealism source | real capture | USD assets | learned video prior | learned video prior |
| Contact dynamics | from real teleop | from PhysX | none (just pixels) | none |
| Cost per new scene | 5 min phone | hours of asset auth | needs sim asset first | n/a |
| Best for | appearance gap | contact-rich + novel motion | sim2real on Isaac assets | online MPC |

🎯 **Interview Tip**: When asked *"Splat-Sim or Isaac Sim?"*, do not answer "depends." Answer: **"Splat-Sim if my failure mode is appearance variation in scenes I can capture. Isaac if my failure mode is contact dynamics or I need RL from scratch with novel motion. The two are complements — production pipelines run Isaac for novel-motion seeding plus Splat-Sim for photometric robustness."**

---

## Boundary

Per-method 3DGS internals → `foundations/3dgs-family/3dgs_original_dissection.md`. Per-embodiment "did this ship on my robot?" → `embodiments/manipulation/`. Cross-embodiment "manip vs drone vs AD 3DGS-sim" → `crossing/representation-migration/3dgs_as_simulator_comparison.md`. Inference-time world models → `foundations/world-model/`.

## References

- Qureshi et al., *Splat-Sim: Zero-Shot Sim2Real Transfer of Manipulation Policies Using Gaussian Splatting*, arXiv:2405.02316 (2024).
- Kerbl et al., *3D Gaussian Splatting for Real-Time Radiance Field Rendering*, SIGGRAPH 2023, arXiv:2308.04079.
- Zheng et al., *GaussianGrasper: 3D Language Gaussian Splatting for Open-Vocabulary Robotic Grasping*, arXiv:2403.09637 (2024).
- To et al., *Sim-to-Real Transfer via Domain Randomization*, OpenAI 2017 (lineage).

---

**Status:** v1 (2026-05-21). UNVERIFIED policy applies to all latency / success-rate / GPU-hour numbers.

[← Back to Generative 3D Sim](./README.md)
