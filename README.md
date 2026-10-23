# DoriResearch

Dorislab 的开放研究系统：研究和策略阅读页、普通 Python API、自有 SQLite 与可编辑源码。MIT 许可证。它提供页面和程序基础，不要求 Agent 遵循固定研究流程。

## 开始研究

Dorislab 的 `data_catalog` 查询已安装行情的范围、字段和 Parquet 路径。需要研究工程依赖、Library 内容接口或修改工程源码时，`prepare_research` 准备或复用工作区并返回受管 Python、Git、副本起点 `base_commit` 及研究内容持久目录 `data`；简单计算可使用已有执行环境。直接用 Python 读取 Parquet，分析方法、是否使用 DoriBT、是否保留探索结果由任务决定。DoriBT 是依赖中的普通 Python 库，没有固定 ETF 回测命令。

普通问答直接回答。研究或策略可保存到资料库；研究工程功能、页面和可调用模块通过 Git 提交和客户端 `activate_research` 启用。平台策略代码可以作为内容附件交付。保存内容不会触发构建、自动合并或模型调用。

## 保存与读取

使用返回的 Python，将回执的 `data` 路径传给 Library，或为该执行进程设置 `DORIRESEARCH_DATA`；`prepare_research` 不修改后续终端的环境变量。下面的 `data_directory` 使用实际回执路径，行情输入使用 `data_catalog` 返回的路径：

```python
from pathlib import Path
from dorislab_research import Library

library = Library(Path(data_directory))
reference = library.save(
    kind="study", title="我的问题成立吗？", summary="一句话结论",
    body=Path("report.md").read_text(encoding="utf-8"),
    files={"charts/curve.parquet": Path("curve.parquet"),
           "charts/nav.echarts.json": Path("nav.echarts.json")},
    data_nature="real",
)
content = library.content(reference)
print(library.links(reference))
```

`kind` 支持 `study`、`strategy`、策略结果 `run`。`references` 存关联引用，`config` 存功能配置。`reference` 是保存回执中的 `kind/id/version`，不是文件路径；`version` 固定读取一个历史修订，省略它则读取该内容当前修订。需要查找已有内容时，按标题或关键词查询并确认目标：

```python
from dorislab_research.library_queries import listing

matches = listing(library, query="研究关键词", kind="study")
print([(item["title"], item["reference"]) for item in matches])
```

### 续改完整修订

`Library.save` 每次写入完整修订，不是字段补丁。省略 `files`、`references` 或 `config` 会使新修订使用空值；摘要和数据性质同样要保留或明确修改。修改同一内容传 `id` 和 `expected_revision`。以下示例只改摘要，保留其余内容；`reference` 来自前一次保存、查询或用户提供的内容引用：

```python
current = library.content({"kind": reference["kind"], "id": reference["id"]})
item = current["item"]
base = item["reference"]
files = {
    file["path"]: library.file(base, file["path"])
    for file in current["files"]
    if file["path"] != "report.md"
}
revised = library.save(
    kind=base["kind"], id=base["id"], expected_revision=int(base["version"]),
    title=item["title"], summary="重新表述后的摘要", body=current["body"],
    files=files, references=current["references"], config=current["config"],
    origin=item["origin"], data_nature=item["data_nature"],
)
print(library.links(revised)["markdown"])
```

`report.md` 由 `body` 参数生成，不放进 `files`。替换附件时更新 `files` 中对应项；删除附件时同时调整正文引用。遇到 `ConflictError`，重新读取当前修订并整合本次修改，不能只替换修订号重试旧内容。保存返回后用 `content`、`file` 读取本次交付的正文与必要文件；旧修订仍可按原 reference 读取。

### 页面和附件链接

保存后用 `library.links(reference)` 取得可直接用于回复的文档 `markdown` 和附件 `files[].markdown`；`content["links"]` 也提供同一回执。附件链接绑定已保存的修订和持久文件，不依赖原对话工作区。文件名中的空格、中文和特殊字符由 API 转义。页面正文中的文件链接使用 `files[].body_markdown` 对应的相对路径形式，例如 `[策略代码](sse50_grid_guojin.py)`；正文撰写时按 `files` 中实际的名称链接。

交付策略时，把完整代码保存为附件，正文解释规则、使用方法和验证结果，回复附可点击的代码与策略页面链接；用户明确要求时再在对话贴完整代码。页面头部已展示标题和摘要，正文从实质内容或章节开始。

`references` 仍精确保留研究依据的修订号；`content["related"]` 是独立的双向导航，按内容身份去重、排除自身，名称和跳转使用当前修订。其他内容引用本页后会自动出现，无需改写本页的旧依据。归档或删除内容不新增反向入口，已引用且删除的内容保留名称与不可用状态。

正文保存为 report.md，files 只列要保留的普通文件，不需要清单、哈希或证明材料。每次修改保留独立内容修订，历史引用仍可读取。SQLite 在客户端显式提供的持久目录的 library.sqlite，文件在 files/；它们不进入源码 Git。0.3.0 使用 host_protocol 2，不读取或迁移旧版研究数据库。缓存和中间行情不必保存进资料库。归档、删除不级联影响关联内容。

## Markdown 阅读组件

继续使用普通 Markdown，按需要加入 fenced code blocks：

````markdown
```metrics
{"src":"metrics.json"}
```

```echarts
{"src":"charts/nav.echarts.json"}
```

```datatable
{"src":"observations.parquet"}
```
````

