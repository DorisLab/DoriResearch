# Dorislab 研究工程

这是当前账号跨对话使用的研究工程，包含页面、分析和策略程序。源码与规范可按用户任务修改；官方仓库开发另遵循仓库根目录约定。

## 开始工作

客户端上下文的 `execution.python` 与 `execution.launcher` 是受管入口：用前者执行后者，再传下面的子命令，依赖由入口准备。保持会话 cwd，计算文件保存在 `results` 的新目录。

开始计算或修改工程前，先调用 `prepare-project`。它创建或接续本会话隔离工作区，返回 `project`、本轮 `results` 和固定的 `base_commit`；随后以返回工程中的 `run.py` 执行命令。普通交流或只读查询不需要准备工程。不要直接修改账号公共源码或沿用历史绝对路径。成果保存与公共代码合并独立：成功结束后客户端验证合并候选，冲突或验证失败保留源码和诊断，不覆盖主线。

- 了解有哪些数据或覆盖范围：`data-catalog --catalog <本轮清单> [--query <数据集名称或ID片段>]`，例如查询 A股、ETF；不搜索证券名称或代码。返回选包身份与已安装范围，不代表逐日连续性核验。
- 读取数据做计算：先用 `data-catalog --catalog <清单> --dataset <ID> --details` 查看字段与口径，再按[数据与执行](docs/data-and-execution.md)调用 `data-read`。
- 执行自编研究脚本：`python <脚本绝对路径> [参数]`，仍由前述 Python 执行 run.py；该入口使用工程锁定依赖（如 NumPy、PyArrow），裸 Python 不等于工程环境，其他依赖先核对 pyproject.toml。
- 研究报告、接续研究：按需使用 [research-study](.agents/skills/research-study/SKILL.md)。
- 策略、回测、选参：按需使用 [strategy-evaluation](.agents/skills/strategy-evaluation/SKILL.md)。
- 图表与封面：使用工程的 ECharts／Matplotlib 公共入口，见[绘图与导出](docs/charting.md)。受管入口已安装 `doribt[plot]`；依赖检查和脚本执行均使用工程环境。
- 定制页面和程序：[README](README.md)提供结构与开发命令；接口不明确时查看相关子命令的 `--help` 或源码。

## 交付与维护

结论和图表以实际计算为依据，数据保留来源、范围和单位。已交付的证据保持不变，更正和重跑使用新版本；正式登记以宿主回执为准。具体产物规则在工作流需要时读取。

即时问答可直接给结论；研究规律、比较方案和检验假设应保存可接续的工程，并登记到研究室。计算研究声明相对路径的执行材料，使用 `save-study`；接续版本使用 `prepare-publication`，按返回的工程与材料路径工作。无计算的综述可用 `export-study` 后 `publish`。见[研究交付入口](docs/study-delivery.md)。交付时可用宿主 open_content 工具主动展示文件或登记链接。

修改程序时同步维护相关说明和读写接口。Python 在 backend 使用受管 uv 运行 `ruff check .`、`ruff format --check .`、`mypy`、`pytest`；前端在 frontend 执行 `npm run typecheck`、`lint`、`test`、`build`。迭代时验证受影响行为，交付前完成对应检查。
