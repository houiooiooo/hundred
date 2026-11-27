#!/usr/bin/env python3
"""百千報：產生每期的靜態文字頁、往期目錄與 sitemap，讓搜尋引擎讀得到。

用法（在 repo 根目錄）：python3 tools/build_news_pages.py
每次新增或修改 news/issues/*.json 之後跑一次，再一起 commit。
"""
import html, json, re
from urllib.parse import quote
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


def body_html(s):
    """正文；有「背景｜標題」段落時，從那段到結尾顯示成獨立方框（與滑卡 news/index.html 的 bodyHtml 一致）。"""
    ps = [p.strip() for p in re.split(r"\n\s*\n", str(s or "")) if p.strip()]
    i = next((k for k, p in enumerate(ps) if p.startswith("背景｜")), -1)
    if i < 0:
        return f'<div class="body">{paras(s)}</div>'
    head = re.sub(r"\[(\d{1,2})\]", r'<sup class="fn">\1</sup>', esc(ps[i]))
    return (f'<div class="body">{paras((chr(10)*2).join(ps[:i]))}</div>'
            f'<aside class="bg"><div class="bgt">{head}</div><div class="body">{paras((chr(10)*2).join(ps[i+1:]))}</div></aside>')


EN = False  # 英文版（每期 JSON 的 lang 為 "en"）時切換介面文字


CUR = None  # 正在產生的那一期 id；section() 用它組出單篇網址

KEYS = ["news", "main", "lesson", "tattoo", "music", "own", "craft", "lit", "far"]
COL = {"news": "新聞", "tattoo": "刺青", "music": "音樂", "own": "百千", "craft": "興趣的藝術", "lit": "文學", "far": "遠方"}
CON = ("反方", "Counterpoint")


def column(key, o):
    """欄位標籤：讀者在頁面上看到的欄名（特輯另標的照特輯）。"""
    if re.fullmatch(r"n\d+", key):  # 夜刊
        return {"回顧": "意識科學", "聽": "音樂"}.get(o.get("tag"), o.get("tag") or "夜刊")
    if o.get("sub") in CON or o.get("series") in CON or o.get("label") in CON:
        return "反方"
    if o.get("tag"):  # 特輯自己標的欄名（例如「rave 特輯」），單篇與標籤頁照它歸欄
        return o["tag"]
    if key == "main":
        return {"Primer": "入門"}.get(o.get("label"), o.get("label") or "反方")
    if key == "lesson":
        return o.get("series") or "意識科學"
    return COL.get(key, key)


def article_tags(o, key):
    ts = [column(key, o)]
    for t in o.get("tags") or []:
        t = str(t).strip()
        if t and t not in ts:
            ts.append(t)
    return ts


def tag_href(t, prefix="../"):
    return f"{prefix}t/{quote(t)}.html"


def tag_chips(o, key, prefix="../"):
    """單篇網址＋標籤（欄位標籤在前、主題標籤在後）。"""
    if not CUR or not key:
        return ""
    ts = article_tags(o, key)
    chips = "".join(f'<a class="chip" href="{tag_href(t, prefix)}">#{esc(t)}</a>' for t in ts)
    one = ("Permalink" if EN else "單篇網址")
    return f'<div class="meta"><a href="{prefix}a/{esc(CUR)}-{esc(key)}.html">{one}</a>{chips}</div>'


def section(label, sub, o, key=None):
    if not o:
        return ""
    # 特輯可在欄位裡寫 tag／sub 改卡片標籤（例如把第二篇反方放在 craft 欄、標成「主線・反方」）
    label = o.get("tag") or label
    sub = o.get("sub") if o.get("sub") is not None else sub
    h = [f'<section><div class="tag"><b>{esc(label)}</b><span>{esc(sub)}</span></div>']
    if o.get("title"):
        h.append(f"<h2>{esc(o['title'])}</h2>")
    h.append(inner(o))
    h.append(tag_chips(o, key))
    h.append("</section>")
    return "".join(h)


