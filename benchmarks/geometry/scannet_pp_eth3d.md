# ScanNet++ vs ETH3D — The Two Indoor Geometry Benchmarks Everyone Cites Wrong

**Status:** v1 — opinionated draft. Saturation claims marked `UNVERIFIED` where based on leaderboard skim, not full rerun.
**TL;DR:** ScanNet++ is the *novel-view synthesis* benchmark people accidentally use as a SLAM benchmark; ETH3D is the *SLAM / MVS* benchmark people accidentally use as a NVS benchmark. They are not interchangeable, and a paper that reports one but not the other is usually hiding a weakness.

---

## 1 · Why pair these two

Indoor geometry has two failure modes nobody talks about together:

- **Photometric** — does the rendered novel view look like the real image (NVS, 3DGS, NeRF lineage)
- **Geometric** — is the reconstructed pose / depth / mesh metrically correct (SLAM, MVS, VIO lineage)

A method can win one and lose the other. ScanNet++ rewards photometric quality at the millimeter scale; ETH3D rewards geometric accuracy across staged trajectories. Reading the two side-by-side is the cleanest way to tell whether a paper's claim is about *appearance* or about *geometry*.

---

## 2 · ScanNet++ (Yeshwanth et al. *ICCV 2023*)

**The rig.** A faro-class laser scanner ground-truth + DSLR captures + iPhone RGB-D streams, registered into a unified coordinate frame. The combination is the point — earlier ScanNet relied on Kinect-class depth which capped reconstruction error around 1–2 cm; ScanNet++ pushes sub-millimeter laser GT plus high-resolution DSLR appearance.

**The labeling protocol.** Dense 3D semantic labels at instance level, ~1000 categories, ~460 scenes at first release `UNVERIFIED — exact scene count varies by version`. The labels are propagated from 3D back to 2D, so semantic segmentation is consistent across views — this is the key feature that made it the default for indoor NVS + open-vocabulary 3D work.

**Why it became the de-facto indoor NVS benchmark.**

| Property | Why it matters for NVS |
|---|---|
| Sub-mm laser GT | Lets you separate rendering error from geometry error |
| DSLR appearance | High-frequency texture forces models to actually render, not blur |
| Held-out novel views | Train/test split is on cameras, not just held-out pixels |
| Diverse scenes | Office / apartment / studio mix — less homogeneous than Replica |

By 2026 every 3DGS / feed-forward 3D paper reports PSNR / SSIM / LPIPS on ScanNet++. VGGT, MASt3R, π³, DUSt3R all benchmark here.

**Known issues (read these before believing a number).**

- **Saturation.** PSNR on ScanNet++ "Image" track has crept past 28 dB on top methods `UNVERIFIED — leaderboard skim 2026-Q1`. Headroom is thin enough that ordering between top-5 methods is within noise of test-time augmentation choices.
- **Train-test leakage rumors.** Community chatter (Reddit, Twitter) has flagged near-duplicate scene fragments across train / test splits `UNVERIFIED — no published audit`. Treat marginal improvements skeptically.
- **DSLR-only LPIPS is misleading.** Methods optimized on iPhone-class images underperform on DSLR test views in ways that don't reflect deployment reality.
- **No motion.** All captures are quasi-static. Anything claiming temporal-consistency wins from ScanNet++ alone is overclaiming.

---

## 3 · ETH3D (Schöps et al. *CVPR 2017*)

**The rig.** Synchronized stereo + laser scanner GT, captured with deliberate trajectory diversity (training / test splits across "high-res multi-view", "low-res many-view", "stereo"). The slow / fast trajectory variants are the load-bearing piece — they actually exercise SLAM front-ends.

**Why SLAM people care.**

- Trajectory ground-truth is laser-derived, not external mocap, so it's valid at the construction-site scale ETH3D is sampled from
- The SLAM track includes deliberately *hard* lighting (dim corridors, outdoor-indoor transitions) — ScanNet++ does not stress this
- Long sequences, real motion, real loop closure opportunities

**What ETH3D measures that ScanNet++ doesn't.**

