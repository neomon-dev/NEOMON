# M13 Phase 0.1 Database Remediation Report

## Scope and baseline

The local development database reported revision `20261114_0015`. The ORM
comparison against a fresh database at that revision found 70 differences:

- `report_versions` was used by the ORM and application code but was absent
  from the historical migration chain. It could already exist when startup
  `create_all()` had run.
- `investigations.workspace_id` and `investigations.owner_id` lacked the
  foreign keys declared by the ORM.
- Several indexes were absent, including notification timestamps/workspaces,
  evidence annotation authors, research gap type, review request ownership and
  targets, workspace activity fields, invitation inviters, and query-history
  relationships.
- Several historical index names differed from current ORM-generated names.
- Research-gap analysis and gap timestamps were nullable in metadata but
  non-nullable in the migrated schema.
- SQLite UUID/string rendering and client-default representation were dialect
  differences, not data-integrity defects.

## Corrective migration

Migration `20261114_0016_schema_alignment`:

- Creates `report_versions` for clean databases with its foreign keys and
  indexes.
- Preserves and normalizes a pre-existing `report_versions` table rather than
  recreating or deleting it.
- Adds the two missing investigation foreign keys with `SET NULL`.
- Adds missing indexes and replaces legacy index names with the ORM contract.
- Keeps `report_versions` and its data during downgrade because the table may
  have been created outside Alembic before this remediation.

No historical migration was edited, deleted, stamped, or skipped.

## Reproducibility results

| Scenario | Result |
|---|---|
| Empty SQLite database -> head | PASS |
| Revision `20261114_0014` -> head | PASS |
| Head -> `20261114_0015` -> head | PASS |
| Existing `report_versions` table -> head | PASS on disposable database |
| Fresh head metadata comparison | PASS, zero differences |
| `alembic check` after head | PASS, no new operations |
| Existing development database | BLOCKED |

The development database is not certified because `PRAGMA integrity_check`
reports malformed pages and the attempted upgrade fails before revision
advancement while SQLite handles its temporary table. The database was not
reset, stamped, dropped, or replaced. A pre-migration copy was retained in the
session workspace for recovery analysis.

## Remaining verification

PostgreSQL and Redis/Docker validation remain NOT TESTED because Docker is
unavailable. The malformed development database requires an approved recovery
process before this phase can pass its existing-database acceptance gate.
