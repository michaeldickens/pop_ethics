#!/bin/bash
scp root@mdickens.me:/var/lib/pop-ethics/quiz-log.jsonl ./ && \
    python analyze_logs.py quiz-log.jsonl --html /tmp/report.html && \
    cat quiz-log.jsonl | grep '"version": 2' > quiz-log-v2.jsonl && \
    python analyze_logs.py quiz-log-v2.jsonl --html /tmp/report-v2.html
