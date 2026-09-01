#!/usr/bin/env python3
"""Summarise the response log written by serve_quiz.py.

    python3 analyse_logs.py quiz-log.jsonl                  # public report
    python3 analyse_logs.py --mode private quiz-log.jsonl    # everything, do not share
    python3 analyse_logs.py --dedupe last quiz-log.jsonl
    python3 analyse_logs.py --json stats.json -o report.md quiz-log.jsonl

The log is one JSON object per line: the server's fields (time, ip,
remote_addr, user_agent) wrapped around the client's `submission` (the
answers, the answer code, the consent choice, and a name if one was given).

Two modes, because the log holds two different kinds of thing:

  public   (default) drops every run that did not consent to public
           aggregate analysis, prints no names, addresses or user agents,
           and suppresses any cell smaller than --min-cell, since a full
           nineteen-answer profile held by one person is as identifying as
           a name. The output is meant to be publishable as it stands.

  private  keeps every run, consented or not, and prints the identifying
           detail. The report carries a do-not-share banner top and bottom.

Runs logged before the consent checkbox existed carry no consent field at
all. They are treated as non-consenting - silence is not consent - and
counted separately so the gap is visible rather than quietly closed.

One person can take the quiz more than once, on more than one device. Runs
are grouped into respondents by name when a name was given (case- and
space-insensitive), and otherwise by the (ip, user-agent) pair the server
recorded. --link-anon additionally folds an unnamed run into a named
respondent when they share a fingerprint and only one name has ever been
seen from it; it is off by default because a fingerprint is a household or
an office as often as it is a person. --dedupe then takes each
respondent's first run, their last, or all of them.

Conflicts and bullets are not recomputed here: the quiz itself scores them,
and a second implementation would drift. The page is loaded in a headless
browser and its own engine is run over each set of answers, the same way
review_views.py does it. That needs playwright:

    python3 -m pip install --user playwright
    python3 -m playwright install chromium

Without it the script still runs and still reports everything that comes
from the answers alone; the conflict and bullet sections say what is
missing instead.

To count how many people hit a card, the space of cards has to be known
first - a card nobody hit is a result too, and there is no static list of
them in the quiz. So the engine is also run over --universe random answer
profiles to enumerate the conflicts and bullets that are reachable at all.
"""

import argparse
import collections
import datetime
import itertools
import json
import math
import pathlib
import re
import sys

# ---------------------------------------------------------------------------
# The quiz's own engine, run in a browser. Everything scored comes from here.
# ---------------------------------------------------------------------------

# Shared by both probes: the results page titles each extra check with the
# <h3> of its card, so read the name off the card rather than restating it.
EXTRA_TITLE_JS = """
  const extraTitle = (x) => {
    const html = CARD_HTML[x.id](x.data, 1);
    const m = html.match(/<h3[^>]*>([\\s\\S]*?)<\\/h3>/);
    return m ? m[1] : x.id;
  };
"""

# One run's answers in, the verdict the person actually saw out. Mirrors
# showResults: answers to questions that later answers retired are pruned
# before anything is scored, so a card can never rest on a question the
# person was never shown.
PROBE = """(a) => {
  const keep = ANS;
  ANS = Object.assign({}, a);
  pruneInactive();
  const eff = ANS;
""" + EXTRA_TITLE_JS + """
  const out = {
    asked: QUESTIONS.filter(q => isActive(q)).map(q => q.id),
    answers: Object.assign({}, eff),
    missing: missingActive().length,
    conflicts: [],
    extras: [],
    bullets: bullets().map(b => b.t),
  };
  const r = analyse(eff);
  r.sets.forEach(S => {
    const ids = [...S].sort();
    const story = storyFor(S, eff);
    out.conflicts.push({
      ids: ids,
      title: story ? (typeof story.title === 'function' ? story.title(eff) : story.title) : null,
    });
  });
  out.conflicts.sort((x, y) => x.ids.join().localeCompare(y.ids.join()));
  r.extras.forEach(x => out.extras.push({id: x.id, title: extraTitle(x)}));
  ANS = keep;
  return out;
}"""

# The questions, in the order they are asked, with each answer value's own
# wording. Read off the page so a reworded option needs no edit here.
META_PROBE = """() => ({
  questions: QUESTIONS.map(q => ({
    id: q.id,
    label: q.label,
    kind: q.kind,
    conditional: !!q.when,
    opts: (q.kind === 'pair' ? PAIR_OPTS(q) : q.opts).map(o => [o[2], o[1]]),
  })),
})"""

# Which cards exist at all. Random profiles rather than a static list,
# because the quiz has no static list: bullets are pushed by imperative code
# and conflict cards are whatever the closure minimises to.
UNIVERSE_PROBE = """(spec) => {
  let s = spec.seed >>> 0 || 1;
  const rnd = () => {
    s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0;
    return s / 4294967296;
  };
  const VALS = {
    pair: ['left', 'right', 'equal', 'none'],
    principle: ['yes', 'no'],
    menu: ['A', 'B', 'Z', 'AB', 'all'],
  };
""" + EXTRA_TITLE_JS + """
  const keep = ANS;
  const conflicts = {}, extras = {}, bullets_ = {};
  for (let i = 0; i < spec.n; i++) {
    const a = {};
    QUESTIONS.forEach(q => {
      const v = VALS[q.kind];
      a[q.id] = v[Math.floor(rnd() * v.length)];
    });
    ANS = a;
    pruneInactive();
    const eff = ANS;
    const r = analyse(eff);
    r.sets.forEach(S => {
      const ids = [...S].sort();
      const story = storyFor(S, eff);
      const title = story
        ? (typeof story.title === 'function' ? story.title(eff) : story.title)
        : null;
      conflicts[ids.join('+') + '\\u0000' + (title || '')] = {ids: ids, title: title};
    });
    r.extras.forEach(x => { extras[x.id] = extraTitle(x); });
    bullets().forEach(b => { bullets_[b.t] = 1; });
  }
  ANS = keep;
  return {
    conflicts: Object.keys(conflicts).map(k => conflicts[k]),
    extras: Object.keys(extras).map(k => ({id: k, title: extras[k]})),
    bullets: Object.keys(bullets_),
  };
}"""


