# Deployment · 工程實戰

The gap between paper and production. Industry knows these; academia doesn't write them; this section closes it.

| Subdirectory | Scope |
|---|---|
| `hardware-selection/` | IMX900 / 850 nm BPF / ToF vs SL / event camera trade-offs |
| `multi-modal-sync/` | RGB + Depth + IMU + IR hardware sync (PTP, hardware trigger, drift) |
| `calibration/` | Multi-cam extrinsics / stereo rectification / IMU–cam / on-flight online cal |
| `compute-budget/` | Jetson Orin / RK3588 / on-device 3DGS / VGGT distillation |
| `failure-modes/` | Camera-shift, vibration, backlight, reflection, transparency, weather, dust, underwater |

Community field notes: drop a `community_field_notes_<topic>.md` next to the relevant subdir or at the root.
