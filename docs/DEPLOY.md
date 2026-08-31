# traceyDB — Deployment

## The server

| | |
|---|---|
| Host | `tracey.unil.ch` / `dcsrs-tracey.ad.unil.ch` (UNIL, RHEL) |
| Web server | Apache (`httpd`) terminates TLS on :443/:80, reverse-proxies to gunicorn |
| App server | `gunicorn.service` (systemd), binds `0.0.0.0:5005`, `workers=1` |
| App user | **`tracey`** — owns `/home/tracey/tracey` (code) and `/home/tracey/tracey_prod` (venv). No sudo. |
| Deploy user | **`cpulidoq`** — passwordless sudo, may `systemctl` and `sudo -u tracey`. |
| Code | `/home/tracey/tracey` (git checkout of `main`) |
| venv | `/home/tracey/tracey_prod` → `bin/python3`, `bin/gunicorn` (use `python3` — the box has several pythons) |
| Secrets | `/home/tracey/tracey/.env` — untracked, edited by hand, **never** touched by deploys |
| DB | External MySQL, pre-existing schema, models are `managed = False` |
| Health check | `curl http://127.0.0.1:5005/` → 200 |

## How a deploy works

`deploy/deploy.sh` is run **by `cpulidoq`** (the only user with sudo). It:

1. aborts if the server working tree has uncommitted changes to tracked files;
2. `git reset --hard` to the target revision, `pip install`, `migrate`, `collectstatic` — all as `tracey`;
3. `sudo systemctl restart gunicorn`;
4. polls the health check for ~20 s;
5. if unhealthy, checks out the previous commit, restarts again, and exits non-zero.

```bash
# normal deploy (origin/main)
bash /home/tracey/tracey/deploy/deploy.sh

# deploy a specific tag
DEPLOY_REF=v1.4.0 bash /home/tracey/tracey/deploy/deploy.sh

# manual rollback to a known-good commit
DEPLOY_REF=<sha> bash /home/tracey/tracey/deploy/deploy.sh
```

> The script reads from `/home/tracey/tracey`; `cpulidoq` can run the copy that
> lives there, or their own clone — the paths inside are absolute.

## First-time / manual run

```bash
ssh cpulidoq@tracey.unil.ch
sudo -u tracey -H bash -c 'cd /home/tracey/tracey && git pull'   # get deploy/ onto the server once
bash /home/tracey/tracey/deploy/deploy.sh
```

## Migrations

Models are `managed = False`, so `migrate` only touches `django_*`, `auth_*`
(contrib) and `captcha_*` tables. Those already exist (site has run for years),
so `migrate` is normally a no-op. **Before trusting it in the script, run once:**

```bash
sudo -u tracey -H /home/tracey/tracey_prod/bin/python3 \
  /home/tracey/tracey/manage.py migrate --plan
```

If the plan is not empty / not obviously safe, deploy with `SKIP_MIGRATE=1` and
apply schema changes by hand (see `docs/MANUAL_en.md` §1.3).

## Rollback

The health check rolls back automatically. To roll back manually later:

```bash
DEPLOY_REF=<last-good-sha> bash /home/tracey/tracey/deploy/deploy.sh
```

Find the last-good SHA in `git log` or from the `deployed/*` tags (added in a
later module).

## Rotating secrets

`SECRET_KEY` and the DB password live only in `/home/tracey/tracey/.env`.
To rotate: edit the file as `tracey`, then `sudo systemctl restart gunicorn`.
Rotating `SECRET_KEY` logs everyone out (invalidates sessions) — expected.

## CI/CD pipeline

- **CI** (`.github/workflows/ci.yml`): runs on every PR and push. Installs deps
  on a clean machine, imports the project, builds static, lints (informational).
  `main` is branch-protected: green `django` + `lint` checks required to merge.
- **CD**: added in a later module — a self-hosted runner (or a pull-based
  systemd timer) invokes `deploy/deploy.sh` after a manual approval.
