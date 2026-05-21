# Neural Map as Memory for VLA Agents

**Status:** v1 — opinionated draft. Production-deployment claims (Figure, 1X) marked `UNVERIFIED`.
**Wedge tier:** W1 · **Handbook flagship bridge doc**
**TL;DR:** LLM context windows can't hold a kitchen layout. Neural maps — SemanticSLAM-style metric-semantic graphs, 3DGS as scene memory, scene-graph-as-text — are the long-horizon memory substrate VLA agents actually need. The hard part isn't building the map; it's making it **queryable** by a language policy in <100 ms.

---

## 1 · The long-horizon problem

Today's VLA policies are good for ~30-second horizons. Anything longer — "make breakfast," "tidy the living room," "find my keys" — hits a memory wall: the RGB context the policy sees is one frame or a short window; the LLM context is gigantic in tokens but *terrible at spatial layout* (a list "fridge | sink | drawer | drawer | counter" loses geometry); a real kitchen / warehouse has hundreds of instances and dozens of meters that don't fit in context. The fix is **external memory** — a persistent spatial representation the agent can query. Three lineages compete.

---

## 2 · The three neural-map lineages

| Lineage | Origin | Memory form | Query | Update cost |
|---|---|---|---|---|
| **SemanticSLAM** | KIMERA / Hydra / Clio (MIT 2019–2024) | Metric-semantic scene graph (objects/places + relations) | Graph + spatial search | Online during exploration |
| **3DGS as memory** | 3DGS (Kerbl 2023); LERF; Splatam | Dense neural scene (Gaussians + features) | Render-and-attend / feature lookup | Heavy per-scene fit; incremental WIP |
| **Scene-graph-as-text** | SayPlan, ConceptGraphs (2023) | Textual / JSON graph as LLM context | Direct LLM lookup | Cheap text; structure tracked aside |

They aren't competing for the same niche — they compete for the same *role* (long-horizon memory), trading off three axes: **query latency, spatial fidelity, language compatibility**.

---

## 3 · The "memory must be queryable" requirement

A working long-horizon VLA needs to answer four kinds of question against memory in real time: (Q1) **"Where is X?"** — semantic instance lookup; (Q2) **"What's between me and X?"** — geometric traversability; (Q3) **"Is the state of X still valid?"** — temporal freshness; (Q4) **"What does this look like from a new viewpoint?"** — view synthesis. Each lineage answers different subsets well:

| | SemanticSLAM | 3DGS memory | Scene-graph-as-text |
|---|---|---|---|
| Q1 instance lookup | ✅ native | ⚠️ needs feature | ✅ if recorded |
| Q2 traversability | ✅ metric map | ✅ via density | ❌ text loses geometry |
| Q3 freshness | ✅ timestamped | ⚠️ refit expensive | ✅ if LLM updates |
| Q4 view synthesis | ❌ | ✅ native | ❌ |
| LLM-native query | ❌ adapter | ❌ adapter | ✅ native |
| Update on the fly | ✅ designed | ⚠️ incremental WIP | ✅ trivial |

Nothing covers all four. **The deployable architecture is hybrid: SemanticSLAM backbone (Q1+Q2+Q3) + optional 3DGS overlays (Q4) + scene-graph-as-text projection for the LLM front-end.** Roughly what Clio + LLM-grounded planners are converging on.

---

## 4 · The latency budget

Long-horizon VLA won't tolerate a 5-second scene-graph query. Practical budgets `UNVERIFIED`: Q1 instance lookup <50 ms (asked mid-action); Q2 path-feasibility <200 ms (pre-planning); Q3 freshness <100 ms (pre-reuse); Q4 view synthesis 200–1000 ms (offline / pre-plan). This rules out **naive LLM-over-text** for Q1 / Q3 — LLM inference is too slow. The text scene graph has to be *indexed* (vector search + structured key lookup), not dumped into context.

---

## 5 · Where each lineage actually wins

