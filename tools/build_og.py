#!/usr/bin/env python3
"""百千報：替每期產生社群分享縮圖 news/og/<id>.png（1200×630）。

用法（在 repo 根目錄）：
  python3 tools/build_og.py            # 只替第 11 期起、還沒有縮圖的期數產生（舊期不補）
  python3 tools/build_og.py --only ID  # 只處理指定期數（可重複）
  python3 tools/build_og.py --force    # 已有縮圖也重畫
每一篇（單篇頁 news/a/<id>-<欄>.html）另有自己的縮圖 news/og/a/<id>-<欄>.jpg：當期的畫＋那一篇的標題
（2026-11-16 主編定，所有中文篇都做，包括舊期；英文版沿用預設圖）。
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
LEGACY_ROTATION = 20  # 只給沒寫 art 的舊期輪流用，固定不改；畫的張數只記在 meta/editor.art_count
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
    if art_n < 1 or not (ART_DIR / f"{art_n:02d}.webp").exists():
        art_n = (no_i - 1) % LEGACY_ROTATION + 1 if no_i > 0 else 0
    if art_n:
        paste_art(img, Image, art_n, (50, 50, 570, 580))
    L, R = 630, W - 70
    brand = load(ImageFont, fonts["black"], 40)
    d.text((L, 70), "百 千 報", font=brand, fill=SEAL_D)
    en = load(ImageFont, fonts["regular"], 22)
    d.text((L + d.textlength("百 千 報", font=brand) + 18, 86), "The Hundred", font=en, fill=CREAM3)
    small = load(ImageFont, fonts["regular"], 26)
    head = meta['special'] if meta.get("special") else f"第 {no_i} 期"
    line = f"{head}　{when(x)}"
    if d.textlength(line, font=small) > R - L:  # 特輯名稱太長時日期換到下一行，避免被裁掉
        d.text((L, 134), head, font=small, fill=CREAM2)
        d.text((L, 168), when(x), font=small, fill=CREAM2)
    else:
        d.text((L, 134), line, font=small, fill=CREAM2)
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


KEYS = ["news", "main", "lesson", "tattoo", "music", "own", "craft", "lit", "far"]
COL = {"news": "新聞", "tattoo": "刺青", "music": "音樂", "own": "百千", "craft": "興趣的藝術", "lit": "文學", "far": "遠方"}


def column(key, o):
    """欄名，跟 build_news_pages.py 的 column() 一致。"""
    if key[0] == "n" and key[1:].isdigit():
        return {"回顧": "意識科學", "聽": "音樂"}.get(o.get("tag"), o.get("tag") or "夜刊")
    if "反方" in (o.get("sub"), o.get("series"), o.get("label")) or "Counterpoint" in (o.get("series"), o.get("label")):
        return "反方"
    if o.get("tag"):  # 特輯自己標的欄名（例如「rave 特輯」），跟 build_news_pages.py 一致
        return o["tag"]
    if key == "main":
        return o.get("label") or "反方"
    if key == "lesson":
        return o.get("series") or "意識科學"
    return COL.get(key, key)


def articles(x):
    if x.get("items"):
        return [(f"n{i + 1}", it) for i, it in enumerate(x["items"]) if it.get("title")]
    return [(k, x[k]) for k in KEYS if isinstance(x.get(k), dict) and x[k].get("title") and x[k].get("body")]


def art_of(meta, x):
    no_i = int(x.get("issue_no") or meta.get("issue_no") or 0)
    try:
        n = int(x.get("art") or 0)
    except (TypeError, ValueError):
        n = 0
    if n < 1 or not (ART_DIR / f"{n:02d}.webp").exists():
        n = (no_i - 1) % LEGACY_ROTATION + 1 if no_i > 0 else 0
    if x.get("edition") == "night":
        n = 3  # 夜刊沒有封面畫，用預設圖那張
    return n, no_i


def wrap_words(draw, text, font, maxw):
    """跟 wrap() 一樣逐字換行，但英文單字、數字不拆開。"""
    import re
    toks = re.findall(r"[A-Za-z0-9'’&.\-]+|\s+|.", text)
    lines, cur = [], ""
    for t in toks:
        if draw.textlength(cur + t, font=font) <= maxw or not cur.strip():
            cur += t
        elif t.isspace():
            lines.append(cur.rstrip()); cur = ""
        elif len(t) == 1 and t in "，。、：；！？」』）》〉…—,.":
            cur += t
        else:
            lines.append(cur.rstrip()); cur = t
        while draw.textlength(cur, font=font) > maxw and len(cur) > 1:  # 單字比整行還長才拆
            k = len(cur)
            while k > 1 and draw.textlength(cur[:k], font=font) > maxw:
                k -= 1
            lines.append(cur[:k]); cur = cur[k:]
    if cur.strip():
        lines.append(cur.strip())
    return lines


def render_article(meta, x, key, o, fonts, ImageFont, Image, ImageDraw):
    """單篇縮圖：當期的畫＋報頭＋期數・欄名＋這一篇的標題。"""
    img = Image.new("RGB", (W, H), DARK)
    d = ImageDraw.Draw(img)
    art_n, no_i = art_of(meta, x)
    if art_n:
        paste_art(img, Image, art_n, (50, 50, 570, 580))
    L, R = 630, W - 70
    brand = load(ImageFont, fonts["black"], 40)
    d.text((L, 70), "百 千 報", font=brand, fill=SEAL_D)
    en = load(ImageFont, fonts["regular"], 22)
    d.text((L + d.textlength("百 千 報", font=brand) + 18, 86), "The Hundred", font=en, fill=CREAM3)
    small = load(ImageFont, fonts["regular"], 26)
    head = meta["special"] if meta.get("special") else f"第 {no_i} 期"
    if column(key, o) == head:  # 欄名就是特輯名時不重複
        head = ""
    col = load(ImageFont, fonts["semibold"], 26)
    d.text((L, 134), column(key, o), font=col, fill=SEAL_D)
    d.text((L + d.textlength(column(key, o), font=col) + 16, 134), head, font=small, fill=CREAM2)
    text = o.get("title") or ""
    for size in (50, 46, 42, 38, 34, 30):
        f = load(ImageFont, fonts["semibold"], size)
        lines = wrap_words(d, text, f, R - L)
        if len(lines) <= 5:
            break
    lh = int(size * 1.5)
    top = 200 + (500 - 200 - lh * len(lines)) // 2 + 10
    for i, ln in enumerate(lines):
        d.text((L, top + i * lh), ln, font=f, fill=CREAM)
    d.text((L, 540), "侯百千 主編", font=small, fill=CREAM3)
    return img


SW, SH = 1080, 1920


def render_story(meta, x, key, o, fonts, ImageFont, Image, ImageDraw):
    """IG 限動用直式圖（1080×1920）：上半當期的畫，下半報頭、欄名・期數、篇名。連結貼紙由發的人自己加，所以下方留白。"""
    img = Image.new("RGB", (SW, SH), DARK)
    d = ImageDraw.Draw(img)
    art_n, no_i = art_of(meta, x)
    if art_n:
        paste_art(img, Image, art_n, (140, 230, SW - 140, 930))
    L, R = 110, SW - 110
    brand = load(ImageFont, fonts["black"], 60)
    d.text((L, 1020), "百 千 報", font=brand, fill=SEAL_D)
    en = load(ImageFont, fonts["regular"], 32)
    d.text((L + d.textlength("百 千 報", font=brand) + 24, 1044), "The Hundred", font=en, fill=CREAM3)
    small = load(ImageFont, fonts["regular"], 38)
    col = load(ImageFont, fonts["semibold"], 38)
    c = column(key, o)
    head = meta["special"] if meta.get("special") else f"第 {no_i} 期"
    if column(key, o) == head:  # 欄名就是特輯名時不重複
        head = ""
    d.text((L, 1120), c, font=col, fill=SEAL_D)
    d.text((L + d.textlength(c, font=col) + 22, 1120), head, font=small, fill=CREAM2)
    text = o.get("title") or ""
    for size in (76, 68, 62, 56, 50, 44):
        f = load(ImageFont, fonts["semibold"], size)
        lines = wrap_words(d, text, f, R - L)
        if len(lines) <= 5 and len(lines[-1].strip()) > 1:  # 不讓最後一行只剩一個字
            break
    lh = int(size * 1.45)
    for i, ln in enumerate(lines):
        d.text((L, 1230 + i * lh), ln, font=f, fill=CREAM)
    d.text((L, 1230 + len(lines) * lh + 40), "侯百千 主編", font=small, fill=CREAM3)
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
        if meta.get("lang") == "en":
            continue  # 英文版沿用預設分享圖
        if not a.only and not meta.get("special") and int(meta.get("issue_no") or 0) < 11:
            continue  # 2026-11-11 他定：從第 11 期開始，舊期不補
        out = OUT / f"{iid}.png"
        if out.exists() and not a.force:
            continue
        x = json.loads((ISSUES / f"{iid}.json").read_text("utf-8"))
        render(meta, x, fonts, ImageFont, Image, ImageDraw).save(out, optimize=True)
        made += 1
        print(f"縮圖：news/og/{iid}.png")
    print(f"產生 {made} 張縮圖")
    # 單篇縮圖：所有中文篇，缺的才畫（--force 全部重畫；--only 只畫那幾期）
    (OUT / "a").mkdir(exist_ok=True)
    made_a = 0
    for meta in issues:
        iid = meta["id"]
        if meta.get("lang") == "en" or (a.only and iid not in a.only):
            continue
        x = json.loads((ISSUES / f"{iid}.json").read_text("utf-8"))
        for key, o in articles(x):
            out = OUT / "a" / f"{iid}-{key}.jpg"
            if out.exists() and not a.force:
                continue
            render_article(meta, x, key, o, fonts, ImageFont, Image, ImageDraw).save(out, "JPEG", quality=86, optimize=True, progressive=True)
            made_a += 1
    print(f"產生 {made_a} 張單篇縮圖")
    # 限動直式圖：news/og/s/<id>-<欄>.jpg（2026-11-16 主編同意，單篇頁與滑卡的「限動」鍵用）
    (OUT / "s").mkdir(exist_ok=True)
    made_s = 0
    for meta in issues:
        iid = meta["id"]
        if meta.get("lang") == "en" or (a.only and iid not in a.only):
            continue
        x = json.loads((ISSUES / f"{iid}.json").read_text("utf-8"))
        for key, o in articles(x):
            out = OUT / "s" / f"{iid}-{key}.jpg"
            if out.exists() and not a.force:
                continue
            render_story(meta, x, key, o, fonts, ImageFont, Image, ImageDraw).save(out, "JPEG", quality=84, optimize=True, progressive=True)
            made_s += 1
    print(f"產生 {made_s} 張限動圖")


if __name__ == "__main__":
    main()
