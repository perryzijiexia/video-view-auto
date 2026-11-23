#!/usr/bin/env python3
"""Render title / caption / end-card / cover PNGs for the reel from a JSON spec.

Usage:
    python3 cards.py cards.json

See examples/cards.example.json for the full schema. Only Pillow is required.
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

FALLBACK_FONTS = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/msyh.ttc",
]


def pick_font(spec):
    for p in [spec.get("font")] + FALLBACK_FONTS:
        if p and os.path.exists(p):
            return p
    sys.exit("no CJK font found: set \"font\" in cards.json")


def make_font(path, size, bold):
    if path.lower().endswith(".ttc"):
        for idx in ([2, 1, 0] if bold else [0]):
            try:
                return ImageFont.truetype(path, size, index=idx)
            except Exception:
                continue
    return ImageFont.truetype(path, size)


def tracked(draw, xy, text, fnt, fill, tracking=0, anchor="la"):
    x, y = xy
    if anchor == "ma":
        total = sum(draw.textlength(c, font=fnt) + tracking for c in text) - tracking
        x = xy[0] - total / 2
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking


def shadow(img, blur=8, alpha=150):
    a = img.split()[3]
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * alpha / 255)))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, 4))
    out.alpha_composite(img)
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    spec = json.load(open(sys.argv[1]))
    W, H = spec.get("width", 1920), spec.get("height", 1080)
    outdir = spec.get("out_dir", "cards")
    os.makedirs(outdir, exist_ok=True)
    F = pick_font(spec)
    white = tuple(spec.get("white", [245, 245, 245, 255]))
    grey = tuple(spec.get("grey", [200, 208, 214, 255]))
    accent = tuple(spec.get("accent", [242, 107, 33, 255]))

    def put(name, img):
        img.save(os.path.join(outdir, name))

    title = spec.get("title")
    if title:
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        tracked(d, (W / 2, title.get("y", 402)), title["main"],
                make_font(F, title.get("main_size", 96), True), white,
                title.get("tracking", 6), "ma")
        if title.get("sub"):
            tracked(d, (W / 2, title.get("sub_y", 540)), title["sub"],
                    make_font(F, title.get("sub_size", 34), False), grey,
                    title.get("sub_tracking", 3), "ma")
        ry = title.get("rule_y", 610)
        d.rectangle([W / 2 - 60, ry, W / 2 + 60, ry + 3], fill=accent)
        put("title.png", shadow(img, 10, 170))

    for i, cap in enumerate(spec.get("captions", [])):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        x, y = spec.get("caption_xy", [100, 828])
        d.rectangle([x, y + 4, x + 5, y + 104], fill=accent)
        tracked(d, (x + 26, y), cap["cn"], make_font(F, spec.get("cap_size", 46), True), white, 2)
        tracked(d, (x + 28, y + 66), cap.get("en", ""),
                make_font(F, spec.get("cap_en_size", 22), False), (214, 220, 226, 230), 4)
        put("cap_%02d.png" % i, shadow(img, 6, 140))

    end = spec.get("endcard")
    if end:
        img = Image.new("RGBA", (W, H), (8, 12, 16, 255))
        d = ImageDraw.Draw(img)
        m = 120
        d.rectangle([m, m, W - m, H - m], outline=(58, 70, 80, 255), width=1)
        tracked(d, (W / 2, 286), end["title"], make_font(F, 66, True), white, 3, "ma")
        d.rectangle([W / 2 - 70, 400, W / 2 + 70, 403], fill=accent)
        for i, ln in enumerate(end.get("lines", [])):
            tracked(d, (W / 2, 452 + i * 56), ln, make_font(F, 32, False), grey, 2, "ma")
        tracked(d, (W / 2, 640), end.get("price", ""), make_font(F, 58, True), white, 2, "ma")
        tracked(d, (W / 2, 730), end.get("meta", ""), make_font(F, 28, False),
                (196, 204, 210, 255), 2, "ma")
        if end.get("footer"):
            tracked(d, (W / 2, 856), end["footer"], make_font(F, 24, False),
                    (138, 148, 158, 255), 6, "ma")
        put("endcard.png", img.convert("RGB"))

    cover = spec.get("cover")
    if cover and os.path.exists(cover["frame"]):
        im = Image.open(cover["frame"]).convert("RGB").resize((W, H))
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for i in range(360):
            d.rectangle([0, H - 360 + i, W, H - 360 + i + 1],
                        fill=(0, 0, 0, int(150 * (i / 360) ** 1.2)))
        im = Image.alpha_composite(im.convert("RGBA"), ov)
        d = ImageDraw.Draw(im)
        tracked(d, (100, 806), cover["main"], make_font(F, 74, True), white, 4)
        tracked(d, (102, 906), cover.get("sub", ""), make_font(F, 30, False),
                (226, 230, 234, 255), 2)
        im.convert("RGB").save(os.path.join(outdir, cover.get("out", "cover.jpg")), quality=92)

    print("cards ->", outdir)


if __name__ == "__main__":
    main()
