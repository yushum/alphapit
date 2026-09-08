# AlphaPit

AI 大模型模拟加密货币交易竞技场，个人维护的开源项目。仅模拟交易，不接入真实下单权限。

仓库：https://github.com/yushum/alphapit

## 当前状态

Phase 1 已验收：最小 API + PostgreSQL + Docker + CI 可运行，无业务表、无交易、无 Agent。

- `ARCHITECTURE.md`：当前真实架构。
- `TASKS.md`：Phase 1–8 路线、任务所有权和验收标准。
- `DESIGNER_PROMPT.md` / `WORKER_PROMPT.md`：协作约束。

## 技术选择

后端 Python 3.12、FastAPI、Psycopg 3、PostgreSQL 17；uv 管理依赖。单个后端服务部署在 VPS Docker 中。未来前端使用 React + TypeScript + Vite，静态产物部署 Cloudflare Pages；第一阶段不安装前端依赖。

## 运行

```sh
uv sync --frozen --extra dev
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest -m 'not integration'
uv run python -m build
```

集成测试使用专用测试库（不接触开发/生产库）：

```sh
TEST_DATABASE_URL='<专用测试数据库 DSN>' uv run pytest -m integration
```

未设置 `TEST_DATABASE_URL` 时本地集成测试明确 skip；`CI=true` 且缺变量时测试失败，不允许用 skip 冒充通过。

Docker 启动：复制 `.env.example` 为 `.env` 并修改开发密码（仅 URL 安全字符），然后：

```sh
docker compose up --build -d --wait
```

- 存活检查 `GET http://127.0.0.1:8000/health/live` → 200 `{"status":"ok"}`，不访问数据库。
- 就绪检查 `GET http://127.0.0.1:8000/health/ready` → 200 `{"status":"ready"}`，失败时 503 `{"status":"not_ready"}`。

不得提交 `.env`、真实 API key、数据库转储或包含 secret 的日志。初期服务仅绑定回环地址；管理鉴权完成前不得直接暴露公网。
