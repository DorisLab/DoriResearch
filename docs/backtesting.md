# 日线 ETF 回测入口

当前可执行 profile 为 `dorislab.etf-momentum.v1`，属于可编辑工程的默认实现，不是宿主领域协议。使用锁定的 DoriBT 0.6.2 公开接口；策略与运行记录保留实际安装的引擎版本。宿主只接收策略和运行成果外壳，不增加金融 Agent Tool。

## 支持范围

固定 ETF 池、月度正动量、做多与现金。首次估值日及以后每月第一个交易日收盘，按 `lookback` 日涨幅排序，保留正动量前 `top_n` 只，平分 `max_exposure` 目标权重；并列按代码排序。下一根日线开盘参考价执行，实际成交受费用、滑点、参与率和委托约束。目标上限不是实时仓位硬限制。期末保留持仓估值，不补造强平。

`warmup_start` 到 `start` 前为预热；`start` 收盘是初始估值点，最早下一交易日成交，指标仅统计 `(start, end]`。两个端点必须是实际开市日。源日历必须逐日覆盖整个请求范围，不从工作日或行情日期推测日历。

行情读取同一明确 selection 的未复权 ETF 日线、CN 日历、ETF 公司行动记录，复用成品对象并校验 SHA-256。出现公司行动记录、昨收与前收不连续、未知停牌状态、缺失或重复 bar 都失败。源停牌标记按 0 正常、1 停牌解释，其他值拒绝；停牌仍须有明确估值价格且成交量为零。固定已上市标的池，不支持上市退市、动态池、股票或分钟线。

当前公司行动数据不足以表达完整到账、交收与历史可知时点，因此本 profile **仅允许未观察到公司行动的区间**，不把缺失字段补成零分红。未发现记录仍不证明源数据完整。事后修订行情也不是 point-in-time 数据；结论保留这两项限制。

涨跌停比例、价位、交易单位、交收日数、费率、滑点和参与率都须在请求中声明。每日限价按昨收乘比例、按价位四舍五入推算，是研究假设，不冒充交易所历史规则库；OHLC 超出声明限价拒绝。不同规则的 ETF 应分开请求或先扩展适配器，不能套用同一规则而不说明。

成交量源单位为手，固定换算成 100 份，与委托单位设置无关。价格只允许不超过 `1e-10` 元的浮点编码噪声校正到声明价位，成交量只允许换算后 `1e-6` 份以内的噪声；真实越价位或碎片数量拒绝。原始浮点值仍在输入快照中。

## 请求与运行

客户端中用本轮 `execution.python` 执行 `execution.launcher`；以下是 `run.py` 后的参数：

```text
backtest-schema
backtest --catalog <本轮 localData 清单> --request <请求 JSON> --output <results 下的新目录>
verify-backtest --bundle <计算目录>
```

请求以当前 `backtest-schema` 为准，不允许未知字段。示例仅说明格式，不推荐该标的或参数：

```json
{
  "title": "ETF 正动量半仓月度轮动回测",
  "selection": "替换为本轮清单中的 64 位 selection ID",
  "symbols": ["159915.SZ"],
  "warmup_start": "2025-01-01",
  "start": "2025-02-07",
  "end": "2025-03-31",
  "parameters": {"lookback": 20, "top_n": 1, "max_exposure": "0.5"},
  "assumptions": {
    "label": "明确描述本次假设及未核验范围",
    "price_tick": "0.001", "lot_size": 100, "settlement_days": 1,
    "price_limit_ratio": "0.2", "commission": "0.0003", "minimum_commission": "5",
    "stamp_duty_sell": "0", "transfer_fee": "0", "slippage_bps": "2", "max_participation": "0.05"
  },
  "benchmark": "none",
  "data_nature": "real"
}
```

`initial_cash` 默认 100000 元；`risk_free_rate` 与 `target_return` 默认显式记录为年率 0。`benchmark=none` 表示没有基准，其指标为 not_applicable；`cash_zero` 才表示主动选择无息现金曲线。数据性质必须对应实际输入；测试样本使用 synthetic，不因引擎执行成功就改成 real。

每次运行保留请求、来源清单、输入快照、源文件与锁、环境、策略定义、DoriBT 原始导出、归一化结果、报告、日志和摘要清单。失败目录也保留；修复后新目录，`previous_run` 指向前次运行 ID。强制中断留下 running 表示未确认结束。

## 指标与校验

按[指标规范](metrics.md)生成累计／年化收益、波动、回撤、最长水下期、夏普、索提诺、最差完整月、平均／最高仓位、单边／年化换手、成交额、订单／成交数与费用。每项有定义版本、单位、状态、原因、参数和证据引用；不以 0 替代不可算值。初始估值点保留，预热不稀释指标。完整月份需有完整日历及前一估值；月末日历覆盖不足时保守标为部分月。没有训练、参数搜索或交易配对，不生成虚假的样本外、胜率、DSR 或蒙卡指标。

`result.json` 保存净值、负号回撤曲线、回撤区间及期末截尾状态、现金、持仓、月收益、费用和换手。DoriBT 原始统计另存 `engine/`；其中回撤为正号等定义差异不覆盖。滑点已经进入成交价，单独展示其价差成本，不再次扣现金。

`charts.json` 使用工程格式 `dorislab.backtest.chart.v1`，只保留 account 中的 date/nav/drawdown/exposure、monthly 和 benchmark，供页面读取。内容取自同次计算并进入文件摘要及独立重放比较，不能由 Agent 为美观另造曲线。默认渲染器优先读此文件，历史结果可回退读 result.json；未知格式保留正文。宿主通用文本读取限 2 MiB，大账本不通过该桥接加载。

运行先用成交记录独立重放现金与持仓，核对账户恒等式、订单／成交关联及数量。`verify-backtest` 还实际重新执行引擎，逐字节比较账本、持仓、账户、原始统计、项目指标和报告；成功仅证明本次复算一致，不证明策略有效。校验要求使用已存档的 Python、依赖与源码版本；工程已更新时明确拒绝，需在隔离副本中恢复归档源码和锁后校验，不修改旧成果。

## 正式交付

```text
export-strategy --bundle <计算目录> --output <新策略包目录>
publish --package <策略包目录>
export-backtest --bundle <计算目录> --output <新运行包目录> --strategy-package <策略包目录> --strategy-receipt <策略回执 JSON>
publish --package <运行包目录>
```

策略导出先核验实际运行，保存规则、参数 Schema、入口和代码依赖，不把此次业绩写进策略定义。同一策略版本可承接不同实际参数的多个独立运行；运行导出检查策略定义摘要与已确认回执，并绑定确切策略版本。策略规则修订支持 `--previous <旧策略回执> --note <说明>`。每次计算都是新的运行成果。

导出包在登记前再次复算；运行包附独立复算记录。回执丢失时对同包再次 publish，不能重新导出制造新身份。正式回执 URI 用于交付，研究室策略／运行板块和全局搜索显示登记内容。运行页提供净值／回撤／仓位切换、月收益、图表引用，以及 Markdown 表格和可下载账本；曲线失败时正文仍可读。完整公司行动和逐日市场规则接入仍待后续实现。

## 列表概览

成功运行另存 `overview.json`（`dorislab.backtest.overview.v1`），包含实际 status、created_at、请求 start/end 和同次结果的 metrics。它进入文件清单、导出与哈希校验；重放还验证其与冻结 run/request/result 一致。列表只展示 computed、ratio 类型的收益和回撤值，缺失不填零。旧包无需改写，列表可读取原有三份文件；未知格式继续提供成果正文入口。
