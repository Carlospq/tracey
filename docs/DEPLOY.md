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
| DB | MySQL, **same box** (`localhost:3306`), pre-existing schema, models are `managed = False` |
| Health check | `curl http://127.0.0.1:5005/` → 200 |
| Monitoring | Grafana Cloud (Alloy agent, `alloy.service`) — see Module 6 |

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

### CI — `.github/workflows/ci.yml`

Runs on every PR and push. Installs deps on a clean machine, imports the
project, builds static, lints (informational). `main` is branch-protected:
green `django` + `lint` checks required to merge.

### CD — pull-based (`deploy/poll-deploy.sh` + `tracey-deploy.timer`)

The repo is public and the server has passwordless sudo, so we do **not** run a
GitHub self-hosted runner. Instead the server polls for a signed intent:

```
you:     merge PR to main  ->  CI green  ->  git tag -a deploy/<stamp> ; git push --tags
server:  tracey-deploy.timer fires every 2 min
         -> poll-deploy.sh: deploy/* tag newer than the last deployed?
         -> yes: are that commit's GitHub checks green? (else wait / skip)
         -> yes: DEPLOY_REF=<tag> deploy/deploy.sh   (health-check + auto-rollback)
         -> record the tag as handled
```

Pushing the `deploy/*` tag is the approval. Nothing reaches production without
it, and nothing reaches production with a red or still-running CI. The poll
script queries `api.github.com/.../commits/<sha>/check-runs` unauthenticated
(public repo); if CI is `pending`/`failed`/`unreachable` it logs once and
retries on later ticks. `REQUIRE_CI=0` on the unit bypasses the gate; the manual
`deploy/deploy.sh` path never checks CI.

**Trigger a deploy:**

```bash
git checkout main && git pull
git tag -a deploy/$(date +%Y%m%d-%H%M) -m "Deploy: <what changed>"
git push origin "deploy/$(date +%Y%m%d-%H%M)"     # use the same stamp
```

**Watch it:**

```bash
journalctl -u tracey-deploy.service -f       # deploy output, live
systemctl list-timers tracey-deploy.timer    # when it next runs
cat ~/.local/state/tracey-deploy/last-tag    # last handled tag
```

**A failed deploy** rolls back automatically (see deploy.sh), the timer unit
shows `failed` for that run, and the tag is marked handled so it does not loop.
Fix forward and push a new `deploy/*` tag.

### Install the pull-based CD (one time)

As `cpulidoq` on the server:

```bash
# 1. control clone (from Module 2; skip if it exists)
git clone --depth 1 https://github.com/Carlospq/tracey.git ~/tracey-deploy

# 2. render the service unit with THIS account's user + home, then install both.
#    (cpulidoq's home here is /home/cpulidoq@ad.unil.ch, not /home/cpulidoq)
sed -e "s|REPLACE_WITH_id_un|$(id -un)|" \
    -e "s|REPLACE_WITH_HOME|$HOME|" \
    ~/tracey-deploy/deploy/tracey-deploy.service | sudo tee /etc/systemd/system/tracey-deploy.service
sudo cp ~/tracey-deploy/deploy/tracey-deploy.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tracey-deploy.timer

# 3. confirm the rendered unit and check sudo works from a systemd context
systemctl cat tracey-deploy.service | grep -E 'User=|ExecStart='
sudo systemctl start tracey-deploy.service         # dry first tick
journalctl -u tracey-deploy.service -n 20 --no-pager

# 4. seed the marker so it does not deploy an old deploy/* tag on first real tick
mkdir -p ~/.local/state/tracey-deploy
git -C ~/tracey-deploy tag -l 'deploy/*' --sort=-creatordate | head -n1 \
  > ~/.local/state/tracey-deploy/last-tag
```

Keep `~/tracey-deploy/deploy/*.sh` executable and up to date
(`git -C ~/tracey-deploy pull` — the poll script does its own fetch, but a
manual pull keeps the scripts themselves current).

### Deploy notifications (Module 5.1)

