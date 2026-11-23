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
        # layout overrides let one cards.json serve 16:9 and 9:16
        L = end.get("layout", {})
        m = L.get("frame_margin", 120)
        d.rectangle([m, m, W - m, H - m], outline=(58, 70, 80, 255), width=1)
        title_y = L.get("title_y", 286)
        title_size = L.get("title_size", 66)
        tracked(d, (W / 2, title_y), end["title"], make_font(F, title_size, True), white, 3, "ma")
        rule_y = L.get("rule_y", title_y + title_size + 48)
        rule_half = L.get("rule_half", 70)
        d.rectangle([W / 2 - rule_half, rule_y, W / 2 + rule_half, rule_y + 3], fill=accent)
        line_y0 = L.get("line_y0", rule_y + 52)
        line_gap = L.get("line_gap", 56)
        line_size = L.get("line_size", 32)
        for i, ln in enumerate(end.get("lines", [])):
            tracked(d, (W / 2, line_y0 + i * line_gap), ln, make_font(F, line_size, False),
                    grey, 2, "ma")
        price_y = L.get("price_y", line_y0 + 140)
        price_size = L.get("price_size", 58)
        tracked(d, (W / 2, price_y), end.get("price", ""), make_font(F, price_size, True),
                white, 2, "ma")
        meta_y = L.get("meta_y", price_y + 90)
        meta_size = L.get("meta_size", 28)
        tracked(d, (W / 2, meta_y), end.get("meta", ""), make_font(F, meta_size, False),
                (196, 204, 210, 255), 2, "ma")
        if end.get("footer"):
            footer_y = L.get("footer_y", meta_y + 126)
            footer_size = L.get("footer_size", 24)
            tracked(d, (W / 2, footer_y), end["footer"], make_font(F, footer_size, False),
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
        main_y = cover.get("main_y", H - 274)
        sub_y = cover.get("sub_y", main_y + 100)
        tracked(d, (cover.get("x", 100), main_y), cover["main"],
                make_font(F, cover.get("main_size", 74), True), white, 4)
        tracked(d, (cover.get("x", 100) + 2, sub_y), cover.get("sub", ""),
                make_font(F, cover.get("sub_size", 30), False), (226, 230, 234, 255), 2)
        im.convert("RGB").save(os.path.join(outdir, cover.get("out", "cover.jpg")), quality=92)

    print("cards ->", outdir)


if __name__ == "__main__":
    main()
