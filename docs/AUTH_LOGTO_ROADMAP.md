# Tovia 所至 — Logto 渐进式接入路线

状态基线：2026-09-20
适用版本：v0.3 数据可维护与正式身份

## 1. 目标

以可验证、可回滚的小阶段接入 Logto。任何阶段都不得要求同时完成整套登录、账户管理和生产切换；每次修改后，现有 v0.2 旅行、地图、日历与开发身份流程必须继续工作。

Logto 只负责凭证、OIDC 登录和会话。Tovia 继续拥有本地 `User`、`UserIdentity`、数据所有权、导出、删除编排与业务审计。

## 2. 全程约束

- 每个阶段单独提交和验收；上一阶段未通过，不进入下一阶段。
- `AUTH_MODE=development` 在正式切换前始终保持可用，且本地默认行为不变。
- 新能力默认关闭；不得通过一次提交直接改变现有用户请求路径。
- 数据库修改只允许向前兼容的新增，不重写现有 User UUID，不批量迁移 Trip、Visit 或 Activity 外键。
- 外部身份只按 `(provider, provider_subject)` 关联，禁止使用 email 作为稳定身份主键。
- Logto 自身表和迁移不纳入 Tovia Alembic；自托管时使用独立数据库和数据库角色。
- FastAPI 业务 service/repository 不依赖 Logto SDK；认证实现只能位于 provider / dependency 边界。
- 每阶段必须通过既有 Ruff、MyPy、Pytest、ESLint、TypeScript、build 和 Playwright 基线。
- 涉及数据库的阶段必须验证新库安装、v0.2 升级和 downgrade/restore 路径。
- 未明确进入阶段范围的功能不得顺带实现。

## 3. 分阶段路线

### 阶段 A — 认证契约与回归基线

目标：先固定 Tovia 对认证系统的需求，不改变运行时行为。

允许修改：

- 定义 `AuthPrincipal` / `AuthProvider` 的输入输出契约。
- 明确 401、403、404 的使用规则以及 token 失效语义。
- 补齐现有 development 身份、无身份和跨用户访问的回归测试。
- 记录 OIDC issuer、audience、subject、JWKS 和时钟偏差配置项，但暂不加载 Logto SDK。

本阶段不做：

- 不增加 Logto 容器或 npm/Python 依赖。
- 不增加登录页面、UserIdentity 表或 JWT 验证。
- 不改变现有 API 请求和 CORS 行为。

验收与回滚：

- 现有功能测试结果与阶段开始前一致。
- production 仍拒绝 development 身份。
- 本阶段只有契约、配置声明和测试，可直接撤销，不涉及数据回滚。

### 阶段 B — 本地身份映射模型

目标：增加外部身份到本地 User UUID 的稳定映射，但仍只使用 development 身份。

允许修改：

- 新增 `UserIdentity` 模型、schema、repository 和 Alembic migration。
- 增加 `(provider, provider_subject)` 唯一约束。
- 提供只供运维使用的显式绑定命令，将未来 Logto subject 绑定到已有 User UUID。
- 增加身份冲突、重复绑定和跨用户绑定测试。

本阶段不做：

- 不自动创建正式身份。
- 不读取 Authorization header。
- 不修改现有用户数据，也不创建登录 UI。

验收与回滚：

- 空 `UserIdentity` 表时，现有 development 用户行为完全不变。
- v0.2 数据升级后所有 User、Trip、Visit 和 Activity ID 保持不变。
- migration upgrade/downgrade 和真实 PostgreSQL 集成测试通过。

### 阶段 C — OIDC Token 验证 Provider

目标：让 FastAPI 具备验证 Logto access token 的能力，但默认不开启。

允许修改：

- 新增 `AUTH_MODE=oidc`，保留 `development` 和 `disabled`。
- 在 provider 边界实现 Bearer token 提取、JWKS 缓存和 JWT 验证。
- 严格校验签名、算法、issuer、audience、expiry 和 subject。
- 将已验证的 `(issuer/provider, subject)` 解析为本地 User。
- 使用本地测试密钥和固定 token fixture 完成成功、过期、错误 audience、错误 issuer 和未知 identity 测试。

本阶段不做：

- 不增加浏览器登录流程。
- 不在业务路由中直接解析 JWT。
- 不自动注册未知 subject，不增加 RBAC、role 或 scope 业务模型。

验收与回滚：

- 默认 development 配置下所有现有测试和页面行为不变。
- 仅显式设置 `AUTH_MODE=oidc` 时才执行 OIDC 路径。
- OIDC 配置不完整时启动失败或返回明确 401，禁止静默降级为 development 用户。
- 回滚只需关闭 `AUTH_MODE=oidc`；UserIdentity 数据可以保留。

### 阶段 D — 可选的 Logto 开发环境

目标：提供可复现的本地 Logto 环境，不把它变成默认开发依赖。

允许修改：

- 增加独立 Compose profile 或单独的开发 compose 文件。
- Logto 使用独立数据库、数据库用户和持久卷。
- 提供初始化说明、回调地址、API Resource 和测试用户配置步骤。
- 固定镜像版本，记录升级和备份方式。

本阶段不做：

- 默认 `docker compose up` 不启动 Logto。
- 不与 Tovia 共用 schema 或 migration role。
- 不加入社交登录、组织、角色、MFA、SAML 或自定义主题。

验收与回滚：

- 不启用 profile 时，现有 Compose 服务集合与行为不变。
- 启用 profile 后可取得能被阶段 C 验证的 access token。
- 删除可选 Logto 环境不会影响 Tovia 数据库。

