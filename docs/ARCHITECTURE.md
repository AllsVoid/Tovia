# Tovia 所至 — 系统架构设计 v0.1

## Phase 0 → Phase 1 落地

Monorepo 使用 npm workspaces（apps/web、packages/*），Python 由 apps/api 下的 uv.lock 独立锁定。Web 是 Next.js App Router / strict TypeScript / Tailwind / shadcn Button，TanStack Query 管理旅行、地图与日历查询，Zustand 仅管理表单开关。

FastAPI 按 routers / services / repositories / models / schemas / providers 分层。SQLAlchemy 使用同步 psycopg 会话，FastAPI 同步 handler 在线程池执行。所有 schema 变更通过 Alembic；生产应用角色可和 migration 角色分离。

Compose 以 db → migrate → api → web 的依赖顺序启动，Redis 预留。认证使用 AuthProvider 接口和显式 development 实现，生产禁止该模式；正式登录接入后仍通过 User ID 关联业务数据。

v0.3 阶段 A 固定 provider-neutral 认证契约：HTTP 边界未来把凭证表示为 `AuthCredential`，Provider 返回 `AuthPrincipal(user_id, provider, subject)`；业务 service 只接收由该 principal 解析出的本地 User。当前 development provider 仍返回固定本地 UUID，不读取 Authorization header。OIDC 配置仅声明、尚未启用，`AUTH_MODE` 仍只允许 disabled/development。

v0.3 阶段 B 增加本地 `UserIdentity` 映射。`(provider, provider_subject)` 是外部身份唯一键，只通过运维命令绑定已有 User UUID；重复绑定同一用户幂等，跨用户绑定冲突。请求路径尚不读取该表，development 身份和所有现有业务路由保持原样。Logto SDK、JWT 验证和自动注册仍未引入。

当前测试与启动方式见 [开发指南](DEVELOPMENT.md)。

## Phase 2 落地

2026-09-19 行政区改版：`providers/regions.py` 读取构建时生成的离线目录，`RegionService` 将明确选择的行政区幂等解析为 Place。路由提供搜索与解析接口，不自行构造实体。目录同时打包到 API 与 Web，边界按省拆分为静态 GeoJSON，MapLibre 按所需行政区加载面并填色。新增选择不依赖在线地理编码。详见 `apps/web/public/maps/regions/README.md` 和 `infra/scripts/build-regions.py`。

原始 AreaCity GCJ-02 数据在构建时转换为 WGS84。世界地图沿用 Natural Earth，海外选择暂按国家粒度。旧 POI 的国内坐标在前端匹配市级面，只改变展示，不重写原数据。未匹配的旧地点保留列表提示。区域边界加载失败有独立重试入口。目录/几何为版本化静态派生资产，不作为每次访问记录存储。

`ExploreService` 负责地图 DTO、收藏与日历聚合；repository 用 SQL 按用户聚合 Visit、关联 WishlistItem，并按指定月份读取相关记录。路由只做参数与 envelope 转换。地图分页默认 200、上限 500；前端显示已加载/总数并可加载下一页。地点详情先展示最近 20 条访问。

Web 以 `MapProvider` 隔离底图样式/视角，MapLibre 仅在客户端加载；地图不可用时仍可操作列表与表单。TanStack Query 在写入后刷新旅行、地图及日历数据。地图与日历通过 place ID / trip ID / date 链接互相跳转。

MapLibre 6 的 ESM worker 使用显式同源 URL。`predev` / `prebuild` 从锁定依赖复制 worker、shared module 和 LICENSE 到 public/maplibre（生成文件，不提交），避免 bundler 的 worker URL 推断错误；参见 [官方 ESM 迁移说明](https://maplibre.org/maplibre-gl-js/docs/guides/v5-to-v6-migration-guide/)。

底图在 `apps/web/public/maps` 随项目提供，Docker runner 同样复制 public。当前为行政轮廓概览，不包含街道瓦片、在线地理编码或 nearby API。地点录入使用行政区目录搜索，不向用户索取坐标。

### 底图来源与许可

2026-09-13 从 Natural Earth 官方仓库取得同为 1:50m 的 GeoJSON，裁剪无关属性。国家填色与描边共用国家几何；省界只保留 China 的 31 个省级面之间共享的内部边，避免省级外轮廓与国家海岸线重复。低分辨率数据不保证小岛和全部行政细节，不能用作导航。运行时无需请求外部地图服务。

- [国家轮廓 ne_50m_admin_0_countries](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_50m_admin_0_countries.geojson)：242 features，`countries.geojson` SHA256 `3ebb06af22f73c54462e173c384bbb924cedf4c588b9df2cfee731dc31fdea00`。
- [省界 ne_50m_admin_1_states_provinces](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_50m_admin_1_states_provinces.geojson)：31 个省级面提取为 72 条内部边界，`provinces.geojson` SHA256 `9ff4cb803c96bd28ce647f8dbaf3378cb53251628996b442b346e20aec588b5f`。
- [Natural Earth 使用条款](https://www.naturalearthdata.com/about/terms-of-use/)：数据为 public domain；地图保留来源署名。

下载上述两个原始 GeoJSON 后，可运行 `node apps/web/scripts/build-map-data.mjs <admin0-50m.json> <admin1-50m.json>` 重建内置地图。该脚本按不同省份共享的边提取内部边界，不将省级海岸线叠加到国家轮廓上。

## 1. 架构目标

- Web MVP 快速上线
- 后续平滑支持 iOS / Android / 微信小程序
- 前后端解耦
- 地理数据为一等公民
- AI 可替换
- OCR 可替换
- 存储可替换
- 支持异步任务
- 保持单体优先，不提前微服务化

---

## 2. 总体架构

```text
Web (Next.js)
Mobile (React Native / Expo)
Mini Program (Taro)
        |
        v
   Unified API
     FastAPI
        |
  -------------------------
  |      |       |        |
Postgres Redis  Storage  Workers
PostGIS        S3/R2     AI/OCR
```

---

## 3. 前端

### Web

- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Query
- Zustand
- MapLibre GL JS

### 后续移动端

- React Native
- Expo
- SQLite / local cache
- MapLibre React Native

### 后续小程序

- Taro + React
- 使用统一 API
- UI 单独适配
- 不强行共享 Web UI

---

## 4. 后端

推荐：

- FastAPI
- SQLAlchemy 2
- Alembic
- Pydantic
- PostgreSQL
- PostGIS
- Redis
- Dramatiq 或 Celery

API 风格：

- REST first
- `/api/v1/...`
- OpenAPI 自动生成

---

## 5. 数据库

核心：

- PostgreSQL
- PostGIS extension

理由：

- 点
- 轨迹
- 行政区
- 距离查询
- point-in-polygon
- nearby
- geo clustering

---

## 6. 对象存储

所有原始文件进入 S3-compatible storage：

- photo
- screenshot
- pdf
- ticket
- receipt

数据库仅存 metadata 和 storage key。

必须保留：

- original file
- thumbnail
- derived assets
- checksum

---

## 7. AI / OCR

必须通过 Provider interface：

```text
OCRProvider
AIProvider
MapProvider
StorageProvider
AuthProvider
```

禁止业务逻辑绑定特定厂商。

---

## 8. 异步任务

所有耗时任务走 Queue：

- OCR
- EXIF extraction
- AI extraction
- thumbnail generation
- pHash
- reverse geocoding
- recap generation

状态：

- PENDING
- PROCESSING
- REVIEW_REQUIRED
- COMPLETED
- FAILED

---

## 9. Map Provider 抽象

目标：

```text
MapProvider
- get_tile_style()
- reverse_geocode()
- search_poi()
- normalize_coordinate()
```

海外：

- MapLibre + OSM compatible

中国：

- 高德 / 腾讯适配

内部统一坐标模型，明确 WGS84 / GCJ02 转换边界。

---

## 10. Auth

抽象：

```text
User
UserIdentity
```

未来支持：

- email
- Apple
- Google
- WeChat

业务表只关联 `user_id`。

认证错误边界：缺少、无效或过期凭证返回 401；已认证但无权执行某类操作返回 403；按 ID 访问其他用户私有实体时返回 404，避免泄露实体是否存在。共享 Place 仍按既有规则读取。

---

## 11. Monorepo

```text
tovia/
  apps/
    web/
    api/
    mobile/
    miniprogram/
  workers/
    ai/
    media/
  packages/
    api-client/
    schemas/
    geo/
    money/
    constants/
  infra/
  docs/
```

MVP 可只初始化：

- apps/web
- apps/api
- workers
- packages/schemas

---

## 12. 部署

MVP 推荐：

- Web: Vercel / container
- API: Docker
- DB: managed PostgreSQL
- Storage: R2 / S3
- Redis: managed Redis

不要第一阶段引入：

- Kubernetes
- Kafka
- Elasticsearch
- service mesh
- event sourcing

---

## 13. 安全

必须：

- signed upload URL
- file MIME validation
- max upload size
- per-user authorization
- storage path isolation
- AI prompt 中避免泄露其他用户数据
- 原始文档访问鉴权
- secrets 只在 server
- audit log 至少覆盖 AI confirm / edit

---

## 14. 可观测性

MVP 最低要求：

- structured logs
- request id
- background job id
- error tracking
- AI provider latency
- AI provider token / cost
- upload failure rate

---

## 15. 架构原则

1. 单体优先
2. Provider 可替换
3. 异步任务与 HTTP 请求分离
4. 正式数据与 AI Candidate 分离
5. 原始资料与派生数据分离
6. 地理实体与旅行实例分离
