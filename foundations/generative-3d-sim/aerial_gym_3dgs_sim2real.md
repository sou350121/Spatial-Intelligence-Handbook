# Aerial Gym 与无人机 3DGS Sim2Real (Aerial Gym and Drone 3DGS Sim2Real)

> **发布时间**：Aerial Gym (Kulkarni et al. 2023, arXiv:2305.16510); Splat-Nav (Chen et al. 2024, arXiv:2403.02751); GS-Splatter sim variants 2024–2025
> **核心定位**：用 3DGS 渲染真实世界森林 / 城市 / 室内走廊作为 *视觉前端*，把 *动力学* 留给 Isaac Gym / Aerial Gym / Gazebo 自带的刚体模拟器 — 是无人机 obstacle avoidance / VIO sim2real 在 2024-2025 的主流配方。

A drone RL policy needs millions of episodes; a manipulation policy needs thousands. **This structural fact is what makes drone 3DGS sim2real fundamentally different from manipulation Splat-Sim**: speed beats fidelity, the scene is rarely edited, and wind / aerodynamics will never come out of a gaussian renderer.

### X-Ray (non-expert friendly)

1. **The problem.** Drone obstacle-avoidance and VIO policies trained on plastic-looking Gazebo worlds fail outdoors — the visual statistics of real trees / brick / sky are far from rendered geometry.
2. **The trick.** Capture the actual flight environment with photogrammetry, fit a 3DGS scene, plug it as the *camera renderer* into Aerial Gym's massively parallel quadrotor simulator. The dynamics stays rigid-body PhysX; only the rendered pixels become real-distribution.
3. **Why a spatial-AI reader should care.** This is where 3DGS-as-simulator hits its highest-throughput customer (1000+ Hz across parallel envs) and where the cleanest separation between geometry/appearance and dynamics gets enforced — wind and prop wake come from a separate model.

### Research Landscape Timeline (X-Ray)

```
  2017─2020 ─ Flightmare / Gazebo / RotorS (plastic worlds; visual gap unsolved)
  2023.05 ── Aerial Gym (Kulkarni et al.): Isaac-based parallel quadrotor sim
  2023.07 ── 3DGS published
  2024.03─10 Splat-Nav, GS-Splatter, Aerial Gym + 3DGS: fit real scene → render
  2025 ───── Default config: 3DGS renderer + Isaac/Aerial Gym dynamics + ext. wind
  Open ───── Wind, prop wake, IMU noise still need external models;
              no gaussian renderer captures aerodynamics
```

---

## 1 · System Overview

### 1.1 Component Comparison vs Splat-Sim (manipulation sibling)

| | Aerial Gym + 3DGS (drone) | Splat-Sim (manipulation) |
|---|---|---|
| Scene scale | 100–10000 m² outdoor / large indoor | 1–3 m³ tabletop |
| Capture | Survey drone 5–15 min | Phone, 2–5 min |
| Render rate target | **1000+ Hz across parallel envs** | 30 Hz, single env |
| Parallelism | 256–4096 envs on one GPU | typically 1 env per GPU |
| Dynamics provider | Isaac Gym / PhysX | borrowed from teleop |
| Wind / aero model | **External plugin** (CFD-lite or empirical) | n/a |
| IMU noise model | External — Allan-variance based | n/a |
| Real-flight in loop | yes, zero-shot transfer | yes, grasp validation |
| Editability | low — scene rarely changes mid-training | low to medium |
| Compute budget `UNVERIFIED` | 8 GPUs × days per policy | 1 GPU × hours per policy |

### 1.2 Key Mechanism

The architectural commitment: **the 3DGS scene is treated as a static, read-only camera renderer**. It does not participate in dynamics, collision, or wind. Collision queries hit a separately exported mesh (TSDF / Poisson reconstruction from the gaussians), not the gaussians.

