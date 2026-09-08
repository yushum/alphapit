# AlphaPit 架构

## 真实现状

当前只有规划文档和最小 `.gitignore`，没有应用、数据库、测试、CI 或部署产物；已初始化 Git，主分支为 `main`。以下是 **Phase 1 待实现契约**，不是当前已实现架构。验收后按真实代码更新本文件，未来阶段方案只在 TASKS.md 中记录。

## 最小技术栈与边界

- Python 3.12、FastAPI、Uvicorn：一个 REST API 进程。
- PostgreSQL 17、Psycopg 3：同步 SQL、显式事务；Phase 1 不使用 ORM、连接池或迁移框架。
- uv + `uv.lock`：固定依赖；运行依赖仅 FastAPI、Uvicorn、Psycopg（binary extra）。
- 开发依赖：pytest、HTTPX（TestClient）、Ruff、mypy、build；采用 setuptools 构建 Python wheel。
- Docker Compose：`api` + `db` 两个服务，数据库持久卷。无 Redis、队列、微服务。
- GitHub Actions：格式、lint、类型、单测、真实 PostgreSQL 集成测试、wheel 和 Docker 构建。
- 前端延至 Phase 6：React / TypeScript / Vite → Cloudflare Pages 静态部署。浏览器仅调用后端 REST / SSE；此阶段无前端工程。

同步数据库调用使用 FastAPI 的同步路由，不在 async 路由里阻塞事件循环。不增加 Repository/Service/Manager 包装。Phase 1 没有 scheduler、Agent loop 或 Broker 占位实现。

## Phase 1 最小目录契约

```text
README.md / ARCHITECTURE.md / TASKS.md
pyproject.toml
uv.lock
src/alphapit/
  __init__.py
  main.py                  # create_app() 与 app、两个健康检查
  db.py                    # 有界连接和 SELECT 1
tests/
  test_health.py
  test_db_integration.py
Dockerfile
compose.yaml
.dockerignore
.env.example
.gitignore
.github/workflows/ci.yml
prompts/phase1-*.md         # 临时派工文件，阶段结束删除
```

不为未来模块创建空包。README 和长期设计文档由总设计师独占维护。

## API、配置与数据库契约

- 导入应用不连接数据库；提供 `create_app()` 和 `alphapit.main:app`。
- `GET /health/live`：无数据库访问，HTTP 200，`{"status":"ok"}`。
- `GET /health/ready`：每次短连接执行 `SELECT 1`；成功 HTTP 200，`{"status":"ready"}`；未配置、连接失败或查询失败 HTTP 503，`{"status":"not_ready"}`。
- 单一后端配置 `DATABASE_URL`，使用标准 `postgresql://...` DSN，禁止日志输出 DSN、密码或底层异常详情。缺少配置时进程仍存活，但不就绪。
- PostgreSQL 连接 timeout 3 秒、服务端 statement timeout 2 秒；连接无论成功失败都关闭；驱动异常转换为通用就绪失败，避免广泛吞掉程序错误。
- 容器启动命令 `uvicorn alphapit.main:app --host 0.0.0.0 --port 8000`，一个 worker。
- 宿主机仅暴露 `127.0.0.1:8000:8000`；`db` 不映射宿主端口。
- Compose 从 `.env` 读取 `POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD`，构造容器内 `DATABASE_URL`，主机名为 `db`。开发示例只用 URL 安全字符，明确不支持未经 URI 编码的任意密码；生产凭据必须正确编码。
- PostgreSQL healthcheck 使用 `pg_isready`；API healthcheck 用 Python 标准库请求 `/health/ready`，不额外安装 curl。
- 就绪失败不等于自动重启；数据库暂时不可用后恢复，无需重启 API 即可重新就绪。

### 最少数据库表

**Phase 1：零业务表。** 验证真实连接、查询和部署持久卷即可；不要为健康检查造表，也不要创建未来 Agent 表。当前没有迁移文件；Phase 2 引入第一份真实 SQL schema 时再确定最小迁移方式。

## 本轮工程契约

`pyproject.toml` 定义 dev extra、src layout、Ruff / mypy / pytest 配置及 `integration` marker；uv 锁定全部依赖。CI / Docker 安装时必须使用 frozen lock。API Worker 拥有依赖文件，其他 Worker 不能改动。

标准检查：`uv run ruff format --check .`、`uv run ruff check .`、`uv run mypy src tests`、`uv run pytest -m 'not integration'`、`uv run python -m build`。

集成测试只读 `TEST_DATABASE_URL`：普通本地运行未设置时可明确 skip；CI 必须设置，CI 中缺失应失败，不允许用 skip 冒充通过。测试须验证真实数据库成功路径、可控不可连接路径及秘密不泄露，不能完全用 mock 替代数据库。测试不删除数据库或卷，不接触生产环境。

CI 在 PR 和 main push 上运行；无发布凭据也必须通过。不在本阶段发布 GHCR，不引入 secret。Docker 使用非 root 用户和 `.dockerignore`，镜像不含 `.env`、`.git`、测试缓存及本机 workspace；只安装运行依赖。

## 后续不可违反的约束（非已实现能力）

金融运算使用 Decimal / PostgreSQL Numeric，API 使用十进制字符串；Broker 唯一可修改余额和仓位。LLM 不可信，仅能通过经验证、带权限和超时的工具请求操作。Agent 身份由后端注入，不能由工具参数自行选择。交易、上下文、记忆、workspace、搜索和费用按 Agent 隔离。

比赛固定规则版本和 Agent 配置；同一逻辑时点使用统一市场数据。记录重放必需的原始输入、排序和输出，保存记录不等于引入 Event Sourcing。Provider key 不进入浏览器、工具日志或 Replay；Phase 3 前明确加密和部署 secret 管理。
