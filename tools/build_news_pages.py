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


EN = False  # 英文版（每期 JSON 的 lang 為 "en"）時切換介面文字


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
        h.append(f'<div class="q{" en" if EN else ""}">{esc(o["question"])}</div>')
    notes = o.get("notes") or []
    if notes:
        h.append('<div class="notes"><div class="nt">' + ("Notes" if EN else "附註") + '</div><ol>'
                 + "".join(f"<li>{esc(n)}</li>" for n in notes) + "</ol></div>")
    src = o.get("source") or {}
    if re.match(r"^https?://", src.get("url") or ""):
        h.append(f'<div class="src">{"Source: " if EN else "來源："}<a href="{esc(src["url"])}" rel="noopener">{esc(src.get("title") or src["url"])}</a></div>')
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
    T = ({"news": "News", "main": "Main", "lesson": "Thread", "tattoo": "Tattoo", "music": "Electronic music",
          "own": "Hundred", "craft": "Arts", "lit": "Literature", "far": "Far away"} if EN else
         {"news": "新聞", "main": "主食", "lesson": "主線", "tattoo": "刺青", "music": "音樂",
          "own": "百千", "craft": "興趣的藝術", "lit": "文學", "far": "調味"})
    parts = [
        ("news", section(T["news"], "Worth knowing" if EN else "值得知道", x.get("news"))),
        ("main", section(T["main"], g("main", "label", "反方"), x.get("main"))),  # 特輯的主食可另標（如「入門」）
        ("lesson", section(T["lesson"], sub, x.get("lesson"))),
        ("tattoo", section(T["tattoo"], g("tattoo", "topic"), x.get("tattoo"))),
        ("music", section(T["music"], g("music", "topic"), x.get("music"))),
        ("own", section(T["own"], g("own", "kind", "自己寫的"), x.get("own"))),
        ("craft", section(T["craft"], g("craft", "domain"), x.get("craft"))),
        ("lit", section(T["lit"], g("lit", "kind", "讀"), x.get("lit"))),
        ("far", section(T["far"], "遠方", x.get("far"))),
    ]
    # 期數 JSON 有 order 時照它排；沒有 order 的舊期維持原順序
    order = x.get("order")
    if isinstance(order, list):
        pos = lambda i: order.index(parts[i][0]) if parts[i][0] in order else 99 + i
        parts = [parts[i] for i in sorted(range(len(parts)), key=pos)]
    return "".join(h for _, h in parts)


