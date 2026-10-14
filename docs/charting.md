# 绘图与导出

公共绘图使用 ECharts（交互页面）和 Matplotlib（静态图表／封面）。策略红、基准蓝、超额金、回撤粉；唯一配色源是 `backend/src/dorislab_research/chart_theme.json`，与 DoriBT 默认值一致。普通比较序列使用同一分类色板；用明确的 role 表达业务含义，不按序列名称猜角色。

## 在受管工程环境中执行

按照 AGENTS.md 的 `execution.python` + `execution.launcher` 入口运行：

```text
chart-schema
chart --request <绝对路径/chart.json> --output <绝对路径/cover.png>
python <绝对路径/analysis.py>
```

`chart` 支持 line、scatter、bar、heatmap，PNG/SVG/PDF 导出。示例请求（数值仅说明格式）：

```json
{"kind":"line","title":"净值对照","x":["2026-01-01","2026-01-02"],"y_label":"净值","series":[{"name":"策略","role":"strategy","values":[1,1.02]},{"name":"基准","role":"benchmark","values":[1,1.01]}]}
```

散点图使用数值横轴；热力图的每个 series 对应一行。缺失值使用 null，保留断点。图表使用实际计算结果；同一报告的数字与图必须来自同一份结果。

复杂排版可直接用 Matplotlib，在 `dorislab_research.charting.chart_style()` 内创建 Figure，使用 `color(role)` 和 `save_figure(figure, output)`。保存不会覆盖已有文件，重跑输出到新目录。DoriBT 的 `result.plot(benchmark=...)` 返回 Figure，交给同一保存入口；当前回测命令自动生成 `cover.png`，运行登记自动引用该图。策略说明不强制使用回测封面。

## ECharts 页面

`frontend/src/charting.ts` 提供 `chartOption(spec)`、`seriesColor(role, index)`、`exportChart(instance, 'png' | 'svg')`。调用方按图型注册 ECharts 模块；现有回测和示例曲线已共用配色。主题字体／深浅颜色继续由 `components/chartAppearance.ts` 投影。

浏览器导出返回图片 data URL，可用于预览或页面下载；导出保留图表显式背景，未指定时沿用所在页面的深浅主题底色。Agent 需要本地 PNG 文件登记封面时，使用上面的受管 `chart` 命令。Matplotlib 与 ECharts 已覆盖常见研究图，不再自行编写 PNG 编码器或引入另一套绘图库。

## 登记与阅读

封面选择一张能表达主要发现的 PNG（建议 120–160 DPI），检查文字和图例清楚且文件不超过宿主的 1 MiB 封面限制。`export-study` 的 `cover` 指向该文件，并同时列入 `files`。没有合适的图可省略封面；不能为填充卡片制造无依据图表。登记后客户端从成果清单读取封面，文件缺失或校验失败只影响封面，并提供重试。
