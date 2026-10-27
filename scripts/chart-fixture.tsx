import { createRoot } from "react-dom/client";
import * as echarts from "echarts";
import { PublishedPage } from "/src/pages/PublishedPage";
import { chartOption, seriesColor } from "/src/charting";
import "/src/styles/base.css";
import "/src/styles/studio.css";
import "/src/styles/report.css";
import "/src/styles/typography.css";
import "/src/embedded/style.css";

const params = new URLSearchParams(location.search);
window.chartFixture = () =>
  echarts.getInstanceByDom(document.querySelector(".content-chart-canvas"));
const font = Number(params.get("font") || 15);
const dark = params.get("dark") === "true";
const kind = params.get("kind") || "study";
document.documentElement.dataset.theme = dark ? "dark" : "light";
document.documentElement.style.cssText = `--ui-font-size:${font}px;--content-font-size:${font}px;--font-ui:Segoe UI,Microsoft YaHei,sans-serif;--font-content:Segoe UI,Microsoft YaHei,sans-serif;--canvas:${dark ? "#16181c" : "#fff"};--text:${dark ? "#f1f2f3" : "#24282c"};--muted:${dark ? "#bbc0c8" : "#60666d"};--line:${dark ? "#454a52" : "#dfe4e8"};--surface:${dark ? "#24282c" : "#f5f6f7"};color:var(--text);background:var(--canvas)`;
const dates = Array.from({ length: 60 }, (_, i) =>
  new Date(Date.UTC(2026, 7, i + 1)).toISOString().slice(0, 10),
);
const base = {
  xAxis: {
    type: "category",
    data: dates,
    name: "交易日期（按交易日顺序展示）",
  },
  yAxis: { type: "value", name: "累计净值（初始基准 = 1）", scale: true },
  series: [
    {
      type: "line",
      name: "合成策略",
      data: dates.map((_, i) => 1 + i * 0.001 + Math.sin(i * 0.5) * 0.015),
    },
  ],
};
const cases = {
  normal: base,
  state: {
    ...base,
    legend: { selected: { 合成策略: true } },
    dataZoom: [
      { type: "inside", start: 5, end: 95 },
      {
        type: "slider",
        bottom: 2,
        height: 16,
        showDetail: false,
        start: 5,
        end: 95,
      },
    ],
  },
  title: {
    ...base,
    title: {
      text: "策略与基准的累计收益比较：包含较长标题的研究图表在窄栏中仍然完整换行",
      subtext: "合成样本，净值以期初为1；标题与口径不占用绘图区。",
    },
  },
  legend: {
    ...base,
    series: Array.from({ length: 8 }, (_, i) => ({
      type: "line",
      name: `第${i + 1}组较长的研究策略名称与比较条件`,
      data: dates.map((_, j) => 1 + j * 0.001 + i * 0.02),
    })),
  },
  count: chartOption({
    title: "事件次数",
    kind: "bar",
    x: ["甲组", "乙组", "丙组", "丁组"],
    x_label: "研究分组",
    y_label: "发生次数",
    series: [{ name: "次数", values: [1, 2, 1, 3] }],
  }),
  drawdown: {
    ...base,
    title: { text: "历史回撤" },
    yAxis: {
      type: "value",
      name: "回撤（%）",
      max: 0,
      axisLabel: { formatter: "{value}%" },
    },
    series: [
      {
        type: "line",
        name: "回撤",
        itemStyle: { color: seriesColor("drawdown", 0, dark) },
        areaStyle: { opacity: 0.15 },
        data: dates.map((_, i) => -Math.abs(Math.sin(i * 0.08) * 12)),
      },
    ],
  },
  time: {
    xAxis: { type: "time", name: "自然日期" },
    yAxis: { type: "value", name: "数值" },
    series: [
      {
        type: "line",
        name: "不等间隔日期",
        data: [
          ["2026-01-01", 1],
          ["2026-01-02", 2],
          ["2026-10-01", 3],
        ],
      },
    ],
  },
  pie: {
    series: [
      {
        type: "pie",
        data: [
          { name: "甲", value: 1 },
          { name: "乙", value: 2 },
        ],
      },
    ],
  },
};
const option = cases[params.get("case") || "normal"];
const reference = { kind, id: "chart-fixture", version: "1" };
const content = {
  item: {
    title: { study: "研究图表", strategy: "策略比较", run: "回测结果" }[kind],
    summary: "隔离合成样本，仅验证图表展示。",
    reference,
    data_nature: "synthetic",
    origin: "project",
    registered_at: 1793059200000,
  },
  body:
    "以下图表用于比较样本中的变化。\n\n```echarts\n" +
    JSON.stringify(option) +
    "\n```\n\n图注：数据为程序生成的合成样本，不代表市场表现。",
  files: [],
  references: [],
  related: [],
  revision_note: "",
};
createRoot(document.getElementById("root")).render(
  <div className="artifact-scroll">
    <PublishedPage
      host={{ open: () => {}, reference: () => {}, protocolVersion: 1 }}
      content={content}
    />
  </div>,
);
