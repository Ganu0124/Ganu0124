#!/usr/bin/env python3
"""
Builds dist/terminal.svg: an animated, terminal-style profile card.

  python ascii_to_svg.py                    # uses photo.jpg / photo.png if present, else a silhouette
  python ascii_to_svg.py --photo me.jpg     # explicit photo

Needs: pip install pillow
"""
import argparse
import os
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFilter, ImageOps

# ----------------------------------------------------------------------------
# EDIT YOUR DETAILS HERE
# ----------------------------------------------------------------------------
HOST = "ganesh@devos"
TITLE = "ganesh@devos ~ % ./profile.sh --live"

# ("label", "value")  ·  None = blank line  ·  ("#", "Section name") = section header
INFO = [
    ("Subject", "Ganesh M"),
    ("Role", "AI/ML Engineer · Data Scientist"),
    ("Origin", "Mysuru, Karnataka, India"),
    ("Education", "MCA AI & DS · CGPA 7.19"),
    ("Status", "Building • Learning • Shipping"),
    ("ToolChain", "VS Code, Git, GitHub, Linux"),
    None,
    ("Core.Lang", "Python, Java, C, SQL"),
    ("Core.AI", "TensorFlow, Keras, PyTorch, OpenCV"),
    ("Core.Data", "Pandas, NumPy, Matplotlib, sklearn"),
    ("Core.Database", "MySQL, SQLite, PostgreSQL, Oracle"),
    None,
    ("#", "Contact"),
    ("Grid.Mail", "gganu8615@gmail.com"),
    ("Grid.LinkedIn", "ganesh-m-217b531b8"),
    ("Grid.Github", "Ganu0124"),
    ("Grid.Portfolio", "coming soon"),
    None,
    ("#", "Live Stats"),
    ("!", "See live GitHub stats below in README ↓"),
]

# ----------------------------------------------------------------------------
W, H = 1100, 530
ASCII_COLS, ASCII_ROWS, ASCII_FS = 96, 58, 6.6
INFO_FS, INFO_LH = 13, 19
CYCLE = 18  # seconds for one full "boot" loop
RAMP = " .:-=+*#%@"
FONT = "'JetBrains Mono','Fira Code',Consolas,'DejaVu Sans Mono',monospace"


def silhouette():
    """Placeholder avatar when no photo is provided."""
    img = Image.new("L", (300, 300), 0)
    d = ImageDraw.Draw(img)
    d.ellipse((95, 40, 205, 170), fill=220)          # head
    d.ellipse((30, 180, 270, 420), fill=170)         # shoulders
    d.rectangle((135, 150, 165, 195), fill=190)      # neck
    return img.filter(ImageFilter.GaussianBlur(5))


def photo_to_ascii(path):
    img = Image.open(path).convert("L") if path else silhouette()
    img = ImageOps.autocontrast(img, cutoff=2)
    # character cells are ~0.6 as wide as tall, so crop to the matching physical aspect
    img = ImageOps.fit(img, (int(ASCII_COLS * 6), int(ASCII_ROWS * 10)), centering=(0.5, 0.25))
    img = img.resize((ASCII_COLS, ASCII_ROWS), Image.LANCZOS)
    px = img.load()
    lines = []
    for y in range(ASCII_ROWS):
        row = "".join(RAMP[int(px[x, y] / 255 * (len(RAMP) - 1))] for x in range(ASCII_COLS))
        lines.append(row.rstrip())
    return lines


def info_lines():
    """Return list of (kind, label, value) rows."""
    rows = []
    rows.append(("host", HOST, "-" * 44))
    for item in INFO:
        if item is None:
            rows.append(("blank", "", ""))
        elif item[0] == "#":
            rows.append(("section", item[1], "-" * 46))
        elif item[0] == "!":
            rows.append(("note", "", item[1]))
        else:
            rows.append(("kv", item[0], item[1]))
    return rows