def inner(o):
    """一篇的內文（副標、正文、提問、附註、來源）；每期頁和單篇頁共用。"""
    h = []
    if o.get("target"):
        h.append(f'<div class="target">{esc(o["target"])}</div>')
    figs = o.get("figure") or []
    for fig in (figs if isinstance(figs, list) else [figs]):  # 作品圖（2026-11-20 夜刊起：公眾領域館藏圖，熱連結官方原圖；2026-11-27 起可為陣列）
        if not isinstance(fig, dict) or not re.match(r"^https://", fig.get("src") or ""):
            continue
        img = f'<img src="{esc(fig["src"])}" alt="{esc(fig.get("alt") or "")}" loading="lazy" decoding="async">'
        if re.match(r"^https?://", fig.get("href") or ""):
            img = f'<a href="{esc(fig["href"])}" rel="noopener">{img}</a>'
        h.append(f'<figure class="work">{img}<figcaption>{esc(fig.get("caption") or "")}</figcaption></figure>')
    vid = o.get("video") or {}
    if re.match(r"^https://(www\.nfb\.ca|www\.youtube-nocookie\.com|player\.vimeo\.com)/", vid.get("embed") or ""):  # 影片作品（2026-11-26 夜刊起：只嵌官方播放器）
        cap = esc(vid.get("caption") or "")
        if re.match(r"^https?://", vid.get("href") or ""):
            cap += f'　<a href="{esc(vid["href"])}" rel="noopener">官方頁面</a>'
        h.append(f'<figure class="work vid"><div class="vf"><iframe src="{esc(vid["embed"])}" title="{esc(vid.get("title") or "影片")}" loading="lazy" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe></div><figcaption>{cap}</figcaption></figure>')
    if o.get("pre"):  # 讀前小卡：正文前的獨立導讀（2026-11-18《世界的晶片》兩集試行）
        h.append(f'<aside class="pre"><div class="pret">讀前｜這篇在說什麼</div>{paras(o["pre"])}</aside>')
    h.append(body_html(o.get("body")))
    if o.get("question"):
        h.append(f'<div class="q{" en" if EN else ""}">{esc(o["question"])}</div>')
    notes = o.get("notes") or []
    if notes:
        h.append('<div class="notes"><div class="nt">' + ("Notes" if EN else "附註") + '</div><ol>'
                 + "".join(f"<li>{esc(n)}</li>" for n in notes) + "</ol></div>")
    src = o.get("source") or {}
    if re.match(r"^https?://", src.get("url") or ""):
        h.append(f'<div class="src">{"Source: " if EN else "來源："}<a href="{esc(src["url"])}" rel="noopener">{esc(src.get("title") or src["url"])}</a></div>')
    return "".join(h)


