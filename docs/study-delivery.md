# 通用研究交付

用于事件研究、分组比较、假设检验、综述和研究修订，不限定指标或分析程序。即时数据查询不必创建正式成果。研究可以很短，证据不足也可交付，但须说明范围和限制。

在本轮 results 的新目录保存可再次运行的分析代码、实际参数与输入身份、计算结果、报告和必要图表。代码从参数读取输入，不依赖临时 shell 变量；报告数字和图表由相同结果生成。复算应另用输出目录，保留已交付证据。大型行情保留宿主发布／选包身份和读取请求，遵循数据边界，不复制另一套行情库。

执行自编脚本时，用 execution.python 执行 execution.launcher，再传 `python <脚本绝对路径> [参数]`，使用同一工程的隔离依赖环境；裸 Python 没有工程依赖。当前锁中有 NumPy、PyArrow；其他库先核对依赖，必要时按授权维护项目和锁文件。首次使用的新 results 目录可直接创建。

在这些文件旁写一个导出请求 JSON。以下名称是文件组织示例，内容须由本次研究真实生成：

```json
{
  "schema_version": 1,
  "title": "通信行业超卖持续时间与后续收益研究",
  "summary": "说明研究范围及有证据支持的主要发现。",
  "data_nature": "real",
  "body": "report.md",
  "files": ["report.md", "code/compute.py", "parameters.json", "provenance.json", "result.json", "episodes.csv", "duration.png", "environment/uv.lock", "execution.log"],
  "cover": "duration.png",
  "execution": {
    "entrypoint": "code/compute.py",
    "parameters": ["parameters.json"],
    "environment": ["environment/uv.lock"],
    "data": ["provenance.json"],
    "evidence": ["execution.log"],
    "instructions": "使用封存工程的 Python 入口，在材料目录运行 code/compute.py，读取 parameters.json，另用新输出目录。按 provenance.json 的确切选包身份重新授权读取数据；缺少该版本时报告缺口。"
  }
}
```

`files` 显式列出要封存的文件，均相对于请求所在目录；保留目录结构，包含程序依赖的本地模块与必要环境依据。`execution` 的路径也以这个材料目录为根，全部列入 `files`，同一路径不在多个角色重复声明。参数中的包内路径同样使用相对路径；外部行情使用确切授权数据身份，不以历史临时目录绝对路径作为唯一入口。Markdown 图片以正文所在目录为根，例如 `![持续时间分布](duration.png)`。

运行上下文声明 `capabilities.artifactExecutionMaterials=true` 时，使用受管 Python 执行本工程 run.py，传以下命令：

```text
save-study --request <请求.json> --output <results 下新的导出目录>
```

该命令整理材料、生成哈希并请求 Rust 保存文件和数据库记录。Rust 额外封存保存时的工程源码及依赖锁，排除依赖缓存和本地私密配置；源码快照与成果版本一起保留。执行入口、参数、环境、数据身份和已有验证记录由 Agent 声明，程序检查它们确实在文件清单中，不会推测任意脚本的全部动态依赖。保存成功不等于复现通过，也不能证明保存时的每份源码都曾用于产生结果。必要时执行一次脱离原目录的验证，并将实际验证记录作为证据保存。

完整字段用 `study-schema` 查看。越界、链接、缺失和重复材料会被拒绝。回执丢失可用相同参数再次 `save-study`，或对已导出的同一包 `publish`；同请求改内容必须使用新目录。无计算的综述可省略 `execution`，用 `export-study` 后 `publish` 保存阅读材料，不生成空脚本；这类成果不会被标作可直接准备执行。

保存成功后得到 receipt.uri，调用宿主 open_content 展示该链接，并在回答中保留 `[研究标题](receipt.uri)`。后续修订用 `--previous <原回执.json> --note <修订说明>` 保存到新目录。

接续已保存版本使用 `prepare-publication --receipt <原回执.json>`。回执可从当前目录索引按确切版本读取并写入本轮临时文件。Rust 将校验过的工程和材料复制到本轮 results 的新目录，返回 `project`、`materials` 和执行说明；它不会运行代码或更换数据，`reproduction_status=not_verified` 表示本次尚未复现。使用返回工程的 run.py 准备原锁定环境，按说明读取材料，输出放新目录；修订保存时追加 `--project <返回的 project>` 固定本次实际选择的工程源码。公共工程合并仍只处理本轮 source 中的改动。

旧成果缺少执行声明时，接续入口会说明限制。保留原成果与原计算目录，补齐材料后保存明确的新版本，不修改封存文件，也不直接删除旧材料。

宿主边界、文件上限、兼容与故障处理见[宿主兼容](host-compatibility.md)，领域质量要求见[产物规范](artifacts.md)。
