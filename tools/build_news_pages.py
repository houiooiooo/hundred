#!/usr/bin/env python3
"""百千報：產生每期的靜態文字頁、往期目錄與 sitemap，讓搜尋引擎讀得到。

用法（在 repo 根目錄）：python3 tools/build_news_pages.py
每次新增或修改 news/issues/*.json 之後跑一次，再一起 commit。
"""
import html, json, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEWS = ROOT / "news"
ISSUES = NEWS / "issues"
OUT = NEWS / "p"
SITE = "https://houiooiooo.github.io/hundred/"
TPE = timezone(timedelta(hours=8))
WD = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

esc = lambda s: html.escape(str(s if s is not None else ""), quote=True)


def when(x):
    try:
        t = datetime.fromisoformat(x["published"]).astimezone(TPE)
        return f"{t.year}年{t.month}月{t.day}日 {WD[t.weekday()]} {t:%H:%M}"
    except Exception:
        return x.get("date", "")


def paras(s):
    out = []
    for p in re.split(r"\n\s*\n", str(s or "")):
        p = p.strip()
        if not p:
            continue
        p = esc(p).replace("\n", "<br>")
        p = re.sub(r"\[(\d{1,2})\]", r'<sup class="fn">\1</sup>', p)
        out.append(f"<p>{p}</p>")
    return "".join(out)


def section(label, sub, o):
    if not o:
        return ""
    h = [f'<section><div class="tag"><b>{esc(label)}</b><span>{esc(sub)}</span></div>']
    if o.get("title"):
        h.append(f"<h2>{esc(o['title'])}</h2>")
    if o.get("target"):
        h.append(f'<div class="target">{esc(o["target"])}</div>')
    h.append(f'<div class="body">{paras(o.get("body"))}</div>')
    if o.get("question"):
        h.append(f'<div class="q">{esc(o["question"])}</div>')
    notes = o.get("notes") or []
    if notes:
        h.append('<div class="notes"><div class="nt">附註</div><ol>'
                 + "".join(f"<li>{esc(n)}</li>" for n in notes) + "</ol></div>")
    src = o.get("source") or {}
    if re.match(r"^https?://", src.get("url") or ""):
        h.append(f'<div class="src">來源：<a href="{esc(src["url"])}" rel="noopener">{esc(src.get("title") or src["url"])}</a></div>')
    h.append("</section>")
    return "".join(h)


def sections(x):
    if x.get("edition") == "night":
        s = "".join(section(it.get("tag", ""), it.get("sub", ""), it) for it in x.get("items") or [])
        if x.get("sleep"):
            s += f'<section><div class="tag"><b>帶進睡眠</b></div><div class="body">{paras(x["sleep"])}</div></section>'
        return s
    les = x.get("lesson") or {}
    sub = (les.get("series") or "") + (f"・第 {les['no']} 課" if les.get("no") else "")
    g = lambda k, f, d="": (x.get(k) or {}).get(f) or d
    return "".join([
        section("新聞", "值得知道", x.get("news")),
        section("主食", "反方", x.get("main")),
        section("主線", sub, x.get("lesson")),
        section("刺青", g("tattoo", "topic"), x.get("tattoo")),
        section("電子音樂", g("music", "topic"), x.get("music")),
        section("百千", g("own", "kind", "自己寫的"), x.get("own")),
        section("興趣的藝術", g("craft", "domain"), x.get("craft")),
        section("文學", g("lit", "kind", "讀"), x.get("lit")),
        section("調味", "遠方", x.get("far")),
    ])


CSS = """
:root{--paper:#f4f0e8;--ink:#1b1a18;--ink2:#55514a;--ink3:#8d877c;--line:#d9d2c4;--seal:#b0342a;--card:#fbf8f2}
@media (prefers-color-scheme:dark){:root{--paper:#121110;--ink:#ebe6dc;--ink2:#b3ac9f;--ink3:#7a7469;--line:#2c2a26;--seal:#d0574a;--card:#1a1917}}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:"Noto Sans TC",system-ui,sans-serif;font-size:17px;line-height:1.85;overflow-wrap:anywhere}
main{max-width:640px;margin:0 auto;padding:40px 22px 80px}a{color:var(--ink2)}
.brand{font-family:"Noto Serif TC",serif;font-weight:900;letter-spacing:.3em;color:var(--seal);text-decoration:none}
.date{color:var(--ink2);font-family:"Noto Serif TC",serif;margin:6px 0 18px}
h1{font-family:"Noto Serif TC",serif;font-weight:600;font-size:26px;line-height:1.6;margin:0 0 10px}
.open{font-family:"Noto Serif TC",serif;font-size:19px;color:var(--ink2);margin:0 0 10px}
.swipe{font-size:14px;margin-bottom:24px}
section{border-top:1px solid var(--line);padding-top:24px;margin-top:28px}
.tag{display:flex;gap:10px;align-items:baseline;margin-bottom:8px}.tag b{font-family:"Noto Serif TC",serif;font-weight:900;font-size:14px;color:var(--seal);letter-spacing:.18em}.tag span{font-size:12px;color:var(--ink3)}
h2{font-family:"Noto Serif TC",serif;font-weight:600;font-size:22px;line-height:1.5;margin:0 0 12px}
.target{font-size:13px;color:var(--ink2);border-left:2px solid var(--seal);padding-left:10px;margin:0 0 14px}
.body p{margin:0 0 14px}sup.fn{color:var(--seal);font-size:11px;font-weight:600}
.q{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px;font-family:"Noto Serif TC",serif}.q::before{content:"問　";color:var(--seal);font-weight:900}
.notes{font-size:14px;color:var(--ink2);margin-top:14px}.nt{color:var(--ink3);font-size:13px}.notes ol{padding-left:20px;margin:6px 0}
.src{font-size:13px;color:var(--ink3);margin-top:10px}
nav.pn{display:flex;justify-content:space-between;gap:12px;border-top:1px solid var(--line);margin-top:40px;padding-top:18px;font-size:14px}
footer{margin-top:30px;font-size:13px;color:var(--ink3)}
ul.list{list-style:none;padding:0}ul.list li{border-bottom:1px solid var(--line);padding:10px 2px}ul.list small{display:block;color:var(--ink3)}
"""


