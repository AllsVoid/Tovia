# Tovia 所至 — 数据模型 v0.1

## Phase 1 实现约定

- 已实现 User、Trip、TripDay、Place、Visit、Activity。其余实体保留为后续设计。
- 全部主键 UUID；timestamp 使用 TIMESTAMPTZ；date 表示当地日历日期。新增 `Trip.timezone`（IANA 名称，默认 UTC），配合 `Place.timezone` 保留旅行时区；跨时区访问以 Place 时区呈现。
- `Trip.cover_photo_id` 推迟到 Photo migration，避免未约束的悬空引用。当前 visibility 仅支持 PRIVATE。
- `Trip.slug` 在同一用户内唯一；省略时自动生成。TripDay 的 date 在已设定的 Trip 日期范围内；缩短 Trip 日期范围时也检查已有 Day。
- Place 使用 `GEOGRAPHY(Point,4326)` 和 GiST 索引，geometry 可空。SQLAlchemy 属性 `metadata_` 映射数据库列 `metadata`，API 仍使用 metadata。地点由用户手动创建，不提供共享 Place 的任意修改/删除入口；供应商 ID 非空时唯一，osm_id 使用含类型的标识（如 `node/123`）。无供应商 ID 的地点不做模糊自动合并。
- Visit 可独立于 Trip；不同 Visit 可关联同一 Place。复合外键保证 Visit 的 Trip 属于同一 user，Visit / Activity 的 TripDay 属于指定 Trip。
- 删除 Trip 时，服务先解除 Visit 的 trip_id / trip_day_id，再删除 Trip；TripDay / Activity 随容器删除。删除 Day 仅解除 Visit 的 trip_day_id。数据库 RESTRICT 外键阻止绕过服务误删访问事实。
- 时间范围和 confidence 0..1 有数据库 CHECK；confidence 为 Numeric，Python 为 Decimal。
- source 枚举保留完整设计值；当前手工 API 仅接受 MANUAL，没有 AI 写入路径。
- avatar 编辑、公共可见性、媒体引用属于后续阶段；本阶段提供可替换开发 AuthProvider。

## Phase 2 实现约定

- 行政区选择新增 `Place.metadata.region_id`（例如南京市 `cn:3201`），对应版本化边界目录；国内新建足迹只解析市级 region_id，区县仅作为搜索别名并提升到父级城市。旧 Place 可无此字段。行政区 Place 的 UUID 由命名空间与 region_id 确定，数据库冲突保护保证多次选择/并发选择不产生多个同城 Place；每次访问仍独立保存。无新增表或迁移。
- 地图从目录读取 Polygon/MultiPolygon；内部 location 仍是 WGS84 代表坐标，不向用户展示输入框。高亮不向父行政区传播，不代表访问其所有下级地区。已有 POI 按坐标投影到所在市，仅聚合显示，访问次数仍来自原 Visit。国外旧地点按所属国家显示。
- Activity 继续使用可空 `place_id` 兼容历史数据；Web 新建活动时从当前 Trip 的 Visit 城市中必选一个 Place。日历以 `place_id` 将 Visit 与 Activity 组织为城市树；空 `place_id` 进入“未分配城市”，不自动猜测关联。

- `0003_wishlist` 增加 WishlistItem：UUID id、user_id、place_id、priority（默认 0，暂未开放排序）、note、created_at。`(user_id, place_id)` 唯一；删除用户级联，地点外键 RESTRICT。

- 未至是独立收藏，不以虚构 Visit 表示。曾至根据 `visited_at <= now`，将至根据 `visited_at > now` 计算。同一 Place 可同时有历史访问、未来访问和收藏；所有访问计数来自 Visit。
- 地图中的地点必须有当前用户的 Visit 或 WishlistItem。国内范围为 CN/HK/MO/TW；海外为其他非空代码；未设置国家/地区仅在全部范围展示。
- Trip 的日期范围包含首尾日。Visit 按 Place.timezone 投影到当地日期，正时长记录的 ended_at 为排他边界；无 ended_at 或零时长仅占抵达当天。午夜离开不占下一天。
- 月历不依赖 Trip 才能展示 Visit。Trip 未填日期但存在 Day、Activity 或 Visit 时，相关日期仍展示容器。归档旅行仍保留历史日历。每日 places_count 对 Visit / Activity 的 place_id 去重。
- 访问录入表单按浏览器本机时区解释 datetime-local，转换为 UTC ISO 时间后提交；页面明确显示输入时区。详情与日历按地点时区显示访问，Activity 按 TripDay 日期归属、Trip 时区显示时间。

## v0.3 阶段 B 实现约定

