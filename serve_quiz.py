#!/usr/bin/env python3
"""Tiny server for the population-ethics quiz.

Serves the quiz's two static files and logs each completed run to a file,
one JSON object per line (JSONL). No third-party dependencies - just the
standard library - so it runs anywhere Python 3.7+ does:

    python3 serve_quiz.py                    # http://localhost:8000
    python3 serve_quiz.py --port 9000
    python3 serve_quiz.py --log runs.jsonl

The client (population-ethics-quiz.js) POSTs the set of answers to /log
when someone finishes; it never POSTs when a shared results link is being
replayed, so each line is one genuine take of the quiz.

Everything identifying is recorded here rather than trusted from the
browser. Behind a reverse proxy (nginx, Caddy, Apache) the visitor's real
address arrives in X-Forwarded-For, not on the socket, so both are kept:
`ip` is the best guess at the visitor (used for spotting repeat takers) and
`remote_addr` is the raw peer. A client can forge X-Forwarded-For, so treat
`ip` as a convenience for grouping, not as proof of identity.

The log is append-only, one line per submission, so the usual tools work on
it directly:

    tail -f quiz-log.jsonl                   # watch takes arrive
    wc -l quiz-log.jsonl                      # how many takes
    python3 -m json.tool < <line>            # pretty-print one

Only the quiz's own files are served; the log, source, and everything else
in the directory stay off the web.
"""

import argparse
import datetime
import json
import os
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

# GET is limited to exactly these paths so the log file, this script, the
# .git directory, and the test suite are never exposed. Fonts load from
# Google's CDN, so the quiz needs nothing else served locally.
STATIC = {
    "/": "population-ethics-quiz.html",
    "/population-ethics-quiz.html": "population-ethics-quiz.html",
    "/population-ethics-quiz.js": "population-ethics-quiz.js",
}

MAX_BODY = 64 * 1024   # a submission is a few hundred bytes; refuse the rest


class Handler(SimpleHTTPRequestHandler):

    def do_GET(self):
        fname = STATIC.get(self.path.split("?", 1)[0])
        if fname is None:
            self.send_error(404, "Not Found")
            return
        self.path = "/" + fname
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_HEAD(self):
        fname = STATIC.get(self.path.split("?", 1)[0])
        if fname is None:
            self.send_error(404, "Not Found")
            return
        self.path = "/" + fname
        return SimpleHTTPRequestHandler.do_HEAD(self)

    def do_POST(self):
        if self.path.split("?", 1)[0].rstrip("/") != "/log":
            self.send_error(404, "Not Found")
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            self.send_error(400, "Empty body")
            return
        if length > MAX_BODY:
            self.send_error(413, "Payload Too Large")
            return
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
            if not isinstance(body, dict):
                raise ValueError("expected a JSON object")
        except (ValueError, UnicodeDecodeError):
            self.send_error(400, "Bad JSON")
            return

        record = {
            "time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "ip": self.client_ip(),
            "remote_addr": self.client_address[0],
            "user_agent": self.headers.get("User-Agent", ""),
            "submission": body,
        }
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        with self.server.log_lock:
            with open(self.server.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

        self.send_response(204)
        self.end_headers()

    def client_ip(self):
        # Honour only the first hop of X-Forwarded-For (the client) - the rest
        # are proxies. Absent it, the socket peer is the client already.
        fwd = self.headers.get("X-Forwarded-For", "")
        if fwd:
            return fwd.split(",")[0].strip()
        return self.client_address[0]

    def log_message(self, fmt, *args):
        pass   # keep stdout quiet; the JSONL file is the record


def main():
    ap = argparse.ArgumentParser(description="Serve the population-ethics quiz and log responses.")
    ap.add_argument("--host", default="0.0.0.0", help="bind address (default: 0.0.0.0)")
    ap.add_argument("--port", type=int, default=8000, help="port (default: 8000)")
    ap.add_argument("--log", default="quiz-log.jsonl", help="response log file (default: quiz-log.jsonl)")
    ap.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)),
                    help="directory holding the quiz files (default: this script's directory)")
    args = ap.parse_args()

    os.chdir(args.dir)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.log_path = os.path.abspath(args.log)
    server.log_lock = threading.Lock()

    print("Serving quiz from %s" % args.dir)
    print("Listening on http://%s:%d/" % (args.host, args.port))
    print("Logging responses to %s" % server.log_path)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
