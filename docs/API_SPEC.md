# Tovia 所至 — API 约定 v0.1

## Phase 0 / Phase 1 当前实现

运行中的 `/openapi.json` 是准确的类型合同，`/docs` 为 Swagger。下文后续模块的路由是规划，尚未实现。

- `GET /health`（无版本前缀、无认证）：返回标准 envelope，data 含 `status`、`database`、`postgis`、`migration`。依赖和迁移均正常时为 200，否则 503。
- 已实现 `/me` GET/PATCH；`/trips` GET/POST；`/trips/{id}` GET/PATCH/DELETE。
- 已实现 `/trips/{id}/days` GET/POST，补充 `/days/{id}` PATCH/DELETE。
- 已实现 `/places/search` GET、`/places/{id}` GET，补充 `/places` POST 供 Phase 1 手工添加。坐标输入为 WGS84 latitude/longitude，范围必须合法且提供 IANA timezone。共享 Place 暂不开放更新/删除；nearby 留到地图阶段。
- 已实现 `/visits` GET/POST，`/visits/{id}` PATCH/DELETE。列表支持 trip_id 过滤。
- 已实现 `/trips/{id}/activities` GET/POST，`/activities/{id}` PATCH/DELETE；通过 PATCH sort_order 调整单项排序，批量 reorder 尚未实现。
- 核心 CRUD 列表支持 limit（1..100，默认 50）和 offset（默认 0），meta 回传分页参数。Phase 2 地图分页格式见下文。
- PATCH 仅更改已提交字段，对合并后的完整实体再次验证；不可空字段显式 null 会报错。DELETE 返回 200 和空 data 的 envelope。
- 错误统一包含 `data: null`、`meta: {}`、`error: {code,message}`。包括 VALIDATION_ERROR (422)、DATA_CONFLICT (409)、AUTH_REQUIRED (401)、DATABASE_UNAVAILABLE (503) 及实体 NOT_FOUND (404)。不暴露 SQL / 连接凭证。
- 所有核心路由需要认证上下文。当前仅显式 development 模式使用固定本地用户，不接受客户端 user_id；production 禁止开发认证。共享 Place 可读取和创建；私有 Trip / Day / Visit / Activity 按用户隔离。
- Visit、Activity 手工创建仅接受 MANUAL source。暂未实现 AI、上传、预订和费用。

## Phase 2 当前实现

行政区录入补充（2026-09-19）：

- `GET /api/v1/regions/search?q=南京`：认证后搜索离线目录，最多 30 条，空查询返回空数组。支持中文路径与不含空格的拼音。国内只返回市级结果；区县命中会提升为所属城市并去重，省名命中返回该省的城市。海外返回国家/地区。返回 id、parent_id、name、short_name、path、pinyin、level、country_code、admin1、city、timezone、代表坐标、bbox、boundary_file。只返回存在边界的条目。
- `POST /api/v1/regions/{region_id}/place`：200，幂等返回 canonical PlaceRead；客户端只提交 region_id，无坐标输入。未知行政区返回 REGION_NOT_FOUND 404。选择只解析 Place，不创建 Visit；用户保存到访后才进入地图。
- MapPlace 增加可空 `region_id`；历史 POI 可为 null。原 `/places` 手工 API 为兼容已有调用保留，Web 不再使用坐标表单。

以下接口均位于 `/api/v1`，使用相同认证与 envelope，所有聚合仅包含当前用户的数据。

| 接口 | 参数及 data |
| --- | --- |
| GET /map/summary | scope=all（默认）/domestic/international；places_count、visited_places、upcoming_places、wishlist_places、visit_count、countries_count、unknown_country_places |
| GET /map/places | scope 同上；可选 status=visited/upcoming/wishlist；limit 默认 200、1..500，offset 默认 0；data={places,total,limit,offset} |
| GET /map/places/{place_id} | data={place,visits,visits_total,wishlist_note}；visits 按抵达时间倒序最多 20 条；无当前用户足迹或收藏返回 404 |
| POST /wishlist | body={place_id,note?}；200，返回 id/place_id/note/created_at；幂等，重复添加保留原有备注 |
| DELETE /wishlist/{place_id} | 200，data=null；幂等，不影响其他用户收藏或 Visit |
| GET /calendar/month | 必填 year=1900..2100、month=1..12；data={year,month,trips,days} |
| GET /calendar/day | 必填 date=YYYY-MM-DD；data={date,trips,visits,activities} |

MapPlace 包含 id/name、国家/行政区/城市、timezone、latitude/longitude、visit_count、upcoming_count、wishlist、last_visited_at、next_visit_at。状态可同时存在，“全部状态”的单点视觉优先级为曾至 → 将至 → 未至，列表显示全部状态。统计按 scope 计算，不受状态筛选限制；国家/地区数排除空代码。

CalendarCell 包含 date、trip_ids、places_count、visits_count、activities_count、has_memory。后者表示这一天已有抵达的访问（不把尚未发生的跨日日期当成回忆）。每日 Visit 附加 place_name/timezone；Activity 附加 place_name/timezone。日期与时区规则见 DATA_MODEL 的 Phase 2 约定。

Web 使用 CalendarDay 中 Visit/Activity 的 `place_id` 与 `place_name` 构建“城市 → 到访与活动”树。API 保持返回事实列表，不嵌入特定展示结构；Activity.place_id 为 null 时客户端显示为“未分配城市”。

`/places/nearby` 与 `/map/region/{region_id}` 仍为规划，未实现。

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

当前认证契约：

- `AuthProvider` 接收 provider-neutral credential，返回包含本地 `user_id`、provider 和稳定 subject 的 principal。
- 默认继续使用 development provider；显式配置 `AUTH_MODE=oidc` 时接受 `Authorization: Bearer <access-token>`。
- OIDC token 固定使用 RS256，并严格校验 JWKS 签名、issuer、audience、expiry 和非空 subject；未知或未绑定 subject 不会自动注册。
- OIDC subject 只通过 `("logto", subject)` 查找已存在的 `UserIdentity`，再解析为本地 User UUID。
- 缺少、无效或过期认证返回 `AUTH_REQUIRED` 401。
- 已认证但不允许执行某类操作时返回 403。
- 访问其他用户的私有实体返回对应 `*_NOT_FOUND` 404，避免 ID 枚举。
- 客户端不得提交 `user_id`，业务查询始终使用认证上下文中的本地 User UUID。

阶段 F 的 Next.js 同源 BFF 使用 `/api/bff/{path}` 承载 Web 已使用的 FastAPI 路由。它不属于 FastAPI `/api/v1` 公共契约，也不是任意反向代理：每个 method、path 和 query key 都必须在服务端白名单中。BFF 不接受客户端 Authorization、`x-user-id`，也拒绝 query 或 JSON body 中任意层级的 `user_id`；服务端只从加密 HttpOnly session 取得 Logto access token。401 时客户端只重试一次，仍失败则进入 `/sign-in`。默认关闭开关时，Web 继续直接使用 `NEXT_PUBLIC_API_URL`。

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
