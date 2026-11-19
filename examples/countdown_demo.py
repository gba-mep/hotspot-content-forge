#!/usr/bin/env python3
"""
Demo: text -> animated demo, the way the xhs video pipeline does it.

Draws 3 frames with PIL (CJK-safe font), assembles them into both a GIF
and an MP4 with ffmpeg (-pix_fmt yuv420p for phone compatibility).

Usage:
    python3 countdown_demo.py [outdir]
Requires: Pillow, ffmpeg on PATH.
"""
import os
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"


def frame(text, idx):
    img = Image.new("RGB", (720, 400), "#F7F5EC")
    d = ImageDraw.Draw(img)
    d.text((60, 60), "发布前自检", fill="#2F4A3C", font=ImageFont.truetype(FONT, 48))
    d.text((60, 180), text, fill="#B5544A" if idx == 0 else "#3E7A57",
           font=ImageFont.truetype(FONT, 36))
    d.text((60, 300), f"step {idx + 1}/3", fill="#888888",
           font=ImageFont.truetype(FONT, 24))
    return img


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    texts = ["标题 21 字 -> 砍到 20", "违禁 CTA -> 改置顶评论", "AI 腔 -> 删掉重写"]
    frames = [frame(t, i) for i, t in enumerate(texts)]

    # frames must have identical palettes for a clean GIF
    paths = []
    for i, f in enumerate(frames):
        p = os.path.join(out, f"frame_{i}.png")
        f.save(p)
        paths.append(p)

    gif = os.path.join(out, "precheck-demo.gif")
    frames[0].save(gif, save_all=True, append_images=frames[1:],
                   duration=1200, loop=0)

    mp4 = os.path.join(out, "precheck-demo.mp4")
    if shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                        "-framerate", "1/1.2",
                        "-i", os.path.join(out, "frame_%d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-vf", "scale=720:400", mp4], check=True)
    else:
        print("ffmpeg not found, MP4 skipped")
        mp4 = None

    print("gif:", gif)
    print("mp4:", mp4 or "-")


if __name__ == "__main__":
    main()
