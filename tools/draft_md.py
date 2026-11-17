#!/usr/bin/env python3
"""把百千報一期的 JSON（db 的 feed 文件）轉成給審稿用的 markdown 初稿。

用法
  python3 tools/draft_md.py 這期.json -o 百千報_第018期_初稿.md --id 20261118-0334

  --id       db 文件 id（feed/ 後面那段）。不給就用 published 推算。
  --version  版本說明，預設「v1（03:33 排程初稿）」。

只做轉檔：不改字、不上網、不寫回 db。檔案開頭附各欄字數（算法同 check_issue.py）。
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_issue import LIMITS, NAME, ROTATE, columns, count, label, main_text  # noqa: E402

WD = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def heading(key, col):
    """欄名｜標題。刺青、音樂帶子題，意識科學帶課號，文學與百千帶類別。"""
    name = label(key, col)
    if not col.get("tag"):
        if key == "lesson" and col.get("no"):
            name += f" 第 {col['no']} 課"
        extra = col.get("topic") or col.get("kind") or col.get("domain")
        if extra:
            name += f"（{extra}）"
    return name


def listing(value):
    """checks 之類的欄位：字串、清單、字典都能列。"""
    if isinstance(value, str):
        return [f"- {value}"]
    if isinstance(value, dict):
        return [f"- {k}：{v}" for k, v in value.items()]
    return [f"- {v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)}" for v in (value or [])]


def render(doc, doc_id="", version="v1（03:33 排程初稿）"):
    cols = columns(doc)
    special = doc.get("special")
    no = doc.get("issue_no")
    title = f"特輯「{special}」" if special else f"第 {no} 期"

    when = doc.get("published") or ""
    try:
        t = datetime.fromisoformat(when)
        when = f"{t:%Y-%m-%d} {WD[t.weekday()]} {t:%H:%M}"
        doc_id = doc_id or f"{t:%Y%m%d-%H%M}"
    except ValueError:
        pass

    out = [f"# 百千報 {title}｜初稿", ""]
    out.append(f"- 期數：{no if no is not None else '特輯，不算期數'}")
    out.append(f"- 出刊時間（台北）：{when or '未記'}")
    out.append(f"- 版本：{version}")
    if not special and isinstance(no, int):
        rot = ROTATE[no % 3]
        out.append(f"- 本期輪替欄：{NAME[rot]}" + ("" if rot in cols else "（這期沒有這一欄）"))
    out.append("- 欄位順序（order）：" + " → ".join(label(k, doc[k]) for k in cols))
    out.append(f"- 封面畫（art）：{doc.get('art', '未記')}")
    sizes = []
    for k in cols:
        n = count(main_text(doc[k].get("body") or ""))
        lim = LIMITS.get(k)
        sizes.append(f"{label(k, doc[k])} {n}" + (f"／{lim[0]}–{lim[1]}" if lim and k != "own" and not special else ""))
    out.append("- 各欄正文字數（不含背景框與附註）：" + "、".join(sizes))
    if doc.get("opening"):
        out += ["", "## 開場", "", doc["opening"]]

    why = doc.get("why") or {}
    out += ["", "## 選題理由", ""]
    reasons = why.get("cols") or {}
    if reasons:
        for k in cols:
            if reasons.get(k):
                out.append(f"- {label(k, doc[k])}：{reasons[k]}")
        for k, v in reasons.items():
            if k not in cols:
                out.append(f"- {k}：{v}")
    else:
        out.append("- 未記錄")
    out += ["", "## 放棄的候選", ""]
    out += [f"- {p}" for p in (why.get("passed") or [])] or ["- 未記錄"]

    for k in cols:
        col = doc[k]
        out += ["", f"## {heading(k, col)}｜{col.get('title') or ''}", ""]
        if col.get("target"):
            out += [col["target"], ""]
        out.append((col.get("body") or "").strip())
        if (col.get("question") or "").strip():
            out += ["", f"問題：{col['question'].strip()}"]
        src = col.get("source") or {}
        if src.get("title") or src.get("url"):
            out += ["", f"來源：{src.get('title') or ''} {src.get('url') or ''}".rstrip()]
        notes = col.get("notes") or []
        if notes:
            out += ["", "附註："]
            out += [f"{i}. {n}" for i, n in enumerate(notes, 1)]
        if col.get("tags"):
            out += ["", "標籤：" + "、".join(col["tags"])]

    checks = doc.get("checks")
    if checks:
        out += ["", "## 查核清單（試行）", "", "這是初稿方提供的證據，不是查核結論。"]
        if isinstance(checks, dict):
            for k in cols + [k for k in checks if k not in cols]:
                if checks.get(k):
                    name = label(k, doc[k]) if k in cols else k
                    out += ["", f"### {name}"] + listing(checks[k])
        else:
            out += [""] + listing(checks)

    out += ["", f"正本在百千報 db feed/{doc_id or '<文件 id>'}，不一致以 db 為準"]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description="百千報一期 JSON → markdown 初稿")
    ap.add_argument("issue", help="這期的 JSON 檔")
    ap.add_argument("-o", "--out", help="輸出的 .md 檔；不給就印在畫面上")
    ap.add_argument("--id", default="", help="db 文件 id，例如 20261118-0334")
    ap.add_argument("--version", default="v1（03:33 排程初稿）")
    a = ap.parse_args()

    doc = json.loads(Path(a.issue).read_text(encoding="utf-8"))
    if isinstance(doc.get("data"), dict) and "order" in doc["data"]:
        doc = doc["data"]
    md = render(doc, a.id, a.version)
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
        print(f"已寫出 {a.out}（{len(md.encode('utf-8'))} 位元組）")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
