# Contributing

This handbook is community + Pulsar-pipeline hybrid. Two ways to contribute:

## Human contributions
- **Paper dissections** under `foundations/*` or `embodiments/*`: file `*_dissection.md` with hyperparams, shape sanity-checks, deployment caveats.
- **Field notes** under `deployment/`: real hardware + sensor + sim/real gotchas.
- **Cross-embodiment cases** under `crossing/*`: side-by-side comparison of the same problem solved differently across embodiments.

## Pulsar pipeline contributions (automated)
Driven by the [VLA-Handbook Pulsar pipeline](https://github.com/sou350121/VLA-Handbook), retargeted with this repo's hypothesis registry. See `reports/` for daily/weekly/biweekly outputs.

## Style
- Markdown with tight, opinionated prose. No essay padding.
- Every claim cites a paper or repo. arXiv links preferred.
- Numbers carry units and the date of the source paper.
- Skip generic background. Assume the reader is at GP-MoE / VGGT / 3DGS familiarity baseline.

## Boundaries (vs. VLA-Handbook)
See README's "与 VLA-Handbook 的边界规则" table. When in doubt, cross-reference rather than duplicate.

## PR checklist
- [ ] Cited every external claim
- [ ] Marked unverified hyperparams as `UNVERIFIED`
- [ ] Included one shape sanity-check if the doc touches code
- [ ] Cross-linked from the relevant section's README
