#!/usr/bin/env python3
"""
Makes two animated GIFs from photo.jpg:
  vid.gif             terminal boot-up (ASCII portrait reveals, profile info types out)
  photo-animated.gif  portrait that scans between ASCII and the real photo

  python make_media.py            # needs: pip install pillow
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps

import ascii_to_svg as A

REG = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

BG, BAR, PANEL, PANEL_LINE = (6, 11, 24), (11, 18, 38), (7, 16, 31), (22, 78, 99)
PURPLE, LAV, TEAL, CYAN = (139, 92, 246), (167, 139, 250), (45, 212, 191), (34, 211, 238)
WHITE, SLATE, DOT = (226, 232, 240), (71, 85, 105), (109, 40, 217)


def font(path, size):
    return ImageFont.truetype(path, size)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def find_photo():
    for c in ("photo.jpg", "photo.jpeg", "photo.png"):
        if os.path.exists(c):
            return c
    raise SystemExit("put your picture next to this script as photo.jpg")


def ascii_image(lines, fs=7):
    f = font(REG, fs)
    cw = f.getlength("M")
    w, h = int(cw * A.ASCII_COLS) + 2, fs * len(lines) + 2
    img = Image.new("RGB", (w, h), PANEL)
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        t = i / max(len(lines) - 1, 1)
        d.text((1, 1 + i * fs), line, font=f, fill=lerp((196, 181, 253), (56, 189, 248), t))
    return img


def save_gif(frames, durations, out):
    pal = [f.convert("P", palette=Image.ADAPTIVE, colors=64) for f in frames]
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=durations, loop=0, disposal=1)
    print(f"wrote {out}: {len(frames)} frames, {os.path.getsize(out) / 1e6:.2f} MB")


def glow_line(img, x, h_top, h_bot, vertical=True):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for off, a in ((-3, 25), (-2, 45), (-1, 80), (0, 230), (1, 80), (2, 45), (3, 25)):
        if vertical:
            d.line([(x + off, h_top), (x + off, h_bot)], fill=CYAN + (a,), width=1)
        else:
            d.line([(h_top, x + off), (h_bot, x + off)], fill=CYAN + (a,), width=1)
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


# ----------------------------------------------------------------------------- portrait
def make_portrait(photo, art):
    aw, ah = art.size
    real = ImageOps.fit(Image.open(photo).convert("RGB"), (aw, ah), centering=(0.5, 0.25))
    pad = 28
    W, H = aw + pad * 2, ah + pad * 2 + 62
    fn_small, fn_name = font(REG, 11), font(BOLD, 18)

    def frame(x, label):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((6, 6, W - 7, H - 7), radius=16, outline=PURPLE, width=2)
        d.text((pad, 14), "VISUAL.MAP", font=fn_small, fill=CYAN)
        d.text((W - pad, 14), label, font=fn_small, fill=(248, 113, 113) if label == "SCANNING" else TEAL, anchor="ra")
        mix = art.copy()
        if x > 0:
            mix.paste(real.crop((0, 0, x, ah)), (0, 0))
        img.paste(mix, (pad, pad + 14))
        if 0 < x < aw:
            img = glow_line(img, pad + x, pad + 14, pad + 14 + ah)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((pad - 1, pad + 13, pad + aw, pad + 14 + ah), radius=4, outline=PANEL_LINE)
        d.text((pad, ah + pad + 26), "Ganesh M", font=fn_name, fill=WHITE)
        d.text((pad, ah + pad + 50), "AI/ML Engineer  ·  Data Scientist", font=fn_small, fill=LAV)
        return img

    ease = lambda t: 0.5 - 0.5 * math.cos(math.pi * t)
    frames, dur = [frame(0, "ASCII")], [900]
    n = 22
    for i in range(1, n + 1):
        frames.append(frame(int(aw * ease(i / n)), "SCANNING")); dur.append(45)
    frames.append(frame(aw, "VERIFIED")); dur.append(1800)
    for i in range(1, n + 1):
        frames.append(frame(int(aw * (1 - ease(i / n))), "SCANNING")); dur.append(45)
    save_gif(frames, dur, "photo-animated.gif")
    frames[n // 2 + 1].save("_preview_portrait.png")


# ----------------------------------------------------------------------------- terminal video
def row_segments(kind, label, value):
    if kind == "host":
        return [(label, PURPLE, True), (" " + value, SLATE, False)]
    if kind == "section":
        return [("- " + label + " " + value, TEAL, False)]
    if kind == "note":
        return [(value, WHITE, False)]
    lab = label + ":"
    lead = " " + "." * max(22 - len(lab), 2) + " "
    return [(". ", DOT, False), (lab, LAV, True), (lead, SLATE, False), (value, WHITE, False)]


def make_video(art):
    W, H = 960, 540
    rows = A.info_lines()
    segs = [row_segments(*r) for r in rows]
    lens = [sum(len(t) for t, _, _ in s) if r[0] != "blank" else 0 for s, r in zip(segs, rows)]
    f_reg, f_bold = font(REG, 12), font(BOLD, 12)
    f_cap, f_title = font(REG, 10), font(REG, 12)
    aw, ah = art.size
    TYPE_START, PER_FRAME = 4, 32
    total_chars = sum(lens) + 4 * len(rows)
    type_frames = math.ceil(total_chars / PER_FRAME)
    n_frames = TYPE_START + type_frames + 22

    def frame(k):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((8, 8, W - 9, H - 9), radius=16, outline=PURPLE, width=2)
        d.rectangle((10, 10, W - 11, 44), fill=BAR)
        for cx, c in ((30, (239, 68, 68)), (50, (245, 158, 11)), (70, (16, 185, 129))):
            d.ellipse((cx - 5, 22, cx + 5, 32), fill=c)
        d.text((W / 2, 27), A.TITLE, font=f_title, fill=(100, 116, 139), anchor="mm")
        if (k // 3) % 2 == 0:
            d.text((W - 30, 27), "● SCANNING", font=f_cap, fill=(248, 113, 113), anchor="rm")

        d.rounded_rectangle((22, 56, 22 + aw + 22, H - 24), radius=10, fill=PANEL, outline=PANEL_LINE)
        d.text((36, 64), "VISUAL.MAP", font=f_cap, fill=CYAN)
        d.rounded_rectangle((22 + aw + 36, 56, W - 22, H - 24), radius=10, fill=PANEL, outline=PANEL_LINE)
        rx = 22 + aw + 54
        d.text((rx, 64), "SYSTEM.INFO", font=f_cap, fill=CYAN)

        # ascii portrait reveals top to bottom
        p = min(1.0, k / 16)
        rh = max(1, int(ah * p))
        img.paste(art.crop((0, 0, aw, rh)), (33, 84))
        if p < 1:
            img = glow_line(img, 84 + rh, 33, 33 + aw, vertical=False)
        d = ImageDraw.Draw(img)

        # info panel types out
        n = max(0, (k - TYPE_START)) * PER_FRAME
        y = 90
        for s, r, ln in zip(segs, rows, lens):
            if r[0] == "blank":
                y += 19
                continue
            x, left = rx, n
            for text, color, bold in s:
                if left <= 0:
                    break
                shown = text[:left]
                fnt = f_bold if bold else f_reg
                d.text((x, y), shown, font=fnt, fill=color)
                x += fnt.getlength(shown)
                left -= len(text)
            n -= ln + 4
            y += 19
            if n <= 0:
                break
        if k - TYPE_START >= 0 and (k // 2) % 2 == 0:
            d.rectangle((x + 4, y - 19 + 2, x + 11, y - 19 + 15), fill=PURPLE)

        # slow scan line sweeping the card once typing is done
        if k >= TYPE_START + type_frames:
            t = (k - TYPE_START - type_frames) / 21
            img = glow_line(img, int(46 + t * (H - 60)), 10, W - 10, vertical=False)
        return img

    frames = [frame(k) for k in range(n_frames)]
    dur = [80] * n_frames
    dur[-1] = 1400
    save_gif(frames, dur, "vid.gif")
    frames[-8].save("_preview_video.png")


if __name__ == "__main__":
    photo = find_photo()
    art = ascii_image(A.photo_to_ascii(photo))
    make_portrait(photo, art)
    make_video(art)