def sections(x):
    if x.get("edition") == "night":
        s = "".join(section(it.get("tag", ""), it.get("sub", ""), it, f"n{i + 1}") for i, it in enumerate(x.get("items") or []))
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
        ("news", section(T["news"], "Worth knowing" if EN else "值得知道", x.get("news"), "news")),
        ("main", section(T["main"], g("main", "label", "反方"), x.get("main"), "main")),  # 特輯的主食可另標（如「入門」）
        ("lesson", section(T["lesson"], sub, x.get("lesson"), "lesson")),
        ("tattoo", section(T["tattoo"], g("tattoo", "topic"), x.get("tattoo"), "tattoo")),
        ("music", section(T["music"], g("music", "topic"), x.get("music"), "music")),
        ("own", section(T["own"], g("own", "kind", "自己寫的"), x.get("own"), "own")),
        ("craft", section(T["craft"], g("craft", "domain"), x.get("craft"), "craft")),
        ("lit", section(T["lit"], g("lit", "kind", "讀"), x.get("lit"), "lit")),
        ("far", section(T["far"], "遠方", x.get("far"), "far")),
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
.work{margin:6px 0 24px}.work img{display:block;width:100%;height:auto;border-radius:6px;background:var(--card)}.work figcaption{font-size:12px;line-height:1.6;color:var(--ink2);margin-top:8px}.vid .vf{position:relative;aspect-ratio:16/9;border-radius:6px;overflow:hidden;background:#000}.vid iframe{position:absolute;inset:0;width:100%;height:100%;border:0}.pre{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--seal);border-radius:8px;padding:12px 16px 0;margin:4px 0 22px;font-size:15px;line-height:1.8;color:var(--ink2)}.pre .pret{font-size:12px;font-weight:600;color:var(--seal);letter-spacing:.12em;margin-bottom:6px}.pre p{margin:0 0 12px}
.body p{margin:0 0 14px}sup.fn{color:var(--seal);font-size:11px;font-weight:600}
.bg{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px 2px;margin:20px 0 8px;font-size:15px;color:var(--ink2)}
.bg .bgt{font-family:"Noto Serif TC",serif;font-weight:600;color:var(--ink);margin-bottom:8px}
.q{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px;font-family:"Noto Serif TC",serif}.q::before{content:"問　";color:var(--seal);font-weight:900}.q.en::before{content:"Q  "}
.notes{font-size:14px;color:var(--ink2);margin-top:14px}.nt{color:var(--ink3);font-size:13px}.notes ol{padding-left:20px;margin:6px 0}
.src{font-size:13px;color:var(--ink3);margin-top:10px}
.meta{display:flex;flex-wrap:wrap;gap:6px 12px;font-size:13px;margin-top:14px;color:var(--ink3)}.meta a{color:var(--ink3);text-decoration:none}.meta a:first-child{color:var(--seal)}
.chip{white-space:nowrap}a.chip:hover,.meta a:hover{text-decoration:underline}
.crumb{font-size:14px;color:var(--ink2);margin:6px 0 18px}.crumb a{color:var(--ink2)}
.cloud{display:flex;flex-wrap:wrap;gap:8px 14px;margin:8px 0 22px}.cloud a{text-decoration:none;color:var(--ink)}.cloud small{color:var(--ink3);margin-left:3px}
h3.sub{font-family:"Noto Serif TC",serif;font-weight:600;font-size:15px;color:var(--ink3);letter-spacing:.12em;margin:26px 0 6px}
input.find{display:block;width:100%;padding:10px 12px;font:inherit;font-size:16px;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:8px;margin:6px 0 4px}
ul.list li .tg{font-size:12px;color:var(--ink3)}
.share{display:flex;align-items:center;gap:10px;margin:0 0 16px}.share.end{margin:22px 0 0}
button.sh{font:inherit;font-size:14px;padding:6px 16px;border:1px solid var(--line);border-radius:999px;background:var(--card);color:var(--ink);cursor:pointer}
button.sh{display:inline-flex;align-items:center;gap:4px;height:36px;line-height:1}button.sh{padding:0 12px;color:var(--seal)}.shm{font-size:13px;color:var(--ink3)}
nav.pn{display:flex;justify-content:space-between;gap:12px;border-top:1px solid var(--line);margin-top:40px;padding-top:18px;font-size:14px}
footer{margin-top:30px;font-size:13px;color:var(--ink3)}
.intro .body ul{padding-left:20px;margin:0 0 14px}.intro .body li{margin-bottom:6px}
.letter h3{font-family:"Noto Serif TC",serif;font-weight:600;font-size:18px;margin:0 0 12px}
form.msg input,form.msg textarea{display:block;width:100%;margin:0 0 10px;padding:10px 12px;font:inherit;font-size:15px;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:8px}
form.msg .row{display:flex;justify-content:space-between;align-items:center;gap:12px}.hintx{font-size:13px;color:var(--ink3)}
form.msg button{font:inherit;font-size:15px;padding:8px 20px;border:0;border-radius:8px;background:var(--seal);color:#fff;cursor:pointer}
ul.list{list-style:none;padding:0}ul.list li{border-bottom:1px solid var(--line);padding:10px 2px}ul.list small{display:block;color:var(--ink3)}ul.list a.sw{float:right;margin:2px 0 0 12px;color:var(--ink2);line-height:0}ul.list a.sw svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}
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


def ld_tag(ld):
    if not ld:
        return ""
    return '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"


def page(title, desc, canonical, body, og=None, ld=None):
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
{ld_tag(ld)}<link rel="alternate" type="application/rss+xml" title="百千報 The Hundred" href="{SITE}news/feed.xml">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-SGQ2CTBMT4"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-SGQ2CTBMT4');</script>
{MODE_JS}
</head>
<body>{MODE_HTML}<main>
{body}
<footer><a href="../../">侯百千</a>主編、發行，AI 協作的刊物。<br>© 侯百千。歡迎附上原文連結分享、引用；轉載全文或商業使用請先來信。・<a href="{SITE}news/feed.xml">RSS 訂閱</a></footer>
</main></body>
</html>
"""


def lab(i):
    """特輯（index.json 有 special）不佔期數，標「特輯・名稱」。"""
    return f'特輯・{i["special"]}' if i.get("special") else f'第 {i.get("issue_no")} 期'


# ───────── 單篇頁與標籤 ─────────
ARTS = NEWS / "a"
TAGS = NEWS / "t"
COL_ORDER = ["新聞", "反方", "入門", "意識科學", "刺青", "音樂", "百千", "文學", "興趣的藝術", "遠方"]


def labels(x, key, o):
    """卡片上的欄名與小標，跟 sections() 一致。"""
    if re.fullmatch(r"n\d+", key):
        return o.get("tag", ""), o.get("sub", "")
    T = ({"news": "News", "main": "Main", "lesson": "Thread", "tattoo": "Tattoo", "music": "Electronic music",
          "own": "Hundred", "craft": "Arts", "lit": "Literature", "far": "Far away"} if EN else
         {"news": "新聞", "main": "主食", "lesson": "主線", "tattoo": "刺青", "music": "音樂",
          "own": "百千", "craft": "興趣的藝術", "lit": "文學", "far": "調味"})
    sub = {"news": "Worth knowing" if EN else "值得知道", "main": o.get("label") or "反方",
           "lesson": (o.get("series") or "") + (f"・第 {o['no']} 課" if o.get("no") else ""),
           "tattoo": o.get("topic") or "", "music": o.get("topic") or "", "own": o.get("kind") or "自己寫的",
           "craft": o.get("domain") or "", "lit": o.get("kind") or "讀", "far": "遠方"}[key]
    label = o.get("tag") or T[key]
    sub = o.get("sub") if o.get("sub") is not None else sub
    return label, sub


def collect(x, meta, headline, L, og):
    """一期裡的每一篇（有正文的欄位），照這一期的卡片順序。"""
    out = []
    if x.get("items"):
        keyed = [(f"n{i + 1}", it) for i, it in enumerate(x["items"])]
    else:
        ks = list(KEYS)
        if isinstance(x.get("order"), list):
            ks.sort(key=lambda k: x["order"].index(k) if k in x["order"] else 99 + KEYS.index(k))
        keyed = [(k, x[k]) for k in ks if isinstance(x.get(k), dict)]
    for n, (k, o) in enumerate(keyed):
        if not o.get("body") or not o.get("title"):
            continue
        lab_, sub = labels(x, k, o)
        out.append({"slug": f"{meta['id']}-{k}", "iid": meta["id"], "key": k, "o": o, "label": lab_, "sub": sub,
                    "col": column(k, o), "tags": article_tags(o, k), "published": x.get("published") or meta.get("published"),
                    "when": when(x), "L": L, "en": EN, "og": og, "n": n, "alt": (x.get("alt") or {}).get("id")})
    return out


def first_para(s, n=110):
    p = next((q.strip() for q in re.split(r"\n\s*\n", str(s or "")) if q.strip()), "")
    p = re.sub(r"\s*\[\d{1,2}\]", "", p)
    return p if len(p) <= n else p[:n].rstrip() + "⋯"


def share_btn(title, url, end=False, story=None):
    t = f"{title}｜百千報"
    label = "Share" if EN else "分享"
    ig = (f'<button type="button" class="sh ig" data-u="{esc(url)}" data-img="{esc(story)}" data-name="{esc(story.rsplit("/", 1)[-1])}" aria-label="分享到 IG 限動" title="分享到 IG 限動"><svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9" stroke-dasharray="3.2 2.4"/><path d="M12 8v8M8 12h8"/></svg></button>'
          if story else "")
    return (f'<div class="share{" end" if end else ""}"><button type="button" class="sh" data-t="{esc(t)}" data-u="{esc(url)}" aria-label="{label}" title="{label}">'
            f'<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12M7.5 7.5 12 3l4.5 4.5"/><path d="M8 11H6a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-8a1 1 0 0 0-1-1h-2"/></svg></button>{ig}<span class="shm"></span></div>')


# 手機叫出系統分享選單（Threads、IG、LINE…）；不支援時複製連結
SHARE_JS = """<script>
document.querySelectorAll('button.sh:not(.ig)').forEach(function(b){b.onclick=async function(){
  var t=b.dataset.t,u=b.dataset.u,m=b.nextElementSibling;
  if(navigator.share){try{await navigator.share({title:t,text:t,url:u});return;}catch(e){if(e&&e.name==='AbortError')return;}}
  try{await navigator.clipboard.writeText(t+' '+u);m.textContent='已複製連結';}
  catch(e){window.prompt('複製這個連結',u);}
  setTimeout(function(){m.textContent='';},2500);
};});
</script>
<script>
/* 分享到 IG 限動：複製這篇的網址，再把直式限動圖交給手機的分享選單（選 Instagram → 限時動態，再加「連結」貼紙貼上網址）。
   手機不支援分享圖片時，改成下載圖片＋複製網址。圖先預載，點下去才不會因為等下載而被瀏覽器擋掉。 */
(function(){
  var cache = {};
  function load(src){ if(!cache[src]) cache[src] = fetch(src).then(function(r){ if(!r.ok) throw 0; return r.blob(); }).then(function(b){ cache[src+'#b'] = b; return b; }); return cache[src]; }
  window.hundredStoryPreload = function(root){ (root||document).querySelectorAll('button.ig').forEach(function(b){ load(b.dataset.img).catch(function(){}); }); };
  document.addEventListener('click', function(e){
    var b = e.target.closest && e.target.closest('button.ig'); if(!b) return;
    var u = b.dataset.u, src = b.dataset.img, name = b.dataset.name || 'hundred-story.jpg';
    var m = b.parentNode.querySelector('.shm');
    var say = function(t){ if(m){ m.textContent = t; clearTimeout(m._t); m._t = setTimeout(function(){ m.textContent=''; }, 6000); } };
    try{ navigator.clipboard.writeText(u); }catch(err){}
    var blob = cache[src+'#b'];
    if(!blob){ say('圖片準備中，請再按一次'); load(src).then(function(){ say('準備好了，再按一次'); }).catch(function(){ say('圖片載入失敗'); }); return; }
    var file = new File([blob], name, {type:'image/jpeg'});
    if(navigator.canShare && navigator.canShare({files:[file]})){
      say('網址已複製：選 Instagram →「限時動態」，再加「連結」貼紙貼上');
      navigator.share({files:[file]}).catch(function(err){ if(!err || err.name !== 'AbortError') say('沒分享出去，可以再試一次'); });
    } else {
      var a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); a.remove();
      say('已下載限動圖，網址也複製好了');
    }
  });
})();
hundredStoryPreload();
</script>"""


def build_articles(arts):
    global EN, CUR
    CUR = None
    ARTS.mkdir(exist_ok=True)
    TAGS.mkdir(exist_ok=True)
    arts.sort(key=lambda a: (str(a["published"]), a["n"]))
    zh = [a for a in arts if not a["en"]]
    by_slug = {a["slug"]: a for a in arts}
    urls, keep_a, keep_t = [], set(), set()

    for a in arts:
        EN = a["en"]
        o = a["o"]
        chain = [b for b in zh if b["col"] == a["col"]] if not EN else []
        i = chain.index(a) if a in chain else None
        prev_ = chain[i - 1] if i else None
        next_ = chain[i + 1] if i is not None and i + 1 < len(chain) else None
        chips = "".join(f'<a class="chip" href="{tag_href(t)}">#{esc(t)}</a>' for t in a["tags"])
        url = f"{SITE}news/a/{a['slug']}.html"
        story = f"../og/s/{a['slug']}.jpg" if (NEWS / "og" / "s" / f"{a['slug']}.jpg").exists() else None
        if EN:
            zh_slug = f"{a['alt']}-{a['key']}" if a.get("alt") else None
            alt = (f'<div class="swipe"><a href="{esc(zh_slug)}.html">中文版 →</a></div>' if zh_slug in by_slug else "")
            nav = (f'<nav class="pn"><span></span><a href="../p/{esc(a["iid"])}.html">Read the whole issue</a>'
                   f'<a href="../tags.html">Tags (in Chinese)</a></nav>')
            form = letter_form_en(f'{a["L"]}・{o["title"]}', a["slug"])
        else:
            en_slug = next((s for s in (f"{a['alt']}-{a['key']}",) if a.get("alt")), None)
            alt = (f'<div class="swipe"><a href="{esc(en_slug)}.html">English →</a></div>' if en_slug in by_slug else "")
            pn = lambda b, arrow: (f'<a href="{esc(b["slug"])}.html">{arrow}{esc(b["L"])}・{esc(b["o"]["title"])}</a>' if b else "")
            nav = (f'<nav class="pn" style="flex-direction:column;gap:8px">'
                   f'<div class="tg" style="color:var(--ink3);font-size:13px">同一欄的{"上一篇、下一篇" if prev_ or next_ else "文章"}（{esc(a["col"])}）</div>'
                   f'<div>{pn(prev_, "← ")}</div><div>{pn(next_, "→ ")}</div>'
                   f'<div style="margin-top:6px"><a href="../p/{esc(a["iid"])}.html">讀整期（{esc(a["L"])}）</a>・<a href="../tags.html">標籤索引</a>・<a href="../archive.html">所有期數</a></div></nav>')
            form = letter_form(f'{a["L"]}・{o["title"]}', a["slug"])
        body = (f'<a class="brand" href="../">百千報<span class="en">The Hundred</span></a>'
                f'<div class="crumb"><a href="../p/{esc(a["iid"])}.html">{esc(a["L"])}</a>　{esc(a["when"])}</div>'
                f'<div class="tag"><b>{esc(a["label"])}</b><span>{esc(a["sub"])}</span></div>'
                f'<h1>{esc(o["title"])}</h1>{share_btn(o["title"], url, story=story)}{alt}{inner(o)}<div class="meta">{chips}</div>'
                f'{share_btn(o["title"], url, end=True, story=story)}{SHARE_JS}'
                f'{nav}{form}{FORM_JS}')
        title = (f'{o["title"]}｜百千報 The Hundred {a["L"]}' if not EN else f'{o["title"]} | The Hundred (百千報)')
        desc = first_para(o.get("body"))
        ld = {"@context": "https://schema.org", "@type": "Article", "headline": o["title"], "url": url,
              "datePublished": a["published"], "inLanguage": "en" if EN else "zh-Hant", "keywords": a["tags"],
              "articleSection": a["col"], "author": {"@type": "Person", "name": "侯百千", "url": SITE},
              "publisher": {"@type": "Person", "name": "侯百千", "url": SITE},
              "isPartOf": {"@type": "Periodical", "name": "百千報", "alternateName": "The Hundred", "url": SITE + "news/"}}
        og = a["og"]
        if (NEWS / "og" / "a" / f"{a['slug']}.jpg").exists():  # 單篇縮圖：當期的畫＋這一篇的標題（tools/build_og.py）
            og = {"url": f"{SITE}news/og/a/{a['slug']}.jpg", "alt": f"百千報 The Hundred {a['L']}：{o['title']}"}
        if og:
            ld["image"] = og["url"]
        (ARTS / f"{a['slug']}.html").write_text(page(title, desc, url, body, og, ld), "utf-8")
        keep_a.add(f"{a['slug']}.html")
        urls.append(url)
    EN = False

    # 標籤頁：只收中文文章（英文版從中文頁的連結進入）
    groups = {}
    for a in zh:
        for t in a["tags"]:
            groups.setdefault(t, []).append(a)
    li = lambda a: (f'<li><a href="../a/{esc(a["slug"])}.html">{esc(a["o"]["title"])}</a>'
                    f'<small>{esc(a["L"])}・{esc(a["col"])}・{esc(a["when"])}</small></li>')
    for t, xs in groups.items():
        body = (f'<a class="brand" href="../">百千報<span class="en">The Hundred</span></a>'
                f'<div class="crumb"><a href="../tags.html">標籤索引</a></div>'
                f'<h1>#{esc(t)}</h1><p class="open">{len(xs)} 篇</p>'
                f'<ul class="list">{"".join(li(a) for a in reversed(xs))}</ul>'
                '<nav class="pn"><span></span><a href="../tags.html">所有標籤</a><span></span></nav>')
        url = f"{SITE}news/t/{quote(t)}.html"
        (TAGS / f"{t}.html").write_text(page(f"#{t}｜百千報 The Hundred", f"百千報裡標成「{t}」的 {len(xs)} 篇文章。", url, body), "utf-8")
        keep_t.add(f"{t}.html")
        urls.append(url)

    cols = [t for t in COL_ORDER if t in groups] + sorted(t for t in groups if t not in COL_ORDER and any(a["col"] == t for a in groups[t]))
    topics = sorted((t for t in groups if t not in cols), key=lambda t: (-len(groups[t]), t))
    cloud = lambda ts: '<div class="cloud">' + "".join(
        f'<a href="t/{quote(t)}.html">#{esc(t)}<small>{len(groups[t])}</small></a>' for t in ts) + "</div>"
    rows = "".join(
        f'<li data-s="{esc((a["o"]["title"] + " " + " ".join(a["tags"]) + " " + a["L"]).lower())}">'
        f'<a href="a/{esc(a["slug"])}.html">{esc(a["o"]["title"])}</a>'
        f'<small>{esc(a["L"])}・{esc(a["when"])}</small><span class="tg">{" ".join("#" + esc(t) for t in a["tags"])}</span></li>'
        for a in reversed(zh))
    find_js = """<script>