### 阶段 E — 最小 Web 登录与 BFF

目标：在功能开关后提供登录、callback、退出和受保护请求，不立即替换当前前端路径。

允许修改：

- Next.js 接入最小 Logto OIDC 客户端。
- 增加 `/sign-in`、`/callback`、`/sign-out`。
- 使用加密 HttpOnly Session 保存服务端 token 状态。
- 增加同源 BFF，将 access token 转发给 FastAPI。
- 客户端处理 401：尝试一次续期；失败后回到登录页。

本阶段不做：

- 不实现社交登录选择器、管理后台、账户中心、角色 UI 或定制登录主题。
- 不在 localStorage 保存 access token 或 refresh token。
- 不一次性迁移所有前端 API 调用。

验收与回滚：

- 功能开关关闭时继续使用现有 `NEXT_PUBLIC_API_URL` 路径。
- 功能开关开启时完成登录、一次业务读取、过期续期和退出 E2E。
- BFF 不接受或注入客户端提供的 `user_id`、`x-user-id`。
- 回滚只关闭 Web OIDC 开关，development 流程仍可运行。

### 阶段 F — 双用户隔离与非生产切换

目标：在非生产环境把完整 Web 请求切换到 OIDC，并验证真实隔离边界。

允许修改：

- 将现有前端 API 调用逐批切到同源 BFF。
- 使用两个真实 Logto 测试账户绑定两个本地 User。
- 为已有 development 用户执行一次显式 subject 绑定，保留原 User UUID。
- 增加跨用户读取、修改、删除、ID 枚举和 session 过期浏览器测试。

本阶段不做：

- 不允许按 email 自动合并账户。
- 不删除 development provider。
- 不开启 production OIDC，也不实现 Profile、导出或删号页面。

验收与回滚：

- 两个账户只能访问各自数据；越权访问统一返回约定的 403 或 404。
- 原 development 用户的 Trip、Visit、Activity 和 WishlistItem 全部仍由同一 UUID 拥有。
- 所有核心浏览器流程连接真实 FastAPI 和 PostgreSQL 通过。
- 可将非生产 Web 开关切回旧请求路径，不回滚身份映射数据。

### 阶段 G — 生产启用与最小运维闭环

目标：完成生产切换所需的安全和运维门槛；仍不扩展身份产品范围。

允许修改：

- 生产环境启用 `AUTH_MODE=oidc`，禁止 development fallback。
- 配置 HTTPS、可信代理、精确 redirect URI、secret 管理和 key rotation 流程。
- 增加认证成功、无效/过期 token、身份映射冲突的结构化审计。
- 增加 Logto 与 JWKS 不可用时的 fail-closed 行为和运维说明。
- 完成备份、恢复和回滚演练。

本阶段不做：

- 不开启 social login、MFA、组织、RBAC、SAML、SCIM 或管理员嵌入页。
- 不把 Logto 用户资料作为旅行数据的 source of truth。
- 不与 Profile、数据导出、账户删除之外的 v0.3 功能混合发布。

验收与回滚：

- 无有效会话时所有业务接口返回 401。
- production 无法配置为 development 身份，也不会在 OIDC 故障时降级。
- 生产切换前完成一次备份；回滚方案是恢复上一应用版本和认证配置，不重写业务外键。

## 4. v0.3 后续独立工作包

以下能力依赖正式身份，但不属于 Logto 基础接入，应在阶段 G 后分别实现和验收：

1. Profile 基础资料页。
2. JSON 全量导出。
3. 账户删除编排与重新验证。
4. 登录异常、导出、账户删除和关键实体删除审计。

账户删除必须同时处理 Logto 身份与 Tovia 本地数据，但不得直接从浏览器调用 Logto Management API。

## 5. 明确排除项

在 v0.3 内，除非发布计划先变更，否则不接入：

- Google、GitHub、微信或其他社交登录。
- MFA、Passkey、短信登录或无密码登录。
- Organization、Team、Role、RBAC、SAML、SCIM。
- Logto Admin Console 嵌入 Tovia。
- 自定义登录主题和复杂品牌化。
- 通过 Webhook 自动创建可信业务实体。

## 6. 阶段完成记录

| 阶段 | 状态 | 完成日期 | 验证记录 | 遗留问题 |
| --- | --- | --- | --- | --- |
| A 认证契约与回归基线 | 已完成 | 2026-09-20 | Ruff、格式、MyPy、Pytest 22 passed；ESLint、TypeScript、production build；Playwright 4 passed | 专用 PostGIS 环境未配置，5 个数据库集成测试按既有规则跳过 |
| B 本地身份映射模型 | 已完成 | 2026-09-20 | Ruff、格式、MyPy；Pytest 37 passed（真实 PostgreSQL/PostGIS）；ESLint、TypeScript、build、Playwright 4 passed；迁移与运维命令冒烟通过 | 尚未读取 Bearer token，按计划留到阶段 C |
| C OIDC Token 验证 Provider | 已完成 | 2026-09-20 | RS256/JWKS、issuer、audience、expiry、subject 与 Bearer API 测试；完整回归见 VERIFICATION | 尚无浏览器登录与真实 Logto tenant，按计划留到阶段 D/E |
| D 可选的 Logto 开发环境 | 未开始 | — | — | — |
| E 最小 Web 登录与 BFF | 未开始 | — | — | — |
| F 双用户隔离与非生产切换 | 未开始 | — | — | — |
| G 生产启用与最小运维闭环 | 未开始 | — | — | — |
