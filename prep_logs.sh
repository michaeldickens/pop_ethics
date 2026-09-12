#!/bin/bash
scp root@mdickens.me:/var/lib/pop-ethics/quiz-log.jsonl ./ && \
    python analyze_logs.py quiz-log.jsonl --html /tmp/report.html && \
    python analyze_logs.py quiz-log.jsonl --html /tmp/report-unfamiliar.html --familiarity no && \
    python analyze_logs.py quiz-log.jsonl --html /tmp/report-familiar.html --familiarity heard,explain
