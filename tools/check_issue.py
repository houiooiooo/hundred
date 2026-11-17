#!/usr/bin/env python3
"""百千報存檔前檢查：字數、附註標號、全站查重。

用法
  python3 tools/check_issue.py 這期.json
      檢查一期。db 的 feed 文件或網站 news/issues 的 JSON 都可以。
  python3 tools/check_issue.py --terms 詞1 詞2 ...
      只查這些詞在往期哪裡出現過（寫庫存、換題、特輯定題時用）。

結果分三種
  【擋】   改到過才存檔：字數超過上限一成、附註標號對不上、缺標題或正文。
  【提醒】 看一眼，自己判斷。
  【查重】 往期（所有欄）有一篇和這篇共用不少稀有的詞（人名、作品名、術語、事件）：
           讀一下那一篇；講的是同一段事實或結論就換題，否則在 why 寫明這次新在哪裡。
           沒列出來不代表沒重複，定題時仍可用 --terms 查核心人名、作品名。

有【擋】時結束碼是 1，其餘是 0。只讀檔案，不改任何東西，不上網。

字數算法：正文裡（不含「背景｜」方框、不含附註、不含 [1] 這類標號），
中文字與全形標點各算 1，一串英文或數字算 1。
上限寫在 LIMITS，正本是百千報 db 的 meta/rules；規則改了這裡要跟著改。
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISSUES = ROOT / "news" / "issues"

KEYS = ["news", "main", "lesson", "tattoo", "music", "own", "craft", "lit", "far"]
NAME = {"news": "新聞", "main": "反方", "lesson": "意識科學", "tattoo": "刺青", "music": "音樂",
        "own": "百千", "craft": "興趣的藝術", "lit": "文學", "far": "遠方"}
# 每欄字數（下限, 上限）。own 是侯百千的原作，不數。
LIMITS = {"main": (450, 650), "lesson": (450, 650), "craft": (450, 650),
          "news": (300, 450), "far": (300, 450), "tattoo": (300, 450), "music": (300, 450),
          "lit": (300, 500)}
OVER = 1.1  # 超過上限一成才擋
ROTATE = {2: "far", 0: "lit", 1: "craft"}  # issue_no 除以 3 的餘數 → 輪替欄

MARK = re.compile(r"\[(\d{1,2})\]")
WORD = re.compile(r"[A-Za-z0-9]+(?:[.,'’\-/:][A-Za-z0-9]+)*")
URL = re.compile(r"https?://\S+")


# ---------- 字數 ----------

def main_text(body):
    """正文去掉「背景｜」方框（從那一段到結尾）。"""
    out = []
    for line in (body or "").split("\n"):
        if line.strip().startswith("背景｜"):
            break
        out.append(line)
    return "\n".join(out)


def count(text):
    text = MARK.sub("", text or "")
    n = len(WORD.findall(text))
    rest = WORD.sub("", text)
    return n + sum(1 for ch in rest if not ch.isspace() and ord(ch) > 127)


def label(key, col):
    """欄名：特輯自標的 tag 優先，其次 lesson 的 series，再來是固定欄名。"""
    name = col.get("tag") or (col.get("series") if key == "lesson" else "") or NAME.get(key, key)
    if col.get("tag") and col.get("sub"):
        name += "・" + str(col["sub"])
    return name


def columns(doc):
    """依 order 列出這期實際有的欄；order 沒寫到的接在後面。"""
    have = [k for k in KEYS if isinstance(doc.get(k), dict) and "body" in doc[k]]
    order = [k for k in (doc.get("order") or []) if k in have]
    return order + [k for k in have if k not in order]


# ---------- 單期檢查 ----------

def check(doc):
    block, warn, sizes = [], [], []
    special = bool(doc.get("special"))
    cols = columns(doc)
    if not cols:
        block.append("這份 JSON 裡找不到任何一欄（news、main、lesson…）")

    for key in cols:
        col = doc[key]
        name = label(key, col)
        body = col.get("body") or ""
        notes = col.get("notes") or []
        if not (col.get("title") or "").strip():
            block.append(f"{name}：沒有標題")
        if not body.strip():
            block.append(f"{name}：沒有正文")
            continue

        # 字數
        n = count(main_text(body))
        lim = LIMITS.get(key)
        if key == "own":
            sizes.append(f"  {name} {n}（原作，不數）")
        elif lim is None:
            sizes.append(f"  {name} {n}")
        else:
            lo, hi = lim
            line = f"  {name} {n}／{lo}–{hi}"
            cap = int(hi * OVER)
            if n > cap:
                over = f"{name}：正文 {n} 字，上限 {hi}（{cap} 以上才擋），要刪 {n - hi} 字左右；刪支線與細節，細節進附註"
                # 特輯不套日刊字數；文學的古典詩全文不算，程式分不出來，所以只提醒
                if special or key == "lit":
                    warn.append(over + ("（特輯只提醒）" if special else "（古典詩全文不算，自己判斷）"))
                    line += " ←偏長"
                else:
                    block.append(over)
                    line += " ←擋"
            elif n > hi:
                warn.append(f"{name}：正文 {n} 字，略超上限 {hi}")
                line += " ←略超"
            elif n < lo and not special:
                warn.append(f"{name}：正文 {n} 字，低於 {lo}")
                line += " ←偏短"
            sizes.append(line)

        # 附註標號
        seen = []
        for m in MARK.findall(body):
            m = int(m)
            if m not in seen:
                seen.append(m)
        for m in seen:
            if m < 1 or m > len(notes):
                block.append(f"{name}：正文有 [{m}]，附註只有 {len(notes)} 則")
        for i in range(1, len(notes) + 1):
            if i not in seen:
                block.append(f"{name}：附註 {i} 在正文沒有標號")
        if seen != sorted(seen):
            warn.append(f"{name}：標號沒有照出現次序（{'、'.join(map(str, seen))}），附註要重編")

        # 網址黏字
        texts = list(notes) + [(col.get("source") or {}).get("url") or ""]
        for t in texts:
            for u in URL.findall(t or ""):
                if u.count("http") > 1:
                    warn.append(f"{name}：兩個網址黏在一起，補空格：{u[:70]}")

        if key != "main" and not special and (col.get("question") or "").strip():
            warn.append(f"{name}：question 只放反方欄")
        if not col.get("tags"):
            warn.append(f"{name}：沒有 tags")

    # 整期結構（特輯不套）
    if not special and cols:
        order = doc.get("order") or []
        if not order:
            warn.append("沒有 order")
        elif order[0] == "news":
            warn.append("order 第一張是新聞（第一張不放新聞）")
        for k in order:
            if k not in cols:
                warn.append(f"order 裡的 {k} 這期沒有內容")
        no = doc.get("issue_no")
        if isinstance(no, int):
            want = ROTATE[no % 3]
            got = [k for k in ("far", "lit", "craft") if k in cols]
            if got != [want]:
                warn.append(f"第 {no} 期輪替欄應該是{NAME[want]}，這期有的是：{'、'.join(NAME[k] for k in got) or '沒有'}")
        for k in ("news", "main", "lesson", "tattoo", "music", "own"):
            if k not in cols:
                warn.append(f"少了固定欄：{NAME[k]}")
        opening = re.sub(r"\s", "", doc.get("opening") or "")
        if not opening:
            warn.append("沒有 opening")
        elif not 20 <= len(opening) <= 40:
            warn.append(f"opening {len(opening)} 字（20–40）")

    return block, warn, sizes


# ---------- 全站查重 ----------
# 做法：把每一篇切成 2–4 個字的片段（英文取整個詞），找出「這篇和往期某一篇都有、
# 而且全站只有一兩期出現過」的片段，在這篇原文上接成片語後計分。
# 人名、作品名、術語、事件都是這種稀有片段；常見用語因為很多期都有，不計分。

RUN = re.compile(r"[\u4e00-\u9fff]+")
LWORD = re.compile(r"[A-Za-z][A-Za-z'’\-]{3,}")
STOP = {"wikipedia", "youtube", "spotify", "instagram", "google", "http", "https", "html", "that", "this",
        "with", "from", "pubmed", "nature", "science", "guardian", "reuters", "january", "february",
        "march", "april", "june", "july", "august", "september", "october", "november", "december",
        "york", "times", "press", "university", "journal", "review", "news"}
WEIGHT = {1: 1.0, 2: 0.5, 3: 0.25}  # 片段在往期幾期出現過 → 權重；四期以上當常見用語
SCORE = 14     # 分數到這裡才列出來
PER_COL = 3    # 每欄最多列幾篇


def grams(text):
    out = set()
    for run in RUN.findall(text):
        for n in (2, 3, 4):
            for i in range(len(run) - n + 1):
                out.add(run[i:i + n])
    for w in LWORD.findall(text):
        if w.lower() not in STOP:
            out.add(w.lower())
    return out


def col_text(col, notes=False):
    t = (col.get("title") or "") + "\n" + main_text(col.get("body") or "")
    if notes:
        t = (col.get("title") or "") + "\n" + (col.get("body") or "") + "\n" + "\n".join(col.get("notes") or [])
    return MARK.sub("", t)


def load_past(issues_dir, skip=None):
    """讀全部往期，每欄一筆。英文版不讀（和中文版重複）。"""
    skip = skip or (lambda stem, d: False)
    past = []
    for f in sorted(Path(issues_dir).glob("*.json")):
        if f.name == "index.json":
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict) or d.get("lang") == "en" or skip(f.stem, d):
            continue
        tag = f"特輯「{d['special']}」" if d.get("special") else f"第 {d.get('issue_no', '?')} 期"
        rows = [(k, label(k, d[k]), d[k]) for k in KEYS if isinstance(d.get(k), dict) and "body" in d[k]]
        if not rows:  # 早期的夜刊：items 陣列
            rows = [("item", "夜刊", {"title": it.get("title"), "body": "\n".join(str(v) for v in it.values() if isinstance(v, str))})
                    for it in d.get("items") or [] if isinstance(it, dict)]
        for key, name, col in rows:
            text = col_text(col, notes=True)
            past.append({"tag": tag, "stem": f.stem, "key": key, "name": name,
                         "title": col.get("title") or "", "text": text.lower(), "grams": grams(text)})
    return past


def shared_phrases(text, weight):
    """把有權重的片段在原文上接成片語。回傳 [(片語, 分數)]。"""
    found = {}
    for run in RUN.findall(text):
        w = [0.0] * len(run)
        for n in (2, 3, 4):
            for i in range(len(run) - n + 1):
                x = weight.get(run[i:i + n], 0)
                if x:
                    for j in range(i, i + n):
                        w[j] = max(w[j], x)
        i = 0
        while i < len(run):
            if w[i]:
                j = i
                while j < len(run) and w[j]:
                    j += 1
                found.setdefault(run[i:j], (j - i - 1) * max(w[i:j]))
                i = j
            else:
                i += 1
    for word in LWORD.findall(text):
        x = weight.get(word.lower(), 0)
        if x:
            found.setdefault(word, 3 * x)
    return sorted(found.items(), key=lambda kv: -kv[1])


def dedupe(doc, past):
    spread = {}
    for p in past:
        for g in p["grams"]:
            spread.setdefault(g, set()).add(p["stem"])
    out = []
    for key in columns(doc):
        if key == "own":
            continue
        col = doc[key]
        text = col_text(col)
        mine = grams(text)
        rows = []
        for p in past:
            if p["key"] == "own":
                continue
            if key == "lesson" and p["key"] == "lesson" and not doc.get("special"):
                continue  # 課與課之間本來就會互相提到
            weight = {g: WEIGHT.get(len(spread[g]), 0) for g in mine & p["grams"]}
            phrases = shared_phrases(text, {g: x for g, x in weight.items() if x})
            score = sum(s for _, s in phrases)
            if score >= SCORE:
                rows.append((score, p, [ph for ph, _ in phrases[:6]]))
        rows.sort(key=lambda r: -r[0])
        for score, p, phrases in rows[:PER_COL]:
            out.append(f"{label(key, col)}〈{col.get('title') or ''}〉→ {p['tag']} {p['name']}〈{p['title']}〉"
                       f"：共有「{'」「'.join(phrases)}」（{score:.0f} 分）")
    return out


def search_terms(terms, past):
    for t in terms:
        where = [p for p in past if t.lower() in p["text"]]
        if not where:
            print(f"「{t}」往期沒出現過")
            continue
        print(f"「{t}」出現在 {len(where)} 篇：")
        for p in where:
            i = p["text"].find(t.lower())
            snip = re.sub(r"\s+", " ", p["text"][max(0, i - 24): i + len(t) + 36])
            print(f"  {p['tag']} {p['name']}〈{p['title']}〉…{snip}…")


# ---------- 主程式 ----------

def main():
    ap = argparse.ArgumentParser(description="百千報存檔前檢查（字數、附註標號、全站查重）")
    ap.add_argument("issue", nargs="?", help="這期的 JSON 檔")
    ap.add_argument("--terms", nargs="+", help="只查這些詞在往期的出現處")
    ap.add_argument("--issues", default=str(ISSUES), help="往期 JSON 資料夾（預設 news/issues）")
    ap.add_argument("--self", dest="self_id", default="", help="這期在網站上的檔名（不含 .json），查重時跳過")
    a = ap.parse_args()

    if a.terms and not a.issue:
        search_terms(a.terms, load_past(a.issues))
        return 0
    if not a.issue:
        ap.print_help()
        return 2

    doc = json.loads(Path(a.issue).read_text(encoding="utf-8"))
    if isinstance(doc.get("data"), dict) and "order" in doc["data"]:
        doc = doc["data"]  # db_get 整包存下來的情況

    def is_self(stem, d):
        if stem == a.self_id or stem == Path(a.issue).stem:
            return True
        if doc.get("published") and d.get("published") == doc.get("published"):
            return True
        return (not doc.get("special") and not d.get("special")
                and isinstance(doc.get("issue_no"), int) and d.get("issue_no") == doc.get("issue_no"))

    past = load_past(a.issues, is_self)
    block, warn, sizes = check(doc)
    dup = dedupe(doc, past)

    head = f"特輯「{doc['special']}」" if doc.get("special") else f"第 {doc.get('issue_no', '?')} 期"
    print(f"百千報 {head}｜存檔前檢查")
    print("字數（正文，不含背景框與附註）")
    print("\n".join(sizes))
    for title, rows in (("【擋】", block), ("【提醒】", warn), ("【查重】換題，或在 why 寫明新在哪裡", dup)):
        if rows:
            print(title)
            print("\n".join("  " + r for r in rows))
    if a.terms:
        search_terms(a.terms, past)
    print(f"結果：擋 {len(block)}、提醒 {len(warn)}、查重 {len(dup)}"
          + ("。有【擋】，改完再跑一次。" if block else "。可以存檔。"))
    return 1 if block else 0


if __name__ == "__main__":
    sys.exit(main())
