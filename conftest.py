"""pytest bootstrap for traceyDB.

The app's models are `managed = False` and point at a pre-existing MySQL schema,
so Django's test runner cannot build the schema itself. Instead we drop/recreate
the test database and load `tests/schema.sql` (a `mysqldump --no-data` of prod,
DEFINER clauses stripped) once per session.

Needs a reachable MySQL — CI provides a service container; locally, point the
DB_* env vars at a throwaway MySQL (see docs/TESTING.md).
"""
from pathlib import Path

import pytest

SCHEMA_SQL = (Path(__file__).parent / "tests" / "schema.sql").read_text(encoding="utf-8")


def _connect(cfg, **extra):
    import MySQLdb

    return MySQLdb.connect(
        host=cfg["HOST"],
        port=int(cfg["PORT"] or 3306),
        user=cfg["USER"],
        passwd=cfg["PASSWORD"],
        **extra,
    )


@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker):
    from MySQLdb.constants import CLIENT
    from django.conf import settings
    from django.db import connections

    cfg = settings.DATABASES["default"]
    test_db = f"test_{cfg['NAME']}"

    # 1. build the test database from the raw schema dump
    conn = _connect(cfg, client_flag=CLIENT.MULTI_STATEMENTS)
    try:
        cur = conn.cursor()
        cur.execute(f"DROP DATABASE IF EXISTS `{test_db}`")
        cur.execute(f"CREATE DATABASE `{test_db}` DEFAULT CHARACTER SET utf8mb4")
        cur.execute(f"USE `{test_db}`")
        cur.execute(SCHEMA_SQL)
        while cur.nextset():
            pass
        conn.commit()
    finally:
        conn.close()

    # 2. point Django at the test DB — and drop any connection that was already
    #    opened against the original name, so the next query reconnects.
    cfg["NAME"] = test_db
    cfg.setdefault("TEST", {})["NAME"] = test_db
    connections["default"].close()

    with django_db_blocker.unblock():
        yield

    connections["default"].close()
    conn = _connect(cfg)
    try:
        conn.cursor().execute(f"DROP DATABASE IF EXISTS `{test_db}`")
        conn.commit()
    finally:
        conn.close()