- `0004_user_identity` 增加 UserIdentity，只保存本地 User UUID、provider、稳定 provider subject 和创建时间。
- `(provider, provider_subject)` 全局唯一；同一映射重复绑定到同一用户时幂等，绑定到另一用户时拒绝。
- 不以 email 作为身份主键，也不在本表复制 Logto 用户资料。删除本地 User 时级联删除映射。
- 本阶段只允许运维命令显式绑定已有 User；未知用户不会被创建，运行时认证仍只使用 development provider。

## v0.3 资料导出与账户删除约定

- JSON 导出版本为 `schema_version: "1.0"`，包含 User、Trip、TripDay、Visit、Activity、被这些记录或 WishlistItem 引用的 Place，以及 WishlistItem；实体 UUID 与关联 UUID 保持不变。导出为只读快照，不含 Logto token 或 M2M secret。
- 账户删除只允许已绑定的 Logto 身份。用户需重新登录；API 额外要求当前 access token 的 `iat` 不早于 5 分钟。服务端使用单独配置的 M2M 凭据调用 Logto Management API；浏览器不访问该 API。
- 外部身份删除成功后，Tovia 在一个数据库事务内先解除 Visit 对 Trip/TripDay 的容器引用，再删除 User；用户的 Trip、TripDay、Activity、Visit、WishlistItem 和 UserIdentity 随数据库级联清理，Place 保留为共享规范地点。
- Management API 失败时不删除本地数据。若身份已删除而本地事务失败，接口返回 `ACCOUNT_DELETION_INCOMPLETE` 并写入审计日志，需要运维介入；应用不得静默降级或泄漏 provider 响应。

## v0.4 Booking / Expense 实现约定

- `0005_finance` 添加 bookings / expenses；UUID 主键、user_id、可空 trip_id / activity_id、created_at / updated_at（TIMESTAMPTZ）以及从 1 开始的 version。Activity 新增 `(id, trip_id)` 唯一约束，支持关联的复合外键。
- Booking：type=FLIGHT/TRAIN/BUS/HOTEL/TICKET/RESTAURANT/OTHER；status=PLANNED/CONFIRMED/COMPLETED/CANCELLED（默认 CONFIRMED）；title、provider_name、reference_no、必填 start_at、可空 end_at、开始 timezone 与 end_timezone、可空 origin_place_id / destination_place_id、address、amount / currency、note。结束时间不早于开始时间。金额和币种一起填写或一起留空。
- Expense：可空 trip_day_id / place_id / merchant，category（默认 OTHER，可自定义 64 字符）、original_amount / original_currency、可空 settled_amount / settled_currency / exchange_rate / payment_method、必填 occurred_at、timezone、note。结算金额/币种成对；汇率必须为正且需有结算数据，含义为“结算币单位 / 原币单位”，只保存用户提供值，不自动计算或纠正实际账单。
- 金额为 Numeric(18,4)，范围 `[0, 10^14)`；汇率 Numeric(18,8)，范围 `(0,10^10)`。输入接受十进制字符串或整数，拒绝浮点、NaN/Infinity、负数、超范围或超精度值；JSON 输出金额字符串。币种按 schema 中支持的大写 ISO 4217 代码校验，不自动舍入。
- TripSummary 的 booking_count 包含所有预订状态。original_totals 按原币种汇总所有费用；paid_totals 和 categories 对每笔费用优先用 settled_amount/settled_currency，否则用 original_amount/original_currency。同币种直接 Decimal 加法；跨币种分别展示，不提供虚构统一总额。零结算值有效，不能回退到原币。Booking.amount 不计入任何费用合计。
- Booking/Expense 可独立于 Trip。activity_id 或 Expense.trip_day_id 有值时必须有 Trip；数据库约束 Trip 属于相同 user、Activity 和 TripDay 属于同一 Trip。Activity 与账目所属旅行日是独立链接，活动移动日期不改写费用实际时间/旅行日。
- 删除 Trip：保留用户账目，清空 trip_id / activity_id 及 Expense.trip_day_id，递增 version。删除 TripDay：清空费用 trip_day_id，同时解除随之删除的 Activity 链接；删除 Activity：只清空账目的 activity_id。相关用户/Place/时间/金额均保留。Place 外键 RESTRICT。删除 User 时先解除容器链接，再随用户级联删除全部账目。
- 新增/更改预订与费用不创建 Visit、Activity 或改变 Trip 状态；不把预订价格自动生成消费。Document/raw_data/source_document_id 等文件及 AI 字段推迟到对应版本，避免无外键的来源引用。
- 新导出 `schema_version: "1.1"` 包含 bookings、expenses 以及其引用的 Place；校验器检查金额、重复 ID、所有权和所有关联，继续接受不含账目的 1.0 文件。

## 1. 核心概念

