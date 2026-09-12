# Tovia 所至 — 产品与工程文档

Phase 0 → Phase 1 已初始化：Next.js Web、FastAPI、PostgreSQL / PostGIS、Alembic、Docker Compose 和核心旅行 CRUD。

启动：在仓库根目录复制 `.env.example` 为 `.env`，运行 `docker compose up --build -d`。
Web 使用 `http://localhost:3000`，API 文档使用 `http://localhost:8000/docs`。
详细配置、验证方式及当前边界见 [开发指南](DEVELOPMENT.md) 和 [文档索引](README.md)。

> 凡我所至，皆有所记。

Tovia 是一个以 **地图、时间、旅行档案与 AI 整理** 为核心的个人旅行数据库。  
产品目标不是只解决“如何规划一次旅行”，而是贯穿：

**想去 → 规划 → 预订 → 出发 → 记录 → 回顾 → 长期归档**

首个版本以 Web MVP 形式发布，后续扩展至 iOS、Android 与微信小程序。

---

## 文档目录

1. [PRD.md](PRD.md) — 产品需求文档
2. [ARCHITECTURE.md](ARCHITECTURE.md) — 系统架构设计
3. [DATA_MODEL.md](DATA_MODEL.md) — 核心数据模型与关系
4. [API_SPEC.md](API_SPEC.md) — API 设计约定
5. [AI_PIPELINE.md](AI_PIPELINE.md) — OCR / AI 导入与规划流程
6. [UX_IA.md](UX_IA.md) — 信息架构、页面与交互
7. [MVP_ROADMAP.md](MVP_ROADMAP.md) — MVP 范围、迭代顺序与验收标准
8. [ENGINEERING.md](ENGINEERING.md) — 工程规范与代码组织
9. [AGENTS.md](../AGENTS.md) — 给 Codex/编码代理的执行说明

---

## 第一阶段技术栈

- Web: Next.js + React + TypeScript
- UI: Tailwind CSS + shadcn/ui
- Server state: TanStack Query
- Local UI state: Zustand
- Map: MapLibre GL JS
- API: FastAPI
- ORM: SQLAlchemy 2
- DB: PostgreSQL + PostGIS
- Migration: Alembic
- Cache/Queue: Redis
- Worker: Dramatiq 或 Celery
- Object Storage: S3-compatible
- Auth: 可插拔，MVP 可先使用邮箱登录
- AI: Provider abstraction
- OCR: Provider abstraction

---

## MVP 核心原则

- 地图优先，而不是 Trip List 优先
- 时间轴与地图必须互通
- Trip 是容器，但照片、地点、消费可独立存在
- AI 只生成 Candidate，不直接覆盖正式数据
- 用户始终可以查看原始凭证并手工修正
- 数据模型优先于 UI
- Web MVP 不为“一套 UI 跨全部端”而牺牲体验
