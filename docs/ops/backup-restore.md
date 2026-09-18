# Backup and restore

## Backup

```bash
pg_dump --format=custom --file=uap.dump "$DATABASE_URL"
```

Point-in-time: keep WAL archiving on the hosted Postgres (RDS/Cloud SQL). This repo does not run a standby.

## Restore exercise (retain output)

```bash
createdb uap_restore
pg_restore --dbname=postgres://uap:uap@localhost/uap_restore uap.dump
cd backend && DATABASE_URL=postgres://uap:uap@localhost/uap_restore python manage.py check
```

Expected evidence: `manage.py check` exits 0; `finance_journal` row count matches the dump.

## Rollback

```bash
python manage.py migrate finance 0027
```

Destructive schema cleanup only after a restore window.

Last local exercise: documented 2026-09-18 (dump/restore commands above; CI Postgres job is the automated role split, not a PITR drill).
