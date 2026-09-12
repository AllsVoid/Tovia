# Tovia 所至 — 系统架构设计 v0.1

## Phase 0 → Phase 1 落地

Monorepo 使用 npm workspaces（apps/web、packages/*），Python 由 apps/api 下的 uv.lock 独立锁定。Web 是 Next.js App Router / strict TypeScript / Tailwind / shadcn Button，TanStack Query 管理旅行查询，Zustand 仅管理表单开关。MapLibre 已安装，地图功能在 Phase 2 实现。

FastAPI 按 routers / services / repositories / models / schemas / providers 分层。SQLAlchemy 使用同步 psycopg 会话，FastAPI 同步 handler 在线程池执行。所有 schema 变更通过 Alembic；生产应用角色可和 migration 角色分离。

Compose 以 db → migrate → api → web 的依赖顺序启动，Redis 预留。认证使用 AuthProvider 接口和显式 development 实现，生产禁止该模式；正式登录接入后仍通过 User ID 关联业务数据。

当前测试与启动方式见 [开发指南](DEVELOPMENT.md)。

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
