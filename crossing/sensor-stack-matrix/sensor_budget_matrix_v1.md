# Sensor Budget Matrix v1

**Status:** DRAFT v0.1 — scaffold only, content pending
**Wedge tier:** W2 (one of 5 launch docs)
**Why this doc exists:** No survey writes the SWaP-C account. Vendors keep it private. This matrix makes the cross-embodiment trade-off concrete in one table.

---

## Thesis

Each embodiment picks its sensor stack on a binding SWaP-C constraint (size, weight, power, cost) that the academic literature does not surface. The matrix below makes the constraint observable and the choices defensible.

---

## Matrix (rows × cols)

|              | RGB mono | RGB stereo | RGBD (active) | LiDAR | IMU | NIR active | Event camera | Acoustic |
|--------------|----------|------------|---------------|-------|-----|------------|--------------|----------|
| Manipulation | maybe | core | core | rare | core | sometimes | rare | rare |
| Humanoid     | core | core | sometimes | sometimes | core | rare | research | rare |
| Ground mobile | core | core | sometimes | core (AGV) | core | rare | rare | sometimes |
| Driving      | core | sometimes | rare | core | core | rare | research | rare |
| Aerial       | core | sometimes | rare | sometimes | core | rare | research | rare |
| Marine       | sometimes | sometimes | rare | rare | core | rare | rare | core |

Each cell will expand into a paragraph covering:
- Why used / not used
- SWaP-C cost in that embodiment
- Dominant failure mode that drives the pick
- Counter-examples (e.g. flagship drones that *do* use LiDAR)

---

## Outline of full doc

1. SWaP-C primer — what each axis costs in each embodiment
2. The matrix above, cell-by-cell
3. Cross-cutting patterns (e.g. "IMU is always core; only price is FOG vs MEMS")
4. The 3 most counterintuitive cells (e.g. why drones don't use RGBD; why AD seldom uses RGBD)
5. Decision tree: given embodiment X + budget Y → starter stack

---

## Starter references

- Industry datasheets (Sony IMX900, Velodyne / Hesai / Innoviz, Bosch BMI270 IMU, AURELION ACOSTRA sonar)
- Skydio engineering blog (drone stack)
- Tesla AI Day archives (driving stack)
- Underwater robotics surveys (sonar dominance under water)
- Maintainer's Autel deployment SWaP-C calculations
