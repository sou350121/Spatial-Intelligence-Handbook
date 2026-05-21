# 3DSRBench vs BLINK — What "Spatial Reasoning" Actually Means in VLM Benchmarks (VLM 空间推理双基准对比)

> **发布时间**: 3DSRBench arXiv 2024 / BLINK ECCV 2024
> **基准名**: 3DSRBench · BLINK
> **核心定位**: 一句话回答 VLM 空间推理两个分开的问题 — 3DSRBench 测显式 3D 关系理解，BLINK 测一组视觉感知能力；两者不可互换。

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item dissection template 2026-05-21. Saturation claims `UNVERIFIED` where based on leaderboard skim.
**TL;DR:** 3DSRBench measures whether a VLM understands explicit 3D relations (depth ordering, orientation, size); BLINK measures whether a VLM can perform a grab-bag of *visual* perception tasks under a chat interface. Conflating them is the most common methodological mistake in 2025–2026 multimodal papers.

### X-Ray (non-expert friendly)

(a) Multimodal LLM (VLM) papers freely claim "spatial reasoning" — but the term means two different things: 3D-grounded relation understanding (behind / facing / depth-order) vs general visual perception (counting, matching, jigsaw). (b) 3DSRBench probes the first cleanly, BLINK probes the second across 14 sub-tasks. (c) For VLM evaluators: reporting only one is overclaiming; reporting BLINK *average* without sub-task breakdown is the most common 2026 mistake.

### 📍 Benchmark Evolution Timeline

```
VQAv2 2017 ─► GQA 2019 ─► MMMU 2023 ─► ★ BLINK ECCV 2024 ─► ★ 3DSRBench 2024 ─► metric-3D-VQA? 2027?
                              │                │                  │
                              │                │                  └── explicit 3D relations
                              │                └── 14 perception sub-tasks
                              └── text-heavy multimodal (where VLMs win)
```

BLINK + 3DSRBench together exposed that VLMs near-human on text-heavy MMMU drop below specialist CV models on perception + 3D; the community is now learning to read both.

### ⚡ Eureka Moment

**"Spatial reasoning" is two questions, not one.** A VLM can excel at *image-plane visual perception* (BLINK average) while failing at *3D-grounded relation understanding* (3DSRBench depth ordering). The benchmark that proves one is silent about the other; conflating them is the methodological tell of 2025–2026 multimodal papers.

### 📌 Napkin Formula

```
VLM spatial-reasoning claim valid ⇔ (3DSRBench per-category) ∧ (BLINK relative-depth + spatial-relations sub-tasks)
                                                      ─ average alone is insufficient ─
```

---

## 1 · Why these two together

A multimodal LLM that claims "spatial reasoning" should answer two distinct questions:

- **Q1 (3D):** does the model understand that *behind*, *taller*, *facing toward me*, *closer to camera* are 3D-grounded predicates, not text-pattern guesses?
- **Q2 (2D visual perception):** can the model do the low-level visual tasks a CV pipeline would do (counting, correspondence, depth ordering, jigsaw, relative reflectance)?

3DSRBench is the cleanest public probe for Q1. BLINK is the cleanest public probe for Q2 (with some Q1 overlap). Reporting only one and claiming spatial intelligence is overclaiming.

---

## 2 · 3DSRBench (Ma et al. 2024)

**Construction.** Curated VQA over real images with 3D-relation annotations: depth ordering, orientation, size comparison, "is A behind B". Questions are designed to be unanswerable by text-only priors — the image must be consulted, and specifically its 3D structure.

**Why it's harder than it looks.** Standard VQA (VQAv2, GQA) leak text priors — a model that has never seen the image hits competitive numbers via question statistics. 3DSRBench breaks that.

**What it measures.** Depth ordering (sort by depth-from-camera), orientation (object facing direction in 3D), size (relative / metric across depth), relative position ("behind / left-of / above" in 3D, not image plane).

