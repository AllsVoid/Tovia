# 本次初始化验证记录

## Phase 2 验证（2026-09-13）

- API Ruff / format / MyPy strict 通过；pytest **15 passed，无跳过**。在仓库 `.cache` 内启动临时 PostgreSQL 17.11 + PostGIS 3.6.2，使用专用测试数据库，未使用用户的业务数据库。
- Alembic head=`0003_wishlist` 实际升级成功，`alembic check` 无差异；另一个可丢弃数据库完成 upgrade → downgrade base → upgrade head → check。
- 新数据库测试验证重复到访、未来访问、收藏幂等、scope 分组、地图分页、用户隔离、闰年/跨月/当地午夜边界、无日期 Trip 的活动归日，以及删除旅行后访问保留。
- Web ESLint、TypeScript strict、Prettier、Next.js production build 通过。Playwright 两条流程覆盖新建旅行、地点录入、二次到访、日历回看、地图 worker 加载及 390px 宽度。
- 真实 API 浏览器联调：创建 Trip → Day → Activity → Place → Visit → 地图详情 → Wishlist → 月历当天记录，全部通过，无页面 JavaScript 异常。地图底图与点位、桌面/月历/手机布局经截图检查。
- 地图依赖的 MapLibre ESM worker 改为同源静态文件，由 predev/prebuild 自动复制；Docker runner 补充 public 目录。
- 额度恢复后的补验：按 Docker runner 的目录结构复制 public / static，启动 Next.js standalone production server，确认 worker、行政轮廓和真实地点点位均渲染；点击点位打开详情通过。测试端口 3003 通过浏览器测试代理读取真实 API，未修改开发 CORS 配置。
- 本机 Docker 命令仍不可用，未执行 Docker 镜像或 Compose 验证，也未触发远端 CI。历史记录中的“数据库未验证”限制已由本节的真实数据库测试解除。
- 临时数据库、下载包、截图和浏览器脚本均位于忽略的 `.cache`，不纳入提交；业务代码不包含演示记录。

## Phase 0 / Phase 1 历史记录

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
