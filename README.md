# AlphaPit

AI 大模型模拟加密货币交易竞技场，个人维护的开源项目。仅模拟交易，不接入真实下单权限。

仓库：https://github.com/yushum/alphapit

## 当前状态

目前只有设计与任务交接文档，尚无可运行服务、数据库 schema 或测试；Phase 1 尚未实现。不要将规划视为已实现能力。

- `ARCHITECTURE.md`：真实现状及 Phase 1 待实现契约。
- `TASKS.md`：Phase 1–8 路线、任务所有权和验收标准。
- `DESIGNER_PROMPT.md` / `WORKER_PROMPT.md`：协作约束。
- `prompts/phase1-*.md`：本轮临时 Worker 任务，验收完成后删除，长期交接回归 `TASKS.md`。

## 技术选择

后端 Python 3.12、FastAPI、Psycopg 3、PostgreSQL 17；uv 管理依赖。单个后端服务部署在 VPS Docker 中。未来前端使用 React + TypeScript + Vite，静态产物部署 Cloudflare Pages；第一阶段不安装前端依赖。

## Phase 1 预定开发命令（当前尚不可执行）

```sh
uv sync --frozen --extra dev
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest -m 'not integration'
uv run python -m build
```

集成测试需设置 `TEST_DATABASE_URL` 指向专用测试 PostgreSQL，执行 `uv run pytest -m integration`；不能使用生产数据库。

预定 Docker 启动：复制 `.env.example` 为 `.env`，设置开发数据库凭据，然后 `docker compose up --build -d`。存活检查 `/health/live`；数据库就绪检查 `/health/ready`。这些命令须在 Phase 1 联合验收通过后才标记为可用。

不得提交 `.env`、真实 API key、数据库转储或包含 secret 的日志。初期服务仅绑定回环地址；管理鉴权完成前不得直接暴露公网。
