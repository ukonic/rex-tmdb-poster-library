# Rex TMDB 热门影视海报图标库

本项目生成 Rex 可订阅的图标库 JSON，格式严格为：

```json
{
  "name": "图标库名称",
  "description": "说明",
  "icons": [
    {"name": "中文片名", "url": "https://image.tmdb.org/t/p/w500/海报路径.jpg"}
  ]
}
```

默认目标为 5000 条真实 TMDB 海报：电影 2000、电视剧 1500、动漫 1000、综艺 500。数据按 TMDB 热度排序，过滤无海报项目；接口请求使用 `language=zh-CN`，因此优先得到 TMDB 已提供的中文名称，未收录中文译名时会保留 TMDB 返回的原名。同名作品会附加年份/类别用于区分。

## 为什么仓库不直接附带伪造的 5000 条

TMDB v3 数据接口需要应用凭据，可使用 API Read Access Token（Bearer Token，推荐）或 v3 API Key。没有凭据时，无法通过官方接口可靠获取 5000 个名称与 `poster_path`。TMDB 的公开每日 ID 导出只适合获得 ID，不包含完成本图标库所需的中文名称和海报路径，因此不存在真正“完全免 Key 且使用官方完整数据”的生成方式。

仓库中的 `example.json` 仅用于验证 Rex 格式和图片地址。取得自己的免费非商业开发凭据后，运行脚本即可生成完整成品；脚本在任何类别数据不足时默认停止且不覆盖旧文件，不会用虚构条目凑数。

## 本地生成

要求 Python 3.10 或更高版本，无第三方依赖。

1. 登录 TMDB，进入账户设置的 API 页面，申请 API 凭据。
2. 设置环境变量（不要把 Token 写入代码或提交到 GitHub）：

   PowerShell：

   ```powershell
   $env:TMDB_BEARER_TOKEN = "你的 API Read Access Token"
   python generate.py --output rex-tmdb-posters.json
   ```

   macOS/Linux：

   ```bash
   export TMDB_BEARER_TOKEN='你的 API Read Access Token'
   python3 generate.py --output rex-tmdb-posters.json
   ```

也可设置 `TMDB_API_KEY` 使用 v3 API Key。若两个变量都存在，脚本优先使用 Bearer Token。

生成后验证：

```bash
python3 validate_library.py rex-tmdb-posters.json --check-links 25
```

`--check-links 25` 会均匀抽检 25 个海报链接；设为 `0` 则只检查全部 JSON 结构、字段、重复 URL 和 URL 前缀。

可以调整分类数量，例如：

```bash
python3 generate.py --movie-count 2000 --tv-count 1500 --anime-count 1000 --variety-count 500
```

“动漫”按 TMDB TV 动画类型（genre 16）划分；“综艺”按真人秀或脱口秀类型（genre 10764/10767）近似划分。TMDB 的类型体系并不存在一个覆盖所有中文语境“综艺/动漫”的精确标签，因此分类结果可能包含边界作品。

## GitHub Actions 自动更新

1. 新建 GitHub 仓库，把本目录全部文件上传到仓库根目录。
2. 打开仓库 `Settings → Secrets and variables → Actions`。
3. 新建 Repository secret：名称为 `TMDB_BEARER_TOKEN`，值为你的 API Read Access Token。
4. 打开 `Actions`，运行一次 `Update Rex TMDB poster library`。
5. 工作流每周一自动更新；也可以随时手动运行。

工作流会生成 `rex-tmdb-posters.json`、校验结构、抽检 25 个真实海报链接，并只在内容变化时提交。Token 只从 GitHub Secret 注入，不会进入 JSON。

## GitHub Raw 订阅 Rex

假设：

- GitHub 用户名：`YOUR_NAME`
- 仓库名：`rex-tmdb-posters`
- 默认分支：`main`
- JSON 位于仓库根目录

Rex 中填写的 Raw 订阅 URL 为：

```text
https://raw.githubusercontent.com/YOUR_NAME/rex-tmdb-posters/main/rex-tmdb-posters.json
```

也可以在 GitHub 中打开该 JSON，点击 **Raw** 后复制地址。公开仓库可直接访问；私有仓库的 Raw 地址需要鉴权，通常不适合作为 Rex 的公开订阅源。更新提交后 Raw/CDN 缓存可能需要短暂时间刷新。

## 真实接口约束

- TMDB Discover 接口单页通常返回 20 条，页码上限为 500；生成器按页获取并尊重 `429`，遇到临时错误会指数退避重试。
- 热度、译名、海报和类型会随 TMDB 数据变化，每次自动更新的结果可能不同。
- 图片链接按 TMDB 官方规则由图片基址、尺寸 `w500` 与接口返回的 `poster_path` 组合。
- TMDB 免费开发 API 面向非商业用途并要求署名；商业使用请向 TMDB 确认许可。请在实际展示页面加入 TMDB 要求的标识与声明。

官方资料：

- [应用认证](https://developer.themoviedb.org/docs/authentication-application)
- [电影 Discover](https://developer.themoviedb.org/reference/discover-movie)
- [电视 Discover](https://developer.themoviedb.org/reference/discover-tv)
- [图片 URL 规则](https://developer.themoviedb.org/docs/image-basics)
- [速率限制](https://developer.themoviedb.org/docs/rate-limiting)
- [TMDB API FAQ 与署名要求](https://developer.themoviedb.org/docs/faq)

## 版权与署名

海报版权归各权利方所有。本项目不缓存或重新分发图片文件，只在 JSON 中引用 TMDB CDN 地址。项目使用 TMDB API，但未经 TMDB 认可或认证（This product uses the TMDB API but is not endorsed or certified by TMDB）。使用者仍需自行确认其用途符合 TMDB 条款、图片权利与当地法律。
