# Deploying ragbot

The bot runs on a GCP VM under systemd, served by gunicorn behind nginx, with
the widget embedded on a Netlify-hosted site.

---

## One-time migration after the restructure

The app moved from `Rag/ragbot/` to `ragbot/`, so the VM needs these steps once.
The gunicorn entry point is unchanged (`ragweb.wsgi:application`) — only the
working directory moves.

**1. SSH in and pull the new layout.**

```bash
gcloud compute ssh ragbot-vm --zone=asia-south1-a
```

```bash
cd ~/GenAI-Course && git checkout -- . && git pull
```

The `git checkout -- .` matters: `.pyc` files used to be committed and the pull
now deletes them, which fails if the VM has locally modified copies. It discards
working-tree changes to tracked files only.

**2. Point systemd at the new directory.** Check what the unit says now:

```bash
systemctl cat ragbot
```

Then edit `WorkingDirectory` to end in `/ragbot` instead of `/Rag/ragbot`:

```bash
sudo systemctl edit --full ragbot
```

**3. Rebuild the index in its new home** (`ragbot/var/index/`). The old
`index.faiss` and `docs.pkl` in `Rag/` are gone, and the chunk file is JSON now
rather than a pickle:

```bash
cd ~/GenAI-Course/ragbot && source .venv/bin/activate && python -m ragcore build-index
```

If the virtualenv still lives at `~/GenAI-Course/Rag/.venv`, either keep using
it by absolute path, or move it and repair the script shebangs:

```bash
mv ~/GenAI-Course/Rag/.venv ~/GenAI-Course/ragbot/.venv && sed -i "s|/Rag/\.venv|/ragbot/.venv|g" ~/GenAI-Course/ragbot/.venv/bin/* ~/GenAI-Course/ragbot/.venv/pyvenv.cfg
```

**4. Restart and check.**

```bash
sudo systemctl daemon-reload && sudo systemctl restart ragbot && curl -s localhost:8000/api/health/
```

`{"status": "ok", "index_ready": true}` means it is serving.

**5. Clean up the empty directory** once everything is confirmed working:

```bash
rm -rf ~/GenAI-Course/Rag
```

---

## Routine deploy

After the migration, shipping a change to the documents or the code is:

```bash
gcloud compute ssh ragbot-vm --zone=asia-south1-a
```

```bash
cd ~/GenAI-Course && git pull && cd ragbot && source .venv/bin/activate && python -m ragcore build-index && sudo systemctl restart ragbot
```

Skip `build-index` when only code changed — it re-embeds the whole corpus.

---

## Reference systemd unit

```ini
[Unit]
Description=ragbot
After=network.target

[Service]
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/GenAI-Course/ragbot
Environment="ANTHROPIC_API_KEY=sk-ant-..."
Environment="DJANGO_SECRET_KEY=..."
Environment="DJANGO_DEBUG=False"
Environment="DJANGO_ALLOWED_HOSTS=ragbot.YOUR-IP.nip.io,localhost,127.0.0.1"
Environment="DJANGO_CSRF_TRUSTED_ORIGINS=https://ragbot.YOUR-IP.nip.io"
Environment="CORS_ALLOWED_ORIGINS=https://your-site.com"
Environment="WIDGET_API_KEY=..."
Environment="RAG_EAGER_LOAD=1"
ExecStart=/home/YOUR_USER/GenAI-Course/ragbot/.venv/bin/gunicorn ragweb.wsgi:application --bind 127.0.0.1:8000 --workers 2 --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```

Two settings worth calling out:

- `RAG_EAGER_LOAD=1` loads the embedding model at boot instead of during the
  first request, which otherwise takes ten seconds or so.
- `--timeout 120` — the default 30s can kill a worker mid-answer on a slow call.

Secrets can live in `ragbot/.env` on the VM instead of the unit file; anything
already in the environment wins over that file.

## Static files

`widget.js` is served by Django in DEBUG. Behind nginx with `DEBUG=False`,
collect it first:

```bash
cd ~/GenAI-Course/ragbot && source .venv/bin/activate && python manage.py collectstatic --noinput
```

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| `/api/health/` returns `index-missing` | Index not built at `ragbot/var/index/` — run `build-index` |
| 503 from `/api/ask/` | Same, or the index and `chunks.json` are out of sync — rebuild |
| 401 from the widget | `WIDGET_API_KEY` doesn't match the `apiKey` in `RAGBOT_CONFIG` |
| CORS error in the browser console | The embedding site isn't in `CORS_ALLOWED_ORIGINS` |
| 400 `DisallowedHost` | Hostname missing from `DJANGO_ALLOWED_HOSTS` |
| CSRF failure on the chat page | Origin missing from `DJANGO_CSRF_TRUSTED_ORIGINS` |

Logs go to stdout, so:

```bash
sudo journalctl -u ragbot -f
```
