# Tovia 所至 — API 约定 v0.1

## Phase 0 / Phase 1 当前实现

运行中的 `/openapi.json` 是准确的类型合同，`/docs` 为 Swagger。下文后续模块的路由是规划，尚未实现。

- `GET /health`（无版本前缀、无认证）：返回标准 envelope，data 含 `status`、`database`、`postgis`、`migration`。依赖和迁移均正常时为 200，否则 503。
- 已实现 `/me` GET/PATCH；`/trips` GET/POST；`/trips/{id}` GET/PATCH/DELETE。
- 已实现 `/trips/{id}/days` GET/POST，补充 `/days/{id}` PATCH/DELETE。
- 已实现 `/places/search` GET、`/places/{id}` GET，补充 `/places` POST 供 Phase 1 手工添加。坐标输入为 WGS84 latitude/longitude，范围必须合法且提供 IANA timezone。共享 Place 暂不开放更新/删除；nearby 留到地图阶段。
- 已实现 `/visits` GET/POST，`/visits/{id}` PATCH/DELETE。列表支持 trip_id 过滤。
- 已实现 `/trips/{id}/activities` GET/POST，`/activities/{id}` PATCH/DELETE；通过 PATCH sort_order 调整单项排序，批量 reorder 尚未实现。
- 所有列表支持 limit（1..100，默认 50）和 offset（默认 0），meta 回传分页参数。
- PATCH 仅更改已提交字段，对合并后的完整实体再次验证；不可空字段显式 null 会报错。DELETE 返回 200 和空 data 的 envelope。
- 错误统一包含 `data: null`、`meta: {}`、`error: {code,message}`。包括 VALIDATION_ERROR (422)、DATA_CONFLICT (409)、AUTH_REQUIRED (401)、DATABASE_UNAVAILABLE (503) 及实体 NOT_FOUND (404)。不暴露 SQL / 连接凭证。
- 所有核心路由需要认证上下文。当前仅显式 development 模式使用固定本地用户，不接受客户端 user_id；production 禁止开发认证。共享 Place 可读取和创建；私有 Trip / Day / Visit / Activity 按用户隔离。
- Visit、Activity 手工创建仅接受 MANUAL source。暂未实现 AI、上传、预订、费用、地图与日历 API。

Base:

```text
/api/v1
```

统一返回：

```json
{
  "data": {},
  "meta": {},
  "error": null
}
```

错误：

```json
{
  "data": null,
  "error": {
    "code": "TRIP_NOT_FOUND",
    "message": "Trip not found"
  }
}
```

---

## Auth

```text
GET    /me
PATCH  /me
```

---

## Trips

```text
GET    /trips
POST   /trips
GET    /trips/{trip_id}
PATCH  /trips/{trip_id}
DELETE /trips/{trip_id}

GET    /trips/{trip_id}/days
POST   /trips/{trip_id}/days
```

---

## Places

```text
GET    /places/search?q=
GET    /places/{place_id}
GET    /places/nearby?lat=&lng=&radius=
```

---

## Visits

```text
GET    /visits
POST   /visits
PATCH  /visits/{visit_id}
DELETE /visits/{visit_id}
```

---

## Map

```text
GET /map/summary?scope=domestic|international
GET /map/places?status=visited|upcoming|wishlist
GET /map/region/{region_id}
```

返回必须是前端友好的轻量 DTO，避免直接返回完整业务实体。

---

## Calendar

```text
GET /calendar/month?year=2026&month=8
GET /calendar/day?date=2026-08-29
```

月返回示例：

```json
{
  "date": "2026-08-29",
  "trip_ids": ["..."],
  "cover_photo_url": "...",
  "has_memory": true,
  "places_count": 8,
  "expense_total": {
    "amount": 584.2,
    "currency": "CNY"
  }
}
```

---

## Activities

```text
GET    /trips/{trip_id}/activities
POST   /trips/{trip_id}/activities
PATCH  /activities/{activity_id}
DELETE /activities/{activity_id}
POST   /activities/reorder
```

---

## Bookings

```text
GET    /trips/{trip_id}/bookings
POST   /bookings
PATCH  /bookings/{booking_id}
DELETE /bookings/{booking_id}
```

---

## Expenses

```text
GET    /trips/{trip_id}/expenses
POST   /expenses
PATCH  /expenses/{expense_id}
DELETE /expenses/{expense_id}
GET    /trips/{trip_id}/expenses/summary
```

---

## Photos

```text
POST /uploads/presign
POST /photos
GET  /trips/{trip_id}/photos
PATCH /photos/{photo_id}
DELETE /photos/{photo_id}
```

上传建议：

1. 客户端申请 presigned URL
2. 直传 storage
3. 调用 `POST /photos`
4. 服务端创建异步 metadata job

---

## Inbox / Import

```text
POST /imports
GET  /imports/{job_id}
GET  /imports/{job_id}/candidates

POST /import-candidates/{candidate_id}/confirm
POST /import-candidates/{candidate_id}/reject
PATCH /import-candidates/{candidate_id}
```

---

## AI Planner

MVP 可先只做：

```text
POST /trips/{trip_id}/ai/plan
```

输入：

- trip id
- user preference
- optional date range

输出：

- Candidate activities
- 不直接写正式 itinerary

---

## Stats

```text
GET /stats/overview
GET /stats/year/{year}
GET /stats/trips/{trip_id}
```

---

## API 版本策略

- v1 不随意 breaking
- 新字段优先 nullable
- enum 通过兼容扩展
- breaking change 升 v2