`deploy/notify.sh <ok|fail|crash> "<summary>" [unit]` posts to Slack (and/or
email) using `/etc/tracey-deploy/notify.env` (`NOTIFY_WEBHOOK` / `NOTIFY_EMAIL`).

- **ok / fail** — sent by `poll-deploy.sh` itself after every deploy it runs, so
  you get a :white_check_mark: on success and a :rotating_light: + journal tail
  on a rolled-back failure. `poll-deploy.sh` then returns 0.
- **crash** — `OnFailure=` on `tracey-deploy.service` runs
  `tracey-deploy-notify@.service` (as root, to read the journal). This only
  fires when `poll-deploy.sh` exits non-zero *without* reporting, i.e. it died
  before it could notify (git/network/tooling error).

```bash
# 1. channel config (root-only — holds the secret webhook URL)
sudo mkdir -p /etc/tracey-deploy
sudo cp ~/tracey-deploy/deploy/notify.env.example /etc/tracey-deploy/notify.env
sudo chmod 600 /etc/tracey-deploy/notify.env
sudo "${EDITOR:-vi}" /etc/tracey-deploy/notify.env      # set NOTIFY_WEBHOOK (and/or NOTIFY_EMAIL)

# 2. render + install both units with this account's user/home
sed "s|REPLACE_WITH_HOME|$HOME|" ~/tracey-deploy/deploy/tracey-deploy-notify@.service \
  | sudo tee /etc/systemd/system/tracey-deploy-notify@.service
sed -e "s|REPLACE_WITH_id_un|$(id -un)|" -e "s|REPLACE_WITH_HOME|$HOME|" \
    ~/tracey-deploy/deploy/tracey-deploy.service \
  | sudo tee /etc/systemd/system/tracey-deploy.service
sudo systemctl daemon-reload

# 3. smoke-test each message type
sudo ~/tracey-deploy/deploy/notify.sh ok    "test: success message"
sudo ~/tracey-deploy/deploy/notify.sh fail  "test: failure message" tracey-deploy.service
sudo systemctl start tracey-deploy-notify@tracey-deploy.service   # exercises the crash path
```

To verify the full chain, push a `deploy/*` tag on a commit you know breaks boot
(e.g. `echo 'raise RuntimeError("x")' >> core/wsgi.py` on a throwaway branch,
tag it, push only the tag), watch it deploy + auto-rollback, and confirm the
:rotating_light: arrives. Then delete the tag.

### Monitoring — Grafana Cloud (Module 6)

Prompted by a real ~13min outage (2026-09-01, `gunicorn.service` failed with
`203/EXEC` after a venv rename left `bin/gunicorn`'s shebang pointing nowhere) that
went undetected until someone happened to `curl` the site. There was no metrics or
uptime alerting at all before this module.

**What it is:** [Grafana Alloy](https://grafana.com/docs/alloy/latest/) (one
collector binary, not separate `node_exporter`/`mysqld_exporter`/`blackbox_exporter`
processes — Alloy embeds equivalents of all three as components, and something in
that family is needed anyway to `remote_write` to Grafana Cloud) shipping to
**Grafana Cloud's free tier** (managed Prometheus + Grafana; Loki/logs came bundled
with the onboarding wizard for free, not originally planned, kept anyway):

- System metrics (CPU/RAM/disk) — `prometheus.exporter.unix`.
- MySQL metrics — `prometheus.exporter.mysql`, using a dedicated read-only-ish
  `alloy_exporter` MySQL user (`PROCESS`, `REPLICATION CLIENT`,
  `SELECT ON performance_schema.*` — deliberately no access to app tables).
- **Site availability — two independent probes**, `prometheus.exporter.blackbox`:
  `tracey_public` (`https://tracey.unil.ch/`, through Apache) and
  `tracey_gunicorn_local` (`http://127.0.0.1:5005/`, straight to gunicorn — the one
  that would have caught the 203/EXEC outage instantly). These must be **two
  separate `prometheus.exporter.blackbox` component instances**, not two `target{}`
  blocks in one component — Alloy doesn't disambiguate multiple targets within one
  component in the exported labels, so one silently overwrote the other's samples
  the first time this was set up.