def page(title, desc, canonical, body, og=None):
    if og:
        img = (f'<meta property="og:image" content="{esc(og["url"])}">\n'
               f'<meta property="og:image:width" content="1200">\n'
               f'<meta property="og:image:height" content="630">\n'
               f'<meta property="og:image:alt" content="{esc(og["alt"])}">\n'
               f'<meta name="twitter:card" content="summary_large_image">\n'
               f'<meta name="twitter:image" content="{esc(og["url"])}">')
    else:
        img = f'<meta property="og:image" content="{SITE}img/studio-wall.jpeg">'
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{esc(canonical)}">
{img}
<style>{CSS}</style>
</head>
<body><main>
{body}
<footer>百千報由 AI 協作撰寫，<a href="../../">侯百千</a>主編並發行。</footer>
</main></body>
</html>
"""


def main():
    issues = json.loads((ISSUES / "index.json").read_text("utf-8"))["issues"]
    issues.sort(key=lambda i: str(i.get("published")))
    OUT.mkdir(exist_ok=True)
    keep = set()
    for n, meta in enumerate(issues):
        iid = meta["id"]
        x = json.loads((ISSUES / f"{iid}.json").read_text("utf-8"))
        headline = meta.get("title") or (x.get("main") or {}).get("title") or ""
        no = x.get("issue_no", meta.get("issue_no"))
        title = f"{headline}｜百千報第 {no} 期"
        desc = x.get("opening") or headline
        url = f"{SITE}news/p/{iid}.html"
        prev_ = issues[n - 1] if n > 0 else None
        next_ = issues[n + 1] if n + 1 < len(issues) else None
        pn = '<nav class="pn"><span>' + (
            f'<a href="{prev_["id"]}.html">← 第 {prev_["issue_no"]} 期</a>' if prev_ else "") + \
            '</span><a href="../archive.html">所有期數</a><span>' + (
            f'<a href="{next_["id"]}.html">第 {next_["issue_no"]} 期 →</a>' if next_ else "") + "</span></nav>"
        body = (f'<a class="brand" href="../">百千報</a>'
                f'<div class="date">第 {esc(no)} 期　{esc(when(x))}{"　夜刊" if x.get("edition") == "night" else ""}</div>'
                f"<h1>{esc(headline)}</h1>"
                f'<p class="open">{esc(x.get("opening"))}</p>'
                f'<div class="swipe"><a href="../#{esc(iid)}">用滑卡讀這一期，也可以寫信給侯百千 →</a></div>'
                f"{sections(x)}{pn}")
        og = None
        if (NEWS / "og" / f"{iid}.png").exists():
            og = {"url": f"{SITE}news/og/{iid}.png", "alt": f"百千報第 {no} 期：{headline}"}
        (OUT / f"{iid}.html").write_text(page(title, desc, url, body, og), "utf-8")
        keep.add(f"{iid}.html")
    for f in OUT.glob("*.html"):
        if f.name not in keep:
            f.unlink()

    items = "".join(
        f'<li><a href="p/{i["id"]}.html">第 {i["issue_no"]} 期　{esc(i.get("title"))}</a>'
        f'<small>{esc(when(i))}{"・夜刊" if i.get("edition") == "night" else ""}</small></li>'
        for i in reversed(issues))
    archive = page("所有期數｜百千報", "百千報往期目錄：一期一期出的白話小報，新聞、反方、意識科學、刺青、電子音樂與侯百千的作品。",
                   f"{SITE}news/archive.html",
                   '<a class="brand" href="./">百千報</a><h1>所有期數</h1>'
                   '<p class="open">一期一期出的白話小報。最新一期用滑卡讀：<a href="./">百千報</a></p>'
                   f'<ul class="list">{items}</ul>')
    (NEWS / "archive.html").write_text(archive.replace('href="../../"', 'href="../"'), "utf-8")

    urls = [SITE] + [SITE + p.name for p in sorted(ROOT.glob("*.html")) if p.name != "index.html" and not p.name.startswith("google")]
    urls += [SITE + "news/", SITE + "news/archive.html"]
    urls += [f"{SITE}news/p/{i['id']}.html" for i in issues]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sm += "".join(f"  <url><loc>{esc(u)}</loc></url>\n" for u in urls) + "</urlset>\n"
    (ROOT / "sitemap.xml").write_text(sm, "utf-8")
    print(f"{len(issues)} 期，sitemap {len(urls)} 個網址")


if __name__ == "__main__":
    main()