- 指标文件为数组，如 `[{"label":"胜率","value":61.2,"unit":"%","description":"本次样本"}]`，也可直接写在 metrics 块中。
- 图表配置是 ECharts option，或 `{"data":"curve.parquet","option":{...}}`。data 相对配置文件，支持 JSON 记录数组、CSV、TSV、Parquet；通过 dataset 列名与 encode 引用数据，无需转存 JSON。配置不含可执行函数。
- 图表使用 ECharts；准确版本读取 `frontend/package.json` 的 `dependencies.echarts`（本版为 6.1.0）。图表宽度随正文变化，窄栏可能只有约 340px；默认高度随字号调整，15px 字号时为 360px。布局、配色、标题和数据口径见[图表编写说明](docs/charts.md)。
- 数据表支持相同数据格式，可搜索、排序、分页。局部读取错误不阻止其他正文阅读。
- 文件侧栏预览由客户端统一管理。控制面通过 `file_path` 解析已校验的资料库文件；`local_table_preview` 为控制面解析后的本地 Parquet 提供每页 100 行的按需读取，游标绑定文件版本。这两个操作不向研究页面开放任意路径访问。
- 研究与策略正文支持 Ctrl+A 全选当前已加载正文、Ctrl+C 复制选文；右键提供复制、全选和引用选中文字，菜单动作／Escape 关闭后保留选区，点击其他区域关闭时不抢回焦点。快捷键不接管输入控件；划词按钮与右键引用共用来源、版本和定位，仍由客户端选择目标输入框，不自动发送。阅读行为与客户端文件预览保持一致，浏览器默认菜单仍屏蔽。
- 列表与详情统一显示本地保存时间（年月日 时:分）；真实数据不重复贴标签，示例及模拟／混合数据继续明确说明。
- 静态图片仍可使用，charting.py 提供可选 Matplotlib 样式；无需为了复用阅读页编写 React。

## 策略与手动回测

策略的 config.backtest 可配置 Python 函数 `module:function`、参数和可选 date_range。参考 example_calculation.py 与 examples.py。函数接收 `(parameters, output_directory)`，返回结果的 title/summary/body/files；这是手动回测面板的适配接口，普通研究不需要使用它。新增或修改 callable 所在模块属于工程源码变更，须随工程启用；只把代码存为策略附件不会使其成为可导入模块。

用户发起的成功回测自动保存并打开独立结果，关联策略版本，参数只作用于本次运行。重新打开已完成的历史任务不会再次跳转。无日期配置时面板不添加限制；策略自行报告数据不足，不自动补数、换数据或缩小区间。Agent 探索可直接调用程序，按需使用 Library 保存。

## 开发与数据库

在 backend 用 uv 同步锁定依赖，运行 `python ../scripts/dev.py` 启动真实 API 和 Vite。预览使用独立的 target/preview 测试数据，初次生成一个模拟研究与一个模拟策略，数值均实际计算。示例只初始化一次，升级不覆盖用户修改或复活删除内容。

数据库由 backend/src/dorislab_research/migrations 中的 Alembic 修订维护。Agent 编写迁移及相关测试，客户端启用时执行正式升级；普通保存不得自动迁移。测试使用隔离数据库和文件目录。

客户端以 `service serve --data <library> --cache <query-cache>` 传入独立内容目录和一次性查询缓存。工程启用期间先冻结写入，`backup` 请求必须包含客户端登记的外部绝对 `path`；失败恢复使用 `service restore --data <library> --backup <backup-file>`。备份和恢复都通过 SQLite API 完成，客户端不复制打开中的数据库；备份保留及缓存回收由客户端负责。

候选工程的 `service verify --data <检查根目录>` 在新分配的隔离目录迁移测试库，启动实际 HTTP 服务并读取健康状态、搜索列表及正文；失败阻止启用，结束后回收子进程和测试数据。此检查不认证研究结论，不访问正式库。

`base_commit` 是会话副本的起点。启用前在该副本用回执中的 Git 执行 `git rev-parse refs/heads/account` 读取当前账号基线，将它整合到候选提交并完成相关验证；账号分支由客户端更新。新请求将完整候选提交、已整合的基线分别传给 `activate_research` 的 `commit`、`baseline`，并提供本次请求的唯一 `request_id`。`checking` 表示仍在处理，只传同一 `request_id` 查询到 `ready` 才表示已启用；`failed` 时按返回信息处理。修复后用新的请求 ID 发起启用；基线已变化时先读取并整合最新基线。

检查入口：`scripts/check.ps1 -Mode Standard`，可加 `-Target Backend` 或 Frontend。生产服务由客户端管理进程生命周期，只接受当前客户端的本地凭证；用户登录、原始数据、商业权益由 Dorislab 管理。

## Search and large files

The desktop keeps a disposable, account-scoped search index. Library changes have a monotonic cursor;
`search_changes` returns bounded deltas and resets the cursor when the database identity changes.
Saving, archiving, restoring and deleting all update this projection. Direct changes to persistent
files are detected on the next search; list and global search share this index and unchanged file bodies are not reread. Filenames and Markdown/
text files up to 1 MiB are searchable. Large data arrays remain data files, not full-text documents.
Search sync failures are surfaced and retried; they never roll back content saves.

Tables stream CSV/TSV/JSON records or Parquet batches into a disposable disk query cache, then filter
and sort the complete dataset before returning a page. The cache holds at most four files and is
invalidated by source changes. The first sorted/filterable view scans the file; it does not hold
all rows in Python memory. JSON must be a record array; individual records are limited to 4 MiB.

Charts can add `columns`, `offset` and `limit` next to `data`, for example
`{"data":"observations.parquet","columns":["date","return"],"offset":0,"limit":500,"option":{...}}`.
Parquet projects the selected columns; JSON/CSV advance through records to the requested range.
The default is the entire file only when it fits within 10,000 rows and 8 MiB; larger inputs produce
an explicit error asking for a range or aggregation. Explicit ranges are not statistical sampling.
File previews and exports use bounded byte chunks and reject changes between chunks.
