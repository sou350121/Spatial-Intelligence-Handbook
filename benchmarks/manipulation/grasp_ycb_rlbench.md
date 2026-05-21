# GraspNet-1Billion, YCB, RLBench — What Each Actually Measures

**Status:** v1 — opinionated draft. Saturation rates and per-task success numbers marked `UNVERIFIED`.
**TL;DR:** These three are not interchangeable. GraspNet-1B scores *grasp planning on a point cloud*, YCB scores *the object set you grasp on*, RLBench scores *closed-loop task execution in a photorealistic sim*. Reporting "we beat SOTA" without saying which axis you tested is the single biggest source of inflated manipulation papers.

---

## 1 · Why the confusion exists

Manipulation benchmarks evolved separately and got pasted into the same tables. A 2024 paper that quotes "98% success on YCB" is almost certainly testing on a *subset* of YCB objects, in a *specific* gripper, often in *one* lab's tabletop setup, with the grasp planner from GraspNet-1B and motion execution either in real or in RLBench. None of those numbers compose linearly.

The fix is to look at what each benchmark actually evaluates — and what it deliberately ignores.

---

## 2 · The three axes — comparison

| Benchmark | What it evaluates | What it ignores | Modality | Year / Lineage |
|---|---|---|---|---|
| **GraspNet-1Billion** | Per-scene grasp pose quality (6-DoF) on cluttered point clouds | Whole-task execution, language conditioning, multi-step planning | RGB-D point cloud, simulation-validated grasps | 2020, SJTU (Fang et al.) |
| **YCB Object Set** | Object *coverage* — does your stack handle the canonical 77-object set? | Scene / clutter / task; it's an object library not a task suite | Physical 3D objects + meshes + textures | 2015 onward, IROS object/model set (Calli et al.) |
| **RLBench** | End-to-end task success across 100+ scripted manipulation tasks | Sim2real, true visual realism, novel object generalization | CoppeliaSim + photorealistic shaders | 2019, Imperial (James et al.) |

The key insight: **YCB is not a benchmark**, it's an *object set*. GraspNet-1B uses YCB-style objects but scores grasp poses. RLBench uses its own objects but scores tasks. Papers that say "evaluated on YCB" usually mean "evaluated grasping on objects from the YCB set" — which is closer to GraspNet-1B's axis than to a task benchmark.

---

## 3 · GraspNet-1Billion — what it actually does

GraspNet-1B provides ~1B annotated 6-DoF grasp poses across ~100 cluttered scenes captured with RealSense + Kinect. The benchmark protocol:

1. Input: RGB-D or point cloud of a cluttered tabletop.
2. Output: ranked list of 6-DoF grasp poses (gripper pose + width).
3. Score: top-K grasp success rate by force-closure simulation.

What this measures is **grasp candidate generation**. It does not measure:
- whether the arm can reach the pose without collision
- whether the controller executes the grasp without slip
- whether the right object was grasped (no language / target conditioning)

That's why GraspNet-1B numbers stay high (top methods cluster around 60–70% AP `UNVERIFIED`) while the same grasp planner deployed in a real cell often produces 20–30% task success. The benchmark deliberately decouples planning from execution.

**Use it for:** comparing grasp pose generators (GraspNet baseline, AnyGrasp, EconomicGrasp, etc).
**Do not use it for:** claiming "our system can manipulate."

---

## 4 · YCB — the object set that everyone shares

The Yale-CMU-Berkeley Object and Model Set (Calli et al. 2015) is 77 physical objects + meshes + textures + sizes spanning kitchen items, tools, food, and shape primitives. It exists because *before YCB, every manipulation paper used a different object set and nothing was comparable*.

YCB is the closest thing manipulation has to ImageNet — not in scale, but in role: a shared coordinate for "did your method generalize across realistic everyday objects?" Any paper that doesn't test on at least a YCB subset gets flagged as cherry-picked.

What YCB **does not** specify:
- a task
- a scene layout
- a success metric
- a sensor rig

