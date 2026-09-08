# AlphaPit 任务交接

## 状态与工作方式

当前：规划完成，Phase 1 待开发；已初始化 Git（`main`），无代码和测试。没有 Worker 在运行，没有任何实现或验收通过的声明。

总设计师负责文档、接口裁决、最终 Review 和合并；Worker 仅在自己的文件范围内实现。实现前阅读 README → ARCHITECTURE → TASKS → 相关代码/测试 → git status，然后说明问题、最小方案和改动路径。

### 派发前置条件

1. `main` 已初始化，最小 `.gitignore` 已排除 `.pi`、环境变量文件和本地生成内容；基线仅包含审核过的规划文档与 `.gitignore`。派发前确认基线已提交、推送且工作树干净。P1-B 后续按需求扩充 `.gitignore`，不得移除这些保护。
2. 规划基线尚不可运行，明确作为 bootstrap 例外；不得把任一未集成组件当成 Phase 1 完成。实现和联合验收在集成分支完成后，main 才接收可运行切片；此后 main 始终可运行。
3. 从同一个已提交、干净基线创建三个独立 worktree/branch：`feat/p1-api`、`feat/p1-docker`、`feat/p1-ci`。集成分支建议 `integration/phase1`。
4. 先确认 Worker 模型与执行通道可用，使用各自支持的最高思考等级；不假定提示词列举的模型已经可用。不在本次规划中启动 Worker。
5. 三个任务独占不同文件。若需修改契约或越界文件，先回报总设计师，不自行改变架构。

## Phase 1 — 最小可运行服务

目标：空业务 API 通过 Docker 访问 PostgreSQL，CI 验证，数据目录持久化；无交易、Agent 或 UI。

| ID | 任务与输入 | 唯一允许修改文件 | 验收 | 状态 |
|---|---|---|---|---|
| P1-A | Python API / DB 检查；输入为 ARCHITECTURE 的 API、依赖、命令契约 | `pyproject.toml`, `uv.lock`, `src/alphapit/**`, `tests/**` | live / ready 精确匹配；数据库成功/失败、超时配置、资源关闭与 secret 脱敏测试；格式/lint/mypy/单测/真实 DB 集成测试/wheel 通过 | 待派发 |
| P1-B | Docker 开发部署；输入为固定导入路径、端口、uv lock 与 env 契约 | `Dockerfile`, `compose.yaml`, `.dockerignore`, `.env.example`, `.gitignore` | 非 root、仅运行依赖、锁文件 frozen；Compose 正常就绪；DB 不对宿主暴露；故障恢复与卷持久化验证 | 待派发 |
| P1-C | GitHub Actions；输入为固定检查命令与端点 | `.github/workflows/ci.yml` | PR/main 自动检查；PG17 集成测试未跳过；wheel/Docker build 和容器 HTTP smoke 通过；最小 read 权限、无 secret/GHCR 推送 | 待派发 |

独立完整 Prompt 在 `prompts/phase1-api.md`、`prompts/phase1-docker.md`、`prompts/phase1-ci.md`。原始 `WORKER_PROMPT.md` 不修改。

**并行边界：** 三项可按已冻结契约并行编写，不是三个完全独立可验收的产物。P1-B 构建依赖 A 的应用和 lock；P1-C 执行依赖 A/B。缺少依赖、Docker 或网络时，状态必须标记 blocked/未验证，不能报告完成。Worker 可提交明确标注未验收的交接 commit 供集成，不可据此合并 main。基础设施失败不允许私自改换模型或执行协议。

**交接和验收顺序：** A 自测 → 总设计师 review A → 向 B/C 的独立分支同步已审核依赖 → B 全量验收 → C 同步 A/B 并验证 → 集成分支全量验收 → main。同步已审核 commit 不改变文件所有权；发现依赖错误交由对应 owner 修复。

每个 Worker 完成时：formatter → lint → type check → tests → build → 完整 diff 自审 → secret/范围检查 → commit。不能执行的命令必须注明原因、阻塞依赖，不得宣称通过。输出 `Changed / Tests / Known issues`，Tests 含命令、退出码与真实结果；提供 commit hash。

### 总设计师最终验收门

