#!/usr/bin/env python3
"""Assemble a stock-footage reel from a shots JSON spec.

Usage:
    python3 build.py shots.json [--dry-run]

The spec (see examples/shots.example.json) lists every shot with its source
file, in-point and duration. This script trims/normalises each shot, chains
them with cross dissolves, overlays PNG captions and a title, lays a music
bed under everything and writes an H.264 MP4 plus an EDL CSV.

Requires ffmpeg. Checked in this order: $FFMPEG, ffmpeg on PATH,
imageio_ffmpeg's bundled binary.
"""
import csv
import json
import os
import shutil
import subprocess
import sys


def find_ffmpeg():
    for cand in (os.environ.get("FFMPEG"), shutil.which("ffmpeg")):
        if cand and os.path.exists(cand):
            return cand
    try:
        import imageio_ffmpeg
        p = imageio_ffmpeg.get_ffmpeg_exe()
        if p and os.path.exists(p):
            return p
    except Exception:
        pass
    sys.exit("ffmpeg not found: install it or set FFMPEG=/path/to/ffmpeg")


FF = find_ffmpeg()


def run(cmd, quiet=True):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        print(p.stdout[-4000:])
        sys.exit("ffmpeg failed: " + " ".join(cmd[:6]) + " ...")
    return p.stdout


