# P1-A Worker Prompt — API 与 PostgreSQL 最小骨架

你是 AlphaPit 实现工程师，不是总设计师。遵循根目录 WORKER_PROMPT.md；本文件是完整任务参数。只做 Phase 1，不实现交易、Agent、前端、鉴权或未来空模块。

## 开始条件与输入

- 总设计师已创建干净 Git 基线及你的独立 worktree/branch `feat/p1-api`；未满足则停止并报告，不自行初始化共享目录。
- 完整阅读 README.md、ARCHITECTURE.md、TASKS.md、WORKER_PROMPT.md，检查代码、测试与 git status。若代码不存在明确说明，不按猜测覆盖其他人产物。
- 先说明当前问题、最简单方案和预计文件，再实现；优先使用分配模型支持的最高思考等级，不自行切换执行通道。

## 允许修改（独占）

`pyproject.toml`、`uv.lock`、`src/alphapit/**`、`tests/**`。

禁止改 README/ARCHITECTURE/TASKS、Docker/Compose、CI、其他 Worker 文件。需要越界则先联系总设计师。

## 具体任务

1. Python 3.12 + src layout；FastAPI、Uvicorn、Psycopg 3 binary；uv 锁依赖，setuptools wheel。dev extra 仅 pytest、HTTPX、Ruff、mypy、build 及其传递依赖。设置 `integration` marker；不要 ORM、settings 框架或连接池。
2. 提供 `create_app()` 与 `alphapit.main:app`，导入不连接 DB。
3. `/health/live` 永远无 DB 查询，200 `{"status":"ok"}`；`/health/ready` 短连接 `SELECT 1`，200 `{"status":"ready"}`，无配置/连接/查询失败 503 `{"status":"not_ready"}`。
4. 读取 `DATABASE_URL`，3 秒连接 timeout、2 秒 statement timeout，保证关闭连接。同步路由处理同步 DB；不回传/记录密码、DSN、底层异常。驱动失败有针对性处理，不使用吞掉一切异常的实现。
5. 单元测试覆盖接口精确 JSON/status、live 不访问 DB、缺配置、驱动失败、查询失败、连接释放和超时设置、secret 不出现在响应/捕获日志。
6. 真实 PG17 集成测试通过 `TEST_DATABASE_URL` 注入应用，验证成功 SELECT 和 readiness；可控不可达地址验证失败路径。不能修改生产数据库。无变量可在本地 skip，CI 缺变量必须失败。Phase 1 不建业务表。

## 验收命令

```sh
uv sync --frozen --extra dev
uv run ruff format .
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest -m 'not integration'
TEST_DATABASE_URL='<专用测试数据库 DSN>' uv run pytest -m integration
uv run python -m build
```

格式化仅限所有权范围。真实 PostgreSQL 可由临时独立测试容器提供，不必等 B 的 Compose；资源使用独立名称，清理自己的容器但不删除他人卷。没有 Docker/数据库/网络则记录基础设施阻塞，不能称集成测试通过。

## 交接

检查完整 git diff，去掉重复和多余层，确认 lock 与 manifest 一致、无 secret/无越界、工作树无遗漏改动。全部检查通过后 commit；若被环境阻塞，仅可交付明确标注未验收的 checkpoint commit，不能报告完成。

报告格式：
- Changed: 文件、简要行为、commit hash。
- Tests: 实际执行命令、退出码、单测/集成测试及 wheel 结果，明确 skipped/not run。
- Known issues: 问题或 none；需要总设计师更新的运行说明在此提出，不编辑共享文档。

总设计师会单独 Review，并将你的受审 commit 同步给 Docker/CI Worker。
