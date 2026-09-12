# Tovia 所至 — 工程规范 v0.1

## 1. Web

- TypeScript strict
- ESLint
- Prettier
- React Server Components 默认
- Client Component 仅交互需要时使用
- API data 统一经 typed client
- TanStack Query 管 server state
- Zustand 只存 UI state

---

## 2. API

- Python 3.12+
- FastAPI
- SQLAlchemy 2 typed models
- Pydantic v2
- Ruff
- MyPy
- Pytest

分层：

```text
routers/
services/
repositories/
models/
schemas/
providers/
```

禁止：

- router 直接写复杂业务
- service 直接依赖第三方 provider SDK

---

## 3. Migration

- 所有 schema 变更必须 Alembic
- 禁止手工改 production DB
- migration 必须可回滚或说明不可回滚原因

---

## 4. ID

统一 UUID。

---

## 5. Time

数据库统一存 timezone-aware timestamp。

旅行时间必须保留当地 timezone。

---

## 6. Money

禁止 float。

使用 decimal/numeric。

币种 ISO 4217。

---

## 7. Geo

内部 canonical geometry 使用 WGS84。

中国地图展示需要转换时在 provider / presentation 层处理。

---

## 8. API Errors

每个错误必须有 stable code。

例如：

```text
TRIP_NOT_FOUND
INVALID_IMPORT_CANDIDATE
UPLOAD_TOO_LARGE
```

---

## 9. Test

最低要求：

### Backend

- service unit tests
- API integration tests
- migration test
- AI schema fixture tests

### Frontend

- key component tests
- page smoke tests
- Playwright for main flow

主流程：

```text
create trip
upload booking
confirm candidate
add expense
view calendar
```

---

## 10. Commit

推荐 Conventional Commits：

```text
feat:
fix:
refactor:
docs:
test:
chore:
```

---

## 11. Feature Flags

AI 等非稳定能力建议可 feature flag。

---

## 12. Security

- no secrets in repo
- `.env.example`
- upload MIME validation
- row ownership check
- signed URLs
- sanitize filenames
- rate limit import endpoints

---

## 13. Performance

首页地图必须使用 summary API。

禁止首页加载所有 Trip 完整数据。

照片默认 thumbnail。

---

## 14. Documentation

每个新核心实体同步更新：

- DATA_MODEL.md
- API_SPEC.md
- migration