CSS = """
:root{--paper:#f4f0e8;--ink:#1b1a18;--ink2:#55514a;--ink3:#8d877c;--line:#d9d2c4;--seal:#b0342a;--card:#fbf8f2}
html.dark{--paper:#121110;--ink:#ebe6dc;--ink2:#b3ac9f;--ink3:#7a7469;--line:#2c2a26;--seal:#d0574a;--card:#1a1917}
.mode{position:fixed;top:10px;right:14px;display:flex;align-items:center;gap:4px;font-size:11px;color:var(--ink3);letter-spacing:.06em;background:var(--paper);padding:2px 4px;border-radius:6px}
.mode button{font:inherit;font-family:"Noto Serif TC",serif;font-size:11px;line-height:1;padding:3px 5px;border:1px solid var(--line);border-radius:4px;background:transparent;color:var(--ink3);cursor:pointer}
.mode button{width:16px;height:16px;padding:0;border:1.5px solid var(--ink2);border-radius:50%;color:transparent;font-size:0;background:transparent}
html.dark .mode button{background:var(--ink);border-color:var(--ink)}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:"Noto Sans TC",system-ui,sans-serif;font-size:17px;line-height:1.85;overflow-wrap:anywhere}
main{max-width:640px;margin:0 auto;padding:40px 22px 80px}a{color:var(--ink2)}
.art{width:100%;height:38vh;max-height:360px;margin:22px auto 8px;background:var(--ink);-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;-webkit-mask-position:center;mask-position:center;-webkit-mask-size:contain;mask-size:contain}
.brand{font-family:"Noto Serif TC",serif;font-weight:900;letter-spacing:.3em;color:var(--seal);text-decoration:none}
.brand .en{font-size:.62em;font-weight:400;letter-spacing:.1em;color:var(--ink3);margin-left:.5em}
.date{color:var(--ink2);font-family:"Noto Serif TC",serif;margin:6px 0 18px}
h1{font-family:"Noto Serif TC",serif;font-weight:600;font-size:26px;line-height:1.6;margin:0 0 10px}
.open{font-family:"Noto Serif TC",serif;font-size:19px;color:var(--ink2);margin:0 0 10px}
.swipe{font-size:14px;margin-bottom:24px}
section{border-top:1px solid var(--line);padding-top:24px;margin-top:28px}
.tag{display:flex;gap:10px;align-items:baseline;margin-bottom:8px}.tag b{font-family:"Noto Serif TC",serif;font-weight:900;font-size:14px;color:var(--seal);letter-spacing:.18em}.tag span{font-size:12px;color:var(--ink3)}
h2{font-family:"Noto Serif TC",serif;font-weight:600;font-size:22px;line-height:1.5;margin:0 0 12px}
.target{font-size:13px;color:var(--ink2);border-left:2px solid var(--seal);padding-left:10px;margin:0 0 14px}
.body p{margin:0 0 14px}sup.fn{color:var(--seal);font-size:11px;font-weight:600}
.q{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px;font-family:"Noto Serif TC",serif}.q::before{content:"問　";color:var(--seal);font-weight:900}.q.en::before{content:"Q  "}
.notes{font-size:14px;color:var(--ink2);margin-top:14px}.nt{color:var(--ink3);font-size:13px}.notes ol{padding-left:20px;margin:6px 0}
.src{font-size:13px;color:var(--ink3);margin-top:10px}
nav.pn{display:flex;justify-content:space-between;gap:12px;border-top:1px solid var(--line);margin-top:40px;padding-top:18px;font-size:14px}
footer{margin-top:30px;font-size:13px;color:var(--ink3)}
.intro .body ul{padding-left:20px;margin:0 0 14px}.intro .body li{margin-bottom:6px}
.letter h3{font-family:"Noto Serif TC",serif;font-weight:600;font-size:18px;margin:0 0 12px}
form.msg input,form.msg textarea{display:block;width:100%;margin:0 0 10px;padding:10px 12px;font:inherit;font-size:15px;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:8px}
form.msg .row{display:flex;justify-content:space-between;align-items:center;gap:12px}.hintx{font-size:13px;color:var(--ink3)}
form.msg button{font:inherit;font-size:15px;padding:8px 20px;border:0;border-radius:8px;background:var(--seal);color:#fff;cursor:pointer}
ul.list{list-style:none;padding:0}ul.list li{border-bottom:1px solid var(--line);padding:10px 2px}ul.list small{display:block;color:var(--ink3)}
"""


