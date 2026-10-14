# DoriResearch

Dorislab 的可编辑研究工程，使用 MIT 许可证。包含研究界面、Python 分析与回测工具、Agent 工作规范及两个任务 Skills。仓库不包含个人成果、行情数据、账户凭据或客户端商业服务。

包含独立 React/TypeScript/Vite 前端、Python CLI 与 DoriBT 回测入口。用户与 Agent 可以修改整个工程。旧 ETF 示例已删除，研究室只展示当前账号正式保存的成果。

内置 DoriBT 固定为 0.6.2（含 plot），依赖和文件摘要由 backend/pyproject.toml 与 uv.lock 锁定。
策略与运行记录保存实际引擎版本；默认日线 ETF profile 的数据与规则范围见[回测入口](docs/backtesting.md)。

## 在 Dorislab 客户端查看

客户端默认从随包发布版初始化当前账号的工程副本，位置由 Agent 的运行上下文给出。源码保存在 `research/project/`，计算成果保存在同级 `research/results/`；`research/host/` 由客户端维护官方基线、构建与启用状态。不要把成果放进构建缓存，也不要手改 host 状态。

保存源码后，客户端自动检查 TypeScript、构建并校验独立页面，所有打开的研究内容标签加载新版本。构建失败时继续显示上一版，并可查看原因和构建日志；修复源码后自动重试。重启保留源码、计算成果与已启用版本。修改 Python 源码不会自动重算研究。

Dorislab 仓库开发启动：

```powershell
# 默认走账号副本；首次或客户端本身修改后使用 -Rebuild
pwsh -NoProfile -File scripts/start-desktop.ps1 -Rebuild

# 显式绑定官方工程源码，保存后构建并更新原生页面
pwsh -NoProfile -File scripts/start-desktop.ps1 -ResearchSource ../DoriResearch

# 验证另一份本地发布包，保留账号已有定制
pwsh -NoProfile -File scripts/start-desktop.ps1 -ResearchRelease <发布包目录>
```

开发绑定只改变源码位置，构建、日志和成果仍在当前账号目录。启动参数应在后续启动时继续提供。`npm run tauri dev` 的调试构建使用仓库生成的本地发布包，源码绑定仍需显式设置 `DORISLAB_RESEARCH_SOURCE`。普通账号默认不直接读写官方仓库。

兼容的客户端使用官方发布包中的真实 Git 提交和 bundle 初始化账号仓库，采用隔离 worktree 开展工程工作。开始计算或修改前调用 `prepare-project`，并使用返回路径；普通聊天不创建工作区。同一会话后续轮次接续源码，输出仍按轮次隔离。公共源码修改在候选验证通过后合并；官方更新和本地修改冲突时保留候选及诊断。具体启用能力以客户端版本和运行上下文为准，单独运行本仓库不会创建账号仓库。

前端更新不会重新计算或登记用户研究。任意研究可通过 [export-study／publish](docs/study-delivery.md) 保存实际代码、报告和证据并进入研究室与全局搜索；export-analysis 继续支持描述统计格式。自编脚本通过 `run.py python <脚本> [参数]` 使用工程隔离依赖。日线 ETF 回测可登记策略及关联运行，具体范围见[回测入口](docs/backtesting.md)。首次修改后的依赖准备可能需要联网；浏览初始页面不需要 Node 安装依赖或 Python 服务。

## 独立浏览器开发预览

前端执行 `npm ci` 与 `npm run dev`，访问 `http://127.0.0.1:48121`。独立预览只展示空列表外壳，不连接个人成果库，不生成示例。正式成果查询、文件读取和交互在 Dorislab 内通过受控接口验证。

## Agent 入口与独立分析

在 Dorislab 内执行研究命令时，宿主 `execution` 提供受管 Python、uv、Node 与 `run.py` 的绝对路径。使用 PowerShell：`& '<execution.python>' '<execution.launcher>' data-catalog --catalog '<本轮清单>'`。入口将参数转交本工程 CLI，按 `backend/uv.lock` 准备依赖，首次可能下载；之后复用账号专用缓存。不会使用用户 PATH 的 uv、用户虚拟环境或用户 Python 包；源码目录不产生 `.venv`，各源码位置与账号的依赖环境独立。缺少客户端工具、锁文件不匹配或下载失败会返回非零状态，修复后执行同一入口重试。项目依赖变更需同步锁文件，`run.py` 不自动更新锁。

下文独立开发使用 `uv` 的命令，在客户端中对应 `run.py` 后的同名子命令；例如 `python run.py doctor --project <source>`。客户端启动脚本同时准备固定 uv/Python/Node，安装包装配携带这些工具。独立开发仍自行准备文中列明的版本。

工程规则在 [AGENTS.md](AGENTS.md)，两项任务 Skill 位于 `.agents/skills/`；产物、指标、数据与宿主兼容规范在 `docs/`。客户端将当前账号工程的技能根注册到 App Server，保持会话 cwd，每轮刷新发现结果；禁用或缺失技能不宣称加载成功。工程与规范一起更新、保留用户修改。