def strip_tags(s):
    """Card titles are HTML fragments; a report is not."""
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in [
        ("&alpha;", "alpha"), ("&beta;", "beta"), ("&middot;", "-"),
        ("&amp;", "&"), ("&rarr;", "->"), ("&larr;", "<-"),
        ("—", "--"), ("’", "'"), ("“", '"'), ("”", '"'),
        ("−", "-"),
    ]:
        s = s.replace(a, b)
    return " ".join(s.split())


# One bullet counts the person's unrankable pairs and puts the number in its
# own title, so two runs that bit the same bullet arrive under different
# strings. Numbers are folded to N, and the all-nine wording - which is the
# same bullet phrased positively - is folded in with them.
_ALL_NINE = "You judged none of the nine pairs rankable."
_ALL_NINE_KEY = "You judged N of the N pairs unrankable."


def card_key(title):
    """A stable identity for a card whose title varies from run to run."""
    t = strip_tags(title)
    if t == _ALL_NINE:
        return _ALL_NINE_KEY
    return re.sub(r"\d+", "N", t)


class Engine:
    """The quiz page, held open, answering one run at a time."""

    def __init__(self, path):
        from playwright.sync_api import sync_playwright   # deferred: optional
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        self.page = self._browser.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.goto("file://" + str(pathlib.Path(path).resolve()))
        self.page.wait_for_timeout(700)
        self.meta = self.page.evaluate(META_PROBE)
        self._cache = {}

    def score(self, answers):
        # Runs repeat: the same profile is scored once and remembered.
        key = json.dumps(answers, sort_keys=True)
        if key not in self._cache:
            self._cache[key] = self.page.evaluate(PROBE, answers)
        return self._cache[key]

    def universe(self, n, seed):
        return self.page.evaluate(UNIVERSE_PROBE, {"n": n, "seed": seed})

    def close(self):
        self._browser.close()
        self._pw.stop()


# ---------------------------------------------------------------------------
# Reading the log
# ---------------------------------------------------------------------------

class Run(object):
    """One line of the log, parsed."""

    __slots__ = ("lineno", "time", "ip", "user_agent", "name", "consent",
                 "consent_recorded", "answers", "code", "page", "identity",
                 "scored")

    def __init__(self, lineno, rec):
        sub = rec.get("submission") or {}
        self.lineno = lineno
        self.time = parse_time(rec.get("time"))
        self.ip = rec.get("ip") or rec.get("remote_addr") or ""
        self.user_agent = rec.get("user_agent") or ""
        self.name = (sub.get("name") or "").strip()
        self.consent_recorded = "consent_public_aggregate" in sub
        self.consent = bool(sub.get("consent_public_aggregate"))
        self.answers = {k: v for k, v in (sub.get("answers") or {}).items()
                        if isinstance(v, str)}
        self.code = sub.get("code") or ""
        self.page = sub.get("page") or ""
        self.identity = None
        self.scored = None

    @property
    def fingerprint(self):
        return (self.ip, self.user_agent)


def parse_time(s):
    if not isinstance(s, str):
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def read_log(path):
    """Parse the JSONL, keeping count of what could not be parsed."""
    runs, bad, blank = [], 0, 0
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                blank += 1
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                bad += 1
                continue
            if not isinstance(rec, dict) or not isinstance(rec.get("submission"), dict):
                bad += 1
                continue
            run = Run(i, rec)
            if not run.answers:
                bad += 1
                continue
            runs.append(run)
    return runs, bad, blank


def norm_name(name):
    return " ".join(name.split()).casefold()


def assign_identities(runs, link_anon):
    """Group runs by person: by name where there is one, else by fingerprint.

    With --link-anon, an unnamed run is folded into a named respondent when
    they share a fingerprint and that fingerprint has only ever carried the
    one name. A fingerprint shared by two names is a household or an office,
    so those runs stay where they are.
    """
    by_fp_names = collections.defaultdict(set)
    for r in runs:
        if r.name:
            by_fp_names[r.fingerprint].add(norm_name(r.name))

    linked = 0
    for r in runs:
        if r.name:
            r.identity = ("name", norm_name(r.name))
            continue
        names = by_fp_names.get(r.fingerprint) or set()
        if link_anon and len(names) == 1:
            r.identity = ("name", next(iter(names)))
            linked += 1
        else:
            r.identity = ("fp",) + r.fingerprint
    return linked


