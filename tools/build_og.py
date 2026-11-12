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


ART_DIR = ROOT / "news" / "art"
ART_COUNT = 20
DARK, CREAM, CREAM2, CREAM3, SEAL_D = "#121110", "#ebe6dc", "#b3ac9f", "#7a7469", "#d0574a"


def paste_art(img, Image, n, box):
    """把侯百千的畫（米白線、透明底）縮放貼進 box=(x0,y0,x1,y1)，置中。"""
    p = ART_DIR / f"{n:02d}.webp"
    if not p.exists():
        return
    art = Image.open(p).convert("RGBA")
    bw, bh = box[2] - box[0], box[3] - box[1]
    art.thumbnail((bw, bh), Image.LANCZOS)
    color = Image.new("RGBA", art.size, CREAM)
    color.putalpha(art.getchannel("A"))
    img.paste(color, (box[0] + (bw - art.width) // 2, box[1] + (bh - art.height) // 2), color)


def render(meta, x, fonts, ImageFont, Image, ImageDraw):
    """2026-11-12 主編定：分享縮圖用侯百千的畫＋開場白，不放新聞標題。畫依期數輪流，與滑卡封面同一張。"""
    img = Image.new("RGB", (W, H), DARK)
    d = ImageDraw.Draw(img)
    no_i = int(x.get("issue_no") or meta.get("issue_no") or 0)
    try:
        art_n = int(x.get("art") or 0)
    except (TypeError, ValueError):
        art_n = 0
    if not 1 <= art_n <= ART_COUNT:
        art_n = (no_i - 1) % ART_COUNT + 1 if no_i > 0 else 0
    if art_n:
        paste_art(img, Image, art_n, (50, 50, 570, 580))
    L, R = 630, W - 70
    brand = load(ImageFont, fonts["black"], 40)
    d.text((L, 70), "百 千 報", font=brand, fill=SEAL_D)
    en = load(ImageFont, fonts["regular"], 22)
    d.text((L + d.textlength("百 千 報", font=brand) + 18, 86), "The Hundred", font=en, fill=CREAM3)
    small = load(ImageFont, fonts["regular"], 26)
    d.text((L, 134), f"第 {no_i} 期　{when(x)}", font=small, fill=CREAM2)
    text = x.get("opening") or meta.get("title") or ""
    for size in (46, 42, 38, 34, 30):
        f = load(ImageFont, fonts["semibold"], size)
        lines = wrap(d, text, f, R - L)
        if len(lines) <= 6:
            break
    lh = int(size * 1.55)
    top = 200 + (470 - 200 - lh * len(lines)) // 2 + 20
    for i, ln in enumerate(lines):
        d.text((L, top + i * lh), ln, font=f, fill=CREAM)
    credit = "侯百千 主編"
    d.text((L, 540), credit, font=small, fill=CREAM3)
    return img


def render_default(fonts, ImageFont, Image, ImageDraw):
    """網站預設分享圖 news/og/default.png：一張畫＋報頭。"""
    img = Image.new("RGB", (W, H), DARK)
    d = ImageDraw.Draw(img)
    paste_art(img, Image, 3, (50, 50, 570, 580))
    L = 630
    brand = load(ImageFont, fonts["black"], 64)
    d.text((L, 210), "百 千 報", font=brand, fill=SEAL_D)
    en = load(ImageFont, fonts["regular"], 30)
    d.text((L + 4, 300), "The Hundred", font=en, fill=CREAM3)
    small = load(ImageFont, fonts["regular"], 28)
    d.text((L + 4, 380), "侯百千 主編", font=small, fill=CREAM2)
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
    if a.force or not (OUT / "default.png").exists():
        OUT.mkdir(exist_ok=True)
        render_default(fonts, ImageFont, Image, ImageDraw).save(OUT / "default.png", optimize=True)
        print("預設分享圖：news/og/default.png")
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
