#!/usr/bin/env python3
"""百千報：替每期產生社群分享縮圖 news/og/<id>.png（1200×630）。

用法（在 repo 根目錄）：
  python3 tools/build_og.py            # 只替第 11 期起、還沒有縮圖的期數產生（舊期不補）
  python3 tools/build_og.py --only ID  # 只處理指定期數（可重複）
  python3 tools/build_og.py --force    # 已有縮圖也重畫
找不到中文明體字型時不產生任何圖片、印出警告並正常結束；
沒有縮圖的期數，文字頁會自動沿用網站預設分享圖。
"""
import argparse, glob, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISSUES = ROOT / "news" / "issues"
OUT = ROOT / "news" / "og"
W, H = 1200, 630
PAPER, INK, INK2, INK3, LINE, SEAL = "#f4f0e8", "#1b1a18", "#55514a", "#8d877c", "#d9d2c4", "#b0342a"
TPE = timezone(timedelta(hours=8))
WD = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

# 依序找：Noto Serif CJK（Debian/Ubuntu 套件 fonts-noto-cjk）的繁中字面
FONT_CANDIDATES = {
    "black": ["/usr/share/fonts/opentype/noto/NotoSerifCJK-Black.ttc"],
    "semibold": ["/usr/share/fonts/opentype/noto/NotoSerifCJK-SemiBold.ttc",
                 "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"],
    "regular": ["/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"],
}


def find_font(kind):
    for p in FONT_CANDIDATES[kind] + sorted(glob.glob("/usr/share/fonts/**/NotoSerifCJK*.ttc", recursive=True)):
        if Path(p).exists():
            return p
    return None


def load(ImageFont, path, size):
    # .ttc 內含 JP/KR/SC/TC/HK；找出 TC 那一個字面
    for i in range(10):
        try:
            f = ImageFont.truetype(path, size, index=i)
        except OSError:
            break
        if "TC" in " ".join(f.getname()):
            return f
    return ImageFont.truetype(path, size)


def when(x):
    try:
        t = datetime.fromisoformat(x["published"]).astimezone(TPE)
        return f"{t.year} 年 {t.month} 月 {t.day} 日　{WD[t.weekday()]}"
    except Exception:
        return x.get("date", "")


def wrap(draw, text, font, maxw):
    """逐字換行（中文不靠空白斷行）；避免標點出現在行首。"""
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=font) <= maxw or not cur:
            cur += ch
        else:
            if ch in "，。、：；！？」』）》〉…—,.":
                cur += ch  # 標點掛在行尾
                continue
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def render(meta, x, fonts, ImageFont, Image, ImageDraw):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    M = 80
    # 報頭
    brand = load(ImageFont, fonts["black"], 46)
    d.text((M, 62), "百 千 報", font=brand, fill=SEAL)
    small = load(ImageFont, fonts["regular"], 28)
    no = f"第 {x.get('issue_no', meta.get('issue_no'))} 期"
    d.text((W - M - d.textlength(no, font=small), 74), no, font=small, fill=INK2)
    d.line((M, 140, W - M, 140), fill=INK, width=2)
    # 主標題：最多 3 行，放不下就縮字
    title = meta.get("title") or (x.get("main") or {}).get("title") or ""
    for size in (72, 66, 60, 54, 48, 44, 40):
        f = load(ImageFont, fonts["semibold"], size)
        lines = wrap(d, title, f, W - 2 * M)
        if len(lines) <= 3:
            break
    # 平衡各行長度，避免最後一行只剩一兩個字
    if len(lines) > 1:
        target = d.textlength(title, font=f) / len(lines) + size * 0.6
        balanced = wrap(d, title, f, min(target, W - 2 * M))
        if len(balanced) == len(lines):
            lines = balanced
    lh = int(size * 1.42)
    block = lh * len(lines)
    top = 140 + (440 - 140 - block) // 2 + 10
    for i, ln in enumerate(lines):
        d.text((M, top + i * lh), ln, font=f, fill=INK)
    # 底部
    d.line((M, 500, W - M, 500), fill=LINE, width=1)
    d.text((M, 528), when(x), font=small, fill=INK2)
    credit = "侯百千 主編"
    d.text((W - M - d.textlength(credit, font=small), 528), credit, font=small, fill=INK3)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("警告：沒有 Pillow（pip install pillow），略過縮圖")
        return
    fonts = {k: find_font(k) for k in FONT_CANDIDATES}
    if not all(fonts.values()):
        print("警告：找不到 Noto Serif CJK 字型（apt 套件 fonts-noto-cjk），略過縮圖；文字頁會沿用預設分享圖")
        return
    issues = json.loads((ISSUES / "index.json").read_text("utf-8"))["issues"]
    OUT.mkdir(exist_ok=True)
    made = 0
    for meta in issues:
        iid = meta["id"]
        if a.only and iid not in a.only:
            continue
        if not a.only and int(meta.get("issue_no") or 0) < 11:
            continue  # 2026-11-11 他定：從第 11 期開始，舊期不補
        out = OUT / f"{iid}.png"
        if out.exists() and not a.force:
            continue
        x = json.loads((ISSUES / f"{iid}.json").read_text("utf-8"))
        render(meta, x, fonts, ImageFont, Image, ImageDraw).save(out, optimize=True)
        made += 1
        print(f"縮圖：news/og/{iid}.png")
    print(f"產生 {made} 張縮圖")


if __name__ == "__main__":
    main()
