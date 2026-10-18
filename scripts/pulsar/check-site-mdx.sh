#!/usr/bin/env bash
set -euo pipefail
# GitHub-hosted runner only; no production server packages or global installs.
PULSAR_MDX_PREFIX="${RUNNER_TEMP:?GitHub runner temp is required}/pulsar-mdx-check"
export PULSAR_MDX_PREFIX
npm install --prefix "$PULSAR_MDX_PREFIX" --no-save --package-lock=false --ignore-scripts --no-audit --no-fund \
  @mdx-js/mdx@3.1.1 remark-math@6.0.0 remark-gfm@4.0.1
node scripts/pulsar/check_site_mdx.mjs
