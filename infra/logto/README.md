# 可选的本地 Logto 环境

这套环境只用于阶段 D 的认证联调，和 Tovia 默认 Compose 完全分离。它使用独立的 Compose project、PostgreSQL 实例、数据库用户和持久卷；运行或删除它不会修改 Tovia 的 `postgres_data`。

当前固定版本：

- Logto `svhd/logto:1.42.0`
- PostgreSQL `postgres:17.11-alpine`

阶段 D 只配置用户名/密码登录、一个测试用户、一个 Device Flow 应用和一个 API Resource。不要在这里开启社交登录、组织、角色、MFA、SAML 或自定义主题。

## 1. 启动

在仓库根目录执行：

```powershell
Copy-Item infra/logto/.env.example infra/logto/.env
docker compose --env-file infra/logto/.env -f infra/logto/compose.yaml up -d
docker compose --env-file infra/logto/.env -f infra/logto/compose.yaml ps
```

在服务器上部署时，将 `infra/logto/.env` 中的 `LOGTO_ENDPOINT` 配为公开认证域名（例如 `https://auth.example.com`），将 `LOGTO_ADMIN_ENDPOINT` 配为受控的 Console 域名（例如 `https://console.example.com`）。`LOGTO_BIND_ADDRESS` / `LOGTO_HOST_PORT` / `LOGTO_ADMIN_HOST_PORT` 控制宿主机端口映射。建议服务只绑定 loopback，由反向代理提供 HTTPS，并限制管理入口。Tovia 的 `LOGTO_ENDPOINT` 与 `OIDC_ISSUER` 使用公开认证 endpoint，issuer 默认以 `/oidc` 结尾。

等待 `logto` 和 `logto-db` 都显示 healthy，然后访问：

- Logto Console：<http://localhost:3002>
- Logto OIDC discovery：<http://auth.localhost:3001/oidc/.well-known/openid-configuration>

本地 OIDC endpoint 使用 `auth.localhost`：浏览器会把 `.localhost` 域名解析到宿主机回环地址；叠加 `compose.tovia-oidc.yaml` 后，API 和 Web 容器会在 Logto 网络内把同一域名解析到 Logto 容器。因此 issuer 在浏览器、Web 服务端和 API 中保持一致，同时端口仍只绑定宿主机 loopback。

首次进入 Console 时创建本地管理员。Compose 的 seed 命令关闭了管理员密码泄露在线检查，避免离线开发环境初始化失败；这不是生产配置。

## 2. 最小控制台配置

1. 在 **API resources** 新建资源，名称使用 `Tovia API`，API identifier 必须是 `https://api.tovia.local`。不要添加 permission、role 或 organization。
2. 在 **Applications** 新建 Native 应用，认证方式选择 **Device flow**，名称使用 `Tovia Stage D Token Test`，记下 App ID（即 `client_id`）。Device Flow 是公开客户端，不需要 App Secret。
3. 在 **User management** 新建两个仅供本地联调的测试用户（例如 `tovia-a`、`tovia-b`），分别设置用户名和密码。阶段 D 的单 token 验证只需其中一个；阶段 F 隔离验收必须使用两个账户。

阶段 E 使用时，再在 **Applications** 新建 Traditional Web 应用 `Tovia Web`，配置：

- Redirect URI：`http://localhost:3000/callback`
- Post sign-out redirect URI：`http://localhost:3000/`
- API Resource：沿用 `https://api.tovia.local`

把该应用的 App ID 和 App Secret 写入 `apps/web/.env.local`。不要复用 Device Flow 应用，也不要把 App Secret 提交到仓库。

若要验证 v0.3 账户删除，请另建专用 **Machine-to-machine** 应用，并分配包含删除用户权限的 Logto Management API role。M2M 凭据只放在根目录 `.env`，由 Compose 仅传给 API：`LOGTO_MANAGEMENT_TOKEN_ENDPOINT=http://logto:3001/oidc/token`、`LOGTO_MANAGEMENT_API_URL=http://logto:3001/api`、`LOGTO_MANAGEMENT_API_RESOURCE=https://default.logto.app/api`，以及对应的 `LOGTO_MANAGEMENT_CLIENT_ID` / `LOGTO_MANAGEMENT_CLIENT_SECRET`。传统 Web 应用与 M2M 应用必须分开。真实删号会永久删除 Logto 用户及该 Tovia 用户的数据，只能对专用测试账户执行。

## 3. 获取用户 access token

把下面的 `<device-app-id>` 替换为第 2 步的 App ID：

```powershell
$deviceCodeResponse = Invoke-RestMethod `
  -Method Post `
  -Uri 'http://auth.localhost:3001/oidc/device/auth' `
  -ContentType 'application/x-www-form-urlencoded' `
  -Body @{
    client_id = '<device-app-id>'
    scope = 'openid offline_access profile'
    resource = 'https://api.tovia.local'
  }

$deviceCodeResponse | Format-List user_code, verification_uri, verification_uri_complete
```

在浏览器打开 `verification_uri_complete`，使用测试用户完成登录。然后至少等待 5 秒，再轮询 token endpoint：

```powershell
$tokenResponse = Invoke-RestMethod `
  -Method Post `
  -Uri 'http://auth.localhost:3001/oidc/token' `
  -ContentType 'application/x-www-form-urlencoded' `
  -Body @{
    client_id = '<device-app-id>'
    grant_type = 'urn:ietf:params:oauth:grant-type:device_code'
    device_code = $deviceCodeResponse.device_code
  }

$accessToken = $tokenResponse.access_token
```

