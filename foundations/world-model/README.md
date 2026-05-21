# World Models · Decision-Useful Slice Only

**Status:** v1 — opinionated lane intro. UNVERIFIED policy applies to all benchmark / latency claims downstream.
**Scope tier:** W2 lane (Cosmos + Genie dissections graduate into W1 once we have real-world VLA training-data deltas measured).

---

World models are the most over-claimed category in 2025 spatial AI. The papers promise "simulators of reality"; the demos show beautiful video that drifts after 3 seconds. This handbook lane deliberately ignores ~70% of what gets pitched under the "world model" banner and keeps **only the slice that closes a loop into an embodied policy**. Two questions gate every entry here: (1) does it produce data, observations, or rollouts that a VLA / RL policy can actually consume? (2) does it survive the geometric / temporal sanity check that a robot will encounter? If the answer to either is no, the system belongs in a generative-media survey, not here.

The strict "decision-useful only" rule is inherited from the project PRD: *Genie Sim is in (it pumps trajectories into VLA training); Marble is mostly out (its target user is a human exploring a generated 3D scene, not a robot integrating depth)*. We dissect Cosmos for its sim2real generation path, Genie for its action-conditional inference-time planning surface, and Marble only for the depth-from-video / NVS slice that a policy could plausibly use as augmentation. Anything labeled "world model" that boils down to longer-context text-to-video gets the ❌ tag in our rating system and does not get a dissection.

| File | Tier | Decision-useful angle |
|---|---|---|
| `nvidia_cosmos_dissection.md` | W2 🔧 [WorldModel] | Robot-training data factory (sim2real video synthesis) |
| `genie_dissection.md` | W2 ⚡ [WorldModel] | Action-conditional planner at inference, not a data source |
| `marble_decision_view.md` | W3 📖 [WorldModel] | Depth-from-video + NVS for policy augmentation; consumer 3D scene gen explicitly excluded |

**Boundary**: per-method physics realism dissection lives in `foundations/physics/`; per-embodiment "did this actually help my VLA?" goes in `bridge-to-vla/` and `embodiments/manipulation/` once we have real measurements. Cross-method comparison across world-model families (Cosmos vs Genie vs UniSim vs DriveDreamer) belongs in `crossing/representation-migration/` — not duplicated into each dissection.

---

*Last lane review: 2026-05-21.*
