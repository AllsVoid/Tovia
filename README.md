# Tovia 所至

> 凡我所至，皆有所记。

以地图、时间和旅行档案为核心的个人旅行数据库。

当前已实现 Phase 0 → Phase 2：基础设施、核心旅行 CRUD、真实数据地图、旅行月历、旅行详情与愿望清单。AI 功能尚未开发。

## 启动

### 使用 Docker

需要 Docker Engine / Docker Desktop（Linux containers）和 Docker Compose v2。在仓库根目录执行：

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

首次启动会创建 PostGIS 数据库并运行 Alembic migration。`migrate` 成功后 API 和 Web 会依次启动。

- Web：<http://localhost:3000>
- API 健康检查：<http://localhost:8000/health>
- API 文档：<http://localhost:8000/docs>

默认使用本地 development 认证。停止服务但保留数据：`docker compose down`。不要加 `-v`，除非确实要删除本地数据库卷。

### 不使用 Docker

需要 Node.js 24、Python 3.12、uv、PostgreSQL 17 和 PostGIS。先安装并启动 PostgreSQL/PostGIS，在 psql 中创建应用数据库（若已有可复用）：

```sql
CREATE USER tovia WITH PASSWORD 'tovia_local_only';
CREATE DATABASE tovia OWNER tovia;
\connect tovia
CREATE EXTENSION IF NOT EXISTS postgis;
```

在仓库根目录的 PowerShell 安装依赖、迁移数据库并启动 API：

```powershell
Copy-Item .env.example .env
uv python install 3.12
uv sync --project apps/api --frozen
npm ci
Set-Location apps/api
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

另开终端，在仓库根目录启动 Web：

```powershell
npm run dev
```

访问地址与 Docker 模式相同。`.env` 的 `DATABASE_URL` 需要匹配本机 PostgreSQL 用户、密码和端口；默认 `AUTH_MODE=development`，本地无需配置登录服务。无 Docker 模式不需要 Redis，当前没有启用异步 worker。

### 可选：接入本地 Logto

默认的 Tovia Compose 使用本地 development 身份，不需要 Logto。启用真实登录时，Logto 是单独的服务：Tovia 主 Compose 不会自动启动它，也不会替你创建 API Resource、Web 应用或测试用户。

先启动独立的 Logto Compose：

```powershell
Copy-Item infra/logto/.env.example infra/logto/.env
docker compose --env-file infra/logto/.env -f infra/logto/compose.yaml up -d
```

等待 `logto` 和 `logto-db` healthy 后，在 <http://localhost:3002> 创建本地管理员，并在 Console 手动完成以下配置：

1. 在 **API resources** 创建 API Resource，identifier 设为 `https://api.tovia.local`。
2. 在 **Applications** 创建 **Traditional Web** 应用 `Tovia Web`，添加 Redirect URI `http://localhost:3000/callback` 和 Post sign-out redirect URI `http://localhost:3000/`，并允许该应用请求上述 API Resource。记下 App ID 和 App Secret。
3. 在 **User management** 创建仅供本地测试的用户。Console 中用户的 User ID 是 token 的 `sub`，稍后需要用它绑定 Tovia 用户。

先在默认 development 模式启动 Tovia，并请求一次 `http://localhost:8000/api/v1/me`，确保默认 Tovia 用户已创建。把 Web 登录配置放进仓库根目录 `.env`（Compose 会传给 Web 容器）：

```dotenv
NEXT_PUBLIC_WEB_AUTH_MODE=oidc
LOGTO_ENDPOINT=http://localhost:3001
LOGTO_BASE_URL=http://localhost:3000
LOGTO_APP_ID=<traditional-web-app-id>
LOGTO_APP_SECRET=<traditional-web-app-secret>
LOGTO_COOKIE_SECRET=<至少32字符的随机值>
LOGTO_API_RESOURCE=https://api.tovia.local
```

`LOGTO_COOKIE_SECRET` 可用 `openssl rand -base64 48` 生成。API 也要切换到 OIDC；在根目录 `.env` 设置：

```dotenv
AUTH_MODE=oidc
OIDC_ISSUER=http://localhost:3001/oidc
OIDC_AUDIENCE=https://api.tovia.local
OIDC_JWKS_URL=http://logto:3001/oidc/jwks
```

然后使用 OIDC override 启动 Tovia：

```powershell
docker compose -f compose.yaml -f infra/logto/compose.tovia-oidc.yaml up --build -d
```

Logto 不会自动创建或按 email 合并 Tovia 用户。将 Console 中的 Logto User ID 显式绑定到已存在的 Tovia 用户：

```powershell
docker compose run --rm api python -m app.commands.bind_identity `
  --provider logto `
  --subject '<logto-user-id>' `
  --user-id '00000000-0000-4000-8000-000000000001'
```

不要提交 `.env`、`infra/logto/.env`、`apps/web/.env.local`、App Secret、cookie secret 或 token。Logto 端口、测试 token 获取方式、备份和清理说明见仓库中的[Logto 运维说明](infra/logto/README.md)。

### 部署到服务器

Compose 的公开 URL 和宿主机端口均可在根目录 `.env` 中修改。部署前至少更改数据库密码和所有认证密钥，并设置公开域名，例如：

```dotenv
POSTGRES_PASSWORD=<强随机数据库密码>
WEB_PUBLIC_URL=https://travel.example.com
API_PUBLIC_URL=https://api.example.com
WEB_BIND_ADDRESS=127.0.0.1
WEB_HOST_PORT=3000
API_BIND_ADDRESS=127.0.0.1
API_HOST_PORT=8000
CORS_ORIGINS=["https://travel.example.com"]
```

关闭 Web OIDC 时，`API_PUBLIC_URL` 应是浏览器可访问的 API HTTPS 地址。启用 Web OIDC/BFF 时，Web 服务端通过内部 `TOVIA_API_URL=http://api:8000` 访问 API；浏览器侧 API 地址通常不参与业务请求。

