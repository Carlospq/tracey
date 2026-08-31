# Running the tests

The app's models are `managed = False` against a pre-existing MySQL schema, so
the test suite runs `pytest` against a **real MySQL** loaded with
`tests/schema.sql` (a `mysqldump --no-data` of production, DEFINER clauses
stripped). `conftest.py` drops/recreates `test_<DB_NAME>` and loads that file
once per session.

## CI

The `test` job in `.github/workflows/ci.yml` starts a `mysql:8.0` service and
runs `pytest`. Nothing to do.

## Locally

You need a throwaway MySQL. Easiest is Docker:

```bash
docker run -d --name tracey-test-mysql \
  -e MYSQL_ROOT_PASSWORD=test -e MYSQL_DATABASE=tracey_test \
  -p 3306:3306 mysql:8.0

pip install -r requirements-dev.txt

DB_NAME=tracey_test DB_USER=root DB_PASSWORD=test DB_HOST=127.0.0.1 DB_PORT=3306 \
SECRET_KEY=test DEBUG=False \
  pytest
```

`conftest.py` creates and loads `test_tracey_test` from `tests/schema.sql`; your
own DB is never touched.

Stop it with `docker rm -f tracey-test-mysql` when done.

## Updating the schema

When the production schema changes (remember: by hand, not migrations — see
`docs/MANUAL_en.md` §1.3), refresh the fixture:

```bash
mysqldump --no-data --skip-comments --routines --events -u <user> -p <DB_NAME> \
  | sed -E 's/DEFINER=`[^`]+`@`[^`]+` //g' > tests/schema.sql
```

## Adding tests

`pytest.ini` collects `test_*.py` under `apps/`. Mark anything that touches the
database or renders a page with `@pytest.mark.django_db` (or a module-level
`pytestmark`). Keep tests runnable against an **empty** schema — load only the
rows a test needs via fixtures.