在 backend 执行 `uv run --no-env-file dorislab-research doctor --project ..` 检查布局，`analysis-schema` 查看当前请求 Schema。`analyze` 接受用户明确提供或授权导出的日期／数值 CSV，不自动获取市场数据：

```json
{
  "title": "ETF 份额变化分析",
  "question": "这份材料覆盖期间的份额如何变化？",
  "input_file": "shares.csv",
  "source_label": "用户提供的份额材料",
  "data_nature": "real",
  "date_column": "date",
  "value_column": "shares",
  "unit": "份",
  "missing": "reject"
}
```

input_file 相对请求文件所在目录解析；来源性质由实际材料决定。运行 `uv run --no-env-file dorislab-research analyze --request <请求文件> --output <results 下的新目录>`，再以 `verify-analysis --bundle <目录>` 检查。程序保留请求、输入快照、源码／锁文件、环境、运行记录、统计结果、校验、报告和摘要清单。失败保留证据，修复后新建目录；输出不是回测，也不声称正式登记。解释更正应另存正文版本，避免覆盖生成的报告证据。

核验后使用 `export-analysis --bundle <计算目录> --output <results 下的新导出目录>`，再 `publish --package <导出目录>`。程序输出正式回执并保存到导出目录旁，使用回执 URI 交付。重复 publish 同包找回回执；修订使用 `--previous <旧回执> --note <说明>` 导出新包。CLI 只在 Dorislab 当前 Agent 终端中获得登记通道；详见[宿主兼容](docs/host-compatibility.md)。当前 profile 见[产物规范](docs/artifacts.md)。

读取已有市场成品使用本轮宿主清单和 `data-catalog`／`data-schema`／`data-read`，或同源 Python API。明确选择版本，按数据集列与日期语义过滤，校验文件并保存 provenance；缺数据不自动下载。用法与限制见[数据与执行](docs/data-and-execution.md)。这层读取复用 Dorislab 原有托管数据，不维护另一套行情主库。`backtest` 复用此读取层和 DoriBT，在无公司行动区间生成正式策略／运行证据；指标定义与限制见[回测入口](docs/backtesting.md)。

## 工程入口

| 位置 | 职责 |
| --- | --- |
| `frontend/src/Studio.tsx` | 三板块导航与内容列表 |
| `frontend/src/pages/` | 研究、策略、运行、系列独立页面 |
| `frontend/src/components/Chart.tsx` | ECharts 与冻结图表引用 |
| `frontend/src/types.ts` | 类型和版本化宿主接口 |
| `frontend/src/preview/` | 仅开发使用的标签、草稿适配器 |
| `frontend/src/embedded/` | 桌面沙箱入口与有限宿主消息桥 |
| `backend/src/dorislab_research/models.py` | 研究请求的严格基础模型 |
| `backend/src/dorislab_research/bundles.py` | 文件摘要与 JSON 写入 |

## 验证

```powershell
pwsh -NoProfile -File scripts/check.ps1
```

该命令在 DoriResearch 仓库根执行类型、lint、格式、行为测试、生产构建、依赖审计和工程规模检查，需要 PowerShell 7.4+、Node 24.13.0、Python 3.13.15 和 uv 0.12.18。局部迭代可分别在前端运行 `npm run typecheck/lint/test/build`，后端运行 `uv run --no-env-file ruff check .`、`ruff format --check .`、`mypy`、`pytest`。检查不需要真实模型、账户凭据或行情网络请求。

Windows 下完整检查前先停止本工程的前后端预览进程，避免依赖重装时被正在使用的原生模块锁住。局部 lint/类型/测试可在预览期间执行。

桌面已接入账号工程副本、源码绑定、构建热更新、原生内容标签、引用草稿与外观同步。正式登记、确切版本阅读、全局搜索与限定范围的真实日线回测已接入；完整公司行动／历史市场规则、专用回测图表、截图圈选、自动升级策略和安装发布由客户端维护，旧示例及专用路径已移除；新示例须由 Agent 实际生成并正式保存。

## 发布与公共组件

`frontend/ui` 是独立版本包 `@dorislab/ui`，由此仓库维护；客户端使用正式发布的压缩包，不依赖相邻源码目录。组件通过主题变量和回调接入，不拥有账号或成果持久化权限。

通过检查并提交后，执行 `node scripts/release.mjs <新输出目录>` 生成包含源码、页面、Git bundle 和完整摘要清单的发布目录。发布的提交身份来自本仓库真实提交，不能使用私有客户端历史。客户端仅使用锁定兼容版本，不追随 main。

成果 Schema 与生成类型来自 Dorislab 的 Rust 契约，随本工程版本发布；接口变化必须通过客户端的契约兼容检查。独立测试不需要私有客户端源码；原生集成测试由客户端负责。