MODE_JS = """<script>
/* 日夜：依台北日出日落自動切換；按「日」「夜」手動切換，維持到下一次日出或日落 */
(function(){
  var LAT=25.04, LON=121.56, R=Math.PI/180;
  function sun(dayMs){ // dayMs: 該日任一時刻；回傳 [日出ms, 日落ms]
    var jd=Math.floor((dayMs+28800000)/86400000)+2440588;
    var n=Math.ceil(jd-2451545.0+0.0008), js=n-LON/360;
    var M=(357.5291+0.98560028*js)%360, C=1.9148*Math.sin(M*R)+0.02*Math.sin(2*M*R)+0.0003*Math.sin(3*M*R);
    var L=(M+C+180+102.9372)%360, jt=2451545+js+0.0053*Math.sin(M*R)-0.0069*Math.sin(2*L*R);
    var d=Math.asin(Math.sin(L*R)*Math.sin(23.4397*R));
    var w=Math.acos((Math.sin(-0.833*R)-Math.sin(LAT*R)*Math.sin(d))/(Math.cos(LAT*R)*Math.cos(d)))/R;
    var ms=function(j){return (j-2440587.5)*86400000;};
    return [ms(jt-w/360), ms(jt+w/360)];
  }
  function state(now){
    var t=sun(now), r=t[0], s=t[1];
    if(now<r){ var y=sun(now-86400000); if(now<y[1]) return {day:true,next:y[1]}; return {day:false,next:r}; }
    if(now<s) return {day:true,next:s};
    return {day:false,next:sun(now+86400000)[0]};
  }
  function get(){ try{ return JSON.parse(localStorage.getItem('hundred-mode')||'null'); }catch(e){ return null; } }
  function put(v){ try{ localStorage.setItem('hundred-mode',JSON.stringify(v)); }catch(e){} }
  function apply(){
    var now=Date.now(), st=state(now), o=get(), day=st.day;
    if(o && now<o.until) day=(o.m==='day'); else if(o) put(null);
    document.documentElement.classList.toggle('dark',!day);
    var b=document.getElementById('modebtn');
    if(b){ b.textContent=day?'日':'夜'; b.setAttribute('aria-label',day?'目前日間，按一下切換到夜間':'目前夜間，按一下切換到日間'); }
    window.hundredDay=day;
  }
  window.hundredMode=function(m){ if(m==='toggle') m=window.hundredDay?'night':'day'; put({m:m,until:state(Date.now()).next}); apply(); };
  apply();
  document.addEventListener('DOMContentLoaded',function(){ apply(); setInterval(apply,60000); });
})();
</script>"""

MODE_HTML = '<div class="mode"><button type="button" id="modebtn" onclick="hundredMode(\'toggle\')" aria-label="切換日夜">日</button></div>'


def intro_html():
    """楔子只寫在 news/index.html 的 INTRO 一處；單頁從那裡讀，改一處兩邊一起變。"""
    src = (NEWS / "index.html").read_text("utf-8")
    m = re.search(r"const INTRO = (.*?);\n", src, re.S)
    if not m:
        return ""
    return "".join(re.findall(r"'((?:[^'\\]|\\.)*)'", m.group(1)))


FORMSPREE = "https://formspree.io/f/mreyadad"


def letter_form_en(label, iid):
    return (f'<section class="letter"><h3>Write to Hou Bai-Qian</h3>'
            f'<form class="msg" action="{FORMSPREE}" method="POST">'
            f'<input type="hidden" name="_subject" value="百千報讀者來信（{esc(label)}）">'
            f'<input type="hidden" name="issue" value="{esc(label)} {esc(iid)}">'
            '<input type="text" name="name" placeholder="Your name" required>'
            '<input type="email" name="email" placeholder="Email (he will reply here)" required>'
            '<textarea name="message" rows="4" placeholder="Thoughts, disagreements, ideas" required></textarea>'
            '<div class="row"><span class="hintx"></span><button type="submit">Send</button></div></form></section>')


def letter_form(label, iid):
    return (f'<section class="letter"><h3>寫信給侯百千</h3>'
            f'<form class="msg" action="{FORMSPREE}" method="POST">'
            f'<input type="hidden" name="_subject" value="百千報讀者來信（{esc(label)}）">'
            f'<input type="hidden" name="issue" value="{esc(label)} {esc(iid)}">'
            '<input type="text" name="name" placeholder="你的名字" required>'
            '<input type="email" name="email" placeholder="Email（他會回信到這裡）" required>'
            '<textarea name="message" rows="4" placeholder="讀完想說的話、反駁、題目建議都可以" required></textarea>'
            '<div class="row"><span class="hintx"></span><button type="submit">送出</button></div></form></section>')


# 有 JavaScript 時留在原頁顯示結果；沒有 JavaScript 時表單照常送出到 Formspree
FORM_JS = """<script>
document.querySelectorAll('form.msg').forEach(f=>f.addEventListener('submit',async e=>{
  e.preventDefault();const h=f.querySelector('.hintx');h.textContent='送出中⋯';
  try{const r=await fetch(f.action,{method:'POST',body:new FormData(f),headers:{'Accept':'application/json'}});
    if(r.ok){f.reset();h.textContent='收到了，謝謝你。';}else h.textContent='沒送出，稍後再試，或寄信到 monbaician@gmail.com';}
  catch(err){h.textContent='沒送出，稍後再試，或寄信到 monbaician@gmail.com';}
}));
</script>"""