`WEB_BIND_ADDRESS`、`API_BIND_ADDRESS` 和对应的 `*_HOST_PORT` 控制宿主机端口映射。与同机反向代理配合时，建议保留 `127.0.0.1` 绑定，由代理处理 HTTPS 和公网入口；数据库和 Redis 也默认只绑定 loopback，不要直接暴露公网。反向代理应将 Web 域名转发到 Web 端口，将 API 域名转发到 API 端口，并启用 HTTPS、设置固定的 Host/协议头及 WebSocket（如有需要）。API 容器不信任 `X-Forwarded-*` 头；不要改成信任任意来源，应用使用 `.env` 中配置的公开 URL。Compose 不会替你配置 DNS、TLS 或反向代理。

如果服务器启用 Logto 登录，`LOGTO_ENDPOINT` 和 `OIDC_ISSUER` 必须使用外部可访问的认证域名，且 issuer 必须与 token 的 `iss` 完全一致；通常是 `https://auth.example.com` 和 `https://auth.example.com/oidc`。Traditional Web 应用的 Redirect URI、登出回调也要改成生产 Web 域名（例如 `https://travel.example.com/callback` 与 `https://travel.example.com/`）。`LOGTO_BASE_URL` 设为 Web HTTPS 地址，`LOGTO_COOKIE_SECRET` 使用新的随机值，`LOGTO_APP_SECRET` 使用生产 Logto 应用的密钥；`OIDC_AUDIENCE` 继续与 API Resource identifier 相同。若 Logto 与 Tovia Compose 共享网络，`OIDC_JWKS_URL` 可继续用 `http://logto:3001/oidc/jwks`；否则需改成 API 容器可以访问的 JWKS 地址。Logto 自身使用独立的 `infra/logto/.env`，其 `LOGTO_ENDPOINT`、`LOGTO_ADMIN_ENDPOINT` 和绑定端口也须按域名及反向代理调整，并保护 Console 管理入口。

生产 API 只接受 `APP_ENV=production` 与 `AUTH_MODE=oidc`，要求 HTTPS issuer 和非示例数据库密码；生产 Web 也必须启用 OIDC 并提供 HTTPS Logto/Web 地址及完整密钥。配置不满足时服务启动失败。OIDC 凭证无效或过期返回 401；Logto/JWKS 暂时不可用返回 503，不会切换到开发用户。API 输出 JSON 认证审计事件（成功、拒绝、provider 不可用、身份绑定冲突），响应头 `X-Request-ID` 可用于关联排查。日志不记录 bearer token 或原始 subject；请限制日志访问并按部署的数据保留政策管理。

Logto 应用密钥轮换时，先在 Logto 创建/轮换密钥并更新部署 secret，再重启 Web；确认登录和登出正常后撤销旧密钥。签名密钥应先让新旧公钥在 JWKS 中并存，验证新签发 token 后，再等最长 access-token 有效期和 API 5 分钟 JWKS 缓存窗口过去后撤销旧密钥。API 会对未知 `kid` 重新读取 JWKS；切勿在重叠验证完成前移除旧公钥。

部署需定期备份 Tovia PostgreSQL 数据库，加密后异地存放，并在独立临时数据库演练恢复。以下 PowerShell 示例从数据库容器导出 PostgreSQL custom-format 备份，再复制到主机；`infra/backups/` 不会提交到 Git：

```powershell
New-Item -ItemType Directory -Force infra/backups | Out-Null
$backupFile = "infra/backups/tovia-$(Get-Date -Format 'yyyyMMdd-HHmmss').dump"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --file=/tmp/tovia.dump'
docker compose cp db:/tmp/tovia.dump $backupFile
docker compose exec -T db rm -f /tmp/tovia.dump
Get-FileHash $backupFile -Algorithm SHA256
```

恢复演练必须使用临时数据库，不能直接覆盖运行中的生产库：

```powershell
docker compose cp $backupFile db:/tmp/tovia-restore-check.dump
docker compose exec -T db sh -c 'createdb -U "$POSTGRES_USER" tovia_restore_check'
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d tovia_restore_check --no-owner --exit-on-error /tmp/tovia-restore-check.dump'
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d tovia_restore_check -c "SELECT PostGIS_Version(); SELECT version_num FROM alembic_version;"'
docker compose exec -T db sh -c 'dropdb -U "$POSTGRES_USER" tovia_restore_check'
docker compose exec -T db rm -f /tmp/tovia-restore-check.dump
```

保留每次部署所用的应用镜像/代码版本、Compose 配置和受控 secret 版本。认证配置或应用回滚时，恢复上一已验证版本与对应配置；OIDC 阶段不改写 User UUID 或旅行数据外键。发生数据库损坏时先停止 API 写入，从已验证备份恢复到新数据库/卷，检查 PostGIS 和 Alembic revision，再切换连接并检查 `/health`。Logto 的身份数据库须独立备份和恢复，步骤见[Logto 运维说明](infra/logto/README.md)。

## 项目结构

```text
apps/web          Next.js Web
apps/api          FastAPI、核心模型、Alembic migration
workers           后续异步任务
packages          共享包
infra             基础设施扩展
docs              产品、架构、工程与开发文档
```

`docs/` 存放产品、架构、工程与开发资料；克隆仓库后若部分资料不可用，README 中的启动、认证和部署说明可独立使用。编码代理约束保留在根目录 [AGENTS.md](AGENTS.md)。
