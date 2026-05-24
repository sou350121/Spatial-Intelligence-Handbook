#!/usr/bin/env python3
"""Inject 5-axis ontology headers into every dissection markdown.

5 軸 (problem / representation / sensor / paradigm / time) 是 ontology v2 的核心。
本腳本根據人工 audit (參考 ontology.md §7 cross-axis table + 內容判讀) 將每篇
dissection 標上 ontology 座標，注入 HTML comment header（Mintlify 渲染時不可見，
但 audit 可 grep）。

Format:
    <!-- ontology-5axis
    problem: VSLAM + Reloc + MultiSession
    representation: SparseLandmarks + KeyframeGraph + Atlas
    sensor: Mono | Stereo | RGBD; IMU optional
    paradigm: Geometric-Indirect + BA + DBoW2
    time: Incremental-Smoother
    ref: ../../cheat-sheet/ontology.md §7
    -->

Run from repo root:
    python3.11 scripts/inject_ontology_headers.py
"""

from __future__ import annotations
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# 5-axis classifications (manually curated against ontology.md v2)
# Key: filename relative to repo root
# Value: dict with 5 axes
CLASSIFICATIONS: dict[str, dict[str, str]] = {
    # ----- Aerial VIO -----
    "embodiments/aerial/vio/openvins_dissection.md": {
        "problem": "VIO",
        "representation": "Sparse + 21-state augmented (含 IMU bias + cam intrinsic)",
        "sensor": "Mono / Stereo + IMU",
        "paradigm": "Filter-MSCKF (null-space projection)",
        "time": "Filter-Streaming",
    },
    "embodiments/aerial/vio/vins_mono_fusion_dissection.md": {
        "problem": "VI-SLAM (含 loop closure) + GPS fusion",
        "representation": "Sparse landmarks + IMU bias + Marginalization prior",
        "sensor": "Mono + IMU + GNSS optional",
        "paradigm": "Geometric-FactorGraph + Ceres",
        "time": "FixedLag-Smoother",
    },
    "embodiments/aerial/vio/droid_slam_dissection.md": {
        "problem": "VO / VSLAM",
        "representation": "Dense flow + pose graph",
        "sensor": "Mono + IMU optional",
        "paradigm": "Hybrid-LearnedFE + Diff-BA layer",
        "time": "Online (GPU 需)",
    },
    "embodiments/aerial/vio/ekf_from_scratch_dissection.md": {
        "problem": "VIO (教學 baseline)",
        "representation": "15-state / 21-state vector + covariance",
        "sensor": "IMU + Camera",
        "paradigm": "Filter-EKF",
        "time": "Filter-Streaming",
    },
    "embodiments/aerial/planning/min_snap_dissection.md": {
        "problem": "Trajectory generation (aerial)",
        "representation": "Polynomial pieces + waypoints",
        "sensor": "NoSensor (planner)",
        "paradigm": "Geometric-Optimization (QP)",
        "time": "Offline",
    },
    "embodiments/aerial/event-camera/event_camera_for_aerial_dissection.md": {
        "problem": "VO + ObstacleAvoidance + PointTracking (high-speed / low-light)",
        "representation": "Sparse event stream",
        "sensor": "Event camera (DVS) + IMU",
        "paradigm": "Event-driven classical + Learned",
        "time": "Streaming async",
    },
    # ----- foundations / classical-slam -----
    "foundations/classical-slam/orb_slam3_dissection.md": {
        "problem": "VSLAM + Reloc + MultiSession (Atlas)",
        "representation": "Sparse landmarks + Keyframe graph + Atlas multi-map",
        "sensor": "Mono / Stereo / RGB-D + IMU optional",
        "paradigm": "Geometric-Indirect + BA + DBoW2",
        "time": "Incremental-Smoother",
    },
    # ----- foundations / 3dgs-family -----
    "foundations/3dgs-family/3dgs_original_dissection.md": {
        "problem": "Novel-view synthesis / Reconstruction",
        "representation": "N×Gaussian primitives (μ, Σ, SH, α)",
        "sensor": "RGB + poses (from COLMAP)",
        "paradigm": "Hybrid-DiffRender (Gaussian rasterize + GD)",
        "time": "PerScene-Optimization",
    },
    "foundations/3dgs-family/gs_slam_dissection.md": {
        "problem": "VSLAM + Reconstruction (Gaussian-based)",
        "representation": "3DGS + camera tracking",
        "sensor": "RGB-D / Mono",
        "paradigm": "Hybrid-DiffRender + tracking",
        "time": "Online (per-scene incremental)",
    },
    # ----- foundations / nerf-family -----
    "foundations/nerf-family/nerf_original_dissection.md": {
        "problem": "Novel-view synthesis",
        "representation": "Implicit MLP radiance field",
        "sensor": "RGB + poses",
        "paradigm": "Hybrid-DiffRender (MLP + volume rendering)",
        "time": "PerScene-Optimization",
    },
    "foundations/nerf-family/mip_nerf_360_dissection.md": {
        "problem": "NVS unbounded scene",
        "representation": "NeRF + IPE (integrated positional encoding)",
        "sensor": "RGB + poses",
        "paradigm": "Hybrid-DiffRender",
        "time": "PerScene-Optimization",
    },
    "foundations/nerf-family/instant_ngp_dissection.md": {
        "problem": "NVS / Reconstruction",
        "representation": "Multi-resolution hash grid + tiny MLP",
        "sensor": "RGB + poses",
        "paradigm": "Hybrid (explicit hash + MLP decoder)",
        "time": "PerScene-Optimization (秒級)",
    },
    # ----- foundations / depth-foundation -----
    "foundations/depth-foundation/depth_anything_v2_dissection.md": {
        "problem": "Relative depth estimation",
        "representation": "Per-pixel depth map (relative)",
        "sensor": "Single RGB",
        "paradigm": "Learned-Foundation (monocular)",
        "time": "FeedForward-OneShot",
    },
    "foundations/depth-foundation/metric3d_dissection.md": {
        "problem": "Metric depth estimation",
        "representation": "Per-pixel depth map (metric)",
        "sensor": "Single RGB (+ intrinsic)",
        "paradigm": "Learned-Foundation (metric)",
        "time": "FeedForward-OneShot",
    },
    "foundations/depth-foundation/moge_dissection.md": {
        "problem": "Affine-invariant point map (single-task)",
        "representation": "Dense point map (up-to-scale)",
        "sensor": "Single RGB",
        "paradigm": "Learned-Foundation",
        "time": "FeedForward-OneShot",
    },
    "foundations/depth-foundation/foundationstereo_dissection.md": {
        "problem": "Stereo depth (foundation)",
        "representation": "Disparity / depth map",
        "sensor": "Stereo RGB",
        "paradigm": "Learned-Foundation (stereo)",
        "time": "FeedForward-OneShot",
    },
    # ----- foundations / feed-forward-3d -----
    "foundations/feed-forward-3d/vggt_cvpr2025_dissection.md": {
        "problem": "FeedForward3D (pose + depth + points + tracks)",
        "representation": "Dense pointmap + depth + pose + tracks",
        "sensor": "Multi-view RGB",
        "paradigm": "Learned-EndToEnd-MultiTask",
        "time": "FeedForward-OneShot (batch)",
    },
    "foundations/feed-forward-3d/vggt_omega_dissection.md": {
        "problem": "FeedForward3D (VGGT variant)",
        "representation": "Dense pointmap + depth + pose",
        "sensor": "Multi-view RGB",
        "paradigm": "Learned-EndToEnd",
        "time": "FeedForward-OneShot",
    },
    "foundations/feed-forward-3d/mapanything_dissection.md": {
        "problem": "FeedForward3D (universal metric, varied camera setups)",
        "representation": "Pointmap + DepthMap + Pose",
        "sensor": "Multi-view RGB (varied)",
        "paradigm": "Learned-Foundation-MultiTask",
        "time": "FeedForward-OneShot",
    },
    # ----- foundations / physics -----
    "foundations/physics/mujoco_mjx_dissection.md": {
        "problem": "Differentiable physics simulation (rigid body)",
        "representation": "Rigid body state + contact constraints",
        "sensor": "NoSensor (simulator)",
        "paradigm": "Hybrid-DiffSim (XLA-JIT)",
        "time": "Offline-Batch / Diff-Optim",
    },
    "foundations/physics/nvidia_warp_dissection.md": {
        "problem": "Differentiable physics (continuum + rigid)",
        "representation": "Particle field + rigid body",
        "sensor": "NoSensor",
        "paradigm": "Hybrid-DiffSim (CUDA kernels)",
        "time": "Offline-Batch",
    },
    "foundations/physics/physgaussian_dissection.md": {
        "problem": "Physics simulation + NVS (3DGS + MPM)",
        "representation": "3DGS + Material Point Method",
        "sensor": "RGB (Gaussian fitted) + physics priors",
        "paradigm": "Hybrid-DiffSim + DiffRender",
        "time": "PerScene + Offline",
    },
    # ----- foundations / pose-tracking -----
    "foundations/pose-tracking/cotracker_and_tap_dissection.md": {
        "problem": "PointTracking (任意點長時跟蹤)",
        "representation": "Per-point trajectory",
        "sensor": "Video (RGB)",
        "paradigm": "Learned-Transformer (iterative refinement)",
        "time": "Online",
    },
    "foundations/pose-tracking/foundation_pose_dissection.md": {
        "problem": "Object 6-DoF pose (foundation)",
        "representation": "Mesh template + RGBD features",
        "sensor": "RGBD + Object mesh",
        "paradigm": "Learned + DiffRender refine",
        "time": "Online",
    },
    "foundations/pose-tracking/megapose_dissection.md": {
        "problem": "Object 6-DoF pose (unseen)",
        "representation": "Rendered template hypothesis",
        "sensor": "RGB + Mesh",
        "paradigm": "Learned-Coarse + DiffRender-Refine",
        "time": "Online",
    },
    "foundations/pose-tracking/siamese_to_transformer_sot_dissection.md": {
        "problem": "VisualTracking (single object, SOT)",
        "representation": "Template matching + correlation",
        "sensor": "Video (RGB)",
        "paradigm": "Learned (Siamese → Transformer 譜系)",
        "time": "Online (per-frame)",
    },
    "foundations/pose-tracking/sort_bytetrack_mot_dissection.md": {
        "problem": "Multi-object 2D tracking (MOT)",
        "representation": "BBox + ID + Kalman state",
        "sensor": "Detection input (RGB)",
        "paradigm": "Data association (Hungarian / IoU) + Kalman",
        "time": "Streaming",
    },
    # ----- foundations / semantic-3d -----
    "foundations/semantic-3d/langsplat_dissection.md": {
        "problem": "Open-vocabulary 3D (text query)",
        "representation": "3DGS + CLIP feature field (per-Gaussian)",
        "sensor": "RGB + CLIP teacher",
        "paradigm": "Hybrid + Feature distillation",
        "time": "PerScene-Optimization",
    },
    "foundations/semantic-3d/lerf_dissection.md": {
        "problem": "Open-vocabulary 3D",
        "representation": "NeRF + CLIP feature field",
        "sensor": "RGB + CLIP",
        "paradigm": "Hybrid + Distillation",
        "time": "PerScene-Optimization",
    },
    "foundations/semantic-3d/openscene_dissection.md": {
        "problem": "Open-vocabulary 3D segmentation",
        "representation": "Voxel + CLIP feature cloud",
        "sensor": "RGBD + CLIP teacher",
        "paradigm": "Zero-shot CLIP fusion (no per-scene 訓練)",
        "time": "Streaming / Batch",
    },
    "foundations/semantic-3d/sam3d_dissection.md": {
        "problem": "Promptable 3D / Image-to-3D (SA3D / SAGA / SAM 3D Objects)",
        "representation": "NeRF + 3DGS feature / Mesh",
        "sensor": "RGB / RGBD / 單 image",
        "paradigm": "Hybrid + Generative (SAM 3D Objects 2025)",
        "time": "PerScene + FeedForward (依變體)",
    },
    # ----- foundations / vlm-spatial-reasoning -----
    "foundations/vlm-spatial-reasoning/3dsrbench_dissection.md": {
        "problem": "Spatial reasoning benchmark (VLM QA)",
        "representation": "Image-QA pair (benchmark dataset)",
        "sensor": "Image input",
        "paradigm": "Benchmark / Evaluation",
        "time": "Offline evaluation",
    },
    "foundations/vlm-spatial-reasoning/spatialbot_dissection.md": {
        "problem": "Spatial reasoning (depth-aware VLM)",
        "representation": "Image + depth conditioned QA",
        "sensor": "RGB + Depth",
        "paradigm": "Learned-VLM (depth-aware)",
        "time": "FeedForward",
    },
    "foundations/vlm-spatial-reasoning/spatialvlm_dissection.md": {
        "problem": "Spatial reasoning (metric inference from VLM)",
        "representation": "Image + metric QA",
        "sensor": "RGB",
        "paradigm": "Learned-VLM",
        "time": "FeedForward",
    },
    # ----- foundations / world-model -----
    "foundations/world-model/genie_dissection.md": {
        "problem": "World model (action-conditioned video gen)",
        "representation": "Latent video tokens",
        "sensor": "Video",
        "paradigm": "Generative-VideoWorldModel (action-conditioned)",
        "time": "FeedForward",
    },
    "foundations/world-model/nvidia_cosmos_dissection.md": {
        "problem": "World model (robotics foundation video)",
        "representation": "Video tokens + 3D generation",
        "sensor": "Video (multi-modal)",
        "paradigm": "Generative-VideoWorldModel + 3D",
        "time": "FeedForward",
    },
}