- 检查完整 diff、无重复实现、无多余架构层、无越界改动和 secret。
- 在干净集成 worktree 执行所有标准检查；真实 PostgreSQL 集成测试确实执行。
- `docker compose config`、build、up 成功；live/ready 状态与契约一致。
- 停止 DB 后 live 仍 200、ready 为 503；恢复 DB 后 ready 200，无泄漏。
- 以专用测试库写入临时标记，重建 DB 容器（不删除卷）后标记仍存在，验证后清理标记；不新增业务表到代码仓库。
- 检查镜像非 root；Docker smoke 确实检查 HTTP/JSON；CI 实际运行通过才声称 CI 通过。
- 更新 README 为实际可执行启动说明，ARCHITECTURE 为真实实现；TASKS 更新状态，移除失效临时 Prompt。

## Phase 2 — 市场数据 + Broker + Paper Account

输入：Phase 1 可运行基线。最小切片为单市场源、BTCUSDT perpetual、USDT 结算、单向持仓、逐仓保证金；不实现跨仓或双向 hedge。采用 Binance 风格但将合约过滤器、费率、维护保证金档位等作为版本化规则数据，核心 Broker 不调用交易所 API。

交付：行情适配、ticker/K线/有序 order book/funding、手动下单查询 REST、确定性 Broker。规定陈旧行情拒单、序列缺口重建、相同时间点事件排序、撮合容量、挂单资金预留及释放；不凭空复制无限盘口流动性。记录实际输入，不承诺模拟具有真实交易所排队准确度。

必须在编码前冻结：market/limit 生命周期、部分成交与残单、滑点、maker/taker fee、杠杆、保证金、mark price 未实现 PnL、实现 PnL、funding 结算、维护保证金/强平流程、reduce-only、最小数量/名义金额和 tick/step 规则。Agent 不参与计算。账户级事务锁、幂等请求键和 DB 约束防止并发超扣；所有账户变更只能从 Broker 进入。

验收：逐项覆盖 market buy/sell、limit fill、partial fill、fee、leverage、margin、unrealized/realized PnL、funding、liquidation、insufficient balance、reduce-only、precision；另测撤单释放、重复请求、并发资金、反向平仓及边界行情。Decimal/Numeric，不从 float 构造金融量；固定输入重跑订单/成交/账户状态一致。结束时无需 LLM 即可通过 API 在实时行情上模拟交易。

## Phase 3 — 单 AI Agent 交易

输入：已验收 Broker 与行情。加入一个 OpenAI-compatible adapter、简单 scheduler + worker loop（同一部署，不引入队列）；单 Agent 默认只以低频定时唤醒，每 Agent 一次只运行一个决策。

交付：ticker/klines/orderbook/funding、portfolio、orders.create/cancel 工具；schema、参数与权限校验、超时、调用日志、结构化错误、最大轮数与预算。保存模型请求/响应、工具输入/输出、配置与 prompt 快照；未知 token/cost 标为未知，不当零。前端永远拿不到 Provider key；管理 API 必须认证，后台 key 加密、主密钥由部署 secret 注入；base_url 仅管理员配置并执行服务端目标访问限制。

验收：假 Provider 确定性端到端测试 + 可选真实 Provider smoke；非法工具、超时、重试不重复下单、重启恢复、预算耗尽、secret 脱敏测试。没有任意 shell 或任意网络工具。一个 Agent 可持续获取行情并交易。

## Phase 4 — 多 Agent 隔离 + CRUD

交付：受认证保护的 Agent REST CRUD（name/provider/model/base_url/key/prompt/必要参数/tools/初始资金/最大杠杆/预算），独立账户、仓位、订单、上下文、memory、workspace、搜索/工具/交易记录与成本。身份由服务端注入，不能信任模型传入的 agent_id。

比赛冻结配置快照和规则；修改运行中配置作用于下次比赛或停止后重启，不悄悄改当前排名条件。已有交易记录的 Agent 采用停用/归档而非级联删除。比赛内每 Agent 独立虚拟流动性账本、相同市场快照和撮合规则，避免 Agent 调度顺序争抢共享模拟盘口；单 Agent 内仍有容量约束。

验收：两 Agent 同时运行，无法互读策略/prompt/仓位/memory/workspace/日志；路径穿越、伪造 ID、并发及重启测试通过。CRUD 不回传 key，只返回是否配置。

## Phase 5 — search / news / watch / memory

交付：统一 web.search/fetch、news.search、memory.read/write、watch.create/delete；定时、价格、funding、新 K线、亏损、新闻关键词 watch，以简单循环持久化触发，限频、去重、合并唤醒。

short-term context 有界；long-term memory 用 text/JSONB；trade journal 保留决策关联。无向量库。记录检索返回内容和工具结果，新闻/网页是不可信数据。