若首次 token 响应没有返回目标 API 的 JWT，使用同一响应中的 refresh token 显式换取：

```powershell
$tokenResponse = Invoke-RestMethod `
  -Method Post `
  -Uri 'http://auth.localhost:3001/oidc/token' `
  -ContentType 'application/x-www-form-urlencoded' `
  -Body @{
    client_id = '<device-app-id>'
    grant_type = 'refresh_token'
    refresh_token = $tokenResponse.refresh_token
    resource = 'https://api.tovia.local'
  }

$accessToken = $tokenResponse.access_token
```

JWT 的 `aud` 应为 `https://api.tovia.local`，`iss` 应为 `http://auth.localhost:3001/oidc`。不要提交 access token、refresh token 或 `infra/logto/.env`。

## 4. 绑定身份并验证阶段 C

阶段 C 不会自动注册未知 subject。先从 Logto Console 的测试用户详情复制 User ID（它就是 JWT 的 `sub`），并绑定到已存在的本地 Tovia 用户。默认 development 用户 ID 为 `00000000-0000-4000-8000-000000000001`：

```powershell
docker compose run --rm api python -m app.commands.bind_identity `
  --provider logto `
  --subject '<logto-user-id>' `
  --user-id '00000000-0000-4000-8000-000000000001'
```

如果该 Tovia 用户还不存在，先以默认 development 模式启动 API 并请求一次 `GET /api/v1/me`，再执行绑定。

阶段 F 需要为第二个 Logto subject 准备另一个已有的 Tovia User UUID，并执行同一命令完成显式绑定。不得复用默认 UUID，也不得根据 email 自动合并。可先在数据库中创建专用测试 User，再把其 UUID 作为第二条命令的 `--user-id`；命令只创建 identity 映射，不会创建 User。

使用可选 override 重启 Tovia API；它只把 API 切到 OIDC，默认 `docker compose up` 仍然使用 development 认证：

```powershell
docker compose `
  -f compose.yaml `
  -f infra/logto/compose.tovia-oidc.yaml `
  up --build -d

Invoke-RestMethod `
  -Uri 'http://localhost:8000/api/v1/me' `
  -Headers @{ Authorization = "Bearer $accessToken" }
```

预期返回绑定用户；无 token、错误 audience 或未绑定 subject 返回 401。API 与 Logto Compose 通过共享的 `tovia-logto_default` 网络访问 JWKS，默认地址为 `http://logto:3001/oidc/jwks`。部署时 issuer 仍须与 token 的 `iss` 完全匹配；只有 Logto 不在该 Docker 网络时，才将 `OIDC_JWKS_URL` 改成 API 容器可访问的 URL。

恢复默认开发认证：

```powershell
docker compose up --build -d
```

## 5. 备份、升级与删除

升级前先创建 SQL 备份：

```powershell
New-Item -ItemType Directory -Force infra/backups | Out-Null
docker compose --env-file infra/logto/.env -f infra/logto/compose.yaml `
  exec -T logto-db sh -c 'pg_dump -U "$POSTGRES_USER" --clean --if-exists "$POSTGRES_DB"' `
  | Set-Content -Encoding utf8 infra/backups/logto.sql
```

升级时只修改 `infra/logto/compose.yaml` 中的固定 Logto tag，先阅读目标版本 release notes。备份完成后拉取镜像；若 release notes 要求 alteration，先只启动数据库并用目标镜像执行官方命令，再启动全部服务：

```powershell
docker compose --env-file infra/logto/.env -f infra/logto/compose.yaml pull
docker compose --env-file infra/logto/.env -f infra/logto/compose.yaml up -d logto-db
# 仅在目标版本 release notes 要求时执行下一条 alteration 命令
docker compose --env-file infra/logto/.env -f infra/logto/compose.yaml `
  run --rm --no-deps --entrypoint sh logto -c 'npm run alteration deploy'
docker compose --env-file infra/logto/.env -f infra/logto/compose.yaml up -d
```

需要恢复时，先停止 Logto，在确认目标是可覆盖的本地 Logto 数据库后导入备份，再重新启动：

```powershell
docker compose --env-file infra/logto/.env -f infra/logto/compose.yaml stop logto
Get-Content -Raw infra/backups/logto.sql `
  | docker compose --env-file infra/logto/.env -f infra/logto/compose.yaml `
      exec -T logto-db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
docker compose --env-file infra/logto/.env -f infra/logto/compose.yaml up -d
```

只停止可选环境并保留身份数据：

```powershell
docker compose --env-file infra/logto/.env -f infra/logto/compose.yaml down
```

确认备份可用后，删除可选环境及其独立卷：

```powershell
docker compose --env-file infra/logto/.env -f infra/logto/compose.yaml down --volumes
```

`down --volumes` 只删除 `tovia-logto` project 的 `logto_postgres_data`，不会删除 Tovia project 的 `postgres_data`。本地 `UserIdentity` 绑定仍保留在 Tovia 数据库中；若以后重建 Logto，新的 subject 必须重新显式绑定。

## 依据

- [Logto 官方 Docker Compose](https://github.com/logto-io/logto/blob/master/docker-compose.yml)
- [Logto 部署与配置](https://docs.logto.io/logto-oss/deployment-and-configuration)
- [Logto CLI 与数据库 alteration](https://docs.logto.io/logto-oss/using-cli)
- [Logto Device Flow](https://docs.logto.io/quick-starts/device-flow)
- [Logto access token 校验](https://docs.logto.io/authorization/validate-access-tokens)
- [Logto release notes](https://github.com/logto-io/logto/releases)
