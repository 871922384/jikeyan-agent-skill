"""Regenerate jikeyan-agent-skill social preview (1280x640).

Layout: dark-teal gradient bg + soft accent circle, transparent logo composited
directly (no white box), brand title, one EN line, one CN line (项目 wording),
today.png as a rounded phone mock on the right.

The phone sits directly on the gradient background: the shadow is the same
rounded-rect silhouette as the phone itself (hidden behind it, only the blurred
fringe shows) plus a small downward offset — no expanded slab, hence no
hard-edged rectangle. Run: ``python3 scripts/social_preview.py``.

Inputs (repo assets only): ``assets/logo.png``,
``assets/screenshots/today.png``. Output: ``assets/social-preview.png``.
Fonts come from the OS (macOS Hiragino/Helvetica; on Linux install Noto Sans
CJK — see docs/distribution.md §5).
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

W, H = 1280, 640
BG_TOP = (13, 30, 37)
BG_BOT = (37, 66, 75)
ACCENT = (46, 155, 255)          # app blue, accents only
INK = (255, 255, 255)
MUTED = (148, 178, 190)

REPO = Path(__file__).resolve().parent.parent
LOGO_SRC = REPO / "assets" / "logo.png"
SHOT_SRC = REPO / "assets" / "screenshots" / "today.png"
OUT = REPO / "assets" / "social-preview.png"

HI = "/System/Library/Fonts/Hiragino Sans GB.ttc"
HE = "/System/Library/Fonts/Helvetica.ttc"


def font(path, size, face=0):
    from PIL import ImageFont

    return ImageFont.truetype(path, size, index=face)


# --- background: vertical gradient + soft circle accent (echoes old card)
bg = Image.new("RGB", (W, H))
px = bg.load()
for y in range(H):
    t = y / (H - 1)
    px_line = tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3))
    for x in range(W):
        px[x, y] = px_line
glow = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(glow)
d.ellipse([-320, 180, 620, 1120], fill=26)   # bottom-left lift, like the old arc
glow = glow.filter(ImageFilter.GaussianBlur(90))
lift = Image.new("RGB", (W, H), (58, 104, 114))
bg = Image.composite(lift, bg, glow)

import numpy as np


def white_to_alpha(img):
    """GIMP-style color-to-alpha against white: drops the near-white paper
    while keeping saturated marks solid. Floor 0.06 keeps the pale orbit
    trails faintly visible without leaving a paper veil (a box)."""
    a = np.asarray(img.convert("RGB")).astype(np.float32) / 255.0
    m = a.min(axis=2, keepdims=True)
    alpha = 1.0 - m
    rgb = np.where(alpha > 1e-3, (a - m) / np.maximum(alpha, 1e-3), 0.0)
    raw = np.clip(alpha[..., 0], 0, 1) ** 0.62
    out = np.dstack([np.clip(rgb, 0, 1), np.clip((raw - 0.06) / 0.94, 0, 1)])
    return Image.fromarray((out * 255).astype(np.uint8), "RGBA")


# --- logo (opaque near-white paper -> transparent, no white box)
logo = white_to_alpha(Image.open(LOGO_SRC))
LOGO = 208  # enlarged so the orbit mark reads as one mark, not loose dots
logo = logo.resize((LOGO, LOGO), Image.LANCZOS)
LX, LY = 104, 128
bg.paste(logo, (LX, LY), logo)

# --- text block
draw = ImageDraw.Draw(bg)
f_title = font(HI, 62, face=1)
f_en = font(HE, 30)
f_cn = font(HI, 40, face=1)
tx = LX + LOGO + 36
draw.text((tx, LY + 8), "极科研 · jikeyan", font=f_title, fill=INK)
draw.text((tx, LY + LOGO + 66), "Give your AI agent a research dashboard.",
          font=f_en, fill=MUTED)
draw.text((tx, LY + LOGO + 116), "让 AI 助理接管你的科研项目看板",
          font=f_cn, fill=INK)
# blue accent bar under CN line
draw.rounded_rectangle([tx, LY + LOGO + 178, tx + 72, LY + LOGO + 186],
                       radius=4, fill=ACCENT)

# --- phone mock (today.png), rounded corners + soft fringe shadow + hairline
shot = Image.open(SHOT_SRC).convert("RGB")
PH = 560
PW = round(PH * shot.width / shot.height)
shot = shot.resize((PW, PH), Image.LANCZOS)
mask = Image.new("L", (PW, PH), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, PW, PH], radius=44, fill=255)
PX, PY = W - 96 - PW, (H - PH) // 2
# Shadow = same silhouette as the phone, blurred; the solid core hides behind
# the phone so only a soft fringe shows — no expanded slab, no hard edges.
SHADOW_ALPHA = 90
SHADOW_BLUR = 26
SHADOW_DX, SHADOW_DY = 0, 16
core = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(core).rounded_rectangle(
    [PX + SHADOW_DX, PY + SHADOW_DY,
     PX + SHADOW_DX + PW, PY + SHADOW_DY + PH],
    radius=44, fill=(0, 0, 0, SHADOW_ALPHA))
halo = core.filter(ImageFilter.GaussianBlur(SHADOW_BLUR))
bg = bg.convert("RGBA")
bg.alpha_composite(halo)
bg.paste(shot, (PX, PY), mask)
edge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(edge).rounded_rectangle([PX, PY, PX + PW, PY + PH], radius=44,
                                       outline=(255, 255, 255, 46), width=2)
bg.alpha_composite(edge)

bg.convert("RGB").save(OUT)
print("saved", OUT, bg.size)
