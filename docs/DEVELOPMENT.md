# Phase 0 → Phase 2 开发指南

## 升级到地图与日历

已有数据库请在 `apps/api` 下运行迁移：

```powershell
Set-Location apps/api
uv run alembic upgrade head
```

新增 head 为 `0004_user_identity`。使用 Docker 时，在根目录运行 `docker compose up --build -d`，migrate 服务会执行升级。

体验路径：新建旅行 → 下一步在地点与足迹中自动展开添加城市 → 搜索城市或区县（区县归并到所属城市）→ 确认抵达时间 → 加入旅行 → 继续添加城市或查看地图高亮 → 新建旅行日并在当天卡片内添加活动。地图也支持独立访问及未至收藏，无需填写经纬度。未来抵达归入将至。输入时间使用本机时区，界面会提示；地点时区影响日历归日。

地图底图及行政区目录内置，无需地图密钥。当前提供省市区面高亮与海外国家面高亮，尚未接入街道底图或在线地理编码。构建行政区数据的方法与来源见 `apps/web/public/maps/regions/README.md`，API 和 Web 的目录需同时更新。

## 快速启动

需要 Docker Engine / Docker Desktop（Linux containers）与 Compose v2。

在仓库根目录执行：

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps -a
```

- Web：<http://localhost:3000>
- API readiness：<http://localhost:8000/health>
- Swagger：<http://localhost:8000/docs>
- OpenAPI：<http://localhost:8000/openapi.json>

启动顺序：PostgreSQL 健康 → `migrate` 成功退出 → API 健康 → Web。Redis 作为后续异步任务基础设施保留，没有 AI / OCR worker。

`migrate` 退出码为 0 属于正常状态。`/health` 在数据库不可用、PostGIS 不可用或迁移不是最新版本时返回 503，不会在应用启动时自动建表。

Compose 使用本机 loopback 端口；默认密码和开发认证仅用于本地。复制 `.env.example` 后按需调整。生产环境必须关闭开发认证；当前没有生产登录实现。

## 本地热更新

需要 Node.js 22+（推荐 24）、uv 和 Python 3.12。

```powershell
docker compose up -d db redis
npm ci
uv sync --project apps/api --frozen
Set-Location apps/api
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

另开终端在根目录运行 `npm run dev`。API 从根目录 `.env` 读取配置。Web 的默认 API 地址为 `http://localhost:8000`；本地改址请设置进程环境变量 `NEXT_PUBLIC_API_URL` 或使用 `apps/web/.env.local`。Docker 构建通过 build arg 固定浏览器 API 地址，改址后需重建 Web 镜像。

## 完全不使用 Docker（Windows）

