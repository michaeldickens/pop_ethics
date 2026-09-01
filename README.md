## Population ethics quiz

The quiz consists of a single HTML file and a single JavaScript import.

Relevant files:

- `population-ethics-quiz.html`: First page and entry point for the quiz.
- `population-ethics-quiz.js`: Contains all the business logic, including every question and every possible end result. Calculates inconsistencies, determines bullets bitten, and includes text for rendering questions and answers.
- `serve_quiz.py`: Tiny standard-library server that serves the quiz and appends one JSON line per completed run to a log file.
- `analyse_logs.py`: Summarises that log — who answered what, the modal answer and what the quiz says back to it, which conflicts and bullets people hit, and how the answers hang together. Prints markdown; `--html` writes the same report as a self-contained page with charts. Defaults to a public mode that drops runs whose taker declined consent and prints nothing identifying; `--mode private` keeps everything and stamps the report do-not-share.
- `review_views.py`: Script that generates `views-review.md` using the contents of `population_ethics_views.py`.
- `population_ethics_views.py`: List of views on population ethics that have been discussed by philosophers, that someone might reasonably endorse, or that tease a particular answer out of the quiz. A view comprises a name and a list of answers for each quiz question. This file was originally AI-generated, but I manually vetted most of the views. (As of an earlier commit, I had manually vetted all of them, but then I asked the AI to make some changes and I haven't done another comprehensive review.)
- `views-review.md`: A human-readable list of views on population ethics, how they answer each quiz question, and what conflicts or unpalatable conclusions they imply. Almost all the prose in this file was AI-generated; some of it is wrong, but fixing it is a low priority.