def group_runs(runs):
    """Respondent -> their runs, oldest first."""
    order = {}
    for i, r in enumerate(runs):
        order[id(r)] = i
    groups = collections.OrderedDict()
    for r in runs:
        groups.setdefault(r.identity, []).append(r)
    for k in groups:
        groups[k].sort(key=lambda r: (r.time or datetime.datetime.min.replace(
            tzinfo=datetime.timezone.utc), order[id(r)]))
    return groups


def select(groups, mode):
    """first-only, last-only, or all, flattened back into a list of runs."""
    out = []
    for runs in groups.values():
        if mode == "first":
            out.append(runs[0])
        elif mode == "last":
            out.append(runs[-1])
        else:
            out.extend(runs)
    return out


# ---------------------------------------------------------------------------
# Statistics. n is small; everything here is descriptive on purpose.
# ---------------------------------------------------------------------------

def _gser(a, x):
    """Regularized lower incomplete gamma, by series."""
    ap, s, d = a, 1.0 / a, 1.0 / a
    for _ in range(1000):
        ap += 1
        d *= x / ap
        s += d
        if abs(d) < abs(s) * 1e-15:
            break
    return s * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gcf(a, x):
    """Regularized upper incomplete gamma, by continued fraction."""
    tiny = 1e-300
    b, c, d = x + 1.0 - a, 1.0 / tiny, 1.0 / (x + 1.0 - a)
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def chi2_sf(x, df):
    """P(chi-square_df > x). Standard-library only, so no scipy import."""
    if df <= 0:
        return 1.0
    if x <= 0:
        return 1.0
    a, xx = df / 2.0, x / 2.0
    return 1.0 - _gser(a, xx) if xx < a + 1.0 else _gcf(a, xx)


def crosstab(pairs):
    """(rows, cols, table) from a list of (a, b)."""
    rows = sorted({a for a, _ in pairs})
    cols = sorted({b for _, b in pairs})
    table = {(a, b): 0 for a in rows for b in cols}
    for a, b in pairs:
        table[(a, b)] += 1
    return rows, cols, table


def association(pairs):
    """Bias-corrected Cramer's V, chi-square and its p, for two answers.

    Bergsma's correction, because with ~100 respondents and four-valued
    answers the uncorrected V is inflated enough to be misleading. The
    p-value uses the chi-square approximation, which wants every expected
    count at 5 or more; min_expected is returned so the report can say when
    it is not met rather than quietly pretending otherwise.
    """
    n = len(pairs)
    rows, cols, table = crosstab(pairs)
    r, k = len(rows), len(cols)
    if n < 2 or r < 2 or k < 2:
        return None
    rsum = {a: sum(table[(a, b)] for b in cols) for a in rows}
    csum = {b: sum(table[(a, b)] for a in rows) for b in cols}
    chi2, min_exp = 0.0, float("inf")
    for a in rows:
        for b in cols:
            e = rsum[a] * csum[b] / float(n)
            if e <= 0:
                continue
            min_exp = min(min_exp, e)
            chi2 += (table[(a, b)] - e) ** 2 / e
    phi2 = chi2 / n
    phi2c = max(0.0, phi2 - (r - 1) * (k - 1) / float(n - 1))
    rc = r - (r - 1) ** 2 / float(n - 1)
    kc = k - (k - 1) ** 2 / float(n - 1)
    denom = min(rc - 1, kc - 1)
    v = math.sqrt(phi2c / denom) if denom > 0 else 0.0
    df = (r - 1) * (k - 1)
    return {
        "n": n, "v": v, "chi2": chi2, "df": df, "p": chi2_sf(chi2, df),
        "min_expected": 0.0 if min_exp == float("inf") else min_exp,
        "rows": rows, "cols": cols, "table": table,
    }


def holm(ps):
    """Holm-Bonferroni adjusted p-values, in the input order."""
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    out, running = [0.0] * m, 0.0
    for rank, i in enumerate(order):
        adj = min(1.0, ps[i] * (m - rank))
        running = max(running, adj)
        out[i] = running
    return out


def median(xs):
    xs = sorted(xs)
    if not xs:
        return 0.0
    mid = len(xs) // 2
    return float(xs[mid]) if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2.0


# ---------------------------------------------------------------------------
# Named views: which catalogued position is each respondent nearest to?
# ---------------------------------------------------------------------------

def load_views():
    try:
        from population_ethics_views import VIEWS
    except Exception:
        return None
    return [(v["key"], v["name"], v["answers"]) for v in VIEWS]


def nearest_view(views, answers):
    """Best agreement over the questions this run and the view both answer."""
    best = None
    for key, name, va in views:
        shared = [q for q in answers if q in va]
        if not shared:
            continue
        agree = sum(1 for q in shared if answers[q] == va[q])
        score = agree / float(len(shared))
        if best is None or score > best[0]:
            best = (score, [(key, name)], len(shared))
        elif abs(score - best[0]) < 1e-12:
            best[1].append((key, name))
    return best


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def pct(k, n):
    return "%d (%.0f%%)" % (k, 100.0 * k / n) if n else "%d (-)" % k


def table(headers, rows):
    """A markdown table that is still readable as plain text."""
    cols = len(headers)
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i in range(cols):
            widths[i] = max(widths[i], len(str(row[i])))
    def line(cells):
        return "| " + " | ".join(
            str(c).ljust(widths[i]) for i, c in enumerate(cells)) + " |"
    out = [line(headers), "|" + "|".join("-" * (w + 2) for w in widths) + "|"]
    out += [line(r) for r in rows]
    return out


