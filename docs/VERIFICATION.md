# 本次初始化验证记录

## Phase 2 验证（2026-09-13）

界面修正：国家填色/轮廓统一为 50m，省界改为共享内部边；沿海地图截图检查通过。月历上限宽度改为 680px、日期格高度 76px（手机 68px），日期文字居中。浏览器测量确认空日期格两轴居中，390px 手机无横向溢出；ESLint、TypeScript 与两项 Playwright 交互测试通过。该修正没有数据库迁移。

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

## v0.3 阶段 A — 认证契约与回归基线（2026-09-20）

- 建立厂商无关的 `AuthCredential`、`AuthPrincipal` 和 `AuthProvider` 契约；现有 development provider 继续返回固定用户，disabled 模式仍拒绝业务访问。
- 声明未来 OIDC issuer、audience、JWKS URL 和时钟偏差配置，但 `AUTH_MODE=oidc` 仍会在启动配置校验时被拒绝。未引入 Logto SDK、Bearer token 解析、数据库迁移或登录 UI。
- 新增结构测试，确认当前 `/api/v1` 业务路由均传递依赖 `current_user`；抽样接口在 disabled 模式下统一返回现有 401 错误信封。
- API：Ruff、Ruff format、MyPy strict 通过；pytest **22 passed、5 skipped**。跳过项需要专用 `TEST_DATABASE_URL` / `MIGRATION_TEST_DATABASE_URL`，本阶段没有数据库或领域行为变更，因此未冒险复用开发数据库。
- Web：ESLint、TypeScript strict、Next.js production build 通过；使用本机 Chrome 执行 Playwright，**4 passed**。测试断言同步当前“同一城市聚合、多次到访分列”的既有界面，未修改生产 Web 代码。
- 已知限制：本轮没有重新执行真实 PostgreSQL/PostGIS 集成与迁移往返；最近一次真实数据库基线仍为本文件“行政区地图与旅行录入验收”记录。FastAPI/Starlette TestClient 有 2 条上游弃用警告，不影响结果。

## v0.3 阶段 B — 本地身份映射模型（2026-09-20）

- 新增 `UserIdentity` 模型、schema、repository/service 和 `0004_user_identity` 迁移；`(provider, provider_subject)` 唯一，用户删除时映射级联删除。
- 运维命令只允许把 provider subject 显式绑定到已有 User UUID；相同绑定幂等、跨用户绑定返回 `IDENTITY_CONFLICT`、未知用户返回 `USER_NOT_FOUND`。真实数据库连续执行两次命令返回同一映射 ID。
- 使用仓库缓存的 PostgreSQL 17.11 + PostGIS 3.6.2，在新建的 `tovia_auth_b_test` 和可丢弃的 `tovia_auth_b_migration` 数据库验证；未接触开发业务数据库。
- Pytest **37 passed、无跳过**。覆盖数据库唯一约束、从 `0003_wishlist` 升级后原 User/Trip UUID 不变、空映射表、新库安装、Alembic check 及 downgrade base → upgrade head 往返。
- Ruff、Ruff format、MyPy strict、ESLint、TypeScript strict 和 Next.js production build 通过；使用本机 Chrome 运行 Playwright，**4 passed**。本阶段没有修改 Web 生产代码、依赖或组件。
- 仍未启用 `AUTH_MODE=oidc`，未读取 Authorization header，未增加 Logto SDK、自动注册、API 绑定接口或登录 UI。FastAPI/Starlette TestClient 的上游弃用警告保持不变。

## v0.3 阶段 C — OIDC Token 验证 Provider（2026-09-20）

- 新增默认关闭的 `AUTH_MODE=oidc`。配置必须同时提供 issuer、audience 和 JWKS URL，缺失时校验失败，不会回退到 development 用户。
- API 从 Authorization header 提取 Bearer credential；provider 只允许 Logto 默认的 ES384 和密钥轮换可用的 RS256，通过 PyJWT 验证 JWKS 签名、issuer、audience、expiry 和非空 subject。JWKS client 按 URL 在进程内复用，集合缓存 5 分钟。
- 验证后的 `("logto", subject)` 必须已绑定到 UserIdentity；未知 identity、已删除用户、无 token、错误 scheme 或无效 token 统一返回 `AUTH_REQUIRED` 401，不自动注册。
- 本地 ES384 与 RSA 测试覆盖成功 Bearer 请求 `/api/v1/me`、过期 token、错误 audience、错误 issuer、错误签名、缺少 subject、未知 identity、非 Bearer 和 JWKS client 复用。
- 使用隔离的 PostgreSQL 17.11 + PostGIS 3.6.2 数据库 `tovia_auth_c_test` 与可丢弃数据库 `tovia_auth_c_migration` 完成全量 Pytest：**48 passed、无跳过**，同时完成现有迁移往返。测试库已删除，临时数据库进程已停止。
- Ruff、Ruff format、MyPy strict、ESLint、TypeScript strict、Next.js production build 通过；使用本机 Chrome 执行 Playwright，**4 passed**。
- 新增最小后端依赖 `PyJWT[crypto]`；未增加 Logto SDK、浏览器登录、自动注册、scope/RBAC、前端组件或数据库迁移。FastAPI/Starlette TestClient 的 2 条上游弃用警告保持不变。