**Saturation 2026.** Frontier VLMs (GPT-4o-class, Claude 3.5+, Gemini 2.x) have made large gains but human gap is substantial `UNVERIFIED — last table 2026-Q1`. Not saturated. Specialist 3D-grounded VLMs (depth / pointmap ingest) measurably beat RGB-only chat VLMs.

**Limitations.** Static images only (no video / temporal). Camera-centric framing — "behind" is camera POV, not ego-centric robot framing. Clean scenes — cluttered industrial / outdoor underrepresented.

---

## 3 · BLINK (Fu et al. *ECCV 2024*)

**Construction.** 14 sub-tasks covering visual perception capabilities that classical CV models solve directly but VLMs often don't: relative depth, spatial relations, jigsaw, art style, IQ test, visual correspondence, semantic correspondence, multi-view reasoning, object localization, forensic detection, counting, relative reflectance, visual similarity, and functional correspondence.

**Why it caught on.** It exposed a sharp gap — VLMs that score near-human on text-heavy MMMU drop to *below specialized small models* on BLINK perception tasks. That gap is the diagnostic.

**What it measures.**

| Sub-task class | Classical CV equivalent |
|---|---|
| Relative depth | Monocular depth estimation |
| Spatial relations | Scene graph parsing |
| Visual / semantic correspondence | Feature matching |
| Jigsaw / multi-view | Implicit 3D reasoning |
| Counting / localization | Detection / segmentation |
| Forensic / reflectance | Low-level intrinsic image |

**Saturation status (2026).** Mixed. Frontier VLMs have closed much of the gap on relations / correspondence / counting; relative-reflectance and forensic-detection remain weak `UNVERIFIED`. Benchmark is not saturated overall but several sub-tasks individually approach ceiling.

**Limitations.**

- Multiple-choice format inflates scores relative to free-response
- 14 sub-tasks averaged into a single number hide which capabilities actually improved
- Limited spatial 3D coverage — most BLINK tasks live in image-plane perception, not metric 3D

---

## 4 · Side-by-side comparison

| Axis | 3DSRBench | BLINK |
|---|---|---|
| Year | 2024 | 2024 (ECCV) |
| Focus | Explicit 3D relations | Broad visual perception (14 tasks) |
| Saturation 2026 | not saturated `UNVERIFIED` | mixed; partial sub-task saturation `UNVERIFIED` |
| Image domain | Real photos, scene-centric | Mixed: photos, art, jigsaw, forensic |
| Text-prior leakage risk | Low (by design) | Medium (some sub-tasks) |
| Tests metric depth understanding | ✅ | ⚠️ relative only |
| Tests orientation | ✅ | partial |
| Tests counting / correspondence | ❌ | ✅ |
| Tests video / temporal | ❌ | ❌ |
| Useful for "is my VLM 3D-aware?" | ✅ canonical | partial |
| Useful for "is my VLM a good visual perceiver?" | partial | ✅ canonical |

---

## 5 · What they actually measure (the part that gets conflated)

The common mistake: a paper reports "+5 on BLINK" and concludes "our model has better spatial reasoning". BLINK's spatial-relation sub-task is one of 14; gains there are diluted into the average. To claim spatial reasoning specifically, the paper should report:

- **3DSRBench overall** + per-category breakdown (depth ordering vs orientation vs size)
- **BLINK relative-depth + spatial-relations sub-tasks** specifically (not the average)
- Ideally a metric-3D probe (depth estimation on NYUv2 / DIODE) to ground the claim

Conversely, a paper that gains only on 3DSRBench but not on BLINK perception sub-tasks is probably overfitting to 3D relations without improving general perception — also worth flagging.

---

## 5.5 · Worked example — auditing a "spatial reasoning" VLM paper

Paper claims "+5 on BLINK, strong spatial reasoning":