Two papers can both claim "98% on YCB" and have tested completely different things. Always ask: which subset, which task, which gripper, which clutter.

There are derivative task suites — **YCB-Video** (object pose tracking), **YCB-Sim2Real** challenges, **YCBInEOAT** (in-hand manipulation) — that add structure on top of the object set.

---

## 5 · RLBench — the LIBERO problem, three years earlier

RLBench (James et al. 2019) packs 100+ manipulation tasks into CoppeliaSim with photorealistic shaders, language descriptions, and demonstration generation. It looks like the ideal benchmark for vision-language-action policies — and it is, *inside the sim*.

The sim2real cliff is brutal:

| Aspect | RLBench (sim) | Real lab |
|---|---|---|
| Visual realism | Photorealistic shaders | True multi-bounce lighting + sensor noise |
| Physics | CoppeliaSim Newton/Bullet | Real contact + friction + compliance |
| Object set | Procedural / hand-modelled | YCB / custom + manufacturing tolerance |
| Failure modes | None outside the sim's tolerance | Slip, partial occlusion, sensor dropout |

This is **the LIBERO problem rebranded**: a policy that scores 95% on RLBench routinely scores 20–40% on the same task in real `UNVERIFIED`. LIBERO (Liu et al. 2023) made the same architectural choice — sim that looks real but is physically thin — and the field has discovered the same cliff twice.

The diagnostic: if the paper reports RLBench numbers but no real-robot ablation, treat the headline number as an *upper bound on the policy's representational capacity*, not as a deployment readiness signal.

**RLBench earns its place** because it's the cheapest way to run policy ablations at scale (1000+ episodes per task per day). It just isn't a deployment proxy.

---

## 6 · How to read manipulation papers

When you see "98% success on benchmark X," parse the claim like this:

1. **Which axis?** Grasp planning (GraspNet-1B), object coverage (YCB-derived), task execution (RLBench / LIBERO / CALVIN), or real-robot?
2. **Subset reported?** YCB has 77 objects, RLBench has 100+ tasks, GraspNet-1B has 100 scenes. Papers cherry-pick.
3. **Sim or real?** Sim numbers do not transfer. Real numbers transfer poorly across labs.
4. **Cross-evaluated?** Does the same method get reported on ≥2 of these axes? If not, suspect over-tuning.

The high-quality manipulation papers in 2024–2026 report on *at least one sim benchmark plus one real-robot evaluation with a reproducible setup* (RT-2 lineage, Octo, OpenVLA). Treat that as the new bar.

---

## 7 · The saturation question

`UNVERIFIED` for all three, but: GraspNet-1B AP crept from ~30% (2020) to ~70% (2024 SOTA), plateau likely; RLBench top methods cluster near ceiling per-task — the harder bar is now multi-task generalization; YCB as an object set can't saturate, it's a coordinate not a metric. The migration is toward real-robot evaluation (RoboArena, RoboCasa real splits) and cross-embodiment policy benchmarks (Open X-Embodiment).

---

## Boundary

This doc compares the three benchmarks' scoring axes. Per-policy dissection (Diffusion Policy, ACT, OpenVLA, π₀) lives in `bridge-to-vla/` and in [VLA-Handbook](https://github.com/sou350121/VLA-Handbook) under policy benchmarks. Object-set engineering (gripper choice, fixture design) belongs in `deployment/`.

## References

- GraspNet-1Billion — Fang et al. *CVPR 2020*. https://arxiv.org/abs/2006.05400
- YCB Object and Model Set — Calli et al. *Adv. Robotics 2017*. https://www.ycbbenchmarks.com/
- YCB-Video — Xiang et al. *RSS 2018*. https://arxiv.org/abs/1711.00199
- RLBench — James et al. *RA-L 2020*. https://arxiv.org/abs/1909.12271
- LIBERO — Liu et al. *NeurIPS 2023*. https://arxiv.org/abs/2306.03310
- Open X-Embodiment — Padalkar et al. 2023. https://arxiv.org/abs/2310.08864
