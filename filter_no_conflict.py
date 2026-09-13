#!/usr/bin/env python3
"""Filter quiz-log.jsonl to the lines whose answers hit no contradiction.

Originally written by Claude Sonnet 5.

    python3 filter_no_conflict.py quiz-log.jsonl > clean.jsonl
    python3 filter_no_conflict.py quiz-log.jsonl --file population-ethics-quiz.html

Contradictions aren't recomputed here - the quiz's own engine scores each
run's answers in a headless browser, the same way analyze_logs.py does it,
since a second implementation would drift. Needs playwright:

    python3 -m pip install --user playwright
    python3 -m playwright install chromium

A run is kept only if it triggers neither a conflict card nor an extra check
(Sen's alpha, the collapsing principle, chaining through the gap) - the two
kinds of contradiction card the results page can show. A bitten bullet alone
does not drop a run: that's a note about the answers, not a contradiction
between them. Malformed lines are skipped with a warning to stderr.
"""

import argparse
import json
import sys

from analyze_logs import Engine


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log", help="quiz-log.jsonl")
    ap.add_argument("--file", default="population-ethics-quiz.html",
                     help="the quiz page to score answers against")
    args = ap.parse_args()

    engine = Engine(args.file)
    kept, dropped, bad = 0, 0, 0
    with open(args.log, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                answers = {k: v for k, v in rec["submission"]["answers"].items()
                           if isinstance(v, str)}
                if not answers:
                    raise ValueError("no answers")
            except (ValueError, KeyError, TypeError):
                bad += 1
                print("line %d: unparseable, skipped" % i, file=sys.stderr)
                continue
            scored = engine.score(answers)
            if scored["conflicts"] or scored["extras"]:
                dropped += 1
            else:
                kept += 1
                sys.stdout.write(line if line.endswith("\n") else line + "\n")
    engine.close()
    print("kept %d, dropped %d (had a contradiction), %d unparseable"
          % (kept, dropped, bad), file=sys.stderr)


if __name__ == "__main__":
    main()
