# 本次初始化验证记录

本地 Windows 环境，2026-09-13。

| 检查 | 结果 |
| --- | --- |
| Web ESLint / TypeScript strict / Prettier | 通过 |
| Next.js production build | 通过 |
| Playwright 首页 → 新建旅行 → 列表更新 | 1 passed（使用 mock API） |
| API Ruff / Ruff format / MyPy strict | 通过 |
| Pytest | 11 passed，3 skipped |
| Alembic 离线 upgrade / downgrade SQL | 通过，包含 PostGIS、外键、GiST、共享 enum 单次创建 |
| Uvicorn 实际启动 | 通过 |
| GET /docs、GET /openapi.json | 200 |
| GET /health，无数据库 | 503，database / postgis / migration 显示 unavailable |
| npm audit | 0 vulnerabilities |

尚未在本机验证：Docker 镜像构建、Compose 启动、真实 PostgreSQL / PostGIS 迁移及 CRUD。未发现 Docker 或 PostgreSQL 可执行程序/服务，WSL 不可访问，因此不能将离线 SQL 检查视为真实迁移成功。

3 项数据库测试分别覆盖完整 CRUD 与用户隔离、空间索引与外键、可丢弃数据库上的 migration 往返。CI 已配置 PostGIS service 和对应环境变量，并增加完整 Compose 构建与启动检查；本次未触发远端 CI。

完整复验命令见 [DEVELOPMENT.md](DEVELOPMENT.md)。

## 首版提交前环境整理

- 补充 Node.js / Python 版本文件、EditorConfig、Git 换行规则和 Prettier 忽略配置。
- `next-env.d.ts` 按 Next.js 生成文件处理，不纳入提交；类型检查先执行 `next typegen`。删除 `.next` 和该文件后，lint、格式检查、类型检查、生产构建均通过。
- 后端 Ruff、格式检查、MyPy 及 pytest 再次通过：11 passed、3 skipped。数据库和 Docker 验证限制保持不变。
- 检查提交候选文件、文档链接与 Web 锁文件一致性；提交范围不含环境文件、依赖目录、运行时或测试产物。
- 清理构建、测试、静态分析、包下载缓存与源码字节码；保留已安装依赖及本地 Python / Playwright 运行时，便于继续开发。
- 整理完成后未创建 Git commit，代码可作为首版提交基线。