def probe_duration(path):
    out = subprocess.run([FF, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    for line in out.splitlines():
        if "Duration:" in line:
            hms = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = hms.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


def normalize(spec, shot, idx, workdir):
    src = shot["src"]
    if not os.path.isabs(src):
        src = os.path.join(workdir, src)
    if not os.path.exists(src):
        sys.exit("missing source: " + src)
    ss = float(shot.get("in", 0))
    dur = float(shot["dur"])
    avail = probe_duration(src)
    if avail and ss + dur > avail + 0.05:
        print("  ! %s has %.2fs, %s requested: clamping" % (os.path.basename(src), avail, ss + dur))
        dur = max(0.5, avail - ss)

    W, H, FPS = spec["width"], spec["height"], spec["fps"]
    # crop.x / crop.y pick which part of the frame survives the reframing:
    # 0 = left/top edge, 1 = right/bottom edge. Default keeps the centre.
    cx = float(shot.get("crop", {}).get("x", 0.5))
    cy = float(shot.get("crop", {}).get("y", 0.5))
    vf = shot.get("pregrade", "") + (
        "scale=%d:%d:force_original_aspect_ratio=increase,"
        "crop=%d:%d:(in_w-out_w)*%s:(in_h-out_h)*%s,"
        "fps=%d,%s,format=yuv420p"
        % (W, H, W, H, cx, cy, FPS, spec.get("grade", ""))
    )
    out = os.path.join(workdir, spec["workdir"], "%02d.mp4" % idx)
    run([FF, "-y", "-v", "error", "-ss", str(ss), "-t", str(dur), "-i", src,
         "-vf", vf, "-an", "-c:v", "libx264", "-crf", "16", "-preset", "veryfast",
         "-r", str(FPS), "-t", str(dur), out])
    return out, dur


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    spec_path = os.path.abspath(sys.argv[1])
    dry = "--dry-run" in sys.argv
    workdir = os.path.dirname(spec_path)
    with open(spec_path) as f:
        spec = json.load(f)

    spec.setdefault("width", 1920)
    spec.setdefault("height", 1080)
    spec.setdefault("fps", 25)
    spec.setdefault("xfade", 0.6)
    spec.setdefault("workdir", "_clips")
    spec.setdefault("crf", 19)
    spec.setdefault("preset", "medium")
    spec.setdefault("grade",
                    "eq=contrast=1.05:saturation=0.94:brightness=-0.006:gamma=1.02,"
                    "colorbalance=rs=-0.015:bs=0.025:rm=0.008:bm=0.012:rh=0.012:bh=-0.008,"
                    "vignette=PI/5")
    shots = spec["shots"]
    end = spec.get("endcard")
    n = len(shots) + (1 if end else 0)
    if n < 2:
        sys.exit("need at least two shots")

    durs = [float(s["dur"]) for s in shots] + ([float(end.get("dur", 3.6))] if end else [])
    xf = float(spec["xfade"])
    total = sum(durs) - xf * (n - 1)

    print("shots=%d  total=%.2fs" % (n, total))
    if dry:
        t = 0.0
        for i, d in enumerate(durs):
            print("  %02d  %6.2f - %6.2f  dur %.2f" % (i + 1, t, t + d, d))
            t += d - xf
        return

    os.makedirs(os.path.join(workdir, spec["workdir"]), exist_ok=True)
    clips = []
    for i, shot in enumerate(shots):
        print("  normalizing %s" % shot["src"])
        path, dur = normalize(spec, shot, i, workdir)
        durs[i] = dur
        clips.append(path)
    total = sum(durs) - xf * (n - 1)

    if end:
        png = end["png"]
        if not os.path.isabs(png):
            png = os.path.join(workdir, png)
        out = os.path.join(workdir, spec["workdir"], "%02d.mp4" % len(shots))
        run([FF, "-y", "-v", "error", "-loop", "1", "-t", str(durs[-1]), "-i", png,
             "-vf", "scale=%d:%d,fps=%d,format=yuv420p" % (spec["width"], spec["height"], spec["fps"]),
             "-an", "-r", str(spec["fps"]), "-c:v", "libx264", "-crf", "16",
             "-preset", "veryfast", out])
        clips.append(out)

    os.makedirs(os.path.dirname(os.path.abspath(spec["output"])) if spec.get("output") else workdir,
                exist_ok=True)
    output = spec.get("output", "out/reel.mp4")
    if not os.path.isabs(output):
        output = os.path.join(workdir, output)

    inputs = []
    for c in clips:
        inputs += ["-i", c]
    has_music = bool(spec.get("music")) and os.path.exists(
        spec["music"] if os.path.isabs(spec["music"]) else os.path.join(workdir, spec["music"]))
    if has_music:
        mpath = spec["music"] if os.path.isabs(spec["music"]) else os.path.join(workdir, spec["music"])
        inputs += ["-ss", str(spec.get("music_in", 0)), "-t", "%.3f" % total, "-i", mpath]

    fg = ["[%d:v]setpts=PTS-STARTPTS,fps=%d,settb=AVTB[v%d]" % (i, spec["fps"], i) for i in range(n)]
    cur, off = "v0", 0.0
    for k in range(1, n):
        off += durs[k - 1] - xf
        lab = "x%d" % k
        fg.append("[%s][v%d]xfade=transition=%s:duration=%s:offset=%.3f[%s]"
                  % (cur, k, "fadeblack" if (k == n - 1) else spec.get("transition", "fade"),
                     xf, off, lab))
        cur = lab

    starts, t = [], 0.0
    for d in durs:
        starts.append(t)
        t += d - xf

    ov, nxt = [], n + (1 if has_music else 0)
    title = spec.get("title")
    if title:
        p = title["png"] if os.path.isabs(title["png"]) else os.path.join(workdir, title["png"])
        ov += ["-i", p]
        fade = spec.get("fade_in", 0.9)
        fg.append("[%s]fade=t=in:st=0:d=%s[fi];[fi][%d:v]overlay=0:0:enable='between(t,%s,%s)'[t1]"
                  % (cur, fade, nxt, title.get("in", 1.2), title.get("out", 5.6)))
        cur, nxt = "t1", nxt + 1

    for k, shot in enumerate(shots):
        cap = shot.get("caption")
        if not cap:
            continue
        p = cap if os.path.isabs(cap) else os.path.join(workdir, cap)
        a = starts[k] + float(shot.get("caption_in", 0.55))
        b = starts[k] + durs[k] - float(shot.get("caption_out", 0.95))
        fg.append("[%s][%d:v]overlay=0:0:enable='between(t,%.2f,%.2f)'[c%d]" % (cur, nxt, a, b, k))
        ov += ["-i", p]
        cur, nxt = "c%d" % k, nxt + 1

    if has_music:
        fg.append("[%d:a]atrim=0:%.2f,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=%s,"
                  "afade=t=out:st=%.2f:d=%s,volume=%s,alimiter=limit=0.95[aout]"
                  % (n, total, spec.get("fade_audio_in", 1.2), total - spec.get("fade_audio_out", 1.8),
                     spec.get("fade_audio_out", 1.8), spec.get("music_gain", 0.9)))

    cmd = [FF, "-y", "-v", "error"] + inputs + ov + [
        "-filter_complex", ";".join(fg),
        "-map", "[%s]" % cur,
    ]
    if has_music:
        cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    cmd += ["-c:v", "libx264", "-crf", str(spec["crf"]), "-preset", spec["preset"],
            "-pix_fmt", "yuv420p", "-r", str(spec["fps"]),
            "-profile:v", "high", "-level", "4.1",
            "-t", "%.3f" % total, "-movflags", "+faststart", output]
    print("  encoding -> %s" % output)
    run(cmd)

    edl = os.path.splitext(output)[0] + "_EDL.csv"
    with open(edl, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["shot", "in", "out", "dur", "source", "source_in"])
        for k, shot in enumerate(shots):
            w.writerow([k + 1, "%.2f" % starts[k], "%.2f" % (starts[k] + durs[k]),
                        "%.2f" % durs[k], os.path.basename(shot["src"]), shot.get("in", 0)])
        if end:
            w.writerow([n, "%.2f" % starts[-1], "%.2f" % (starts[-1] + durs[-1]),
                        "%.2f" % durs[-1], "endcard", "-"])
    print("done: %s  (%.2fs, EDL: %s)" % (output, total, os.path.basename(edl)))


if __name__ == "__main__":
    main()
