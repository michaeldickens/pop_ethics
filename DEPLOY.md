# Deploying the quiz with response logging (nginx + systemd)

The quiz is static HTML/JS. Logging needs one small always-on process
(`serve_quiz.py`) that accepts the answer POSTs and appends them to a file.
The clean split on a box you control is:

- **nginx** serves the two static files (fast, and it already runs).
- **`serve_quiz.py`** runs as a systemd service bound to `127.0.0.1`, handling
  only `POST /log`. nginx reverse-proxies that one path to it.

This keeps the Python process off the public internet, restarts it on crash,
and starts it on boot. Paths below assume the quiz lives at
`https://your-domain/pop-ethics/`; adjust to taste.

## 1. Put the files on the server

```bash
cd /var/www
git clone https://github.com/michaeldickens/pop_ethics.git
sudo mv pop_ethics pop-ethics

# The service writes the log as www-data, so that user must own the directory.
sudo chown -R www-data:www-data /var/www/pop-ethics
```

The client posts to `LOG_ENDPOINT="log"` (relative to the page, set near the
top of `population-ethics-quiz.js`), so serving the quiz at `/pop-ethics/`
makes the browser POST to `/pop-ethics/log`. Nothing to change in the JS.

## 2. Run the logger as a systemd service

Create `/etc/systemd/system/pop-ethics.service`:

```ini
[Unit]
Description=Population ethics quiz - response logging endpoint
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/pop-ethics
ExecStart=/usr/bin/python3 /var/www/pop-ethics/serve_quiz.py \
    --host 127.0.0.1 --port 8137 \
    --log /var/www/pop-ethics/quiz-log.jsonl
Restart=on-failure
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pop-ethics
sudo systemctl status pop-ethics        # should be "active (running)"
```

## 3. Point nginx at it

Inside the `server { ... }` block for your domain (the one that already
terminates TLS), add:

```nginx
# Static quiz files
location /pop-ethics/ {
    root  /var/www;                          # files live in /var/www/pop-ethics/
    index population-ethics-quiz.html;
    try_files $uri $uri/ =404;
}

# The one dynamic path: forward the answer POSTs to the logger.
# Exact match, so it wins over the prefix location above.
location = /pop-ethics/log {
    proxy_pass http://127.0.0.1:8137/log;
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
}
```

`X-Forwarded-For` is what carries the visitor's real IP to the logger;
without it every row would read `127.0.0.1` (nginx itself). Then:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

Visit `https://your-domain/pop-ethics/`, take the quiz to the end, and:

```bash
tail -f /var/www/pop-ethics/quiz-log.jsonl
```

should show one JSON line appear when you hit the verdict.

## 4. Reading the log

One JSON object per line (JSONL), so ordinary tools work:

```bash
wc -l quiz-log.jsonl                                   # how many completed takes
tail -n 20 quiz-log.jsonl | python3 -m json.tool       # inspect the latest
# group takes by visitor IP (rough - see caveat below):
python3 -c "import json,collections,sys; \
c=collections.Counter(json.loads(l)['ip'] for l in open('quiz-log.jsonl')); \
[print(n,ip) for ip,n in c.most_common()]"
```

Each line carries `time`, `ip`, `remote_addr`, `user_agent`, and the
`submission` (`code`, the decoded `answers` map, and the page URL). The `code`
is the same string the share link uses, so pasting it into
`https://your-domain/pop-ethics/#a=<code>` replays that person's exact result.

**Caveat on IP:** it's a convenience for spotting the same person, not proof.
People behind the same NAT (household, office, campus) share one IP, mobile
users' IPs rotate, and a client can forge `X-Forwarded-For`. Good enough for
"roughly how many repeat takers"; not an identity.

## 5. Housekeeping (optional)

Keep the log from growing forever with logrotate. Create
`/etc/logrotate.d/pop-ethics`:

```
/var/www/pop-ethics/quiz-log.jsonl {
    weekly
    rotate 12
    compress
    missingok
    notifempty
    copytruncate
}
```

`copytruncate` matters here: the service holds the file open, so rotating in
place (rather than renaming) avoids having to restart it.

## Notes

- **No CORS needed:** the page and `/log` are the same origin.
- **Privacy:** you're logging IP addresses, which are personal data in some
  jurisdictions. If the quiz is public, a line in a privacy note is worth it.
- **Disabling logging:** set `LOG_ENDPOINT=""` at the top of the JS, or just
  stop the service — the client's POST fails silently and the quiz is
  unaffected.
