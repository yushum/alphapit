# P1-B Worker Prompt — Docker 与开发环境

你是 AlphaPit 实现工程师，不重新设计系统。遵循根目录 WORKER_PROMPT.md；本文件给出具体任务。只做 Phase 1 部署，不开发 API、不建表、不增加 Redis/代理/前端服务。

## 开始条件与输入

- 已有干净 Git 基线及独立 worktree/branch `feat/p1-docker`；否则停止报告。
- 完整阅读 README.md、ARCHITECTURE.md、TASKS.md、WORKER_PROMPT.md，检查代码、测试、git status，再说明现状、方案和文件。
- 接口已冻结：Python 3.12；`pyproject.toml` / `uv.lock` / `src/alphapit`；uv frozen 安装；启动 `uvicorn alphapit.main:app --host 0.0.0.0 --port 8000`；DATABASE_URL；两个 health 端点，精确 JSON 见 ARCHITECTURE。
- A 独占依赖和应用，可按契约先编写；A 未到位时禁止造假应用、另建依赖 manifest 或擅改启动路径。实际构建须等待总设计师同步受审 A commit。

## 允许修改（独占）

`Dockerfile`、`compose.yaml`、`.dockerignore`、`.env.example`、`.gitignore`。

不得修改 Python、tests、uv.lock、CI、长期文档。依赖错误回报 A/总设计师；所有权外修复先请求授权。

## 具体任务

1. 最小可维护 Dockerfile：Python 3.12，固定 uv 工具版本，`uv sync --frozen --no-dev` 或同等 frozen 生产安装；非 root 运行，只包含运行需要的文件。不要为省行删除必要安装/权限处理。
2. Compose 仅 `api`、`db`；PostgreSQL 17，命名持久卷；pg_isready 健康检查，API 等待数据库 healthy；API 通过 Python 标准库请求 `/health/ready` 做健康检查，不安装 curl。
3. 仅 API 绑定 `127.0.0.1:8000:8000`；db 无宿主端口；不挂 Docker socket，不使用 privileged。
4. `.env.example` 给出仅开发用的 `POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD`；构造 `postgresql://...@db:5432/...` 给 API。使用 URL 安全示例密码，注释说明其他字符需 URI 编码、不可直接用于生产。配置缺失有明确错误，不打印真实连接信息。
5. `.dockerignore` 排除 .git、.pi、.env、缓存、workspace 和非运行文件；注意保留构建实际需要的 README/manifest/源码。`.gitignore` 排除本地 .env/.pi/.venv/build/cache 等，但允许 `.env.example` 和 `uv.lock` 入库。

## 验收

使用独立 Compose project 与临时测试凭据，不覆盖用户已有 `.env`，不删除他人资源。命令和临时资源名写入报告，不提交凭据。

- `docker compose --env-file <临时env> config --quiet`。
- A 到位后 `docker compose --env-file <临时env> up --build -d --wait`，请求 live 和 ready 验证 HTTP 与 JSON。
- 检查容器运行 UID 非 0、数据库无宿主端口；镜像无 `.env` 或其他 secret。
- 停止 db 后 live 200、ready 503，响应和日志无 DSN/密码；重新启动 db 后 ready 恢复 200，无需重启 API。
- 在专用测试库建立临时验证标记，重建 db 容器、不删除卷，验证标记存在，再清理标记。禁止对生产库操作，禁止 `down -v` 清除非本任务数据。
- 有 A 后执行项目 formatter/check、lint、type check、单测、真实 PG 集成测试、wheel 构建及 Docker build；格式化仅限本任务所有权，依赖文件出现问题回报对应 owner。

Docker/权限/依赖不可用时写 blocked/not run，不能以静态检查替代运行验收。可提供未验收 checkpoint commit，不能声称完成或合并 main。

## 交接

完整 diff 自审，检查范围、重复配置和 secret，再 commit。输出仅：
- Changed: 文件和 commit hash。
- Tests: 精确命令、退出码、服务健康/故障恢复/持久卷/镜像验证结果。
- Known issues: 阻塞或 none；README 所需启动说明供总设计师更新，不自行编辑。