BANNER = (
    "> **PRIVATE - DO NOT SHARE.** This report was built in private mode. It "
    "includes runs whose takers did not consent to public aggregate "
    "analysis, and it prints names, IP addresses and user agents. Publishing "
    "any of it, in whole or in part, breaks a promise made on the quiz's own "
    "consent checkbox. Use `--mode public` for a report that can be shared."
)


class Report(object):

    def __init__(self, args, engine):
        self.args = args
        self.engine = engine
        self.lines = []
        self.stats = {}
        # Filled in properly once the answers section has seen the log; set
        # here because the respondents section names questions too.
        self.meta_by_id = {q["id"]: q for q in
                           (engine.meta["questions"] if engine else [])}

    def h(self, level, text):
        self.lines += ["", "#" * level + " " + text, ""]

    def p(self, text):
        self.lines += [text, ""]

    def rows(self, headers, rows):
        if not rows:
            self.p("(nothing to show)")
            return
        self.lines += table(headers, rows) + [""]

    # -- sections ---------------------------------------------------------

    def corpus(self, all_runs, kept, dropped_consent, dropped_unrecorded, bad, blank):
        self.h(2, "The corpus")
        times = [r.time for r in kept if r.time]
        rows = [
            ["Lines in the log", len(all_runs) + bad + blank],
            ["Unparseable / skipped", bad + blank],
            ["Runs read", len(all_runs)],
        ]
        if self.args.mode == "public":
            rows += [
                ["Dropped: consent declined", dropped_consent],
                ["Dropped: no consent recorded (pre-checkbox)", dropped_unrecorded],
            ]
        else:
            rows += [
                ["Of which consent declined", dropped_consent],
                ["Of which no consent recorded (pre-checkbox)", dropped_unrecorded],
            ]
        rows += [["Runs analysed", len(kept)]]
        if times:
            rows += [
                ["First run", min(times).strftime("%Y-%m-%d %H:%M UTC")],
                ["Last run", max(times).strftime("%Y-%m-%d %H:%M UTC")],
            ]
        self.rows(["", "Count"], rows)

        consented = sum(1 for r in all_runs if r.consent_recorded and r.consent)
        recorded = sum(1 for r in all_runs if r.consent_recorded)
        if recorded:
            self.p("Consent rate among runs that were asked: %s."
                   % pct(consented, recorded))
        named = sum(1 for r in all_runs if r.name)
        self.p("Gave a name: %s of all runs read." % pct(named, len(all_runs)))

        if times:
            per_day = collections.Counter(t.date().isoformat() for t in times)
            self.h(3, "Runs per day")
            self.rows(["Day", "Runs", ""],
                      [[d, per_day[d], "#" * min(per_day[d], 60)]
                       for d in sorted(per_day)])

        self.stats["corpus"] = {
            "lines": len(all_runs) + bad + blank, "unparseable": bad + blank,
            "runs_read": len(all_runs), "runs_analysed": len(kept),
            "dropped_consent_declined": dropped_consent,
            "dropped_consent_unrecorded": dropped_unrecorded,
            "consent_rate": (consented / float(recorded)) if recorded else None,
            "named_runs": named,
            "first": min(times).isoformat() if times else None,
            "last": max(times).isoformat() if times else None,
        }

    def respondents(self, groups, selected, linked):
        self.h(2, "Respondents")
        named = sum(1 for k in groups if k[0] == "name")
        repeats = {k: v for k, v in groups.items() if len(v) > 1}
        self.p(
            "%d run%s from %d distinct respondent%s (%d identified by name, "
            "%d by (IP, user-agent) fingerprint). `--dedupe %s` keeps %d of "
            "them for everything below."
            % (sum(len(v) for v in groups.values()),
               "" if sum(len(v) for v in groups.values()) == 1 else "s",
               len(groups), "" if len(groups) == 1 else "s",
               named, len(groups) - named, self.args.dedupe, len(selected)))
        if linked:
            self.p("`--link-anon` folded %d unnamed run%s into a named "
                   "respondent sharing its fingerprint." % (linked, "" if linked == 1 else "s"))
        if self.args.mode == "public" and self.args.dedupe != "all":
            self.p("Runs that did not consent were dropped before this "
                   "grouping, so \"first\" and \"last\" mean the first and "
                   "last *consenting* run - a person whose earlier run is "
                   "not in the corpus is counted from the one that is.")
        if repeats:
            sizes = collections.Counter(len(v) for v in repeats.values())
            self.p("Repeat takers: %d respondent%s took the quiz more than "
                   "once (%s)."
                   % (len(repeats), "" if len(repeats) == 1 else "s",
                      ", ".join("%d took it %d times" % (c, n)
                                for n, c in sorted(sizes.items()))))
            # By the answers rather than the code: a run logged before the
            # code was recorded carries an empty one, and two empties are not
            # an unchanged mind.
            changed = sum(1 for v in repeats.values()
                          if any(r.answers != v[0].answers for r in v[1:]))
            self.p("Of those, %d changed at least one answer between their "
                   "first and a later run." % changed)
            churn = collections.Counter()
            for v in repeats.values():
                first, last = v[0], v[-1]
                for q in sorted(set(first.answers) & set(last.answers)):
                    if first.answers[q] != last.answers[q]:
                        churn[q] += 1
            if churn:
                self.h(3, "Answers most often changed on a retake")
                ranked = sorted(churn.items(), key=lambda kv: (-kv[1], kv[0]))
                self.rows(["Question", "Respondents who changed it"],
                          [[self.qlabel(q), c] for q, c in ranked[:10]])
        else:
            self.p("No respondent appears more than once, so `--dedupe` makes "
                   "no difference to this log.")

        self.stats["respondents"] = {
            "distinct": len(groups), "by_name": named,
            "by_fingerprint": len(groups) - named,
            "repeat_takers": len(repeats), "analysed": len(selected),
            "dedupe": self.args.dedupe, "linked_anon": linked,
        }

        if self.args.mode == "private" and groups:
            self.h(3, "Per respondent (private mode only)")
            rows = []
            for key, runs in groups.items():
                # Names are matched case- and space-insensitively but shown as
                # last typed, which is what the person would recognise.
                typed = [r.name for r in runs if r.name]
                if not typed:
                    # skip anyone without a name
                    continue
                who = (typed[-1] if typed else key[1]) if key[0] == "name" \
                    else "%s / %s" % (key[1], (key[2] or "")[:60])
                rows.append([who, len(runs),
                             runs[-1].time.strftime("%Y-%m-%d") if runs[-1].time else "?",
                             runs[-1].code])
            rows.sort(key=lambda r: (-r[1], str(r[0])))
            self.rows(["Respondent", "Runs", "Latest", "Answer code"], rows)

    # -- answers ----------------------------------------------------------

    def qlabel(self, qid):
        return self.meta_by_id.get(qid, {}).get("label", qid)

    def vlabel(self, qid, value, width=24):
        """A question's own wording for one answer, short enough for a cell."""
        opts = dict(self.meta_by_id.get(qid, {}).get("opts") or [])
        if value not in opts:
            return value
        text = strip_tags(opts[value])
        return text if len(text) <= width else text[:width - 1].rstrip() + "…"

    def in_option_order(self, qid, values):
        """Answers as the quiz offers them, not as they sort."""
        known = [v for v, _ in (self.meta_by_id.get(qid, {}).get("opts") or [])]
        return ([v for v in known if v in values]
                + [v for v in sorted(values) if v not in known])

    def answers(self, runs):
        self.h(2, "Answers, question by question")
        if self.engine:
            qs = self.engine.meta["questions"]
        else:
            qs = self.fallback_questions(runs)
        self.meta_by_id = {q["id"]: q for q in qs}

        n_cond = sum(1 for q in qs if q.get("conditional"))
        if n_cond:
            self.p("Percentages are of the people who were *asked* the "
                   "question: %d of them appear only when earlier answers "
                   "give them something to bite on." % n_cond)

        stats = {}
        for q in qs:
            asked = [r for r in runs if q["id"] in self.effective(r)]
            counts = collections.Counter(self.effective(r)[q["id"]] for r in asked)
            opts = q.get("opts") or []
            known = [v for v, _ in opts]
            values = known + [v for v in sorted(counts) if v not in known]
            n = len(asked)
            head = "%s (`%s`)" % (q["label"], q["id"])
            if q.get("conditional"):
                head += " - asked of %s" % pct(n, len(runs))
            self.h(3, head)
            rows = [[strip_tags(dict(opts).get(v, v)), "`%s`" % v, pct(counts.get(v, 0), n)]
                    for v in values]
            self.rows(["Answer", "Value", "Respondents"], rows)
            stats[q["id"]] = {"label": q["label"], "asked": n,
                              "counts": dict(counts)}
        self.stats["questions"] = stats

    def fallback_questions(self, runs):
        """Without the browser, the questions are whatever the log contains."""
        seen = collections.OrderedDict()
        for r in runs:
            for q in r.answers:
                seen.setdefault(q, {"id": q, "label": q, "kind": "?",
                                    "conditional": False, "opts": []})
        return list(seen.values())

    def effective(self, run):
        """The answers the person's verdict actually rested on.

        With the engine, that is the pruned set the quiz itself scores;
        without it, the raw log, which may carry an answer to a question a
        later answer retired.
        """
        if run.scored:
            return run.scored["answers"]
        return run.answers

    # -- cards ------------------------------------------------------------

    def cards(self, runs, universe):
        self.h(2, "Conflicts")
        if not self.engine:
            self.p("*Skipped: playwright is not installed, so the quiz's "
                   "engine could not be run. `python3 -m pip install --user "
                   "playwright && python3 -m playwright install chromium` "
                   "turns this section on.*")
            return

        n = len(runs)
        # Conflict cards are identified by the answers they blame plus the
        # story told about them: the same four answers can be jointly
        # unsatisfiable for more than one reason, and the quiz shows those as
        # different cards.
        seen = collections.Counter()
        titles, idsets = {}, {}
        for r in runs:
            keys = set()
            for c in r.scored["conflicts"]:
                key = ("+".join(c["ids"]), card_key(c["title"] or "(generic card)"))
                keys.add(key)
                titles[key] = card_key(c["title"] or "(generic card)")
                idsets[key] = "+".join(c["ids"])
            for x in r.scored["extras"]:
                key = ("extra:" + x["id"], card_key(x["title"]))
                keys.add(key)
                titles[key] = card_key(x["title"])
                idsets[key] = x["id"]
            seen.update(keys)

        universe_keys = {}
        if universe:
            for c in universe["conflicts"]:
                key = ("+".join(c["ids"]), card_key(c["title"] or "(generic card)"))
                universe_keys[key] = ("+".join(c["ids"]),
                                      card_key(c["title"] or "(generic card)"))
            for x in universe["extras"]:
                key = ("extra:" + x["id"], card_key(x["title"]))
                universe_keys[key] = (x["id"], card_key(x["title"]))
        for key in seen:
            universe_keys.setdefault(key, (idsets[key], titles[key]))

        rows, hidden = [], 0
        for key in sorted(universe_keys):
            ids, title = universe_keys[key]
            c = seen.get(key, 0)
            if self.args.mode == "public" and 0 < c < self.args.min_cell:
                hidden += 1
                continue
            rows.append([title, "`%s`" % ids, c, pct(c, n)])
        rows.sort(key=lambda r: (-r[2], r[0], r[1]))
        self.rows(["Conflict card", "Answers blamed", "N", "Respondents"], rows)
        if universe:
            hit = sum(1 for k in universe_keys if seen.get(k))
            self.p("%d of the %d conflict cards reachable at all were hit by "
                   "somebody. Cards at 0 are ones the quiz can produce and "
                   "nobody here produced." % (hit, len(universe_keys)))
        if hidden:
            self.p("%d further card%s hit by fewer than %d people and "
                   "withheld: a rare card plus a set of blamed answers comes "
                   "close to naming the run behind it."
                   % (hidden, "" if hidden == 1 else "s", self.args.min_cell))

        counts = [len(r.scored["conflicts"]) + len(r.scored["extras"]) for r in runs]
        dist = collections.Counter(counts)
        self.h(3, "How many conflicts each person had")
        self.rows(["Conflicts", "Respondents", ""],
                  [[k, pct(dist[k], n), "#" * min(dist[k], 60)]
                   for k in sorted(dist)])
        self.p("Mean %.2f, median %.1f. %s came out with no conflict at all."
               % (sum(counts) / float(n) if n else 0.0, median(counts),
                  pct(dist.get(0, 0), n)))

        self.h(2, "Bullets bitten")
        bseen = collections.Counter()
        for r in runs:
            bseen.update({card_key(b) for b in r.scored["bullets"]})
        buniverse = {card_key(b) for b in (universe["bullets"] if universe else [])}
        buniverse |= set(bseen)
        rows, hidden = [], 0
        for b in sorted(buniverse):
            c = bseen.get(b, 0)
            if self.args.mode == "public" and 0 < c < self.args.min_cell:
                hidden += 1
                continue
            rows.append([b, c, pct(c, n)])
        rows.sort(key=lambda r: (-r[1], r[0]))
        self.rows(["Bullet", "N", "Respondents"], rows)
        if hidden:
            self.p("%d further bullet%s bitten by fewer than %d people and "
                   "withheld." % (hidden, "" if hidden == 1 else "s",
                                  self.args.min_cell))
        self.p("A title with `N` in it had a number filled in per run; the "
               "\"none of the nine pairs rankable\" wording is the same "
               "bullet as the unrankable-pairs row and is counted with it.")

        bcounts = [len({card_key(b) for b in r.scored["bullets"]}) for r in runs]
        bdist = collections.Counter(bcounts)
        self.h(3, "How many bullets each person bit")
        self.rows(["Bullets", "Respondents", ""],
                  [[k, pct(bdist[k], n), "#" * min(bdist[k], 60)]
                   for k in sorted(bdist)])
        clean = sum(1 for r in runs
                    if not r.scored["conflicts"] and not r.scored["extras"]
                    and not r.scored["bullets"])
        self.p("Mean %.2f, median %.1f. %s walked away with neither a "
               "conflict nor a bullet."
               % (sum(bcounts) / float(n) if n else 0.0, median(bcounts),
                  pct(clean, n)))

        self.stats["conflicts"] = {
            "%s|%s" % k: seen.get(k, 0) for k in universe_keys}
        self.stats["bullets"] = {b: bseen.get(b, 0) for b in buniverse}
        self.stats["conflict_count_distribution"] = dict(dist)
        self.stats["bullet_count_distribution"] = dict(bdist)
        self.stats["clean_runs"] = clean

    # -- views ------------------------------------------------------------

    def views(self, runs, views):
        if not views:
            return
        self.h(2, "Nearest catalogued view")
        self.p("For each respondent, the view in `population_ethics_views.py` "
               "that agrees with the most of their answers. This is a "
               "nearest-neighbour label, not a claim that anyone holds the "
               "view: ties are broken by listing every view that ties, and "
               "the agreement figure says how close the match really is.")
        hits = collections.Counter()
        scores, tied = [], 0
        for r in runs:
            best = nearest_view(views, self.effective(r))
            if not best:
                continue
            score, names, _ = best
            scores.append(score)
            if len(names) > 1:
                tied += 1
            for key, name in names:
                hits[(key, name)] += 1.0 / len(names)
        ranked = sorted(hits.items(), key=lambda kv: (-kv[1], kv[0][0]))
        rows = [[name, "`%s`" % key, "%.1f" % v,
                 "%.0f%%" % (100.0 * v / len(runs)) if runs else "-"]
                for (key, name), v in ranked
                if not (self.args.mode == "public" and v < self.args.min_cell)]
        self.rows(["View", "Key", "Respondents (ties split)", "Share"], rows)
        if scores:
            self.p("Agreement with the nearest view: mean %.0f%%, median "
                   "%.0f%%, worst %.0f%%. A low figure means the catalogue "
                   "has nothing close to that person's answers."
                   % (100.0 * sum(scores) / len(scores), 100.0 * median(scores),
                      100.0 * min(scores)))
            self.p("%s had two or more views tied for nearest; each tie is "
                   "split evenly between them, which is why the counts are "
                   "fractional." % pct(tied, len(scores)))
        self.stats["nearest_view"] = {k[0]: v for k, v in hits.items()}

    # -- associations -----------------------------------------------------

    def associations(self, runs):
        self.h(2, "Associations between answers")
        self.p(
            "Every pair of questions, scored with a bias-corrected Cramer's V "
            "(0 = no association, 1 = one answer determines the other). With "
            "a sample this size this section is *exploratory only*: it is "
            "hypothesis-generating, not hypothesis-testing. Every pair is "
            "tested, so the largest V will look impressive whether or not "
            "anything is there; the Holm-adjusted p next to the raw one is "
            "what accounts for that, and a pair whose smallest expected cell "
            "is under 5 has an unreliable p whatever it says. A pair is "
            "scored only over the respondents who were asked both questions, "
            "which is why n varies.")

        qids = [q["id"] for q in (self.engine.meta["questions"] if self.engine
                                  else self.fallback_questions(runs))]
        results = []
        for a, b in itertools.combinations(qids, 2):
            pairs = [(self.effective(r)[a], self.effective(r)[b]) for r in runs
                     if a in self.effective(r) and b in self.effective(r)]
            if len(pairs) < self.args.min_assoc_n:
                continue
            res = association(pairs)
            if res:
                results.append((a, b, res))
        if not results:
            self.p("Not enough overlapping answers to test any pair "
                   "(`--min-assoc-n` is %d)." % self.args.min_assoc_n)
            return

        adj = holm([r[2]["p"] for r in results])
        for i, (_, _, res) in enumerate(results):
            res["p_holm"] = adj[i]
        results.sort(key=lambda t: (-t[2]["v"], t[0], t[1]))

        top = results[:self.args.top_assoc]
        self.rows(
            ["Question A", "Question B", "n", "V", "p", "p (Holm)", "min exp"],
            [[self.qlabel(a), self.qlabel(b), res["n"], "%.2f" % res["v"],
              "%.3f" % res["p"], "%.3f" % res["p_holm"],
              "%.1f%s" % (res["min_expected"],
                          " !" if res["min_expected"] < 5 else "")]
             for a, b, res in top])
        self.p("`!` marks a table too sparse for the chi-square "
               "approximation; read those p-values as decoration.")

        survivors = [t for t in results if t[2]["p_holm"] < 0.05]
        self.p("%d of %d pairs survive Holm correction at 0.05."
               % (len(survivors), len(results)))

        for a, b, res in top[:self.args.crosstabs]:
            if self.args.mode == "public" and res["n"] < self.args.min_assoc_n:
                continue
            self.h(3, "%s x %s" % (self.qlabel(a), self.qlabel(b)))
            ra_vals = self.in_option_order(a, res["rows"])
            cb_vals = self.in_option_order(b, res["cols"])
            headers = ([self.qlabel(a) + " \\ " + self.qlabel(b)]
                       + [self.vlabel(b, cb, 16) for cb in cb_vals]
                       + ["total"])
            rows = []
            for ra in ra_vals:
                cells = [res["table"][(ra, cb)] for cb in cb_vals]
                rows.append([self.vlabel(a, ra)] + cells + [sum(cells)])
            rows.append(["total"] + [sum(res["table"][(ra, cb)] for ra in ra_vals)
                                     for cb in cb_vals] + [res["n"]])
            self.rows(headers, rows)

        self.stats["associations"] = [
            {"a": a, "b": b, "n": res["n"], "v": res["v"], "p": res["p"],
             "p_holm": res["p_holm"], "min_expected": res["min_expected"]}
            for a, b, res in results]

    # -- profiles ---------------------------------------------------------

    def profiles(self, runs):
        self.h(2, "Whole answer profiles")
        counts = collections.Counter(r.code for r in runs if r.code)
        n = len(runs)
        self.p("%d distinct answer profile%s across %d respondent%s. A "
               "profile is the whole run, one character per question, and it "
               "is the share link's payload: append `#a=<profile>` to the "
               "quiz URL to open it."
               % (len(counts), "" if len(counts) == 1 else "s",
                  n, "" if n == 1 else "s"))
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
        rows = [[("`%s`" % code), pct(c, n)] for code, c in ranked
                if not (self.args.mode == "public" and c < self.args.min_cell)]
        if rows:
            self.rows(["Profile", "Respondents"], rows)
        elif self.args.mode == "public":
            self.p("Every profile is unique to one person, so none is shown: "
                   "in public mode a whole profile below `--min-cell` (%d) is "
                   "as identifying as a name." % self.args.min_cell)
        self.stats["distinct_profiles"] = len(counts)

    # -- assembly ---------------------------------------------------------

    def render(self):
        return "\n".join(self.lines).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser(
        description="Summarise the quiz response log.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Public mode is the default and is safe to publish; private "
               "mode includes non-consenting runs and identifying detail.")
    ap.add_argument("log", nargs="?", default="quiz-log.jsonl",
                    help="the JSONL written by serve_quiz.py (default: quiz-log.jsonl)")
    ap.add_argument("--mode", choices=("public", "private"), default="public",
                    help="public (default) drops non-consenting runs and all "
                         "identifying detail; private keeps everything and "
                         "stamps the report do-not-share")
    ap.add_argument("--dedupe", choices=("first", "last", "all"), default="first",
                    help="which of a respondent's runs to count: their first "
                         "(default - the answers they gave before seeing any "
                         "verdict), their last, or every run")
    ap.add_argument("--link-anon", action="store_true",
                    help="fold an unnamed run into a named respondent when "
                         "they share an (IP, user-agent) and only one name "
                         "has ever come from it")
    ap.add_argument("--file", default="population-ethics-quiz.html",
                    help="the quiz page, whose engine scores the conflicts "
                         "and bullets (default: population-ethics-quiz.html)")
    ap.add_argument("--no-engine", action="store_true",
                    help="skip the browser entirely; report only what the "
                         "answers alone give")
    ap.add_argument("--universe", type=int, default=4000,
                    help="random profiles used to enumerate the cards the "
                         "quiz can produce, so cards nobody hit can be shown "
                         "at 0 (default: 4000; 0 to skip)")
    ap.add_argument("--seed", type=int, default=20260901,
                    help="seed for the universe sweep (default: 20260901)")
    ap.add_argument("--min-cell", type=int, default=None,
                    help="in public mode, suppress non-zero counts below this "
                         "(default: 2 public, 1 private)")
    ap.add_argument("--min-assoc-n", type=int, default=20,
                    help="don't test a pair of questions with fewer than this "
                         "many respondents answering both (default: 20)")
    ap.add_argument("--top-assoc", type=int, default=15,
                    help="how many of the strongest associations to list "
                         "(default: 15)")
    ap.add_argument("--crosstabs", type=int, default=3,
                    help="how many of those to print as a cross-tab "
                         "(default: 3)")
    ap.add_argument("-o", "--out", help="also write the report to this file")
    ap.add_argument("--json", help="write the numbers to this file as JSON")
    args = ap.parse_args()

    if args.min_cell is None:
        args.min_cell = 2 if args.mode == "public" else 1

    try:
        all_runs, bad, blank = read_log(args.log)
    except IOError as e:
        sys.exit("cannot read %s: %s" % (args.log, e))
    if not all_runs:
        sys.exit("no usable runs in %s (%d unparseable lines)" % (args.log, bad))

    declined = [r for r in all_runs if r.consent_recorded and not r.consent]
    unrecorded = [r for r in all_runs if not r.consent_recorded]
    if args.mode == "public":
        kept = [r for r in all_runs if r.consent_recorded and r.consent]
    else:
        kept = list(all_runs)
    if not kept:
        sys.exit("no runs left after the consent filter; try --mode private "
                 "if you are the one holding the log")

    linked = assign_identities(kept, args.link_anon)
    groups = group_runs(kept)
    selected = select(groups, args.dedupe)

    engine, universe = None, None
    if not args.no_engine:
        try:
            engine = Engine(args.file)
        except ImportError:
            print("playwright not installed: skipping conflicts and bullets",
                  file=sys.stderr)
        except Exception as e:                       # a missing quiz file, say
            print("could not run the quiz engine (%s): skipping conflicts and "
                  "bullets" % e, file=sys.stderr)
    if engine:
        for r in selected:
            r.scored = engine.score(r.answers)
        incomplete = [r for r in selected if r.scored["missing"]]
        if incomplete:
            print("warning: %d run(s) are missing an answer to a live "
                  "question and are scored as given" % len(incomplete),
                  file=sys.stderr)
        if args.universe > 0:
            universe = engine.universe(args.universe, args.seed)
        if engine.errors:
            print("page errors: " + "; ".join(engine.errors), file=sys.stderr)

    rep = Report(args, engine)
    rep.lines += ["# Population ethics quiz - response log", ""]
    if args.mode == "private":
        rep.p(BANNER)
    rep.p("Generated %s from `%s` in **%s** mode, `--dedupe %s`."
          % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), args.log,
             args.mode, args.dedupe))
    if args.mode == "public":
        rep.p("Only runs whose taker consented to public aggregate analysis "
              "are included, and nothing below identifies anybody.")

    rep.corpus(all_runs, kept, len(declined), len(unrecorded), bad, blank)
    rep.respondents(groups, selected, linked)
    rep.answers(selected)
    rep.cards(selected, universe)
    rep.views(selected, load_views())
    rep.associations(selected)
    rep.profiles(selected)

    if args.mode == "private":
        rep.lines += ["", "---", "", BANNER, ""]

    text = rep.render()
    sys.stdout.write(text)
    if args.out:
        pathlib.Path(args.out).write_text(text, encoding="utf-8")
        print("wrote %s" % args.out, file=sys.stderr)
    if args.json:
        rep.stats["mode"] = args.mode
        rep.stats["dedupe"] = args.dedupe
        if args.mode == "private":
            rep.stats["warning"] = ("built in private mode: includes runs "
                                    "that did not consent to public "
                                    "aggregate analysis - do not publish")
        pathlib.Path(args.json).write_text(
            json.dumps(rep.stats, indent=2, sort_keys=True), encoding="utf-8")
        print("wrote %s" % args.json, file=sys.stderr)

    if engine:
        engine.close()


if __name__ == "__main__":
    main()