## v0.3 阶段 D — 可选的 Logto 开发环境（2026-09-20）

- 新增独立 `tovia-logto` Compose project，固定 `svhd/logto:1.42.0` 与 `postgres:17.11-alpine`。Logto 使用独立数据库用户、容器网络和 `logto_postgres_data`，没有修改 Tovia 默认 `compose.yaml` 或 `postgres_data`。
- 增加本地初始化、API Resource、测试用户、Device Flow 用户 token、显式 UserIdentity 绑定和阶段 C Bearer 请求验证说明。未增加浏览器 callback、BFF、Logto SDK、社交登录、组织、角色、MFA、SAML 或主题组件。
- 增加仅在显式叠加时把 API 切换为 OIDC 的 Compose override；普通 `docker compose up` 继续使用 development 认证。
- 文档记录固定版本升级、数据库 alteration、SQL 备份、保留数据停止及独立卷删除方式。
- 静态配置与文档通过 Prettier 和 `git diff --check`；默认 `compose.yaml` 无差异。API Ruff、format、MyPy 通过；Pytest **42 passed、6 skipped**，跳过项仍是未配置专用 PostgreSQL 的既有集成测试。Web ESLint、TypeScript、production build 通过，并使用本机 Chrome 完成 Playwright **4 passed**。
- 本机没有 Docker CLI，无法启动 Logto 容器或取得真实 token，因此容器健康、Device Flow 与阶段 C 的端到端联调仍需在具备 Docker 的环境复验；本阶段不把静态配置检查宣称为运行时通过。

## v0.3 阶段 E — 最小 Web 登录与 BFF（2026-09-21）

- 固定新增 `@logto/next` 4.2.11，提供默认关闭的 `/sign-in`、`/callback` 和 `/sign-out`。SDK 使用至少 32 字符密钥加密 session cookie，并设置 HttpOnly、SameSite=Lax；浏览器端不保存或读取 access token / refresh token。
- 同源 BFF 当前只开放固定的 `GET /api/bff/me`。服务端取得 API Resource access token，并转发到 FastAPI `/api/v1/me`，不接受客户端 Authorization、`x-user-id`、`user_id` 或其他 query；不复制客户端身份 header。
- 客户端仅对该 BFF 读取处理 401：第二次请求使 SDK 有机会执行 refresh token 续期，仍返回 401 时进入 `/sign-in`。其余地图、日历、旅行读写仍走现有 `NEXT_PUBLIC_API_URL`，未提前执行阶段 F 的批量迁移。
- 默认关闭模式生产构建通过；显式 `NEXT_PUBLIC_WEB_AUTH_MODE=oidc` 且未提供 secret 时同样可以构建，运行时认证路由明确返回 503，不回退到 development 身份。ESLint、TypeScript、Prettier 和 npm audit（0 vulnerabilities）通过。
- Playwright 默认关闭模式 **5 passed、3 skipped**，覆盖原有 4 条核心流程和“不请求 BFF”的新回归；显式开启模式认证用例 **3 passed、1 skipped**，覆盖一次 401 重试成功、重试失败进入登录、BFF 拒绝 query/header 身份输入。
- API Ruff、format、MyPy 通过；Pytest **42 passed、6 skipped**，跳过项需要专用 PostgreSQL，阶段 E 没有后端或数据库修改。
- 本机仍没有 Docker CLI，无法完成真实 Logto authorization code、过期 token refresh、FastAPI `/me` 和 Logto 全局退出的端到端流程。Roadmap 因此标记为“实现完成（待真实 Logto 验收）”，没有把受控浏览器响应测试宣称为真实身份系统 E2E。

## v0.3 阶段 F — 双用户隔离与非生产切换（2026-09-21）