(function(){var q=document.getElementById('q'),ls=document.querySelectorAll('#all li'),n=document.getElementById('n');
function f(){var w=q.value.trim().toLowerCase().replace(/#/g,'').split(/\\s+/).filter(Boolean),c=0;
ls.forEach(function(l){var s=l.getAttribute('data-s'),ok=w.every(function(x){return s.indexOf(x)>=0;});l.style.display=ok?'':'none';if(ok)c++;});
n.textContent=w.length?('找到 '+c+' 篇'):('共 '+ls.length+' 篇');}
q.addEventListener('input',f);var h=decodeURIComponent(location.hash.slice(1));if(h){q.value=h;}f();})();
</script>"""
    body = ('<a class="brand" href="./">百千報<span class="en">The Hundred</span></a><h1>標籤索引</h1>'
            '<p class="open">每一篇都有自己的網址。用欄位或主題找，也可以直接搜標題。</p>'
            '<input class="find" id="q" type="search" placeholder="搜尋標題或標籤，例如：女性　刺青" aria-label="搜尋">'
            '<div class="tg" id="n" style="font-size:13px;color:var(--ink3)"></div>'
            f'<h3 class="sub">欄位</h3>{cloud(cols)}<h3 class="sub">主題</h3>{cloud(topics)}'
            f'<h3 class="sub">所有文章</h3><ul class="list" id="all">{rows}</ul>'
            '<nav class="pn"><a href="./">最新一期</a><a href="archive.html">所有期數</a><a href="feed.xml">RSS 訂閱</a></nav>' + find_js)
    html_ = page("標籤索引｜百千報 The Hundred", "百千報所有文章的標籤索引與搜尋：新聞、反方、意識科學、刺青、音樂、文學與侯百千的作品。",
                 f"{SITE}news/tags.html", body)
    (NEWS / "tags.html").write_text(html_.replace('href="../../', 'href="../'), "utf-8")
    urls.append(f"{SITE}news/tags.html")

    # RSS：最新 60 篇單篇（中文），讀者可以用閱讀器訂閱
    from email.utils import format_datetime
    items = []
    for a in list(reversed(zh))[:60]:
        try:
            pd = format_datetime(datetime.fromisoformat(str(a["published"])))
        except Exception:
            pd = ""
        link = f"{SITE}news/a/{a['slug']}.html"
        cats = "".join(f"<category>{esc(t)}</category>" for t in a["tags"])
        items.append(f"<item><title>{esc(a['o']['title'])}</title><link>{link}</link><guid isPermaLink=\"true\">{link}</guid>"
                     f"<pubDate>{pd}</pubDate>{cats}<description>{esc(first_para(a['o'].get('body'), 160))}</description></item>")
    rss = ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
           f'<title>百千報 The Hundred</title><link>{SITE}news/</link>'
           f'<atom:link href="{SITE}news/feed.xml" rel="self" type="application/rss+xml"/>'
           '<description>侯百千主編、發行，AI 協作的刊物。每天清晨一期：新聞、反方、意識科學、刺青、音樂與侯百千的作品。</description>'
           '<language>zh-Hant</language>' + "".join(items) + '</channel></rss>\n')
    (NEWS / "feed.xml").write_text(rss, "utf-8")

    for d, keep in ((ARTS, keep_a), (TAGS, keep_t)):
        for f in d.glob("*.html"):
            if f.name not in keep:
                f.unlink()
    print(f"單篇 {len(keep_a)} 頁，標籤 {len(keep_t)} 個")
    return urls


def sync_night_art(issues):
    """2026-11-20 主編定：夜刊封面共用同期日刊的畫。夜刊 JSON 沒寫 art 時，從同期數的日刊抄進去並存檔，滑卡、單篇頁、縮圖都讀同一個欄位。"""
    morning = {}
    for i in issues:
        if i.get("edition") != "night" and not i.get("special"):
            try:
                a = json.loads((ISSUES / f"{i['id']}.json").read_text("utf-8")).get("art")
            except FileNotFoundError:
                continue
            if isinstance(a, int) and a >= 1:
                morning[i.get("issue_no")] = a
    for i in issues:
        if i.get("edition") != "night":
            continue
        f = ISSUES / f"{i['id']}.json"
        x = json.loads(f.read_text("utf-8"))
        if not x.get("art") and morning.get(x.get("issue_no")):
            x["art"] = morning[x["issue_no"]]
            f.write_text(json.dumps(x, ensure_ascii=False, indent=1) + "\n", "utf-8")


def main():
    issues = json.loads((ISSUES / "index.json").read_text("utf-8"))["issues"]
    issues.sort(key=lambda i: str(i.get("published")))
    regular = [i for i in issues if not i.get("special")]
    OUT.mkdir(exist_ok=True)
    keep = set()
    INTRO = intro_html()
    global EN, CUR
    sync_night_art(issues)
    arts = []
    for n, meta in enumerate(issues):
        iid = meta["id"]
        x = json.loads((ISSUES / f"{iid}.json").read_text("utf-8"))
        EN = x.get("lang") == "en" or meta.get("lang") == "en"
        CUR = iid
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
        art_n = (int(a) if isinstance(a, int) and a >= 1 else 0) if x.get("edition") == "night" else (int(a) if isinstance(a, int) and a >= 1 else ((int(no) - 1) % LEGACY_ROTATION + 1 if isinstance(no, int) and no > 0 else 0))
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
        arts += collect(x, meta, headline, L, og)
    for f in OUT.glob("*.html"):
        if f.name not in keep:
            f.unlink()

    items = "".join(
        f'<li><a class="sw" href="./#{i["id"]}" title="滑卡" aria-label="用滑卡讀"><svg viewBox="0 0 16 16" aria-hidden="true"><rect x="4" y="2.5" width="8" height="11" rx="1.5"/><path d="M1.5 4.5v7M14.5 4.5v7"/></svg></a><a href="p/{i["id"]}.html">{esc(lab(i))}{"　" + esc(i.get("_headline") or i.get("title")) if not i.get("special") or i.get("title") != i["special"] else ""}</a>'
        f'<small>{esc(when(i))}{"・夜刊" if i.get("edition") == "night" else ""}</small></li>'
        for i in reversed(issues) if i.get("lang") != "en")  # 英文版不另列，從中文頁的連結進入
    archive = page("所有期數｜百千報 The Hundred", "百千報往期目錄：侯百千主編、發行，AI 協作的刊物。一期一期出的白話小報，新聞、反方、意識科學、刺青、音樂與侯百千的作品。",
                   f"{SITE}news/archive.html",
                   '<a class="brand" href="./">百千報<span class="en">The Hundred</span></a><h1>所有期數</h1>'
                   '<p class="open">一期一期出的白話小報。最新一期用滑卡讀：<a href="./">百千報</a>。每一篇都有自己的網址，可以從<a href="tags.html">標籤索引</a>找。</p>'
                   f'<ul class="list">{items}</ul>')
    (NEWS / "archive.html").write_text(archive.replace('href="../../', 'href="../'), "utf-8")

    urls = [SITE] + [SITE + p.name for p in sorted(ROOT.glob("*.html")) if p.name != "index.html" and not p.name.startswith("google")]
    urls += [SITE + "news/", SITE + "news/archive.html"]
    urls += [f"{SITE}news/p/{i['id']}.html" for i in issues]
    urls += build_articles(arts)
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sm += "".join(f"  <url><loc>{esc(u)}</loc></url>\n" for u in urls) + "</urlset>\n"
    (ROOT / "sitemap.xml").write_text(sm, "utf-8")
    print(f"{len(issues)} 期，sitemap {len(urls)} 個網址")


if __name__ == "__main__":
    main()
