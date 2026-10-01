# Tovia 文档

项目文档统一维护在本目录。根目录 README 为项目入口，AGENTS.md / CLAUDE.md 保留在各自作用目录供编码工具读取。

当前业务交付：v0.4 手工预订与费用，范围及验证记录见 [VERSION_0_4.md](VERSION_0_4.md)。v0.3 待完成的真实环境审查按用户要求暂不收口。

## 产品与设计

- [项目概览](OVERVIEW.md)
- [产品需求 PRD](PRD.md)
- [系统架构](ARCHITECTURE.md)
- [数据模型](DATA_MODEL.md)
- [API 约定](API_SPEC.md)
- [信息架构与交互](UX_IA.md)
- [MVP Roadmap](MVP_ROADMAP.md)
- [AI / OCR 流程设计（后续阶段）](AI_PIPELINE.md)

## 开发与运维

- [工程规范](ENGINEERING.md)
- [本地开发与验收](DEVELOPMENT.md)
- [本次初始化验证记录](VERIFICATION.md)
- [本地基础设施](INFRASTRUCTURE.md)
- [异步任务](WORKERS.md)
- [共享合同与 Schema](SCHEMAS.md)
- [编码代理约束](../AGENTS.md)

当前交付范围包括基础设施、核心旅行数据、地图与日历、身份与数据维护，以及 v0.4 手工预订和费用。旅行详情可维护地点、访问、每日安排、活动与账目；媒体与 AI 留待后续版本。
