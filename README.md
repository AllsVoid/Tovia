# Tovia 所至

> 凡我所至，皆有所记。

以地图、时间和旅行档案为核心的个人旅行数据库。

当前已初始化 Phase 0 → Phase 1：Next.js、FastAPI、PostgreSQL / PostGIS、Alembic、Docker Compose 和核心旅行 CRUD。AI 功能尚未开发。

## 启动

需要 Docker 和 Docker Compose。在仓库根目录执行：

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

- [Web](http://localhost:3000)
- [API 文档](http://localhost:8000/docs)

## 项目结构

```text
apps/web          Next.js Web
apps/api          FastAPI、核心模型、Alembic migration
workers           后续异步任务
packages          共享包
infra             基础设施扩展
docs              产品、架构、工程与开发文档
```

完整文档统一维护于 [docs](docs/README.md)，包括[项目概览](docs/OVERVIEW.md)、[开发指南](docs/DEVELOPMENT.md)和[验证记录](docs/VERIFICATION.md)。编码代理约束保留在根目录 [AGENTS.md](AGENTS.md)。