### Place
现实世界中的地理实体。

### Visit
某个用户在某个时间访问某个 Place 的事实。

### Trip
一段旅行的逻辑容器。

### TripDay
Trip 内的日期结构。

### Activity
某一天的计划 / 实际活动。

### Booking
预订信息。

### Document
原始文档。

### Photo
照片与 EXIF。

### Expense
消费。

### ImportCandidate
AI/OCR 产生、尚未确认的结构化数据。

---

## 2. 关键关系

```text
User
 |
 +-- Trip
 |    +-- TripDay
 |    |    +-- Activity
 |    +-- Booking
 |    +-- Expense
 |    +-- Photo
 |    +-- Note
 |
 +-- Visit ---- Place
 |
 +-- WishlistItem ---- Place
 |
 +-- ImportJob
      +-- ImportCandidate
```

---

## 3. User

```text
id UUID PK
display_name
avatar_url
timezone
locale
created_at
updated_at
```

---

## 4. UserIdentity

```text
id
user_id
provider
provider_subject
created_at
```

约束：`(provider, provider_subject)` 唯一，`user_id` 外键指向 User 并在用户删除时级联。

---

## 5. Trip

```text
id
user_id
title
slug
status
start_date
end_date
cover_photo_id
summary
visibility
created_at
updated_at
```

status:

- IDEA
- PLANNING
- BOOKED
- TRAVELING
- COMPLETED
- ARCHIVED

---

## 6. TripDay

```text
id
trip_id
date
title
note
sort_order
```

唯一约束：

```text
(trip_id, date)
```

---

## 7. Place

```text
id
canonical_name
local_name
country_code
admin1
admin2
city
timezone
location GEOGRAPHY(Point, 4326)
geometry nullable
osm_id nullable
google_place_id nullable
amap_id nullable
metadata jsonb
created_at
```

---

## 8. Visit

```text
id
user_id
trip_id nullable
trip_day_id nullable
place_id
visited_at
ended_at nullable
source
confidence nullable
note
created_at
```

source:

- MANUAL
- PHOTO
- BOOKING
- IMPORT
- GPS
- AI

---

## 9. Activity

```text
id
trip_id
trip_day_id
place_id nullable
type
title
start_at nullable
end_at nullable
status
sort_order
note
source
created_at
updated_at
```

type 示例：

- VISIT
- TRANSPORT
- FOOD
- HOTEL
- EVENT
- FREE_TIME
- OTHER

status:

- CANDIDATE
- PLANNED
- CONFIRMED
- COMPLETED
- SKIPPED

---

## 10. Booking

```text
id
user_id
trip_id nullable
type
title
provider_name
reference_no
start_at
end_at
origin_place_id nullable
destination_place_id nullable
address
currency
amount
raw_data jsonb
source_document_id nullable
created_at
updated_at
```

---

## 11. Document

```text
id
user_id
trip_id nullable
type
storage_key
mime_type
original_filename
sha256
ocr_text nullable
created_at
```

---

## 12. Photo

```text
id
user_id
trip_id nullable
trip_day_id nullable
place_id nullable
storage_key
thumbnail_key
sha256
phash
taken_at
width
height
latitude nullable
longitude nullable
exif jsonb
created_at
```

后续可将经纬度也存 geography。

---

## 13. Expense

```text
id
user_id
trip_id nullable
trip_day_id nullable
place_id nullable

merchant
category

original_amount numeric
original_currency char(3)

settled_amount numeric nullable
settled_currency char(3) nullable
exchange_rate numeric nullable

payment_method
occurred_at
source_document_id nullable
note
created_at
```

---

## 14. Note

```text
id
user_id
trip_id nullable
trip_day_id nullable
place_id nullable
title
content
created_at
updated_at
```

---

## 15. WishlistItem

```text
id
user_id
place_id
priority
note
created_at
```

---

## 16. ImportJob

```text
id
user_id
trip_id nullable
status
input_count
provider
error_message nullable
created_at
updated_at
```

---

## 17. ImportCandidate

```text
id
import_job_id
document_id nullable
candidate_type
payload jsonb
confidence
status
created_at
updated_at
```

status:

- PENDING
- CONFIRMED
- EDITED
- REJECTED

---

## 18. Media 去重

上传流程：

1. SHA256 完全去重
2. pHash 近似去重
3. 相同用户范围内判断
4. 不自动删除，仅提示“可能重复”

---

## 19. 关键索引

- `Place.location` GiST
- `Visit(user_id, visited_at)`
- `Trip(user_id, start_date)`
- `Photo(user_id, taken_at)`
- `Expense(user_id, occurred_at)`
- `Booking(user_id, start_at)`
- `ImportJob(user_id, created_at)`
