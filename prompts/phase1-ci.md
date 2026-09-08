# P1-C Worker Prompt — GitHub Actions

你是 AlphaPit 实现工程师，不是架构师。遵循根目录 WORKER_PROMPT.md；本文件给出具体任务。只做 Phase 1 CI，不增加发布平台、测试框架、交易功能或前端工程。

## 开始条件与输入

- 已有干净基线和独立 worktree/branch `feat/p1-ci`；否则停止并报告。
- 完整阅读 README.md、ARCHITECTURE.md、TASKS.md、WORKER_PROMPT.md；检查代码、测试与 git status，再说明方案和修改文件。
- A 提供 Python 3.12 src 工程、dev extra、uv.lock、标准检查命令与 integration marker；B 提供 Dockerfile。可按契约并行写 YAML，真正执行需总设计师同步受审 A/B commit。
- 不补写假应用、Dockerfile、依赖文件来让 CI 变绿。不因本机没有 GitHub remote 就报告 Actions 已通过。

## 允许修改（独占）

仅 `.github/workflows/ci.yml`。不编辑其他 workflow、应用、tests、Dockerfile、lock、文档。

## 具体任务

1. `pull_request` 和 main `push` 触发，最小 `contents: read` 权限；合理 job timeout；同分支过时 run 可取消。不要 pull_request_target，不接触 secret，不发布 GHCR。
2. 使用可信、明确版本的 checkout / setup-python / setup-uv actions；uv 工具版本与 B 协调一致。不要 latest 或 curl 未固定脚本。
3. Python 3.12、PostgreSQL 17 service（临时测试凭据、healthcheck）；给测试显式设置 `TEST_DATABASE_URL`，仅临时 CI 数据库；不打印凭据。
4. `uv sync --frozen --extra dev`，依次执行：

```sh
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest -m 'not integration'
uv run pytest -m integration
uv run python -m build
```

5. 构建 B 的 Dockerfile：`docker build -t alphapit:ci .`。实际运行该镜像并检查 `/health/live` 的 HTTP 200 + JSON；将其连接临时 PG service（例如 Linux runner host network 与相应 DSN），检查 `/health/ready` HTTP 200 + JSON。等待有界、有超时，失败正确返回非零，最后无论成功失败都清理自己创建的容器。不得 `|| true` 掩盖检查失败。
6. 无需新测试脚本时直接使用少量内联 shell/Python 标准库；不自制 CI 框架，不增加仅供 CI 使用的大依赖。PR 不需要 GHCR write 权限。

## 验收与依赖

- 检查 YAML 语法、触发器和 permissions；允许使用环境已有 YAML/actionlint 工具，不为它修改项目依赖。
- A/B 到位后在 Linux 环境执行同样格式/lint/mypy/tests/build 命令及容器 HTTP smoke；集成测试必须真实执行，不接受全跳过。
- 若有已授权的 GitHub 远端，正常 PR workflow 实际运行通过，提供 run 链接。没有远端/权限则明确“Actions 未执行，待总设计师远端验收”，不能把本地检查称为 CI 通过。
- 没有 A/B、Docker/网络等基础设施时报告阻塞；不要改换执行通道或越界修复。

## 交接

执行可用项目检查（格式化不触碰所有权外文件），完整 diff 自审，确认无泄漏或多余 job，再 commit。环境阻塞时只交明确未验收 checkpoint，不能报告完成。

输出：
- Changed: workflow 和 commit hash。
- Tests: 命令/退出码、本地结果、实际 Actions run 链接或 not run。
- Known issues: 待集成项或 none。

最终由总设计师合并到集成分支、执行联合验收，再合并 main。