- **SemanticSLAM (Hydra / Clio)**: wins where geometric precision matters and the agent needs to localize (kitchen / warehouse / lab). Metric backbone gives traversability + instance localization for free. Weak at view synthesis and language-native queries (needs a wrapper).
- **3DGS as memory**: wins where imagining viewpoints helps — manipulation pre-grasp, cluttered nav, AR. LERF-style language-feature attachment makes it semantic-queryable at a cost; per-scene fitting still expensive in 2026, feed-forward 3DGS may flip this in ~12 months.
- **Scene-graph-as-text**: wins for high-level planning where the agent reasons in language and geometry can be coarse (SayPlan, ConceptGraphs for household). Falls apart for fine geometric manipulation.

The 2026 deployment pattern (Figure / 1X, `UNVERIFIED`): SemanticSLAM-style metric-semantic backbone + scene-graph-as-text projection for the LLM planner + 3DGS-style local memory for manipulation hotspots. Nobody is shipping pure-3DGS or pure-text.

---

## 6 · The two-end contract with VLA

Spatial side provides: metric-semantic scene graph (instances + locations + relations + timestamps), optional local 3DGS patches for manipulation hotspots, coordinate-frame guarantees aligned with the policy's action frame, update API ("object X moved to Y at t"). VLA side provides: structured query interface (Q1/Q2/Q3) + free-text fallback, memory write-back ("I picked up X"), long-horizon planner that decomposes goals into queries.

The **missing contract** in 2026: a canonical scene-graph schema (object / place nodes, relation edges) both libraries agree on (every paper defines its own); a versioned scene-state handoff for "what's changed since t"; a confidence / decay channel so the planner knows how stale a fact is. This is exactly the cross-handbook coordination wedge to track with [VLA-Handbook](https://github.com/sou350121/VLA-Handbook).

---

## 7 · Where this breaks

Three failure modes: (1) **Stale memory** — agent acts on a fact that no longer holds; fix: short TTL + re-perceive before critical actions. (2) **Map drift** — long missions degrade metric coords; fix: VGGT-class loop-closure as global anchor (see `crossing/slam-vio-migration/vggt_vs_drone_vio.md`). (3) **Language-grounding mismatch** — LLM asks "blue mug" but graph stored `mug_07 {color:cyan}`; fix: embedding match. Known fixes; difficulty is engineering them under the latency budget.

---

## 8 · 2-year outlook + falsifiable prediction

By 2027 the field will have: a converged scene-graph schema (ConceptGraphs / Clio lineage); incremental 3DGS cheap enough to serve as online memory for manipulation hotspots; a standard "memory-aware VLA" benchmark (current long-horizon benchmarks like ALFRED / Behavior-1k are *not* memory-evaluating).

**Falsifiable prediction:** before 2027-12, a published humanoid VLA stack (Figure / 1X / lab equivalent) uses a Clio-lineage scene graph as primary long-horizon memory and demonstrates a >5-minute kitchen task with explicit memory queries handling object-moved-since-last-seen cases. Bet against any claim that LLM context alone (no external map) reaches multi-minute kitchen tasks at >50% success.

---

## Boundary

Compares neural-map lineages at the *memory-substrate* level for VLA. Per-method dissection (Hydra, Clio, LERF, ConceptGraphs papers) → `foundations/semantic-3d/` + `foundations/3dgs/`. Policy-side consumption → [VLA-Handbook](https://github.com/sou350121/VLA-Handbook). Feature-pipeline engineering → [`feature-cloud-to-action.md`](./feature-cloud-to-action.md). 3D-aware VLA arch → [`3d_aware_vla.md`](./3d_aware_vla.md).

## References

- Hydra (online metric-semantic SLAM) — Hughes et al. *RSS 2022*. https://arxiv.org/abs/2201.13360
- Clio (task-driven open-set scene graphs) — Maggio et al. 2024. https://arxiv.org/abs/2404.13696
- KIMERA — Rosinol et al. *ICRA 2020*. https://arxiv.org/abs/1910.02490
- 3DGS — Kerbl et al. *SIGGRAPH 2023*. https://arxiv.org/abs/2308.04079
- LERF — Kerr et al. *ICCV 2023*. https://arxiv.org/abs/2303.09553
- ConceptGraphs — Gu et al. *ICRA 2024*. https://arxiv.org/abs/2309.16650
- SayPlan — Rana et al. *CoRL 2023*
- Behavior-1K — Li et al. *CoRL 2022* `UNVERIFIED canonical`
