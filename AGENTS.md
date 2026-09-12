# AGENTS.md — Tovia Codex Instructions

你正在开发 **Tovia 所至**。

产品定位：

> 一个以地图、时间、旅行档案与 AI 整理为核心的个人旅行数据库。

核心原则：

1. Map-first
2. Calendar-first
3. AI Candidate first, never AI auto-write
4. Preserve original documents
5. Place != Visit
6. Trip is a container, not the only source of truth
7. Use PostgreSQL + PostGIS
8. Keep architecture modular but monolithic
9. Do not over-engineer MVP

---

## Priority

严格按以下顺序：

1. Foundation
2. Core data model
3. Map
4. Calendar
5. Booking / Expense
6. Upload / Inbox
7. OCR / AI Candidate
8. Polish

---

## Required stack

Web:

- Next.js
- React
- TypeScript
- Tailwind
- shadcn/ui
- TanStack Query
- Zustand
- MapLibre GL JS

API:

- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL
- PostGIS
- Pydantic v2

Async:

- Redis
- Dramatiq or Celery

---

## First implementation task

Create the repository skeleton:

```text
apps/web
apps/api
workers
packages
infra
docs
```

Then implement:

- `/health`
- database connection
- PostGIS enable migration
- User model
- Trip model
- Place model
- Visit model
- Alembic migration
- OpenAPI
- basic Next.js shell

Do not start AI features before the core data model works.

---

## Coding constraints

- TypeScript strict
- Python type hints
- UUID ids
- timezone-aware datetime
- Decimal for money
- WGS84 internal geo
- provider abstractions
- no business logic in route handlers
- no direct third-party SDK dependency in domain services

---

## Product vocabulary

Use:

- 曾至 = visited
- 将至 = upcoming
- 未至 = wishlist

Trip statuses:

- IDEA
- PLANNING
- BOOKED
- TRAVELING
- COMPLETED
- ARCHIVED

---

## Important domain decisions

### Place

Represents a canonical geographic place.

### Visit

Represents a user's actual/planned presence at a Place.

Never infer visit count from duplicated Place rows.

### AI Import

Pipeline:

```text
Document
-> OCR
-> classification
-> structured extraction
-> ImportCandidate
-> user review
-> confirmed entity
```

AI must never directly create trusted entities without confirmation.

---

## Definition of done for MVP

A user can:

1. Create a trip
2. Add locations
3. See them on My World map
4. See the trip on calendar
5. Upload a booking screenshot
6. Review AI/OCR candidate
7. Confirm booking
8. Add an expense
9. Add photos
10. Open a completed trip and see its timeline

---

## Before coding any feature

Read:

- `docs/PRD.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_MODEL.md`
- `docs/API_SPEC.md`

When implementation requires changing domain behavior, update docs too.
