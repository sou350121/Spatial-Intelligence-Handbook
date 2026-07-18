#!/usr/bin/env python3.11
"""Generate the Spatial-Intelligence-Handbook README hero banner (GitHub-native SVG).

Design: "instrument" aesthetic — a dark navy field carrying a precise point cloud
(echoing the live Atlas star-map) above a cm->km scale axis that encodes the book's
thesis: the SAME spatial problem across manipulation / aerial / driving / marine.
Colours trace to the brand tokens (#0EA5E9 / #38BDF8 / #0369A1). Self-contained dark
background so it reads on both GitHub light and dark themes. Halton low-discrepancy
scatter (not hand-drawn), deterministic — no randomness.
"""

W, H = 1280, 360

def halton(i, b):
    f, r = 1.0, 0.0
    while i > 0:
        f /= b
        r += f * (i % b)
        i //= b
    return r

# ---- point cloud: right ~55%, above the scale axis -------------------------
PX0, PX1 = 548, 1224      # cloud x range (left kept clear for the wordmark)
PY0, PY1 = 54, 250        # cloud y range (above axis at y=292)
N = 46
pts = []
for i in range(1, N + 1):
    x = PX0 + halton(i, 2) * (PX1 - PX0)
    y = PY0 + halton(i, 3) * (PY1 - PY0)
    v = halton(i, 5)                       # "load-bearing"-ness → size/brightness
    r = 1.4 + v * 2.4
    op = 0.22 + v * 0.62
    pts.append((x, y, r, op, v))

circles = []
for x, y, r, op, v in pts:
    if v > 0.86:                            # a few bright anchors get a soft halo
        circles.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r*2.6:.1f}" fill="#38BDF8" opacity="0.10"/>')
    circles.append(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="#7DD3FC" opacity="{op:.2f}"/>')

# a couple of faint connecting lines between near-bright anchors (constellation feel)
bright = sorted([p for p in pts if p[4] > 0.7], key=lambda p: p[0])
lines = []
for a, b in zip(bright, bright[1:]):
    lines.append(
        f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
        f'stroke="#38BDF8" stroke-width="0.6" opacity="0.14"/>')

# ---- scale axis: cm -> km, four embodiment ticks ---------------------------
AX_Y = 292
AX0, AX1 = 548, 1224
ticks = [
    (0.04, "1&#8202;cm", "manipulation"),
    (0.36, "1&#8202;m",  "humanoid&#8202;/&#8202;ground"),
    (0.66, "100&#8202;m", "aerial"),
    (0.95, "1&#8202;km", "driving&#8202;/&#8202;marine"),
]
axis = [f'<line x1="{AX0}" y1="{AX_Y}" x2="{AX1}" y2="{AX_Y}" stroke="#1e3a5f" stroke-width="1"/>']
for t, big, small in ticks:
    tx = AX0 + t * (AX1 - AX0)
    axis.append(f'<line x1="{tx:.0f}" y1="{AX_Y-5}" x2="{tx:.0f}" y2="{AX_Y+5}" stroke="#2f5a86" stroke-width="1.4"/>')
    axis.append(f'<text x="{tx:.0f}" y="{AX_Y+22}" fill="#7DD3FC" font-size="14" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" text-anchor="middle" font-weight="600">{big}</text>')
    axis.append(f'<text x="{tx:.0f}" y="{AX_Y+40}" fill="#5b7290" font-size="11.5" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" text-anchor="middle">{small}</text>')

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Spatial Intelligence Handbook">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0a0f1e"/>
      <stop offset="1" stop-color="#0c1424"/>
    </linearGradient>
    <linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#38BDF8"/>
      <stop offset="1" stop-color="#0369A1"/>
    </linearGradient>
  </defs>

  <rect width="{W}" height="{H}" fill="url(#bg)"/>

  <!-- point cloud (Atlas motif) -->
  <g>
    {chr(10).join('    ' + l for l in lines)}
    {chr(10).join('    ' + c for c in circles)}
  </g>

  <!-- scale axis: cm -> km -->
  <g>
    {chr(10).join('    ' + a for a in axis)}
  </g>

  <!-- wordmark -->
  <text x="64" y="112" fill="#5b7290" font-size="15" letter-spacing="4" font-family="{MONO}">照见 · PULSAR · CROSS-EMBODIMENT SPATIAL AI</text>
  <text x="62" y="182" font-size="60" font-weight="800" font-family="{SANS}" letter-spacing="-1.5">
    <tspan fill="#38BDF8">Spatial</tspan><tspan fill="#eaf4ff"> Intelligence</tspan>
  </text>
  <text x="64" y="232" fill="#eaf4ff" font-size="60" font-weight="800" font-family="{SANS}" letter-spacing="-1.5">Handbook</text>
  <rect x="66" y="256" width="132" height="3" rx="1.5" fill="url(#rule)"/>
  <text x="64" y="292" fill="#9fb4cc" font-size="17" font-family="{SANS}">One problem &#8212; SLAM, VIO, 3D reconstruction &#8212; read across every embodiment.</text>
  <text x="64" y="316" fill="#5b7290" font-size="14" font-family="{MONO}">daily arxiv pipeline &#183; 5-axis ontology &#183; a living paper atlas, not a static survey</text>
</svg>
'''

open("/home/claudeuser/Spatial-Intelligence-Handbook/assets/hero.svg", "w").write(svg)
print("wrote hero.svg", len(svg), "bytes,", len(pts), "points")
