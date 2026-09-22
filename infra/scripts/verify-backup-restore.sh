#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../.." && pwd)"
backup_dir="${1:-$repo_root/infra/backups}"
project_name="${TOVIA_COMPOSE_PROJECT:-}"

compose=(docker compose -f "$repo_root/compose.yaml")
if [[ -n "$project_name" ]]; then
  compose=(docker compose -p "$project_name" -f "$repo_root/compose.yaml")
fi

if [[ "$("${compose[@]}" ps --status running --services db)" != "db" ]]; then
  echo "Database service is not running. Start it with: docker compose up -d db migrate" >&2
  exit 1
fi

db_user="$("${compose[@]}" exec -T db sh -c 'printf %s "$POSTGRES_USER"')"
db_name="$("${compose[@]}" exec -T db sh -c 'printf %s "$POSTGRES_DB"')"
timestamp="$(date -u +%Y%m%d-%H%M%S)"
restore_db="tovia_restore_check_${timestamp//-/_}_$$"
container_backup="/tmp/${restore_db}.dump"
backup_file="$backup_dir/tovia-$timestamp.dump"

if [[ ! "$restore_db" =~ ^tovia_restore_check_[0-9_]+$ ]] || [[ "$restore_db" == "$db_name" ]]; then
  echo "Refusing unsafe restore database name: $restore_db" >&2
  exit 1
fi

cleanup() {
  set +e
  if [[ "$restore_db" =~ ^tovia_restore_check_[0-9_]+$ ]]; then
    "${compose[@]}" exec -T db dropdb --if-exists --force -U "$db_user" "$restore_db" \
      >/dev/null 2>&1
  fi
  "${compose[@]}" exec -T db rm -f "$container_backup" >/dev/null 2>&1
}
trap cleanup EXIT

mkdir -p "$backup_dir"
"${compose[@]}" exec -T db pg_dump \
  -U "$db_user" -d "$db_name" --format=custom --file="$container_backup"
"${compose[@]}" cp "db:$container_backup" "$backup_file" >/dev/null

"${compose[@]}" exec -T db createdb -U "$db_user" "$restore_db"
"${compose[@]}" exec -T db pg_restore \
  -U "$db_user" -d "$restore_db" --no-owner --exit-on-error "$container_backup"

source_revision="$(
  "${compose[@]}" exec -T db psql -U "$db_user" -d "$db_name" \
    --tuples-only --no-align --command='SELECT version_num FROM alembic_version'
)"
restore_revision="$(
  "${compose[@]}" exec -T db psql -U "$db_user" -d "$restore_db" \
    --tuples-only --no-align --command='SELECT version_num FROM alembic_version'
)"
restore_postgis="$(
  "${compose[@]}" exec -T db psql -U "$db_user" -d "$restore_db" \
    --tuples-only --no-align --command='SELECT PostGIS_Version()'
)"

if [[ -z "$source_revision" ]] || [[ "$source_revision" != "$restore_revision" ]]; then
  echo "Alembic revision mismatch: source=$source_revision restore=$restore_revision" >&2
  exit 1
fi
if [[ -z "$restore_postgis" ]]; then
  echo "PostGIS is unavailable in the restored database" >&2
  exit 1
fi

tables=(users user_identities trips trip_days places visits activities wishlist_items)
for table in "${tables[@]}"; do
  source_count="$(
    "${compose[@]}" exec -T db psql -U "$db_user" -d "$db_name" \
      --tuples-only --no-align --command="SELECT count(*) FROM $table"
  )"
  restore_count="$(
    "${compose[@]}" exec -T db psql -U "$db_user" -d "$restore_db" \
      --tuples-only --no-align --command="SELECT count(*) FROM $table"
  )"
  if [[ "$source_count" != "$restore_count" ]]; then
    echo "Row count mismatch for $table: source=$source_count restore=$restore_count" >&2
    exit 1
  fi
done

checksum="$(sha256sum "$backup_file" | cut -d ' ' -f 1)"
echo "Backup and restore verification passed"
echo "Backup: $backup_file"
echo "SHA256: $checksum"
echo "Alembic: $restore_revision"
echo "PostGIS: $restore_postgis"
