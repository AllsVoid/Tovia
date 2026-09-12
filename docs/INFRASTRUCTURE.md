# Local infrastructure

Use `docker compose` from the repository root. PostgreSQL data lives in the `postgres_data` named volume. Redis is reserved for future workers. The migration service must finish successfully before the API starts.

Do not run `docker compose down -v` unless you intend to delete local database data.
