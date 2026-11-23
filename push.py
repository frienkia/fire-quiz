# -*- coding: utf-8 -*-
"""把题库源文件 + 网站产物一次性提交到 GitHub（单条 commit）。

凭据顺序：环境变量 GH_TOKEN/GITHUB_TOKEN -> gh CLI -> 工作区根目录 gh_token.txt
用法：python build.py && python push.py
"""
import base64, hashlib, json, os, pathlib, subprocess, sys, time
import urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
REPO = "frienkia/fire-quiz"
BRANCH = "main"
API = "https://api.github.com"
GH_PATHS = [r"C:\Program Files\GitHub CLI\gh.exe", "gh"]

SITE_FILES = ["quiz.html", "index.html", "manifest.webmanifest", "sw.js",
              "icon-192.png", "icon-512.png"]
SOURCE_FILES = ["README.md", "CHANGELOG.md", "LICENSE", ".gitignore", "DEPLOY.md",
                "bank.json", "build.py", "template.html", "push.py"]

def plan():
    items = []
    for f in SITE_FILES:
        items.append((ROOT / "deploy" / f, f))
    for f in SOURCE_FILES:
        items.append((ROOT / f, f))
    for p in sorted((ROOT / "parts").glob("*.jsonl")):
        items.append((p, "parts/" + p.name))
    return [(p, r) for p, r in items if p.exists()]

def gh_token():
    for exe in GH_PATHS:
        try:
            r = subprocess.run([exe, "auth", "token"], capture_output=True, text=True, timeout=20)
            if r.returncode == 0 and (r.stdout or "").strip():
                return r.stdout.strip()
        except Exception:
            pass
    return ""

def find_token():
    t = (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()
    if t:
        return t
    t = gh_token()
    if t:
        return t
    for p in [ROOT.parent / "gh_token.txt", ROOT / "gh_token.txt"]:
        if p.exists() and p.read_text(encoding="utf-8").strip():
            return p.read_text(encoding="utf-8").strip()
    sys.exit("没有可用凭据：运行 gh auth login，或把 token 写到 " + str(ROOT.parent / "gh_token.txt"))

def call(method, path, token, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "xf-quiz-push")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            raw = r.read().decode("utf-8")
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw or "{}")
        except Exception:
            return e.code, {"message": raw[:200]}

def git_blob_sha(data):
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()

def main():
    token = find_token()
    st, me = call("GET", "/user", token)
    if st != 200:
        sys.exit("token 无效（%s）：%s" % (st, me.get("message")))
    print("已认证：", me.get("login"))

    st, ref = call("GET", "/repos/%s/git/ref/heads/%s" % (REPO, BRANCH), token)
    if st != 200:
        sys.exit("读取分支失败：%s %s" % (st, ref.get("message")))
    head = ref["object"]["sha"]

    st, commit = call("GET", "/repos/%s/git/commits/%s" % (REPO, head), token)
    if st != 200:
        sys.exit("读取 commit 失败：%s" % commit.get("message"))
    base_tree = commit["tree"]["sha"]

    st, tree = call("GET", "/repos/%s/git/trees/%s?recursive=1" % (REPO, base_tree), token)
    if st != 200:
        sys.exit("读取 tree 失败：%s" % tree.get("message"))
    remote = {t["path"]: t["sha"] for t in tree.get("tree", []) if t.get("type") == "blob"}

    changed, skipped = [], 0
    for local, repo_path in plan():
        data = local.read_bytes()
        if remote.get(repo_path) == git_blob_sha(data):
            skipped += 1
            continue
        changed.append((repo_path, data))

    if not changed:
        print("没有变化，跳过提交。")
        return

    items = []
    for repo_path, data in changed:
        st, blob = call("POST", "/repos/%s/git/blobs" % REPO, token,
                        {"content": base64.b64encode(data).decode("ascii"), "encoding": "base64"})
        if st not in (200, 201):
            sys.exit("创建 blob 失败 %s：%s" % (repo_path, blob.get("message")))
        items.append({"path": repo_path, "mode": "100644", "type": "blob", "sha": blob["sha"]})

    st, new_tree = call("POST", "/repos/%s/git/trees" % REPO, token,
                        {"base_tree": base_tree, "tree": items})
    if st not in (200, 201):
        sys.exit("创建 tree 失败：%s" % new_tree.get("message"))

    msg = "更新：%s（共 %d 个文件）" % (time.strftime("%Y-%m-%d %H:%M"), len(items))
    st, new_commit = call("POST", "/repos/%s/git/commits" % REPO, token,
                          {"message": msg, "tree": new_tree["sha"], "parents": [head]})
    if st not in (200, 201):
        sys.exit("创建 commit 失败：%s" % new_commit.get("message"))

    st, upd = call("PATCH", "/repos/%s/git/refs/heads/%s" % (REPO, BRANCH), token,
                   {"sha": new_commit["sha"], "force": False})
    if st not in (200, 201):
        sys.exit("更新分支失败：%s" % upd.get("message"))

    print("提交成功：%s" % new_commit["sha"][:8])
    for p, _ in changed:
        print("  +", p)
    print("未变化：%d 个文件" % skipped)
    print("站点：https://frienkia.github.io/fire-quiz/")

if __name__ == "__main__":
    main()
