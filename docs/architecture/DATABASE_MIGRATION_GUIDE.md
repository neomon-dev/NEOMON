# NEOMON Database Migration & Schema Evolution Guide

NEOMON uses **Alembic** alongside **SQLAlchemy 2.0 Async** to manage database schema evolutions deterministically across both SQLite (local development) and PostgreSQL (production).

---

## 1. Directory Structure

- `backend/alembic.ini`: Primary configuration file pointing to migrations environment.
- `backend/migrations/env.py`: Asynchronous runner importing SQLAlchemy models (`app.models.Base.metadata`).
- `backend/migrations/versions/`: Linear migration revision history.

---

## 2. Running Migrations

All Alembic commands must be executed from within the `backend/` directory or with `cd backend`:

### Upgrading to Latest Version
```bash
cd backend
python -m alembic upgrade head
```

### Checking Current Revision
```bash
cd backend
python -m alembic current
```

### Viewing Migration History
```bash
cd backend
python -m alembic history --verbose
```

---

## 3. Creating New Revisions

When modifying models in `backend/app/models.py`:

```bash
cd backend
python -m alembic revision --autogenerate -m "describe_changes_here"
```

> [!IMPORTANT]
> Always inspect the newly generated migration file in `backend/migrations/versions/`.
> Ensure dialect neutrality: use generic types (`sa.String`, `sa.Text`, `sa.DateTime`) rather than dialect-exclusive constructs unless guarded with conditional branches.

---

## 4. Rollback & Downgrade Safety

To revert to the previous revision:
```bash
cd backend
python -m alembic downgrade -1
```

To downgrade to a specific historical revision ID:
```bash
cd backend
python -m alembic downgrade <revision_id>
```

---

## 5. Production Zero-Downtime Deployment Practices

1. **Additive Schema Changes**: Always add columns with `nullable=True` or a safe server default first.
2. **Pre-Deployment Migration**: Run `python -m alembic upgrade head` prior to spinning up new container instances.
3. **Data Backfills**: Execute heavy backfills asynchronously using `JobService` rather than locking tables inside DDL migrations.
4. **Deprecation Phase**: Once all application replicas run the new code, drop legacy columns in a subsequent release.