HEADER_MARKER = "<!-- ontology-5axis"
HEADER_END = "-->"


def compute_ref_path(file_path: Path) -> str:
    """Compute relative path from dissection file to cheat-sheet/ontology.md."""
    rel = Path("cheat-sheet/ontology.md")
    # depth of file from repo root (number of `..` needed)
    depth = len(file_path.parts) - 1
    return "/".join([".."] * depth + ["cheat-sheet", "ontology.md"])


def build_header(file_path: Path, axes: dict[str, str]) -> str:
    ref = compute_ref_path(file_path)
    lines = [HEADER_MARKER]
    for key in ("problem", "representation", "sensor", "paradigm", "time"):
        lines.append(f"{key}: {axes[key]}")
    lines.append(f"ref: {ref} §7")
    lines.append(HEADER_END)
    return "\n".join(lines) + "\n\n"


def inject_into_file(file_path: Path, axes: dict[str, str]) -> str:
    """Inject header at top of file (replacing existing if present)."""
    text = file_path.read_text(encoding="utf-8")
    header = build_header(file_path.relative_to(REPO_ROOT), axes)

    # Remove existing header if present (idempotent)
    if text.startswith(HEADER_MARKER):
        end_idx = text.find(HEADER_END, len(HEADER_MARKER))
        if end_idx > 0:
            after = text[end_idx + len(HEADER_END) :].lstrip("\n")
            text = after

    new_text = header + text
    file_path.write_text(new_text, encoding="utf-8")
    return "injected"


def main() -> int:
    print(f"Injecting ontology headers into {len(CLASSIFICATIONS)} dissections...\n")
    injected = 0
    skipped = []
    for rel_path, axes in CLASSIFICATIONS.items():
        fp = REPO_ROOT / rel_path
        if not fp.exists():
            skipped.append((rel_path, "file not found"))
            continue
        status = inject_into_file(fp, axes)
        print(f"  {status:10s}  {rel_path}")
        injected += 1

    # Cross-check: any dissection file without classification?
    all_dissections = set()
    for md in REPO_ROOT.rglob("*_dissection.md"):
        if ".git" in md.parts:
            continue
        all_dissections.add(str(md.relative_to(REPO_ROOT)))
    unclassified = sorted(all_dissections - set(CLASSIFICATIONS.keys()))

    print(f"\nInjected: {injected}")
    if skipped:
        print(f"Skipped: {len(skipped)}")
        for s in skipped:
            print(f"  - {s[0]}: {s[1]}")
    if unclassified:
        print(f"\nWARNING: {len(unclassified)} dissection(s) not classified:")
        for u in unclassified:
            print(f"  - {u}")
    else:
        print(f"\nAll {len(all_dissections)} dissection files have classifications.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