安装 Node.js 24、uv、Python 3.12 和 PostgreSQL 17。PostGIS 可通过 PostgreSQL 安装器附带的 StackBuilder 安装，参见 [PostGIS Windows 安装说明](https://postgis.net/documentation/getting_started/install_windows/released_versions/)。启动 PostgreSQL 服务；当前阶段无异步任务，不需要 Redis。

首次使用时，在 SQL Shell（psql）中以 postgres 管理员连接，执行：

```sql
CREATE USER tovia WITH PASSWORD 'tovia_local_only';
CREATE DATABASE tovia OWNER tovia;
\connect tovia
CREATE EXTENSION IF NOT EXISTS postgis;
```

在项目根目录的 PowerShell 中执行：

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uv python install 3.12
uv sync --project apps/api --frozen
npm ci
Set-Location apps/api
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

已有同名用户或数据库时复用现有配置，不重复执行创建语句。根目录 `.env` 的 DATABASE_URL 应与本机账号、密码、端口一致；开发环境使用 `APP_ENV=development`、`AUTH_MODE=development`。管理员提前启用 PostGIS 后，普通应用用户即可运行剩余迁移。

另开终端，在项目根目录运行 `npm run dev`。访问 `http://localhost:3000`，检查 `http://localhost:8000/health` 返回 200。以后启动只需数据库服务与两个应用终端，schema 有变化时再运行迁移。

## 首版提交与可复现环境

- `.node-version` 指定 Node.js 24，`apps/api/.python-version` 指定 Python 3.12；依赖由 package-lock.json 和 uv.lock 锁定，分别使用 `npm ci` 和 `uv sync --frozen` 安装。
- `.editorconfig` 和 `.gitattributes` 统一 UTF-8、缩进与换行；业务代码、迁移、测试和 docs 均纳入版本控制。
- `next-env.d.ts`、`.next` 和 TypeScript 增量信息由工具生成。`npm run typecheck` 先执行 `next typegen`，无需先启动前端或构建。
- 本地依赖、Python 运行时、浏览器运行时、缓存和测试输出不提交；`.env`、上传文件、基础设施本地数据也不提交。保留 `.env.example` 作为配置入口。
- 首版验证范围及尚未执行的数据库检查见 [验证记录](VERIFICATION.md)。

## 迁移

```powershell
Set-Location apps/api
uv run alembic current
uv run alembic upgrade head
uv run alembic check
```

迁移顺序：

1. `0001_postgis`：启用 PostGIS，需要数据库角色有创建 extension 的权限。
2. `0002_core`：User、Trip、TripDay、Place、Visit、Activity 及约束和索引。
3. `0003_wishlist`：独立愿望清单及用户/地点约束。
4. `0004_user_identity`：外部 provider subject 到本地 User UUID 的稳定映射。

`alembic downgrade 0001_postgis` 会删除核心表和全部旅行数据，仅应在可丢弃数据库上执行。继续降到 base 不删除 PostGIS extension，因为它可能被其他 schema 使用。升级脚本固定保存建表定义，不导入运行时 ORM 模型。

## 开发认证与 CRUD 验收

`.env` 中 `AUTH_MODE=development` 使用固定 `DEV_USER_ID`，首次认证请求通过幂等插入创建开发用户。API 不信任客户端提交的 user_id 或任意身份 header。`AUTH_MODE=disabled` 返回 `AUTH_REQUIRED`；production 配置 development 会拒绝启动。

阶段 B 可由运维人员把未来 Logto subject 显式绑定到已有用户。命令不会创建用户；同一映射重复执行返回同一记录，绑定到其他用户会以 `IDENTITY_CONFLICT` 失败：

```powershell
Set-Location apps/api
uv run python -m app.commands.bind_identity `
  --provider logto `
  --subject '<logto-subject>' `
  --user-id '<existing-user-uuid>'
```

该映射在阶段 C 之前不参与请求认证；当前仍不读取 Authorization header。

通过 Swagger 顺序执行：

1. `GET /api/v1/me`。
2. `POST /api/v1/trips`：`{"title":"秋日京都","start_date":"2026-10-01","end_date":"2026-10-05","timezone":"Asia/Tokyo"}`。
3. `POST /api/v1/places`：`{"canonical_name":"京都","latitude":35.0116,"longitude":135.7681,"timezone":"Asia/Tokyo"}`。
4. `POST /api/v1/trips/{trip_id}/days`：`{"date":"2026-10-02"}`。
5. `POST /api/v1/visits`：填入 place_id、trip_id、trip_day_id 和 `visited_at: "2026-10-02T09:00:00+09:00"`。
6. `POST /api/v1/trips/{trip_id}/activities`：填入 trip_day_id、place_id、title。
7. 查看 Trips、Days、Activities、Visits 列表；同一 Place 可以关联多次 Visit。
8. 删除 Trip 后，Visit 保留，trip_id / trip_day_id 清空；独立 Place 保留。

Web 目前提供导航、空状态、旅行列表和创建旅行表单。其他核心数据通过 API 操作。地图、日历与收件箱页面仅是占位。

## 检查

根目录：

```powershell
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm run test:web
```

`apps/api`：

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
```

不配置数据库时，pytest 执行 service、校验、API health/OpenAPI 和离线迁移测试，并明确跳过数据库测试。完整验证必须使用专用测试数据库：

```powershell
$env:TEST_DATABASE_URL = 'postgresql+psycopg://tovia:password@localhost:5432/tovia_test'
$env:DATABASE_URL = $env:TEST_DATABASE_URL
uv run alembic upgrade head
$env:MIGRATION_TEST_DATABASE_URL = 'postgresql+psycopg://tovia:password@localhost:5432/tovia_migration'
uv run pytest
```

先创建上述两个数据库。`tovia_migration` 必须可丢弃，测试会执行 downgrade / upgrade。CI 自动创建测试库，验证 schema 漂移、CRUD、用户隔离、外键、GiST 索引、迁移往返和 Compose 启动。浏览器 smoke 使用 API mock，数据库 CRUD 由后端集成测试覆盖。
