# -*- coding: utf-8 -*-
"""合并 parts/*.jsonl -> bank.json / quiz.html / 题库.csv

支持三种题型：
  t="s" 单选：opts 4 个，ans 为 0~3
  t="j" 判断：opts 固定 ["正确","错误"]，ans 为 0/1
  t="m" 多选：opts 4 个，ans 为 2~3 个下标的数组
"""
import glob, json, os, re, sys, collections, difflib

BASE = os.path.dirname(os.path.abspath(__file__))
CATS = ["法律法规与职业道德","燃烧与火灾基础","建筑防火","电气消防","火灾自动报警系统",
        "自动喷水与消火栓","气体与泡沫灭火系统","灭火器与消防水源","防排烟与防火分隔",
        "应急照明与消防电梯","消防控制室监控与维保"]
TYPES = ("s", "m", "j")

def norm(s):
    return re.sub(r"[\s，。、；：？！（）()“”\"'’‘·．.,;:!?\-—_]", "", str(s))

def bad(msg):
    print("  ! " + msg)

def part_no(path):
    m = re.search(r"part(\d+)", os.path.basename(path))
    return int(m.group(1)) if m else 0

def load_part(path):
    items, errs = [], 0
    with open(path, encoding="utf-8-sig") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip().rstrip(",")
            if not line or line in "[]":
                continue
            try:
                items.append(json.loads(line))
            except Exception as e:
                errs += 1
                bad(os.path.basename(path) + " 第%d行 JSON 错误: %s" % (ln, e))
    return items, errs

def clean(o):
    if not isinstance(o, dict):
        return None
    t = str(o.get("t") or "s").strip()
    if t not in TYPES:
        t = "s"
    stem = str(o.get("stem", "")).strip()
    opts = o.get("opts")
    if not stem or not isinstance(opts, list):
        return None
    opts = [str(x).strip() for x in opts]
    if any(not x for x in opts) or len(set(opts)) != len(opts):
        return None
    cat = str(o.get("cat", "")).strip()
    if cat not in CATS:
        return None
    ans = o.get("ans")
    if t == "j":
        if len(opts) != 2:
            return None
        if ans not in (0, 1):
            return None
    elif t == "m":
        if len(opts) != 4 or not isinstance(ans, list) or not (2 <= len(ans) <= 3):
            return None
        if any((not isinstance(x, int)) or x < 0 or x > 3 for x in ans) or len(set(ans)) != len(ans):
            return None
        ans = sorted(ans)
    else:
        if len(opts) != 4 or not isinstance(ans, int) or ans < 0 or ans > 3:
            return None
    g = str(o.get("g") or "").strip() or stem[:8]
    return {"id": str(o.get("id") or "").strip(), "cat": cat, "g": g, "t": t, "stem": stem,
            "opts": opts, "ans": ans, "exp": str(o.get("exp") or "").strip()}

def bigrams(s):
    s = norm(s)
    return set(s[i:i+2] for i in range(max(0, len(s)-1)))

def similar(a, b):
    if abs(len(a) - len(b)) > max(len(a), len(b)) * 0.5:
        return 0.0
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()

def main():
    files = sorted(glob.glob(os.path.join(BASE, "parts", "*.jsonl")), key=part_no)
    raw, total_err = [], 0
    for p in files:
        items, e = load_part(p)
        total_err += e
        print("%-16s %4d 行" % (os.path.basename(p), len(items)))
        raw.extend(items)

    seen_stem, seen_g = {}, collections.Counter()
    good, dropped = [], collections.Counter()
    kept_by_cat = collections.defaultdict(list)

    for idx, o in enumerate(raw):
        c = clean(o)
        if not c:
            dropped["格式不合规"] += 1
            continue
        k = norm(c["stem"])
        if k in seen_stem:
            dropped["题干重复"] += 1
            continue
        if seen_g[c["g"]] >= 3:
            dropped["同组超过3道"] += 1
            continue
        # 与新题型做近似重复检查（避免判断题/多选题和单选题考同一句话）
        if c["t"] != "s":
            dup = None
            for old in kept_by_cat[c["cat"]]:
                th = 0.90 if old["t"] == c["t"] else 0.83
                if similar(c["stem"], old["stem"]) >= th:
                    dup = old
                    break
            if dup:
                dropped["近似重复"] += 1
                continue
        seen_stem[k] = 1
        seen_g[c["g"]] += 1
        good.append(c)
        kept_by_cat[c["cat"]].append(c)

    order = {c: i for i, c in enumerate(CATS)}
    for i, q in enumerate(good, 1):
        q["id"] = "Q%04d" % i
    good.sort(key=lambda q: (order.get(q["cat"], 99), q["id"]))

    with open(os.path.join(BASE, "bank.json"), "w", encoding="utf-8") as f:
        json.dump(good, f, ensure_ascii=False, separators=(",", ":"))

    print("\n合并完成：%d 道（丢弃 %d）" % (len(good), sum(dropped.values())))
    for k, v in dropped.items():
        print("   丢弃-%s: %d" % (k, v))
    if total_err:
        print("   JSON 解析错误行: %d" % total_err)

    cats = collections.Counter(q["cat"] for q in good)
    print("\n分类：")
    for c in CATS:
        print("  %-14s %4d" % (c, cats.get(c, 0)))
    tt = collections.Counter(q["t"] for q in good)
    print("\n题型：单选 %d · 多选 %d · 判断 %d" % (tt["s"], tt["m"], tt["j"]))
    ansd = collections.Counter(q["ans"] for q in good if q["t"] == "s")
    print("单选答案分布 A/B/C/D：%d / %d / %d / %d" % (ansd[0], ansd[1], ansd[2], ansd[3]))

    payload = json.dumps(good, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    with open(os.path.join(BASE, "template.html"), encoding="utf-8") as f:
        tpl = f.read()
    html = tpl.replace("__BANK__", payload)
    with open(os.path.join(BASE, "quiz.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("\n已生成 quiz.html（%.0f KB）" % (len(html.encode("utf-8")) / 1024))

    import csv
    with open(os.path.join(BASE, "题库.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["序号", "题型", "模块", "知识点", "题干", "A", "B", "C", "D", "正确答案", "解析"])
        for i, q in enumerate(good, 1):
            if q["t"] == "m":
                ans = "".join("ABCD"[x] for x in q["ans"])
            elif q["t"] == "j":
                ans = "正确" if q["ans"] == 0 else "错误"
            else:
                ans = "ABCD"[q["ans"]]
            opts = q["opts"] + [""] * (4 - len(q["opts"]))
            w.writerow([i, {"s":"单选","m":"多选","j":"判断"}[q["t"]], q["cat"], q["g"], q["stem"]] +
                       opts + [ans, q["exp"]])
    print("已生成 题库.csv")

if __name__ == "__main__":
    main()
