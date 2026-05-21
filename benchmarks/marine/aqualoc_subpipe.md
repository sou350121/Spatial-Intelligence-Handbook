# AQUALOC, SubPipe, and the Marine SLAM Data Desert

**Status:** v1 — opinionated draft. Sequence counts and license details marked `UNVERIFIED`.
**TL;DR:** Marine SLAM has essentially three public datasets that anyone outside an ocean lab can use, and they exist *because nothing else does*. The visibility tier (clear water vs turbid vs ROV-pipeline) matters more than the algorithm. "Saturation" doesn't apply yet — there aren't enough methods competing on enough datasets.

---

## 1 · Why the marine data desert exists

Underwater data collection has four structural problems:

1. **Cost.** Field deployment requires a vessel + crew + ROV / AUV pilot. A single dataset season can cost six figures.
2. **Localization ground truth is hard.** GPS doesn't work; ground truth needs USBL / LBL acoustic positioning, which is its own integration project.
3. **Sharing is restricted.** A lot of marine survey data is owned by oil & gas operators or defense contractors and never gets released.
4. **Generalization is suspect.** A SLAM benchmark in Mediterranean clear water tells you almost nothing about a tannin-stained estuary.

Result: a handful of public datasets that academics share, each tied to a specific institution and rig.

---

## 2 · The three public datasets — comparison

| Dataset | Origin | Environment | Sensors | Ground truth | Size `UNVERIFIED` |
|---|---|---|---|---|---|
| **AQUALOC** | Toulon / IFREMER (France) | Harbor + archaeological site + deep sea | Mono camera + low-cost MEMS IMU + depth + (sometimes) sonar | Loop-closure based; no global ref | ~17 sequences |
| **SubPipe** | INESC TEC (Portugal) | ROV inspecting subsea pipeline | Stereo + IMU + DVL + USBL | USBL acoustic positioning | ~10 sequences |
| **Marine Robotics Dataset family** (e.g., FLSea, Tahoe, EuRoC-underwater attempts) | Various | Mixed | Mixed | Patchy | scattered |

These are the canonical three; most marine SLAM papers in 2023–2026 evaluate on AQUALOC + SubPipe + a few proprietary clips and call that the bar.

---

## 3 · The visibility tier — the axis nobody publishes

The thing that makes marine benchmarks *different* from terrestrial ones is that "the dataset" is really "the dataset at this visibility tier." A method that works on AQUALOC's clear-water harbor clip can fail outright on the same dataset's turbid sequence.

A pragmatic three-tier model:

| Tier | Visibility | Typical attenuation | What works | What fails |
|---|---|---|---|---|
| **Clear** | >10 m visibility (Mediterranean, tropical) | Mild blue-green absorption | Standard monocular / stereo VO with color correction | Long-range texture (still attenuated) |
| **Turbid** | 1–5 m (coastal, post-storm, estuary) | Strong scattering | Short-baseline stereo + DVL fusion | Monocular VO; long-baseline stereo |
| **ROV-pipeline / dark** | <1 m or active light dominated | Total ambient loss; sensor sees only what its light reaches | Active acoustic (sonar / DVL); proprioception; structured light short-range | Any passive RGB |

AQUALOC spans tiers 1 and 2 across its sequences. SubPipe is a tier 3 dataset (ROV inspection lighting + close range to pipe). Reporting "AQUALOC trajectory ATE" without saying which sequence is meaningless — the harbor clip and the deep-sea archaeology clip are different problems.

---

## 4 · Why "saturation" isn't the right question

Terrestrial SLAM benchmarks (EuRoC, TUM-RGBD, KITTI) saturated because dozens of methods competed on the same data over a decade. Marine SLAM doesn't have that density:

- Methods that report on AQUALOC in any given year: probably <10 `UNVERIFIED`.
- Methods that report on SubPipe: even fewer.
- The same lab often produces both the dataset *and* the SOTA method on it.

This is structurally different from the terrestrial "ScanNet++ saturated" problem. Marine SLAM is in an *exploration phase*, not a *saturation phase*. The right question is "does the method generalize across visibility tiers?", not "does it beat the leaderboard?"

A useful negative test: a paper that quotes AQUALOC numbers but doesn't show results on at least one turbid sequence is signaling that turbid is where it falls down. Most do.

---

## 5 · What this means for VGGT-class methods underwater

Tying this to the [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) thread: feed-forward 3D inherits whatever the monocular RGB front-end can see. Underwater that becomes:

- Tier 1 (clear): VGGT *might* run — but no marine VGGT paper exists yet `UNVERIFIED`.
- Tier 2 (turbid): featureless scattering kills any ViT encoder that wasn't trained on underwater scenes.
- Tier 3 (ROV / dark): not even a question.

This is why marine is the contrasting-case anchor in the VGGT-vs-VIO piece: it's the embodiment where the visual-only paradigm doesn't compete at all, full stop. Marine SLAM stacks are *acoustic first, visual auxiliary*, and that ordering is unlikely to flip on any 5-year horizon.

---

## 6 · The dataset-creation gap as a research opportunity

Marine SLAM's biggest unlock isn't a new architecture, it's *more datasets*. Specifically:

- Multi-tier visibility benchmarks (same scene, three water conditions).
- AUV swarm datasets (multi-agent SLAM underwater is barely benchmarked).
- Sonar-camera tightly-synced datasets with ground truth (most public sets sync poorly).
- Long-duration deployment data (10+ hour AUV missions reveal drift behaviors short clips hide).

For practitioners: if you have access to ocean / harbor time, *releasing a good marine dataset is currently a higher-leverage contribution than publishing a new method on the existing three*.

---

## 7 · Practical defaults for marine SLAM evaluation

If you have to evaluate a method, the 2026 pragmatic protocol is:

1. **AQUALOC**, all harbor + archaeology sequences — primary monocular / stereo test.
2. **SubPipe**, full set — DVL-fusion + acoustic test.
3. **One proprietary clip** — disclose institution, water conditions, ground-truth source. This is mandatory if you claim "real-world."
4. **Cross-tier ablation** — at minimum, report performance separately for clear vs turbid sequences. Aggregated numbers hide the failure mode.

Without this protocol, marine SLAM papers regress to the "EuRoC 100%" trap: optically benign sequences inflate the headline, and the field looks more solved than it is.

---

## Boundary

This doc compares public marine SLAM datasets. Per-method dissection (Aqua-SLAM, DVL-tightly-coupled VIO variants, sonar-camera fusion methods) goes to `embodiments/marine/`. Sensor physics (sonar imaging, DVL operating principles, underwater optics attenuation curves) lives in `foundations/sensor-physics/`. Cross-embodiment "visual-only ceiling" framing belongs in `crossing/`.

Cross-link: see `embodiments/marine/` for AUV / ROV stack architecture and the "why visual is auxiliary" discussion.

## References

- AQUALOC — Ferrera et al. *IJRR 2019*. https://arxiv.org/abs/1809.07076
- SubPipe — Álvarez-Tuñón et al. *IROS 2024*. https://arxiv.org/abs/2401.17907
- FLSea — Randall et al. https://sites.google.com/view/aquaslam (UNVERIFIED, no DOI yet for full collection)
- Underwater attenuation model (Akkaynak–Treibitz) — *CVPR 2018*. https://openaccess.thecvf.com/content_cvpr_2018/papers/Akkaynak_A_Revised_Underwater_CVPR_2018_paper.pdf
- BlueROV2 reference platform (most academic ROV data uses this rig) — https://bluerobotics.com/ (no DOI)