def page(title, desc, canonical, body, og=None):
    if og:
        img = (f'<meta property="og:image" content="{esc(og["url"])}">\n'
               f'<meta property="og:image:width" content="1200">\n'
               f'<meta property="og:image:height" content="630">\n'
               f'<meta property="og:image:alt" content="{esc(og["alt"])}">\n'
               f'<meta name="twitter:card" content="summary_large_image">\n'
               f'<meta name="twitter:image" content="{esc(og["url"])}">')
    else:
        img = f'<meta property="og:image" content="{SITE}news/og/default.png">'
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="author" content="侯百千">
<link rel="canonical" href="{esc(canonical)}">
<link rel="icon" href="../../favicon.ico" sizes="any"><link rel="icon" type="image/png" href="../../icon-192.png"><link rel="apple-touch-icon" href="../../apple-touch-icon.png">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{esc(canonical)}">
{img}
<style>{CSS}</style>
{MODE_JS}
</head>
<body>{MODE_HTML}<main>
{body}
<footer><a href="../../">侯百千</a>主編、發行，AI 協作的刊物。</footer>
</main></body>
</html>
"""


def lab(i):
    """特輯（index.json 有 special）不佔期數，標「特輯・名稱」。"""
    return f'特輯・{i["special"]}' if i.get("special") else f'第 {i.get("issue_no")} 期'


def main():
    issues = json.loads((ISSUES / "index.json").read_text("utf-8"))["issues"]
    issues.sort(key=lambda i: str(i.get("published")))
    regular = [i for i in issues if not i.get("special")]
    OUT.mkdir(exist_ok=True)
    keep = set()
    INTRO = intro_html()
    global EN
    for n, meta in enumerate(issues):
        iid = meta["id"]
        x = json.loads((ISSUES / f"{iid}.json").read_text("utf-8"))
        EN = x.get("lang") == "en" or meta.get("lang") == "en"
        alt = x.get("alt") or {}
        alt_link = (f'<div class="swipe"><a href="{esc(alt["id"])}.html">{esc(alt.get("label") or alt["id"])} →</a></div>'
                    if alt.get("id") else "")
        # 標題跟滑卡一致：有 order 就用第一張卡的標題（2026-11-15 主編定），沒有 order 的舊期照 index.json
        # 第 12 期起開場白跟著第一張卡走；特輯與第 11 期以前照原本標題
        first = None if meta.get("special") or not isinstance(x.get("issue_no"), int) or x["issue_no"] < 12 else \
            next((x.get(k) for k in (x.get("order") or []) if isinstance(x.get(k), dict) and x[k].get("title")), None)
        headline = (first or {}).get("title") or meta.get("title") or (x.get("main") or {}).get("title") or ""
        meta["_headline"] = headline
        no = x.get("issue_no", meta.get("issue_no"))
        L = lab(meta)
        title = f"{headline}｜百千報 The Hundred {L}" if not EN else f"{headline} | The Hundred (百千報)"
        desc = x.get("opening") or headline
        url = f"{SITE}news/p/{iid}.html"
        if EN:
            t = datetime.fromisoformat(x["published"]).astimezone(TPE)
            en_when = f"{t:%A} {t.day} {t:%B %Y}"
        # 上一期／下一期只在常規期之間跳；特輯頁沒有上下期，只連回所有期數
        r = regular.index(meta) if meta in regular else None
        prev_ = regular[r - 1] if r else None
        next_ = regular[r + 1] if r is not None and r + 1 < len(regular) else None
        pn = '<nav class="pn"><span>' + (
            f'<a href="{prev_["id"]}.html">← 第 {prev_["issue_no"]} 期</a>' if prev_ else "") + \
            '</span><a href="../archive.html">所有期數</a><span>' + (
            f'<a href="{next_["id"]}.html">第 {next_["issue_no"]} 期 →</a>' if next_ else "") + "</span></nav>"
        LEGACY_ROTATION = 20  # 只給沒寫 art 的舊期輪流用，固定不改；畫的張數只記在 meta/editor.art_count
        a = x.get("art")
        art_n = 0 if x.get("edition") == "night" else (int(a) if isinstance(a, int) and a >= 1 else ((int(no) - 1) % LEGACY_ROTATION + 1 if isinstance(no, int) and no > 0 else 0))
        art = (f'<div class="art" role="img" aria-label="侯百千的畫" style="-webkit-mask-image:url(../art/{art_n:02d}.webp);mask-image:url(../art/{art_n:02d}.webp)"></div>' if art_n else "")
        if EN:
            body = (f'<a class="brand" href="../">百千報<span class="en">The Hundred</span></a>{art}'
                    f'<div class="date">{esc(meta.get("special") or "")}　{esc(en_when)}</div>'
                    f"<h1>{esc(headline)}</h1>"
                    f'<p class="open">{esc(x.get("opening"))}</p>{alt_link}'
                    f"{sections(x)}"
                    f'{letter_form_en(L, iid)}<nav class="pn"><span></span><a href="../archive.html">All issues (in Chinese)</a><span></span></nav>{FORM_JS}')
        else:
          body = (f'<a class="brand" href="../">百千報<span class="en">The Hundred</span></a>{art}'
                f'<div class="date">{esc(L)}　{esc(when(x))}{"　夜刊" if x.get("edition") == "night" else ""}</div>'
                f"<h1>{esc(headline)}</h1>"
                f'<p class="open">{esc(x.get("opening"))}</p>'
                f'{alt_link}<div class="swipe"><a href="../#{esc(iid)}">用滑卡讀這一期，也可以寫信給侯百千 →</a></div>'
                f"{sections(x)}"
                f'<section class="intro">{INTRO}</section>'
                f"{letter_form(L, iid)}{pn}{FORM_JS}")
        og = None
        if (NEWS / "og" / f"{iid}.png").exists():
            og = {"url": f"{SITE}news/og/{iid}.png", "alt": f"百千報 The Hundred {L}：{headline}"}
        (OUT / f"{iid}.html").write_text(page(title, desc, url, body, og), "utf-8")
        keep.add(f"{iid}.html")
    for f in OUT.glob("*.html"):
        if f.name not in keep:
            f.unlink()

    items = "".join(
        f'<li><a href="p/{i["id"]}.html">{esc(lab(i))}{"　" + esc(i.get("_headline") or i.get("title")) if not i.get("special") or i.get("title") != i["special"] else ""}</a>'
        f'<small>{esc(when(i))}{"・夜刊" if i.get("edition") == "night" else ""}</small></li>'
        for i in reversed(issues) if i.get("lang") != "en")  # 英文版不另列，從中文頁的連結進入
    archive = page("所有期數｜百千報 The Hundred", "百千報往期目錄：侯百千主編、發行，AI 協作的刊物。一期一期出的白話小報，新聞、反方、意識科學、刺青、音樂與侯百千的作品。",
                   f"{SITE}news/archive.html",
                   '<a class="brand" href="./">百千報<span class="en">The Hundred</span></a><h1>所有期數</h1>'
                   '<p class="open">一期一期出的白話小報。最新一期用滑卡讀：<a href="./">百千報</a></p>'
                   f'<ul class="list">{items}</ul>')
    (NEWS / "archive.html").write_text(archive.replace('href="../../', 'href="../'), "utf-8")

    urls = [SITE] + [SITE + p.name for p in sorted(ROOT.glob("*.html")) if p.name != "index.html" and not p.name.startswith("google")]
    urls += [SITE + "news/", SITE + "news/archive.html"]
    urls += [f"{SITE}news/p/{i['id']}.html" for i in issues]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sm += "".join(f"  <url><loc>{esc(u)}</loc></url>\n" for u in urls) + "</urlset>\n"
    (ROOT / "sitemap.xml").write_text(sm, "utf-8")
    print(f"{len(issues)} 期，sitemap {len(urls)} 個網址")


if __name__ == "__main__":
    main()