def build(photo):
    art = photo_to_ascii(photo)
    rows = info_lines()

    css = [f"text{{font-family:{FONT};white-space:pre}}",
           ".dot{fill:#6d28d9}.lbl{fill:#a78bfa;font-weight:700}.lead{fill:#475569}",
           ".val{fill:#e2e8f0}.host{fill:#8b5cf6;font-weight:700}.sec{fill:#2dd4bf}.rule{fill:#334155}",
           ".note{fill:#e2e8f0}.cap{fill:#38bdf8;letter-spacing:2px;font-size:10px}",
           ".blink{animation:blink 1s steps(1) infinite}",
           ".tag{animation:blink 1.4s steps(1) infinite}",
           "@keyframes blink{50%{opacity:0}}"]

    n = len(rows)
    body = []
    for i, (kind, label, value) in enumerate(rows):
        if kind == "blank":
            continue
        y = 98 + i * INFO_LH
        start = 4 + i * (40 / n)      # % of cycle when this line appears
        css.append(
            f"@keyframes l{i}{{0%,{start:.2f}%{{opacity:0}}{start + 1.5:.2f}%,94%{{opacity:1}}100%{{opacity:0}}}}"
            f".r{i}{{opacity:0;animation:l{i} {CYCLE}s infinite}}"
        )
        x = 510
        if kind == "host":
            t = f'<tspan class="host">{escape(label)}</tspan> <tspan class="rule">{escape(value)}</tspan>'
        elif kind == "section":
            t = f'<tspan class="sec">- {escape(label)} {escape(value)}</tspan>'
        elif kind == "note":
            t = f'<tspan class="note" dx="14">{escape(value)}</tspan>'
        else:
            lab = f"{label}:"
            leader = " " + "." * max(22 - len(lab), 2) + " "
            t = (f'<tspan class="dot">. </tspan><tspan class="lbl">{escape(lab)}</tspan>'
                 f'<tspan class="lead">{leader}</tspan><tspan class="val">{escape(value)}</tspan>')
        body.append(f'<text class="r{i}" x="{x}" y="{y}" font-size="{INFO_FS}" xml:space="preserve">{t}</text>')

    art_svg = "".join(
        f'<text x="52" y="{86 + i * ASCII_FS:.1f}" font-size="{ASCII_FS}" xml:space="preserve">{escape(line)}</text>'
        for i, line in enumerate(art)
    )
    reveal_h = ASCII_ROWS * ASCII_FS + 10

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>{"".join(css)}</style>
<defs>
  <linearGradient id="border" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#8b5cf6"/><stop offset="1" stop-color="#22d3ee"/>
  </linearGradient>
  <linearGradient id="art" gradientUnits="userSpaceOnUse" x1="0" y1="80" x2="0" y2="{80 + reveal_h}">
    <stop offset="0" stop-color="#c4b5fd"/><stop offset="1" stop-color="#38bdf8"/>
  </linearGradient>
  <linearGradient id="scan" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#22d3ee" stop-opacity="0"/>
    <stop offset=".5" stop-color="#22d3ee" stop-opacity=".55"/>
    <stop offset="1" stop-color="#22d3ee" stop-opacity="0"/>
  </linearGradient>
  <pattern id="lines" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="1" fill="#fff" opacity=".035"/>
  </pattern>
  <clipPath id="card"><rect x="8" y="8" width="{W - 16}" height="{H - 16}" rx="16"/></clipPath>
  <clipPath id="reveal">
    <rect x="40" y="62" width="440" height="0">
      <animate attributeName="height" dur="{CYCLE}s" repeatCount="indefinite"
               keyTimes="0;0.1;0.94;1" values="0;{reveal_h:.0f};{reveal_h:.0f};0"/>
    </rect>
  </clipPath>
</defs>

<rect x="8" y="8" width="{W - 16}" height="{H - 16}" rx="16" fill="#060b18" stroke="url(#border)" stroke-width="2"/>
<g clip-path="url(#card)">
  <rect x="8" y="8" width="{W - 16}" height="38" fill="#0b1226"/>
  <circle cx="30" cy="27" r="5" fill="#ef4444"/><circle cx="50" cy="27" r="5" fill="#f59e0b"/><circle cx="70" cy="27" r="5" fill="#10b981"/>
  <text x="{W / 2}" y="31" font-size="11" fill="#64748b" text-anchor="middle">{escape(TITLE)}</text>
  <text class="tag" x="{W - 40}" y="31" font-size="10" fill="#f87171" text-anchor="end">● SCANNING</text>

  <rect x="32" y="62" width="448" height="{H - 100}" rx="10" fill="#07101f" stroke="#164e63" stroke-opacity=".8"/>
  <text class="cap" x="46" y="76">VISUAL.MAP</text>
  <g clip-path="url(#reveal)" fill="url(#art)">{art_svg}</g>

  <rect x="494" y="62" width="{W - 526}" height="{H - 100}" rx="10" fill="#07101f" stroke="#164e63" stroke-opacity=".8"/>
  <text class="cap" x="510" y="76">SYSTEM.INFO</text>
  {"".join(body)}
  <rect class="blink" x="510" y="{98 + (n - 1) * INFO_LH - 10}" width="7" height="13" fill="#8b5cf6"/>

  <rect x="8" y="46" width="{W - 16}" height="3" fill="url(#scan)">
    <animate attributeName="y" values="46;{H - 10};46" dur="6s" repeatCount="indefinite"/>
  </rect>
  <rect x="8" y="8" width="{W - 16}" height="{H - 16}" fill="url(#lines)"/>
</g>
</svg>
'''
    return svg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photo")
    ap.add_argument("--out", default="dist/terminal.svg")
    a = ap.parse_args()

    photo = a.photo
    if not photo:
        for cand in ("photo.jpg", "photo.jpeg", "photo.png"):
            if os.path.exists(cand):
                photo = cand
                break

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(build(photo))
    print(f"wrote {a.out} ({'photo: ' + photo if photo else 'placeholder silhouette'})")


if __name__ == "__main__":
    main()
