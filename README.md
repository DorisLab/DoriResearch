# DoriResearch

Dorislab 的开放研究系统：研究和策略阅读页、普通 Python API、自有 SQLite 与可编辑源码。MIT 许可证。它提供页面和程序基础，不要求 Agent 遵循固定研究流程。

## 开始研究

Dorislab 的 `data_catalog` 查询已安装数据；`prepare_research` 返回工作区、受管 Python、Git 和持久数据目录。直接用 Python 读取 Parquet，分析方法、是否使用 DoriBT、是否保留探索结果由任务决定。DoriBT 是依赖中的普通 Python 库，没有固定 ETF 回测命令。

普通问答直接回答。研究或策略可保存到资料库；源码功能通过 Git 提交和客户端 `activate_research` 启用。保存内容不会触发构建、自动合并或模型调用。

## 保存与读取

使用返回的 Python，把 `DORIRESEARCH_DATA` 设置为返回的持久目录，或直接传给 Library：

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
```

`kind` 支持 `study`、`strategy`、策略结果 `run`。`references` 存关联引用，`config` 存功能配置。更新同一条内容传 `id` 和 `expected_revision`；冲突抛出 `ConflictError`，先重新读取并整合。

正文保存为 report.md，files 只列要保留的普通文件，不需要清单、哈希或证明材料。每次修改保留独立内容修订，历史引用仍可读取。SQLite 在持久目录的 research.sqlite3，文件在 files/；它们不进入源码 Git。缓存和中间行情不必保存进资料库。归档、删除不级联影响关联内容。

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
- 数据表支持相同数据格式，可搜索、排序、分页。局部读取错误不阻止其他正文阅读。
- 静态图片仍可使用，charting.py 提供可选 Matplotlib 样式；无需为了复用阅读页编写 React。

## 策略与手动回测

策略的 config.backtest 可配置 Python 函数 `module:function`、参数和可选 date_range。参考 example_calculation.py 与 examples.py。函数接收 `(parameters, output_directory)`，返回结果的 title/summary/body/files；这是手动回测面板的适配接口，普通研究不需要使用它。

用户发起的成功回测自动保存为独立结果，关联策略版本，参数只作用于本次运行。无日期配置时面板不添加限制；策略自行报告数据不足，不自动补数、换数据或缩小区间。Agent 探索可直接调用程序，按需使用 Library 保存。

## 开发与数据库

在 backend 用 uv 同步锁定依赖，运行 `python ../scripts/dev.py` 启动真实 API 和 Vite。预览使用独立的 target/preview 测试数据，初次生成一个模拟研究与一个模拟策略，数值均实际计算。示例只初始化一次，升级不覆盖用户修改或复活删除内容。

数据库由 backend/src/dorislab_research/migrations 中的 Alembic 修订维护。Agent 编写迁移及相关测试，客户端启用时执行正式升级；普通保存不得自动迁移。测试使用隔离数据库和文件目录。

检查入口：`scripts/check.ps1 -Mode Standard`，可加 `-Target Backend` 或 Frontend。生产服务由客户端管理进程生命周期，只接受当前客户端的本地凭证；用户登录、原始数据、商业权益由 Dorislab 管理。

## Search and large files

The desktop keeps a disposable, account-scoped search index. Library changes have a monotonic cursor;
`search_changes` returns bounded deltas and resets the cursor when the database identity changes.
Saving, archiving, restoring and deleting all update this projection. Direct changes to persistent
files are detected on the next search; unchanged file bodies are not reread. Filenames and Markdown/
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