- An alert rule (`probe_success < 1`, 1-2min `for`) on both blackbox targets, to a
  dedicated Slack contact point (a separate webhook from `deploy/notify.sh`'s — kept
  deploy notifications and monitoring alerts in different channels on purpose).

**Reference files** (`deploy/monitoring/`, NOT applied automatically — same
convention as `gunicorn.service`):
- `alloy-config.alloy` — reference copy of `/etc/alloy/config.alloy`.
- `mysql-secret.example` — template for `/var/lib/alloy/mysql-secret` (the MySQL
  DSN, chmod 600, owned by the `alloy` system user).

**Install (one-time), on `tracey.unil.ch` as `cpulidoq`:**

1. In the Grafana Cloud UI (**Connections**), run the **"Linux Server"** integration
   wizard — it gives an install command (installs the `alloy` RPM, writes
   `/etc/alloy/config.alloy`) and starts `alloy.service`.
2. **Lock down the config file** — the wizard's install command writes it
   world-readable (`644 root:root`) even though it embeds a Grafana Cloud API token
   in plain text:
   ```bash
   sudo chown root:alloy /etc/alloy/config.alloy
   sudo chmod 640 /etc/alloy/config.alloy
   ```
3. Create the MySQL monitoring user (adjust the host/CIDR — `localhost` here since
   the DB is on the same box):
   ```sql
   CREATE USER 'alloy_exporter'@'localhost'
     IDENTIFIED BY '<STRONG_PASSWORD>'
     WITH MAX_USER_CONNECTIONS 3;
   GRANT PROCESS, REPLICATION CLIENT ON *.* TO 'alloy_exporter'@'localhost';
   GRANT SELECT ON performance_schema.* TO 'alloy_exporter'@'localhost';
   FLUSH PRIVILEGES;
   ```
4. Run the Grafana Cloud **"MySQL"** integration wizard (pick the classic
   instance-metrics one, not "Database Observability" — that's a separate billed
   product). It gives a config snippet expecting a DSN in a `local.file` secret:
   ```bash
   printf 'alloy_exporter:<PASSWORD>@tcp(127.0.0.1:3306)/' | sudo tee /var/lib/alloy/mysql-secret > /dev/null
   sudo chmod 600 /var/lib/alloy/mysql-secret
   sudo chown alloy /var/lib/alloy/mysql-secret
   ```
   **No trailing newline** in that file — a plain `echo` instead of `printf` breaks
   the exporter with `Error 1102: Incorrect database name '\n'`.
5. Append (`sudo tee -a /etc/alloy/config.alloy`, never overwrite — it already holds
   the Linux Server block) the MySQL wizard's snippet, then the blackbox block from
   `deploy/monitoring/alloy-config.alloy` (two components, per the note above).
6. `sudo systemctl restart alloy`, `sudo journalctl -u alloy -n 50` — no errors
   besides the expected root-only `/var/log/*` permission-denied lines from the
   bundled log tailer (harmless, not fixed).
7. In Grafana Cloud: **Alerting → Contact points**, add a Slack contact point with
   its own Incoming Webhook. **Alerting → Alert rules**, new rule on
   `probe_success{job="integrations/blackbox"} < 1`, eval `1m`, for `1-2m`, notify
   the contact point above.

**Verify:**

```bash
sudo systemctl status alloy
sudo journalctl -u alloy -n 50 --no-pager
```

In Grafana Cloud → Explore, confirm recent data for `up{job="integrations/node_exporter"}`,
`mysql_up`, and `probe_success` (both `instance` values). Then, like Module 5.1's
notification test, break something on purpose and confirm the full alert lifecycle
in Slack — not just "no data", the actual fire-and-resolve round trip:

```bash
sudo systemctl stop gunicorn    # both probes should go red within ~1-2min
# ... confirm [FIRING:2] arrives in Slack for both tracey_public and tracey_gunicorn_local ...
sudo systemctl start gunicorn
curl -sI http://127.0.0.1:5005/
# ... confirm [RESOLVED] arrives for both ...
```

