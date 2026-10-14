"""Readable reports composed from actual request and computed evidence."""

from typing import Any

from .backtest_request import BacktestRequest

LABELS = {
    "total_return": "累计收益",
    "annual_return": "年化收益",
    "annual_volatility": "年化波动",
    "max_drawdown": "最大回撤",
    "longest_underwater": "最长水下期",
    "sharpe": "夏普",
    "sortino": "索提诺",
    "worst_complete_month": "最差完整月份",
    "average_exposure": "平均仓位",
    "maximum_exposure": "最高仓位",
    "one_way_turnover": "单边换手",
    "annual_turnover": "年化单边换手",
    "traded_value": "成交金额",
    "fill_count": "成交笔数",
    "order_count": "订单数",
    "fees": "实际费用",
    "benchmark_return": "基准收益",
}


def metric_row(value: dict[str, Any]) -> str:
    name, number = value["metric_id"], value["value"]
    reasons = {
        "no benchmark selected": "未选择基准",
        "no downside observations": "没有下行收益观察值",
        "fewer than two daily returns": "日收益不足两个观察值",
        "insufficient returns or zero variance": "样本不足或收益方差为零",
        "no proven complete calendar month": "没有可确认的完整月份",
        "invalid duration or terminal equity": "估值跨度或期末权益不适用",
    }
    if number is None:
        return f"| {LABELS[name]} | — | {reasons.get(value['reason'], value['reason'])} |"
    if name in {"sharpe", "sortino"}:
        display = f"{number:.3f}"
    elif name in {"one_way_turnover", "annual_turnover"}:
        display = f"{number:.3f} 倍"
    elif value["unit"] == "ratio":
        display = f"{number:.2%}"
    else:
        unit = {"count": "笔", "CNY": "元", "trading_days": "个交易日"}[value["unit"]]
        display = f"{number:,.2f} {unit}" if value["unit"] == "CNY" else f"{number} {unit}"
    return f"| {LABELS[name]} | {display} | |"


def assumptions_text(request: BacktestRequest) -> str:
    a = request.assumptions
    return (
        f"初始资金 {request.initial_cash:,.2f} 元；佣金 {a.commission:.3%}，"
        f"最低 {a.minimum_commission} 元；"
        f"滑点 {a.slippage_bps} bp；参与率上限 {a.max_participation:.1%}。\n\n"
        f"假设价格变动单位 {a.price_tick} 元，委托单位 {a.lot_size} 份，"
        f"交收 {a.settlement_days} 个交易日，涨跌停幅度 {a.price_limit_ratio:.0%}；"
        f"卖出印花税 {a.stamp_duty_sell:.3%}，过户费 {a.transfer_fee:.3%}。"
    )


def report(request: BacktestRequest, result: dict[str, Any]) -> str:
    lines = [
        f"# {request.title}",
        "",
        "固定规则的一次描述性回测；没有参数搜索、训练或样本外验证。",
        "",
        f"初始估值：{request.start} 收盘；结束：{request.end} 收盘。"
        f"预热从 {request.warmup_start} 开始，"
        "不计入收益区间。期末保留持仓并按市值估值，不强制平仓。",
        "",
        f"标的：{'、'.join(request.symbols)}。"
        f"数据性质：{'真实行情' if request.data_nature == 'real' else '合成样本'}。",
        "",
        "## 规则与实际参数",
        "",
        "按正动量排序，首次估值日及此后每月第一个交易日收盘生成目标；"
        "仅使用已完成日线，下一交易日开盘尝试执行。非正动量不持有，余款为现金；"
        "仓位上限约束目标权重，日内价格变化可能使实际仓位超过目标。",
        "",
        f"本次回看 {request.parameters.lookback} 个交易日、最多持有 {request.parameters.top_n} 只，"
        f"目标总仓位 {request.parameters.max_exposure:.0%}。",
        "",
        "## 指标",
        "",
        "| 指标 | 数值 | 说明 |",
        "| --- | ---: | --- |",
    ]
    lines.extend(metric_row(m) for m in result["metrics"])
    lines += [
        "",
        "夏普和索提诺为无量纲比值。"
        "年化按实际日历跨度计算，短样本的年化不是收益预测。"
        "统计定义见结构化指标的 definition_version。",
        "",
        "## 月度收益",
        "",
        "| 月份 | 收益 | 完整性 |",
        "| --- | ---: | --- |",
    ]
    lines += [
        f"| {r['month']} | {r['return_rate']:.2%} | "
        f"{'完整' if r['complete'] else '部分或日历覆盖不足'} |"
        for r in result["monthly"]
    ]
    lines += [
        "",
        "## 成交假设与边界",
        "",
        request.assumptions.label,
        "",
        assumptions_text(request),
        "",
        "价格、停牌标记和日历来自已选本地成品；价格是事后修订数据，不能证明历史可知时点。"
        "涨跌停价按声明的比例和价位四舍五入推算，交易规则是研究假设，不是逐日交易所规则事实。"
        "成交量按源单位手换算为 100 份；不补缺失行情。",
        "",
        "预热及运行区间发现公司行动记录或昨收不连续即拒绝运行。未发现记录不等于证明源数据完整。"
        "当前不支持分红到账、拆分、上市退市、动态标的池或分钟交易。",
        "",
        f"基准：{'无息现金' if request.benchmark == 'cash_zero' else '未选择'}。"
        "未定义交易配对，因此不输出胜率、盈亏比或蒙卡盈利概率。",
        "",
        "## 证据",
        "",
        "result.json 保留估值、净值、回撤区间、持仓、月收益和指标；"
        "engine/ 保留 DoriBT 原始账户、订单、成交、意图和统计，含零成交时的空表。"
        "sources/ 与输入及来源清单固定本次代码、依赖和数据身份。滑点已计入成交价，不重复扣费。",
        "",
    ]
    return "\n".join(lines)


def strategy_report(definition: dict[str, Any]) -> str:
    defaults = definition["default_parameters"]
    return "\n".join(
        [
            "# ETF 正动量月度轮动策略",
            "",
            "首次估值日及每月第一个交易日收盘，计算固定标的池在回看期内的价格变化，"
            "选择涨幅为正、排名靠前的 ETF，平分目标总仓位；其余资金留在现金。"
            "并列时按证券代码排序。下一交易日尝试成交，期末按市值估值。",
            "",
            "这是一份可运行规则，业绩属于具体运行。标的、实际参数、数据窗口和成交假设由每次运行明确给出。",
            "",
            "## 参数与数据要求",
            "",
            f"默认回看 {defaults['lookback']} 个交易日、最多持有 {defaults['top_n']} 只 ETF、"
            f"目标总仓位 {float(defaults['max_exposure']):.0%}。"
            "需要独立 CN 交易日历、完整未复权 ETF 日线、停牌标记与公司行动检查；"
            "预热长度至少覆盖回看期。仅支持无公司行动区间。",
            "",
            "## 运行与版本",
            "",
            "通过对话指定标的、时间范围、参数与成交假设后运行。"
            "不同运行分别保存其数据、代码、账本与费用，不覆盖历史结果。"
            "数据或公司行动超出支持范围时明确报告失败。",
            "",
            "完整参数定义与运行入口见 [策略定义](strategy.json)，实际代码与依赖列于文件与版本。",
            "",
        ]
    )