| Capability | ScanNet++ | ETH3D |
|---|---|---|
| Novel-view PSNR | ✅ canonical | ⚠️ possible but not standard |
| Trajectory error (ATE) | ⚠️ derivable | ✅ canonical |
| MVS completeness / accuracy | ⚠️ partial | ✅ canonical |
| Loop closure stress | ❌ minimal | ✅ moderate |
| Lighting / exposure variation | ❌ benign | ✅ deliberate |

**Saturation status.** SLAM track ATE is below 1 cm for top methods on most sequences `UNVERIFIED — last full table inspected 2026-Q1`. The benchmark is closer to a regression suite than a frontier in 2026 — but that's still the cleanest indoor SLAM number you can publish.

---

## 4 · Side-by-side: what each one secretly measures

| Question | Ask ScanNet++ | Ask ETH3D |
|---|---|---|
| Can my method render a held-out view? | ✅ | ❌ not its job |
| Is my pose estimate metrically correct? | ⚠️ weak signal | ✅ |
| Does my front-end survive dim corridors? | ❌ | ✅ |
| Does my reconstruction look photoreal at 4K? | ✅ | ❌ low-res tracks |
| Does my method generalize across scenes? | ✅ ~460 scenes | ⚠️ ~25 scenes |

The diagnostic: if a 3DGS paper reports only ScanNet++, they're claiming an *appearance* win and probably haven't tested geometry. If a SLAM paper reports only ETH3D, they're claiming a *trajectory* win and probably can't render. Demand both for any feed-forward 3D claim that wants to span both regimes (VGGT-class).

---

## 5 · What to use when

- **Indoor NVS / 3DGS / feed-forward 3D appearance** → ScanNet++ (mandatory in 2026)
- **Indoor SLAM / VIO trajectory** → ETH3D + EuRoC (see `benchmarks/aerial/euroc_uzh_fpv_hilti.md`)
- **MVS dense reconstruction** → ETH3D (high-res multi-view track) + Tanks & Temples
- **Open-vocabulary 3D semantic** → ScanNet++ (its labels are the moat)
- **Cross-method comparison spanning appearance + geometry** → both, side-by-side

---

## 6 · 2-year outlook

ScanNet++ saturation is going to force one of two things by 2027: a v2 with explicit train/test scene-fragment audit + harder splits, or a new indoor benchmark with native dynamic content + lighting changes (ARKit-Scenes is the closest existing candidate; its GT is weaker). ETH3D will keep being cited because it's the only public indoor benchmark with laser GT on long real trajectories.

**Falsifiable prediction:** before 2027-06 a top-conference paper will publish a ScanNet++ train/test leakage audit, and the post-audit leaderboard will shuffle the top-5 by ≥2 positions.

---

## For the reader

- **NVS / 3DGS researcher** — report ScanNet++ but also a non-saturated benchmark (Tanks & Temples or custom set). Reviewers are catching on.
- **SLAM researcher** — ETH3D + EuRoC + KITTI is the canonical triple. ScanNet++ trajectory error is not ETH3D trajectory error.
- **Feed-forward 3D researcher** — report both. Anything else looks like cherry-picking.

---

## References

- ScanNet++ — Yeshwanth et al. *ICCV 2023*. https://arxiv.org/abs/2308.11417
- ETH3D — Schöps et al. *CVPR 2017*. https://www.eth3d.net/ · https://openaccess.thecvf.com/content_cvpr_2017/papers/Schops_A_Multi-View_Stereo_CVPR_2017_paper.pdf
- ScanNet (original, for context) — Dai et al. *CVPR 2017*. https://arxiv.org/abs/1702.04405
- Cross-ref: `crossing/slam-vio-migration/vggt_vs_drone_vio.md` for why benchmark numbers don't translate to drone deployment.

## Boundary

This doc compares two benchmarks at the protocol level. Per-method deep dives (how VGGT does on ScanNet++, how DROID-SLAM does on ETH3D) live in `foundations/feed-forward-3d/` and `embodiments/<x>/slam/` respectively. Indoor real-world deployment gap discussion belongs in `deployment/failure-modes/`.

---

*Last opinion update: 2026-05-21. Saturation claims to be reverified at next leaderboard refresh.*
