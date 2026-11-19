#!/usr/bin/env python3
"""
xhs_precheck -- pre-publish compliance checker for Xiaohongshu (RED) posts.

Encodes the content rules as runnable checks:

  1. Title length  -- platform rejects titles over 20 chars
                      (every char counts: punctuation, digits, CJK)
  2. Forbidden CTA -- "comment to claim / lottery / follow-for-follow"
                      hooks get flagged as induced-interaction violations
  3. Hook quality  -- does the title carry a number (the proven hook) and
                      avoid banned words (superlatives, price promises)
  4. AI-flavour    -- detects telltale AI-ish connective phrases in body text

Usage:
    python3 xhs_precheck.py --title "..." [--body "..."]

Requires: Pillow only for the report card (--card), stdlib otherwise.
Exit code 0 = pass, 1 = violations found.
"""
import argparse
import json
import sys

MAX_TITLE = 20

FORBIDDEN_CTA = [
    "扣字", "扣1", "扣1领", "评论领", "评论区领", "扣要", "留言领取",
    "抽奖", "抽3人", "互关", "互赞", "点赞过百", "人多就",
]
BANNED_WORDS = ["第一", "最强", "最牛", "史上最", "全网最", "保证涨粉", "稳赚"]
AI_FLAVOUR = ["首先", "其次", "综上", "赋能", "助力", "总而言之", "值得一提的是"]


def check_title(title):
    findings = []
    n = len(title)
    if n > MAX_TITLE:
        findings.append({"level": "FAIL", "check": "标题长度",
                         "msg": f"{n} 字 > {MAX_TITLE} 上限，平台会直接卡标题；先砍修饰语保数字钩子"})
    else:
        findings.append({"level": "PASS", "check": "标题长度", "msg": f"{n}/{MAX_TITLE} 字，逐字符计数（标点全算）"})
    hit = [w for w in FORBIDDEN_CTA if w in title]
    if hit:
        findings.append({"level": "FAIL", "check": "诱导互动",
                         "msg": f"命中违禁 CTA：{hit} —— 判「诱导互动」会取消推荐，改为「资料在置顶评论，自取」"})
    else:
        findings.append({"level": "PASS", "check": "诱导互动", "msg": "未命中扣字/抽奖/互赞类违禁钩子"})
    banned = [w for w in BANNED_WORDS if w in title]
    if banned:
        findings.append({"level": "FAIL", "check": "极限词", "msg": f"命中广告法极限词：{banned}"})
    else:
        findings.append({"level": "PASS", "check": "极限词", "msg": "无最/第一/承诺类词汇"})
    if any(ch.isdigit() for ch in title):
        findings.append({"level": "PASS", "check": "数字钩子", "msg": "标题含数字（已验证的最强钩子型）"})
    else:
        findings.append({"level": "WARN", "check": "数字钩子",
                         "msg": "标题无数字——数字反差是 3 秒留人的核心钩子，建议加"})
    return findings


def check_body(body):
    findings = []
    hits = [w for w in AI_FLAVOUR if w in body]
    if hits:
        findings.append({"level": "FAIL", "check": "AI味词",
                         "msg": f"命中 AI 腔：{hits} —— 删掉，改短句白描"})
    else:
        findings.append({"level": "PASS", "check": "AI味词", "msg": "无首先/其次/综上/赋能类腔调词"})
    flavour = [k for k in ("报错", "翻车", "试了", "第一次", "踩坑") if k in body]
    if flavour:
        findings.append({"level": "PASS", "check": "真实细节",
                         "msg": f"含操作者细节线索：{flavour}"})
    else:
        findings.append({"level": "WARN", "check": "真实细节",
                         "msg": "未见「只有真实操作者才会写出的细节」（报错信息/调参耗时/首次使用的意外），去AI味自检不过"})
    return findings


def _wrap(d, s, font, max_w):
    lines, cur = [], ""
    for ch in s:
        if d.textlength(cur + ch, font=font) > max_w:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines or [""]


def render_card(results, path):
    from PIL import Image, ImageDraw, ImageFont
    W = 720
    pad, lh, sw = 40, 30, 100
    try:
        font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 26)
        font_s = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 20)
        title_f = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 34)
    except OSError:
        font = font_s = title_f = ImageFont.load_default()
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    max_w = W - pad - sw - pad
    wrapped = {s: [(f, _wrap(probe, f"{f['check']}：{f['msg']}", font_s, max_w))
                   for f in fs] for s, fs in results.items()}
    n_lines = sum(sum(len(l) for _, l in ls) + len(ls) for ls in wrapped.values())
    H = pad * 2 + 70 + n_lines * lh + len(results) * 30
    img = Image.new("RGB", (W, H), "#F7F5EC")          # 奶白底（护眼浅色规范）
    d = ImageDraw.Draw(img)
    d.text((pad, pad), "小红书发布前自检报告", fill="#2F4A3C", font=title_f)
    y = pad + 70
    COLORS = {"PASS": "#3E7A57", "WARN": "#C28A2E", "FAIL": "#B5544A"}
    for section, items in wrapped.items():
        d.text((pad, y), f"【{section}】", fill="#2F4A3C", font=font)
        y += 40
        for f, lines in items:
            d.rounded_rectangle([pad, y, pad + 64, y + 28], 8, fill=COLORS[f["level"]])
            d.text((pad + 12, y + 2), f["level"], fill="white", font=font_s)
            for i, ln in enumerate(lines):
                d.text((pad + sw, y + i * lh), ln, fill="#444444", font=font_s)
            y += lh * len(lines) + 8
    img.save(path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--body", default="")
    ap.add_argument("--card", help="optional path for a PNG report card")
    args = ap.parse_args()

    results = {"标题": check_title(args.title)}
    if args.body:
        results["正文"] = check_body(args.body)

    for section, findings in results.items():
        for f in findings:
            print(json.dumps({"section": section, **f}, ensure_ascii=False))
    fails = sum(1 for fs in results.values() for f in fs if f["level"] == "FAIL")
    if args.card:
        print("card:", render_card(results, args.card))
    print(f"\nsummary: {fails} FAIL")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