⚡ **Eureka Moment**: *3DGS solves the **visual** sim2real gap for drones. It does not pretend to solve the **dynamic** sim2real gap (wind, prop wake, ground effect) — those stay as separate external models, and that hygiene is what makes the combination shippable.*

### 1.3 Pipeline Flow

```
  survey drone / photogrammetry → 3DGS fit (30 min – 4 hr)
       ↓
  3DGS scene file (~5 GB) → export coarse mesh (collision proxy)
       ↓
  Aerial Gym env:
    - quadrotor PhysX dynamics  ← wind field model (external)
    - mesh collision            ← IMU noise model (external)
    - 3DGS render at cam pose
       ↓
  N parallel envs at 1000+ Hz aggregate → RL policy (PPO / SAC)
       ↓
  Real drone (zero-shot)
```

---

## 2 · Why a Drone Cannot Reuse the Manipulation Recipe

📌 **Napkin Formula**:
```
  Manipulation:  L = E_{view}[ policy(I_render(scene, view)) → action ]
                       (teleop labels survive; contact baked into demos)
  Drone:         L = E_{state}[ R(quadrotor(state, action, wind, IMU))
                               + π(I_render(scene, cam(state))) → action ]
                       (RL — actions invented online; dynamics must be live)
```

Two structural differences:

1. **No teleop label survives.** Splat-Sim trusts the teleop trajectory's contact outcome and re-renders only pixels. Drone RL invents actions online, so the simulator must produce correct *next states* — that's the dynamics model's job, not 3DGS's.
2. **Aerodynamics is unavoidable.** Prop wake, ground effect, gusts — none visible features; none inferable from a 3DGS scene. Must be added externally: learned wind field, empirical Dryden turbulence, or Gazebo aero plugins.

> Variables: `cam(state)` is the camera pose extracted from the quadrotor state; `R(·)` is the dynamics step.

---

## 3 · Worked Example: Urban Obstacle Avoidance

Task: train a quadrotor RL policy to fly through a real urban courtyard with brick walls, lamp posts, hanging signs.

1. **Capture.** Survey drone records 10 min RGB + GPS (~3000 frames).
2. **Reconstruct.** 3DGS fit → ~2M gaussians, ~5 GB scene. Export a 200k-triangle mesh as collision proxy.
3. **Wrap into Aerial Gym.** Mesh into PhysX; 3DGS into the rendering pipeline; spawn 1024 parallel quadrotor envs sharing the scene.
4. **Add external models.** Dryden turbulence peak gust 3 m/s. Allan-variance IMU noise (matched to MPU-9250 or BMI088). 20 ms first-order motor delay.
5. **Train.** PPO at 1000+ env-Hz aggregate, ~8 hours on 8× A100 (`UNVERIFIED`).
6. **Deploy.** Fly the real drone in the actual courtyard. Published results report 60–85% zero-shot success (`UNVERIFIED`), with unmodeled gusts the dominant remaining failure.

The visual distribution is matched exactly because the training scene *is* the test scene. This is "specialized policy with photometric scene replay" — more honest framing than "fully generalist policy."

---

## 4 · Engineering View

| Component | Why it lives where it does |
|---|---|
| 3DGS scene | Renders RGB only. Cannot serve collision queries (too dense, no clean surface). |
| Coarse mesh | Cheap collision; trades geometric fidelity (~10 cm) for microsecond queries. |
| Aerial Gym / Isaac dynamics | PhysX rigid body, optimized for 1000+ parallel envs / GPU. |
| Wind model | Empirical (Dryden) or learned. The data-hungry component. |
| IMU noise model | Allan variance + bias drift; must match deployment hardware. |
| RL update | Standard PPO / SAC. 3DGS rendering is 60–80% of step wall-clock. |

The bottleneck is rendering — the open research direction is *parallel batched 3DGS rasterization* across many envs that shares tile-level work rather than re-rasterizing the same scene N times.

---

