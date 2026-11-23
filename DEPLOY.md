# 部署到 https（手机安装成 App，离线可用）

目标：把 `deploy` 文件夹放到一个 https 静态站点上，手机打开一次，然后「添加到主屏幕」，之后断网也能刷。

`deploy` 里就 6 个文件，**上传这 6 个文件本身**（不要上传 `deploy` 这个文件夹）：

```
quiz.html              主程序（题库已内嵌，1.1MB）
index.html             跳转到 quiz.html 的小页面
manifest.webmanifest   App 名称、图标、启动方式
sw.js                  离线缓存
icon-192.png           图标
icon-512.png           图标
```

---

## 方案一：GitHub Pages（免费、推荐，全程网页操作）

1. 打开 https://github.com ，登录（没有就注册一个）。
2. 右上角 **+ → New repository**
   - Repository name：`fire-quiz`（名字随便，会出现在网址里）
   - 选 **Public**（私有仓库的 Pages 要付费）
   - 点 **Create repository**
3. 在仓库页点 **Add file → Upload files**，把 `deploy` 里的 6 个文件拖进去，点 **Commit changes**。
4. 仓库页 **Settings → Pages**：
   - Source 选 **Deploy from a branch**
   - Branch 选 **main**，目录选 **/ (root)**，点 **Save**
5. 等 1～2 分钟，刷新 Settings → Pages，顶部会出现网址，形如：

   ```
   https://你的用户名.github.io/fire-quiz/
   ```

   直接访问 `.../fire-quiz/quiz.html` 也行（根地址会自动跳转）。

6. 手机浏览器打开这个网址 → 菜单里选「添加到主屏幕 / 安装应用」。

> 首次打开必须联网（下载 + 缓存），之后断网可用。

---

## 方案二：Cloudflare Pages（拖拽上传，更快）

1. 打开 https://dash.cloudflare.com ，注册/登录。
2. 左侧 **Workers & Pages → Create → Pages → Upload assets**。
3. 项目名随便填，把 `deploy` 文件夹拖进去，点 **Deploy**。
4. 得到网址 `https://xxx.pages.dev`，手机打开 → 添加到主屏幕。

---

## 手机上怎么"装"

| 系统 | 操作 |
| --- | --- |
| Android Chrome / Edge | 打开网址 → 右上角 ⋮ → **安装应用** 或 **添加到主屏幕** |
| iPhone Safari | 打开网址 → 底部 **分享** 按钮 → **添加到主屏幕** |

装完桌面会多一个「消防刷题」图标，点开是全屏的，没有浏览器地址栏，断网照样用。

> 注意：iPhone 必须用 **Safari** 打开再添加；用微信内置浏览器打开是加不到桌面的。

---

## 以后题库更新了怎么办

1. 本地改完题库跑 `python build.py`；
2. 把新的 `quiz.html` 重新上传覆盖（GitHub 页面上传同名文件即可）；
3. 手机联网打开一次，会自动拿到新版；没联网时仍用旧缓存。

`sw.js` 已经写成"导航请求先走网络、失败用缓存"，所以不会出现改了题手机还显示旧版的情况。

---

## 常见问题

**Q：能不能不公开？**
GitHub Pages 的私有仓库需要付费；Cloudflare Pages 可以用访问控制，但配置更麻烦。题库是自己的练习内容，公开不影响使用。

**Q：断网后打开是白屏？**
说明之前没联网成功缓存过。联网打开一次、等页面完全出来再关。

**Q：手机和电脑的错题本互通吗？**
不互通。用首页「导出错题与成绩」→ 在另一台设备「导入数据」即可迁移。

**Q：局域网 http 地址能装吗？**
不能。浏览器只允许 https（或 localhost）注册离线缓存，所以必须走上面的托管方案。
