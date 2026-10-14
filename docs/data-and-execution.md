# 数据、计算和环境

## 路径与实际能力

运行时 `source` 是当前账号的完整工程，`results` 保存跨对话计算与证据，`status` 是前端构建状态。保持会话 cwd，原生命令可显式指定工程 backend 为工作目录。定制可改变内部布局，先核对 README、CLI 帮助和源码。

客户端内使用 `execution.python` 执行 `execution.launcher`，再传下面的 CLI 参数；入口自动准备隔离依赖。独立开发才在 backend 使用 `uv sync --locked` 与 `uv run --no-env-file dorislab-research`。

受管入口隔离外部 Python／uv 配置及 DoriBT 原生扩展开关，默认安装锁定的官方纯 Python wheel。
自编工程需要可选加速时须明确声明依赖和配置，不能依靠外部 shell 设置改变默认执行。

## 数据来源

使用 Dorislab 已登记成品的发布／选择身份和本工程读取器，或用户授权材料。本轮上下文给出 `dorislab.local-data.v1` 清单路径与 available/error；没有清单时明确缺口，不扫描缓存或另造行情主库。CSV／JSON／Parquet 等只作为声明的输入材料、派生输出或临时计算。

查询数据范围时使用 `data-catalog --catalog <宿主清单路径> [--query <名称或ID片段>]`；摘要区分目录声明范围与本地文件分区端点，不代表完整性核验。需要逐行计算时执行 `data-catalog --catalog <宿主清单路径> --dataset <数据集ID> --details`，从实际返回中选定 selection 并核对 spec／view 的列、单位、日期语义、限制。使用 `data-schema` 查看格式。例如请求如下，selection 必须替换成实际返回的64位身份，日期必须在该选包内，字段与证券必须按目录确定：

```json
{"selection":"<实际选包身份>","dataset":"raw/market/bars_1d_etf","columns":["trade_date","symbol","close"],"symbols":["510300.SH"],"start":"2025-01-01","end":"2025-01-31","max_rows":100000}
```

执行 `data-read --catalog <同一清单> --request <请求JSON> --output <results下新目录>`。请求 JSON 可放会话 `.tmp`；输出目录由程序创建，传入尚不存在的路径，避免覆盖已有证据。也可调用 `dorislab_research.local_data.read_data`。程序校验选包范围、字段、对象大小／Hash、主键和行数，不自动补数／换版本。每日按日期过滤，区间按重叠与 end_exclusive，快照不能当作历史时点数据。导出 data.json 保留 null，provenance.json 固定查询、发布／选包、字段、对象、质量元数据和输出 Hash。转成分析／回测输入时必须随包保留来源，不能只留下摘出的数值。

行数超过上限直接失败；缩小窗口，不把截断当作完整结果。数据集日期端点与已安装状态不能证明连续覆盖；质量元数据缺失记录为未知，不能据此宣称完整或历史时点可用。缺文件／校验失败时交由 Dorislab 数据设置修复，不扫描其他版本代替。

数值证据保存来源、字段、区间、频率、单位、数量、预热、日历、复权、可知时点与缺失处置；必要时保存获授权输入快照。免费数据目标 2025-01—2026-09、日线，不构成长期或独立样本外证据。实际可用性由服务确认；不以假数据声称完成分钟研究。

旧合成示例已移除；内置 DoriBT 固定为 0.6.2，提供日期化历史规则和证券／日期 override，具体范围见[引擎规则手册](https://dorislab.github.io/DoriBT/china-market.html)。工程默认日线 ETF profile 仍使用显式研究假设，未自动接入完整历史规则或公司行动；其他策略通过自编脚本按实际输入调用引擎。用户材料可用于分析，但必须保留其身份和实际覆盖，分钟回测须另有合格分钟数据。

## 运行证据

保存 request、实际输入身份／快照、源码和锁文件、环境、实际参数、结果、日志与校验。一次用户发送可产生多个计算；修复后重试另建身份并关联前次。普通探索命令不全部强制登记。

已完成／失败目录不覆盖，中断保存已有文件，不在重启后自动重放。工程记录表达领域状态，不冒充宿主观察的进程事实。取消受理不代表已停止。复现分别说明输入／环境可获得、是否实际复算及容差。

## 当前可执行路径

- `analyze --request <JSON> --output <新目录>`、`verify-analysis --bundle <目录>`：明确来源的日期／数值 CSV 分析，保存独立证据和 Markdown。请求格式用 `analysis-schema` 查看。
- `backtest`、`verify-backtest`、`export-strategy`、`export-backtest`：真实本地成品或明确合成样本的日线 ETF 回测，使用 DoriBT 公共接口。适用范围、必需假设和终端步骤见[回测入口](backtesting.md)。不支持的公司行动与缺失数据明确失败。
- `doctor --project <工程根>`：检查资料与两个 Skill、CLI 版本和已支持 profile，不代表正式登记可用。

入口可按任务扩展，新增功能同步 Schema、检查、说明和消费者。宿主 `localDataRead` 仅表示发现接入，本轮 available/error 与实际读取决定可用性。正式宿主登记仍以 capabilities 为准。