## 5 · Data & Eval Conventions

Drone 3DGS sim2real papers typically report:

- **Same-scene zero-shot** success (highest, ~70–90%)
- **Cross-scene transfer** (~30–50%; photometric advantage erodes)
- On-board perception latency (~30–60 ms target)
- Collision rate per km flown

Honest reporting requires the cross-scene number. Several papers report only same-scene and overclaim generality.

---

## 6 · Capabilities & Failure Modes

**Works**: static obstacle avoidance in textured environments; VIO frontend training; sim2real for monocular depth / segmentation; specialized policies for known environments (industrial inspection, recurring delivery routes).

**Does not work**: generalist outdoor flight in unseen scenes; high-speed flight (>10 m/s) where motion blur / rolling-shutter dominate (3DGS renders perfect frames); indoor flight with dynamic actors (gaussians are static); wind-dominated regimes.

### 6.1 Hidden Assumptions

1. **Deployment environment = captured environment.** Most published wins are same-scene transfer. "sim2real" here means dynamics-real, not scene-real — the photometric advantage is scene-specific.
2. **Wind / turbulence / prop wake can be modeled externally.** When gusts dominate, no amount of 3DGS visual fidelity rescues the policy. Wind-field-randomized training becomes mandatory.
3. **Collision approximated by coarse mesh.** Thin obstacles (wire, foliage twigs) disappear in TSDF / Poisson proxies; the policy will fly into them in the real world.
4. **Rolling shutter, motion blur, lens distortion are negligible during training.** 3DGS renders ideal pinhole frames at infinite shutter. Real cameras at 10 m/s give very different statistics. Most production pipelines do not patch this.
5. **Non-visual sensors via external noise models.** Correct, but the integration burden falls on the simulator author; bugs in IMU modeling silently kill VIO sim2real.

---

## 7 · Comparison & Interview Tip

| | 3DGS in Aerial Gym | Pure Aerial Gym (no 3DGS) | Gazebo + textured terrain | NeRF in drone sim |
|---|---|---|---|---|
| Visual realism | ★★★★ | ★ | ★★ | ★★★★ (slow) |
| Render rate `UNVERIFIED` | 100–500 Hz/env | 1000+ Hz/env | 100 Hz/env | 1–10 Hz/env |
| Best when | scene known, visual gap dominant | dynamics tuning, no visual transfer | legacy stacks, SITL | research |

🎯 **Interview Tip**: When asked *"why use 3DGS in your drone sim instead of just better Gazebo textures?"*, do not answer "it looks better." Answer: **"3DGS gives me the *captured* visual distribution of the *specific* deployment environment. For specialized policies in known environments (inspection, recurring routes), 3DGS earns its compute; for generalist outdoor flight, neither saves us — the wind model and cross-scene generalization are the unsolved problems."**

---

## Boundary

Per-method 3DGS rasterization details → `foundations/3dgs-family/3dgs_original_dissection.md`. Per-embodiment aerial deployment, VIO, sensors → `embodiments/aerial/`. Cross-embodiment "manip vs drone vs AD 3DGS-sim" → `crossing/representation-migration/3dgs_as_simulator_comparison.md`. Inference-time world models for planning → `foundations/world-model/`.

## References

- Kulkarni et al., *Aerial Gym — Isaac Gym Simulator for Aerial Robots*, arXiv:2305.16510 (2023).
- Chen et al., *Splat-Nav: Safe Real-Time Robot Navigation in Gaussian Splatting Maps*, arXiv:2403.02751 (2024).
- Kerbl et al., *3D Gaussian Splatting*, SIGGRAPH 2023, arXiv:2308.04079.
- See also `crossing/representation-migration/3dgs_as_simulator_comparison.md`.

---

**Status:** v1 (2026-05-21). UNVERIFIED policy applies to all latency / success-rate / GPU-hour numbers.

[← Back to Generative 3D Sim](./README.md)