验收：web.fetch 限制 scheme、端口、响应体、重定向和超时；初始与每次跳转校验解析 IP，阻断私网/回环/链路本地/云元数据/IPv6 特例并防 DNS rebinding；部署出站网络防护作为纵深措施。测试 Agent 隔离、超额调用、重复触发、重启恢复。无任意互联网访问或 shell。

## Phase 6 — 简单前端 + 排行榜

交付：Cloudflare Pages 静态站；Dashboard、Agents、Agent Detail、Market、Trades、Leaderboard、Settings；REST + SSE，无浏览器 WebSocket 需求。跨域 origin 白名单及管理认证；公开榜单和私密管理接口分离，Provider key 写入后不回显。

详情含资产/PnL/持仓/挂单/决策/搜索/memory/token-cost/equity curve。榜单含 equity、PnL、ROI、max drawdown、Sharpe、win rate、fees、funding、LLM API cost。Phase 6 实现可核验基础口径，缺数据指标显示 N/A，Phase 7 完善，不伪造零值。

验收：关键页面、CRUD、SSE 重连、错误状态、访问权限和生产静态构建通过；资金数值不在前端用 JS Number 重算。

## Phase 7 — Replay + API cost + 完整统计

输入：从 Phase 2 起保存的市场/账户记录，从 Phase 3 起保存的模型/工具记录；不能到此阶段才开始采集。

交付：按版本规则与有序市场记录离线重放；两种模式明确区分：固定历史 LLM/tool 输出的确定性重放，和同历史行情重新调用模型的实验（输出不保证一致）。历史行情不能泄漏未来；禁用实时网络，缺少必要输入显式失败。配置和 prompt 快照不含 key。

完善 prompt/completion/total tokens、版本化价格表、estimated cost；先预算预留、结算后释放，未知价格/usage 明确标注且有调用次数硬上限。分别展示 Trading Profit 与 Trading Profit - AI Cost，不将 API 账单偷偷扣进 Broker 交易余额。

统一统计区间、收益采样、Sharpe 年化和零方差/N不足处理、回撤口径、完整平仓交易胜率、资金流处理、fee/funding 符号及净值时点。

验收：相同市场/规则/订单重放得到相同 fills/fees/account state；LLM 重跑不声称确定性；成本与统计使用手算 fixtures 验证，导出没有 secret。

## Phase 8 — 真实度增强与 UX

只依据实际运行误差逐项选择：更多合约、维护保证金档位、盘口队列/延迟近似、连接恢复、必要限额、数据留存/备份恢复和界面改善。不默认引入跨仓、微服务或新数据库。

验收：每项增强有可度量问题、回归 fixture、版本化规则和兼容性说明；过去比赛仍可按旧规则重放；每个增量仍可部署运行。

## 最少数据表演进草案（不是当前 schema）

Phase 1 零表。下表仅用于防止过度拆表；到对应阶段由总设计师按代码和查询需求复核，不能提前创建。

| 引入阶段 | 最小候选表 | 边界 |
|---|---|---|
| 2 | `accounts` | 一账户一行，余额/保证金 Numeric；初期少量仓位放 JSONB，内部十进制字符串，Broker 校验并账户行锁保护 |
| 2 | `orders`, `fills` | 可查询的订单生命周期及不可变成交；account 外键、幂等键、状态/数值约束；价格/数量/fee 使用 Numeric |
| 2 | `market_events` | 公共有序市场输入，source time/接收时间/sequence/版本；交易所适配与 Broker 解耦，数据量和留存后续按实测处理 |
| 2 | `account_records` | funding/强平等非成交变动、账户快照及原因关联；只由 Broker 写，支持审计/净值，非 Event Sourcing |
| 3 | `agents`, `agent_runs` | 当前配置/加密 key/简单长期 memory；每次决策快照、上下文、模型及 tool 记录、usage 与 cost；JSONB 避免拆很多日志表 |
| 4 | `competitions` | 冻结交易规则、成员配置、市场区间；账户增加比赛/Agent 关联，不改写历史比赛配置 |
| 5 | `watches` | 可独立调度的触发状态、归属和去重信息；搜索历史仍在 tool 记录中 |

不另建 positions/memory/search_history/tool_calls/cost/leaderboard 表，除非有实测理由。trade journal 关联 runs/orders/fills/account_records，workspace 用后端受控 Agent 专属路径。关系字段与关键可约束资金字段用普通列；不以 JSONB 为借口放弃校验。完整初期方案约九表，按阶段逐步引入，不提前迁移。