1. **3DSRBench with per-category** — absent? "spatial reasoning" likely = "BLINK average up".
2. **BLINK sub-task drill-down** — +5 on relative-depth + spatial-relations, or diluted across counting / forensic / art-style?
3. **Metric-3D probes** (NYUv2 / DIODE)? — grounds claim in 3D, not VQA framing.
4. **RGB-only vs depth/pointmap-ingest** — if 3D-grounded variant doesn't beat own RGB-only on 3DSRBench, 3D ingestion isn't doing work.
5. **Embodied transfer** (manipulation / nav SR) — neither benchmark guarantees; see `bridge-to-vla/`.

Five minutes; most 2025–2026 "spatial reasoning" claims fail steps 1 or 2.

---

## 6 · What's missing from both

Neither benchmark tests **ego-centric / embodied** 3D reasoning ("which way should I move to face the chair"), **video / temporal** reasoning (object permanence, causal scene dynamics), **metric scale** (both predict answer classes, not "depth in meters"), or **action-conditioned** spatial reasoning (reachability given affordances). A 3DSRBench + BLINK winner is *not* guaranteed to be a useful embodied spatial reasoner. See `bridge-to-vla/` for that side of the contract.

---

## 6.5 · Hidden Assumptions

Assumptions that, when violated, make scores misleading:

- **MCQ format** — free-response would drop scores 10–20% `UNVERIFIED` and reorder leaderboards.
- **Camera-centric framing** — embodied robots use ego-centric, different conventions.
- **Static single-image** — video / temporal / object permanence untested.
- **Web photography bias** — industrial, medical, aerial, AR-VR underrepresented.
- **Ordinal answer classes** — neither asks "depth in meters".
- **Single-step reasoning** — multi-hop spatial reasoning absent.
- **No action conditioning** — affordance / reachability untested.
- **English-only** — multilingual spatial conventions untested.

---

## 6.6 · Interview Tip

When asked "is my VLM spatially intelligent?" — give a two-sentence answer: "3DSRBench (with per-category breakdown) for 3D-relation grounding + BLINK *specific sub-tasks* (relative-depth, spatial-relations — not the average) for visual perception. The single-number claim is what reviewers are starting to reject in 2026." Bonus: note that neither benchmark guarantees embodied transfer (manipulation / nav success); call them necessary-but-not-sufficient.

---

## 7 · 2-year outlook

By 2027 frontier VLMs will likely saturate BLINK's perception sub-tasks and the community will move to per-sub-task reporting (already happening in 2026 papers). 3DSRBench will get a successor with video + ego-centric framing. A "metric-3D VQA" benchmark with depth-in-meters answers is overdue; whoever ships it owns the next two years.

**Falsifiable prediction:** before 2027-06 a paper will explicitly demonstrate that gains on BLINK do *not* transfer to embodied 3D tasks (manipulation, navigation success rate), and the community will stop using BLINK-average as a spatial-reasoning claim.

---

## For the reader

- **VLM researcher claiming spatial reasoning** — report both with sub-task breakdowns; the single-number era is ending.
- **Embodied / VLA researcher** — neither benchmark is sufficient signal for downstream success. Necessary but not sufficient gates.
- **Reviewer** — "+X on BLINK" without sub-task breakdown is a flag.

---

## References

- 3DSRBench — Ma et al. 2024. https://arxiv.org/abs/2412.07825
- BLINK — Fu et al. *ECCV 2024*. https://arxiv.org/abs/2404.12390 · https://zeyofu.github.io/blink/
- Related: MMMU — Yue et al. *CVPR 2024*. https://arxiv.org/abs/2311.16502 (the text-heavy benchmark BLINK was designed to contrast with)
- Cross-ref: `bridge-to-vla/` for embodied spatial-reasoning contract; `foundations/feed-forward-3d/` for models that ingest 3D explicitly.

## Boundary

This doc compares two benchmarks at the protocol + saturation level. Per-VLM scorecards belong in model-specific dissection docs under `foundations/` or `companies/`. Embodied spatial reasoning (robot success rate) is a different evaluation and belongs in `benchmarks/manipulation/` or `bridge-to-vla/`.

---

*Last opinion update: 2026-05-21. v1.1 — backfilled to AGENTS.md 14-item template.*