- `NEXT_PUBLIC_WEB_AUTH_MODE=oidc` 开启时，现有用户、旅行、地点、访问、活动、地图、日历和收藏请求全部改走同源 `/api/bff/*`；关闭时仍直接使用 `NEXT_PUBLIC_API_URL`，默认开发方式未改变。
- BFF 只开放 Web 当前使用的 method、path 和 query 白名单。客户端 Authorization、`x-user-id`，以及 query 或嵌套 JSON body 中的 `user_id` 均返回 400；服务端只转发 session 中取得的 Bearer token。
- 所有业务请求的 401 只重试一次，第二次 401 统一进入 `/sign-in`；网络错误保持普通服务不可用提示。TanStack Query 不再继续重试已经确认的认证失效。
- API Ruff、格式、MyPy 通过。使用仓库内隔离 PostgreSQL 17 + PostGIS 实例执行完整 Pytest：**48 passed**；跨用户回归覆盖已知 Trip/Visit/Activity ID 的读取、修改、删除和关联创建，均返回 404，并验证所有者数据未被改变。
- Web ESLint、TypeScript、Prettier 通过；默认模式和 OIDC 模式 production build 均通过。使用本机 Chrome 的 Playwright：默认模式 **5 passed、4 skipped**，OIDC/BFF 模式 **8 passed、1 skipped**。OIDC 模式的旅行、地点录入、地图、日历核心流程全部经过同源 BFF mock，另覆盖身份输入拒绝、一次 401 重试和 session 失效跳转。
- 本机仍没有 Docker CLI，不能创建两个真实 Logto 账户并完成 authorization code 浏览器 E2E。真实双账户 subject 绑定、退出后换号、session/token 实际过期续期仍须按 DEVELOPMENT 和 `infra/logto/README.md` 复验，因此 Roadmap 状态为“实现完成（待真实双账户验收）”。

## 首版提交前环境整理

- 补充 Node.js / Python 版本文件、EditorConfig、Git 换行规则和 Prettier 忽略配置。
- `next-env.d.ts` 按 Next.js 生成文件处理，不纳入提交；类型检查先执行 `next typegen`。删除 `.next` 和该文件后，lint、格式检查、类型检查、生产构建均通过。
- 后端 Ruff、格式检查、MyPy 及 pytest 再次通过：11 passed、3 skipped。数据库和 Docker 验证限制保持不变。
- 检查提交候选文件、文档链接与 Web 锁文件一致性；提交范围不含环境文件、依赖目录、运行时或测试产物。
- 清理构建、测试、静态分析、包下载缓存与源码字节码；保留已安装依赖及本地 Python / Playwright 运行时，便于继续开发。
- 整理完成后未创建 Git commit，代码可作为首版提交基线。
# 行政区地图与旅行录入验收（2026-09-20）

- 旅行详情紧凑化补验：删除独立“旅行已建立”面板，地点录入嵌入窄栏并收起可选字段；每日安排使用更宽主栏，旅行日独立成卡并在卡内添加活动。Playwright 的过去/未来旅行流程均实际新增两个城市、一个旅行日和一个当天活动后打开地图，4 项测试通过；截图检查桌面双栏层级清晰。
- 国内新足迹收敛为市级。南京/拼音返回南京市；“鼓楼”返回南京市、徐州市等所属城市，不返回鼓楼区；省名返回其市级结果。服务拒绝直接解析国内区县 region_id。相关 Python 单元测试、Ruff、MyPy、前端 ESLint、TypeScript、Prettier 和 Next.js 生产构建通过。

- 行政区数据：3485 个可选条目；逐一检查目录关联边界，无缺失、无无效几何；API/Web 目录一致。南京市区域包含南京中心，不包含苏州中心。
- Playwright：过去旅行、未来旅行的创建 → 南京/苏州连续录入 → 地图面高亮；独立地点记录 → 多次访问 → 日历跳转；旧坐标匹配和重复访问合并显示，共 4 项通过。浏览器使用 mock API，真实静态边界和 MapLibre 渲染。
- 后端：18 项全部通过、无跳过。使用仓库缓存的 PostgreSQL 17 / PostGIS，在 `tmp/regions-pg` 新建隔离集群，仅监听 127.0.0.1:55439；测试库为 `tovia_regions_test`，迁移往返使用另一个可丢弃库 `tovia_regions_migration`，未接触业务库。真实数据库验证行政区搜索、重复选择复用 Place、未保存访问不进入地图、旅行访问关联及 MapPlace.region_id 返回，同时验证现有 CRUD、用户隔离及迁移往返。浏览器流程仍采用 mock API，未宣称浏览器直接连接真实 API 完成端到端测试。
- Next.js 生产构建、TypeScript、ESLint、Prettier、Python Ruff/mypy 均通过。
- 无 schema 迁移；现有访问记录保留。国内边界不完整地区不开放新选择；海外当前仅国家粒度。计划到期自动归为曾至仍遵循既有规则。
