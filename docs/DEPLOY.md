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
         -> poll-deploy.sh: is there a deploy/* tag newer than the last deployed?
         -> yes: DEPLOY_REF=<tag> deploy/deploy.sh   (health-check + auto-rollback)
         -> record the tag as handled
```

Pushing the `deploy/*` tag is the approval. Nothing reaches production without it.

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

### Failure alerts (Module 5.1)

If a deploy fails, `deploy.sh` rolls back but the only record is the journal.
`OnFailure=` on `tracey-deploy.service` runs `tracey-deploy-notify@.service`
(as root, so it can read the journal), which calls `deploy/notify-failure.sh`.
That script sends an email and/or a chat webhook, whichever is configured in
`/etc/tracey-deploy/notify.env`.

```bash
# 1. channel config (root-only — may hold a secret webhook URL)
sudo mkdir -p /etc/tracey-deploy
sudo cp ~/tracey-deploy/deploy/notify.env.example /etc/tracey-deploy/notify.env
sudo chmod 600 /etc/tracey-deploy/notify.env
sudo "${EDITOR:-vi}" /etc/tracey-deploy/notify.env      # set NOTIFY_EMAIL and/or NOTIFY_WEBHOOK

# 2. install the notifier unit (render the script path)
sed "s|REPLACE_WITH_HOME|$HOME|" \
    ~/tracey-deploy/deploy/tracey-deploy-notify@.service \
  | sudo tee /etc/systemd/system/tracey-deploy-notify@.service

# 3. re-render tracey-deploy.service so it now carries OnFailure=
sed -e "s|REPLACE_WITH_id_un|$(id -un)|" -e "s|REPLACE_WITH_HOME|$HOME|" \
    ~/tracey-deploy/deploy/tracey-deploy.service \
  | sudo tee /etc/systemd/system/tracey-deploy.service
sudo systemctl daemon-reload

# 4. test — run the notifier directly, then exercise the templated unit
sudo ~/tracey-deploy/deploy/notify-failure.sh tracey-deploy.service
sudo systemctl start tracey-deploy-notify@tracey-deploy.service
sudo journalctl -u 'tracey-deploy-notify@*' -n 20 --no-pager
```

To verify the full chain end-to-end, push a deploy tag on a commit you know
breaks boot (e.g. a bad import), let it deploy + auto-rollback, and confirm the
alert arrives. Then push a good tag.

