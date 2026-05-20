# Embodiments · 各 embodiment 应用层

Per-embodiment SOTA stack + the spatial-specific problems each one owns alone. Drone is depth-prioritized (maintainer anchor); marine intentionally light (contrasting case > coverage).

| Subdirectory | Scope | Depth tier |
|---|---|---|
| `manipulation/` | Desktop / grasping / bimanual / humanoid upper-body | Major |
| `humanoid-legged/` | Whole-body locomotion + spatial reasoning | Major |
| `ground-mobile/` | AGV / indoor / VLN (HM3D, ObjectNav benchmarks) | Major |
| `driving/` | BEV / occupancy / Cosmos / Wayve GAIA | Major (with care: not an AD survey) |
| `aerial/` ★ | Drone — VIO / obstacle avoidance / active tracking / on-board 3DGS / event camera / swarm | **First among equals (1.5–2× depth)** |
| `marine/` | AUV / USV / sonar / underwater visual degradation | Minor — stress-test case |

AR/VR (Vision Pro / Quest) and space robotics: see boundary rules in root README.
