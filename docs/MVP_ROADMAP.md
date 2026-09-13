# Tovia 所至 — MVP Roadmap v0.1

## Phase 0 — Foundation

目标：项目可运行。

- Monorepo
- Next.js
- FastAPI
- PostgreSQL
- PostGIS
- Alembic
- Docker Compose
- Auth placeholder
- OpenAPI
- CI

验收：

- web 可访问
- api `/health`
- database migration 成功

---

## Phase 1 — Core Travel Data

- User
- Trip
- TripDay
- Place
- Visit
- Activity
- CRUD API

验收：

- 可创建 Trip
- 可添加 Place
- 可关联 Visit
- 可添加 Day / Activity

---

## Phase 2 — Map + Calendar

当前已实现本阶段：地图范围/状态筛选、访问次数、地点详情与录入、独立愿望清单、月历和当天记录，以及旅行详情中的 Day / Activity 操作。实际数据库与浏览器验证见 [VERIFICATION.md](VERIFICATION.md)。下一阶段为 Phase 3；AI 仍未开发。

后续体验改进：填写旅途及行程地点后，地图自动展示相应的计划地点，减少重复手动录入。当前暂不实现；具体计划地点与 Visit 的映射规则在开发前补充，继续遵守 Place != Visit。

- 首页地图
- 国内 / 海外切换
- visited / upcoming / wishlist 状态
- 月历
- Trip 日期高亮
- Day detail

验收：

- Trip 数据可同时在地图和日历体现

---

## Phase 3 — Bookings + Expenses

- Booking CRUD
- Expense CRUD
- Trip summary
- payment method
- original / settled currency

验收：

- 可完整记录一次旅行预算与实际花费

---

## Phase 4 — Upload + Inbox

- S3 upload
- Document
- Photo
- EXIF
- SHA256
- Inbox UI
- Job status

验收：

- 可上传截图 / PDF / 照片
- 可看到处理状态

---

## Phase 5 — OCR / AI Import

- OCR Provider
- AI Provider
- Candidate
- Review UI
- confirm / edit / reject

验收：

- 上传一张机票或酒店截图
- 自动提取
- 用户确认
- 生成 Booking

---

## Phase 6 — MVP Polish

- error handling
- loading
- empty states
- responsive
- basic telemetry
- export JSON

验收：

能完成以下完整闭环：

创建 Trip → 上传 booking → AI 识别 → 确认 → 规划 → 记录 expense/photo → 地图/日历回看

---

## MVP 明确不做

- Native app
- 小程序
- 社交
- 多人协作
- 自动 GPS trace
- Public profile
- PDF Travel Book
- 复杂 AI agent
