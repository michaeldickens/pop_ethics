#!/usr/bin/env python3
"""Summarise the response log written by serve_quiz.py.

    python3 analyze_logs.py quiz-log.jsonl                  # public report
    python3 analyze_logs.py --mode private quiz-log.jsonl    # everything, do not share
    python3 analyze_logs.py --dedupe last quiz-log.jsonl
    python3 analyze_logs.py --html report.html quiz-log.jsonl
    python3 analyze_logs.py --json stats.json -o report.md quiz-log.jsonl

The report prints as markdown, which is also readable as plain text.
--html writes the same report as a self-contained page - no CDN, no
plotting dependency - with each table drawn as a chart beside it.

The log is one JSON object per line: the server's fields (time, ip,
remote_addr, user_agent) wrapped around the client's `submission` (the
answers, the answer code, the consent choice, and a name if one was given).

Two modes, because the log holds two different kinds of thing:

  public   (default) drops every run that did not consent to public
           aggregate analysis, prints no names, addresses or user agents,
           and suppresses any cell smaller than --min-cell, since a full
           nineteen-answer profile held by one person is as identifying as
           a name. The output is meant to be publishable as it stands.

  private  keeps every run, consented or not, and names the people who
           gave a name. The report carries a do-not-share banner top and
           bottom.

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

Runs by a name on the exclusion list - the author's own test runs, "MD
Test", by default - are dropped from the corpus before anything is counted.
--exclude-name replaces that list, --keep-excluded turns it off.

Besides the per-question tallies there is a "modal answer" section: the
most popular answer to every question, assembled into one run and put back
through the quiz. A majority on each question separately can still be
jointly inconsistent, so the composite gets a verdict of its own.

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
    // Taken after pruning, so a question these answers never reach encodes
    // as a gap. Append it to the quiz URL as #a=<code> to open the run.
    code: encodeAns(),
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
# What the results page shows when a conflict's blamed answers match no story
# in the quiz: a card that says only what is true of every route to that
# contradiction. Several different answer shapes share the row.
NO_STORY = "(no story for this shape)"

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


# The quiz's author takes it repeatedly while working on it, under this name.
# Those runs are not survey responses and would skew a corpus this size, so
# they come out by default; --exclude-name replaces the list, --keep-excluded
# turns the filter off.
DEFAULT_EXCLUDED_NAMES = ["MD Test"]


def drop_excluded(groups, names):
    """Remove whole respondents whose name is on the exclusion list.

    Done per respondent rather than per run, so that a run linked to an
    excluded name by --link-anon goes with it rather than surviving as an
    anonymous stranger.
    """
    wanted = {norm_name(n) for n in names if n.strip()}
    dropped, kept = 0, collections.OrderedDict()
    for key, runs in groups.items():
        if key[0] == "name" and key[1] in wanted:
            dropped += len(runs)
            continue
        kept[key] = runs
    return kept, dropped


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
# Charts. Plain inline SVG, written by hand: the repo carries no plotting
# dependency and does not need one for bars and a line. Every chart here plots
# one series - a count against a category - so all of them use the one
# sequential hue rather than a categorical palette, and none needs a legend.
# Values are labelled on the marks, and the same numbers sit in the table
# beside every chart, so nothing is available only by hovering.
# ---------------------------------------------------------------------------

# Chart surface, ink and the blue ramp are CSS custom properties defined once
# in HTML_HEAD, so light and dark swap in one place and the SVG below is
# written against roles rather than hex.
BAR_H = 22          # mark thickness, under the 24px cap
BAND_H = 32         # leaves 10px of air between neighbouring bars
RADIUS = 4          # rounded data-end, square at the baseline


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _bar_path(x, y, w, h, r=RADIUS):
    """A bar with its data-end rounded and its baseline end square."""
    r = max(0.0, min(float(r), w))
    if r <= 0:
        return "M%.1f %.1f h%.1f v%.1f h%.1f Z" % (x, y, w, h, -w)
    return ("M%.1f %.1f h%.1f a%.1f %.1f 0 0 1 %.1f %.1f v%.1f "
            "a%.1f %.1f 0 0 1 %.1f %.1f h%.1f Z"
            % (x, y, w - r, r, r, r, r, h - 2 * r, r, r, -r, r, -(w - r)))


def _column_path(x, y, w, h, r=RADIUS):
    """The same bar stood up: rounded cap, square where it meets the axis."""
    r = max(0.0, min(float(r), h, w / 2.0))
    if r <= 0:
        return "M%.1f %.1f h%.1f v%.1f h%.1f Z" % (x, y, w, h, -w)
    return ("M%.1f %.1f a%.1f %.1f 0 0 1 %.1f %.1f h%.1f "
            "a%.1f %.1f 0 0 1 %.1f %.1f v%.1f h%.1f Z"
            % (x, y + r, r, r, r, -r, w - 2 * r, r, r, r, r, h - r, -w))


def _num(v):
    """Counts print as integers; a tie split between views does not."""
    return "%d" % v if float(v).is_integer() else "%.1f" % v


def _nice_max(v):
    """A round number at or above v, for an axis that ends somewhere sane."""
    if v <= 0:
        return 1
    step = 10 ** int(math.floor(math.log10(v)))
    for mult in (1, 2, 2.5, 5, 10):
        if step * mult >= v:
            return int(math.ceil(step * mult))
    return int(v)


# Rather than measure text (which would tie chart drawing to the browser),
# assume a per-character width comfortably above 12px system sans's average,
# so an estimate errs towards a wider gutter and a shorter label rather than
# towards a label that runs off its own chart. Whatever still will not fit is
# ellipsised, with the full text in the row's tooltip and in the table beside
# the chart, so nothing is lost.
CHAR_W = 7.0
LABEL_MIN, LABEL_MAX = 110, 380
LABEL_PAD = 24                  # gutter room the estimate is not asked to fill


def _clip(text, chars):
    text = str(text)
    return text if len(text) <= chars else text[:chars - 1].rstrip() + "…"


def chart_bar_h(rows, total=None, bar_w=300):
    """Horizontal bars: one count per category, category names on the left.

    Horizontal because the categories are sentences - the quiz's own answer
    wordings, and whole bullet titles - and a column chart would have to turn
    them on their side. The gutter grows to fit the labels, up to a cap.
    """
    rows = list(rows)
    if not rows:
        return ""
    label_chars = int((LABEL_MAX - LABEL_PAD) / CHAR_W)
    longest = max(len(_clip(l, label_chars)) for l, _ in rows)
    label_w = int(min(LABEL_MAX,
                      max(LABEL_MIN, longest * CHAR_W + LABEL_PAD)))
    # The tip label is the value and its share - "104 (100%)" at the widest -
    # and it sits 8px past the bar, so reserve enough that it never runs off.
    tip_w = int(8 + CHAR_W * max(len(_num(v)) + (7 if total else 0)
                                 for _, v in rows) + 6)
    width = label_w + bar_w + tip_w
    plot_x = label_w
    plot_w = bar_w
    top = 8
    height = top + len(rows) * BAND_H + 8
    hi = max([v for _, v in rows] + [1])
    out = ['<svg class="chart" viewBox="0 0 %d %d" width="%d" height="%d" '
           'role="img" xmlns="http://www.w3.org/2000/svg">'
           % (width, height, width, height)]
    for i, (label, value) in enumerate(rows):
        y = top + i * BAND_H
        by = y + (BAND_H - BAR_H) / 2.0
        w = plot_w * value / float(hi)
        share = "" if not total else " (%.0f%%)" % (100.0 * value / total)
        out.append('<text class="cat" x="%d" y="%.1f">%s</text>'
                   % (plot_x - 10, y + BAND_H / 2.0 + 4,
                      esc(_clip(label, label_chars))))
        if value:
            out.append('<path class="mark" d="%s"><title>%s: %s%s</title></path>'
                       % (_bar_path(plot_x, by, w, BAR_H), esc(label),
                          _num(value), share))
        out.append('<text class="val" x="%.1f" y="%.1f">%s%s</text>'
                   % (plot_x + w + 8, y + BAND_H / 2.0 + 4, _num(value), share))
    # The baseline every bar grows from, drawn last so no mark sits on it.
    out.append('<line class="axis" x1="%d" y1="%d" x2="%d" y2="%.1f"/>'
               % (plot_x, top, plot_x, top + len(rows) * BAND_H))
    out.append("</svg>")
    return "\n".join(out)


def chart_columns(rows, total=None, width=680, height=220):
    """Columns over an ordered scale - 0 conflicts, 1, 2, ... - so the shape
    of the distribution is the point rather than any single bar."""
    rows = list(rows)
    if not rows:
        return ""
    left, right, top, bottom = 44, 12, 18, 34
    plot_w = width - left - right
    plot_h = height - top - bottom
    hi = _nice_max(max([v for _, v in rows] + [1]))
    band = plot_w / float(len(rows))
    bw = min(24.0, band - 8)
    out = ['<svg class="chart" viewBox="0 0 %d %d" width="%d" height="%d" '
           'role="img" xmlns="http://www.w3.org/2000/svg">'
           % (width, height, width, height)]
    for t in (0, hi / 2.0, hi):
        y = top + plot_h - plot_h * t / float(hi)
        out.append('<line class="grid" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>'
                   % (left, y, width - right, y))
        out.append('<text class="tick" x="%d" y="%.1f">%g</text>'
                   % (left - 8, y + 4, round(t, 1)))
    for i, (label, value) in enumerate(rows):
        x = left + i * band + (band - bw) / 2.0
        h = plot_h * value / float(hi)
        share = "" if not total else " (%.0f%%)" % (100.0 * value / total)
        if value:
            out.append('<path class="mark" d="%s"><title>%s: %d%s</title></path>'
                       % (_column_path(x, top + plot_h - h, bw, h),
                          esc(label), value, share))
            out.append('<text class="cap" x="%.1f" y="%.1f">%d</text>'
                       % (x + bw / 2.0, top + plot_h - h - 6, value))
        out.append('<text class="cat mid" x="%.1f" y="%d">%s</text>'
                   % (x + bw / 2.0, height - 12, esc(label)))
    out.append('<line class="axis" x1="%d" y1="%d" x2="%d" y2="%d"/>'
               % (left, top + plot_h, width - right, top + plot_h))
    out.append("</svg>")
    return "\n".join(out)


def chart_line(points, width=680, height=200):
    """A count over time. One series, so a line with a wash under it."""
    points = list(points)
    if len(points) < 2:
        return chart_columns(points)
    left, right, top, bottom = 44, 12, 18, 30
    plot_w = width - left - right
    plot_h = height - top - bottom
    hi = _nice_max(max(v for _, v in points))
    xs = [left + plot_w * i / float(len(points) - 1)
          for i in range(len(points))]
    ys = [top + plot_h - plot_h * v / float(hi) for _, v in points]
    out = ['<svg class="chart" viewBox="0 0 %d %d" width="%d" height="%d" '
           'role="img" xmlns="http://www.w3.org/2000/svg">'
           % (width, height, width, height)]
    for t in (0, hi / 2.0, hi):
        y = top + plot_h - plot_h * t / float(hi)
        out.append('<line class="grid" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>'
                   % (left, y, width - right, y))
        out.append('<text class="tick" x="%d" y="%.1f">%g</text>'
                   % (left - 8, y + 4, round(t, 1)))
    area = ("M%.1f %.1f " % (xs[0], top + plot_h)
            + " ".join("L%.1f %.1f" % (x, y) for x, y in zip(xs, ys))
            + " L%.1f %.1f Z" % (xs[-1], top + plot_h))
    out.append('<path class="wash" d="%s"/>' % area)
    out.append('<path class="line" d="%s"/>'
               % ("M" + " L".join("%.1f %.1f" % (x, y) for x, y in zip(xs, ys))))
    for (label, value), x, y in zip(points, xs, ys):
        out.append('<circle class="hit" cx="%.1f" cy="%.1f" r="7">'
                   '<title>%s: %d</title></circle>' % (x, y, esc(label), value))
    out.append('<circle class="dot" cx="%.1f" cy="%.1f" r="4"/>'
               % (xs[-1], ys[-1]))
    # Only the ends are labelled: a tick under every day would be unreadable.
    out.append('<text class="cat start" x="%d" y="%d">%s</text>'
               % (left, height - 8, esc(points[0][0])))
    out.append('<text class="cat end" x="%d" y="%d">%s</text>'
               % (width - right, height - 8, esc(points[-1][0])))
    out.append('<line class="axis" x1="%d" y1="%d" x2="%d" y2="%d"/>'
               % (left, top + plot_h, width - right, top + plot_h))
    out.append("</svg>")
    return "\n".join(out)


CHARTS = {"bar_h": chart_bar_h, "columns": chart_columns, "line": chart_line}

# Values from the reference palette: blue as the single sequential hue, with
# its own dark step, plus that palette's chart chrome and ink. Declared under
# both the media query and the data-theme scope so a viewer's explicit choice
# wins in either direction.
HTML_HEAD = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<style>
:root{
  color-scheme: light;
  --plane:#f9f9f7; --surface:#fcfcfb;
  --ink:#0b0b0b; --ink-2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --axis:#c3c2b7; --rule:rgba(11,11,11,.10);
  --series:#2a78d6; --wash:rgba(42,120,214,.10);
  --warn-bg:#fdf3e3; --warn-ink:#7a4a06; --warn-edge:#eda100;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --plane:#0d0d0d; --surface:#1a1a19;
    --ink:#fff; --ink-2:#c3c2b7; --muted:#898781;
    --grid:#2c2c2a; --axis:#383835; --rule:rgba(255,255,255,.10);
    --series:#3987e5; --wash:rgba(57,135,229,.12);
    --warn-bg:#2a2213; --warn-ink:#eda100; --warn-edge:#c98500;
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --plane:#0d0d0d; --surface:#1a1a19;
  --ink:#fff; --ink-2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --axis:#383835; --rule:rgba(255,255,255,.10);
  --series:#3987e5; --wash:rgba(57,135,229,.12);
  --warn-bg:#2a2213; --warn-ink:#eda100; --warn-edge:#c98500;
}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--ink);
  font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:820px;margin:0 auto;padding:40px 20px 80px}
h1{font-size:28px;line-height:1.2;margin:0 0 6px}
h2{font-size:21px;margin:44px 0 8px;padding-top:18px;border-top:1px solid var(--rule)}
h3{font-size:16px;margin:28px 0 6px}
p{margin:10px 0;color:var(--ink-2);max-width:70ch}
code{font:13px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;
  background:var(--surface);border:1px solid var(--rule);
  border-radius:4px;padding:1px 5px}
figure{margin:14px 0;padding:12px 4px;background:var(--surface);
  border:1px solid var(--rule);border-radius:8px;overflow-x:auto}
svg.chart{display:block;max-width:100%%;height:auto}
.chart .mark{fill:var(--series)}
.chart .line{fill:none;stroke:var(--series);stroke-width:2;
  stroke-linejoin:round;stroke-linecap:round}
.chart .wash{fill:var(--wash)}
.chart .dot{fill:var(--series);stroke:var(--surface);stroke-width:2}
.chart .hit{fill:transparent}
.chart .grid{stroke:var(--grid);stroke-width:1}
.chart .axis{stroke:var(--axis);stroke-width:1}
.chart text{font:12px system-ui,-apple-system,"Segoe UI",sans-serif}
.chart .cat{fill:var(--ink-2);text-anchor:end}
.chart .cat.mid{text-anchor:middle}
.chart .cat.end{text-anchor:end}
.chart .cat.start{text-anchor:start}
.chart .val,.chart .cap{fill:var(--ink-2);font-variant-numeric:tabular-nums}
.chart .cap{text-anchor:middle}
.chart .tick{fill:var(--muted);text-anchor:end;font-variant-numeric:tabular-nums}
.chart .mark:hover{fill-opacity:.78}
.tablewrap{overflow-x:auto;margin:14px 0}
table{border-collapse:collapse;font-size:14px;min-width:100%%}
th,td{text-align:left;padding:6px 12px 6px 0;border-bottom:1px solid var(--rule);
  vertical-align:top;white-space:nowrap}
th{color:var(--muted);font-weight:600;font-size:12px;
  text-transform:uppercase;letter-spacing:.04em}
td{font-variant-numeric:tabular-nums}
td:first-child,th:first-child{white-space:normal}
blockquote{margin:18px 0;padding:12px 16px;border-left:3px solid var(--warn-edge);
  background:var(--warn-bg);color:var(--warn-ink);border-radius:0 6px 6px 0}
blockquote p{color:inherit}
</style>
<main>
"""


# ---------------------------------------------------------------------------
# Report. Sections append blocks - headings, prose, tables, charts - and the
# two renderers walk them, so the markdown and the HTML cannot drift apart.
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
    "**PRIVATE - DO NOT SHARE.** This report was built in private mode. It "
    "includes runs whose takers did not consent to public aggregate "
    "analysis, and it prints the names people gave beside their answers. "
    "Publishing any of it, in whole or in part, breaks a promise made on the "
    "quiz's own consent checkbox. Use `--mode public` for a report that can "
    "be shared."
)


class Report(object):

    def __init__(self, args, engine):
        self.args = args
        self.engine = engine
        self.blocks = []
        self.stats = {}
        # Filled in properly once the answers section has seen the log; set
        # here because the respondents section names questions too.
        self.meta_by_id = {q["id"]: q for q in
                           (engine.meta["questions"] if engine else [])}

    def h(self, level, text):
        self.blocks.append(("h", level, text))

    def p(self, text):
        self.blocks.append(("p", text))

    def quote(self, text):
        self.blocks.append(("quote", text))

    def rows(self, headers, rows, chart=None, data=None, total=None):
        """A table, optionally with a chart of the same numbers beside it.

        The table is the record - it carries every figure and survives being
        read as plain text. The chart is drawn only in the HTML report, from
        `data` (label, value pairs) rather than from the formatted cells.
        """
        if not rows:
            self.p("(nothing to show)")
            return
        if chart and data:
            self.blocks.append(("chart", chart, list(data), total))
        self.blocks.append(("table", headers, rows))

    # -- sections ---------------------------------------------------------

    def corpus(self, all_runs, kept, dropped_consent, dropped_unrecorded, bad,
               blank, dropped_named):
        self.h(2, "The corpus")
        times = [r.time for r in kept if r.time]
        rows = [
            ["Lines in the log", len(all_runs) + bad + blank],
            ["Unparseable / skipped", bad + blank],
            ["Runs read", len(all_runs)],
        ]
        if dropped_named:
            rows.append(["Dropped: excluded by name", dropped_named])
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
            # Every day between the first run and the last, so a quiet stretch
            # shows as a trough rather than closing up.
            first, last = min(times).date(), max(times).date()
            per_day = collections.Counter(t.date().isoformat() for t in times)
            days = [(first + datetime.timedelta(days=i)).isoformat()
                    for i in range((last - first).days + 1)]
            self.h(3, "Runs per day")
            self.rows(["Day", "Runs"], [[d, per_day.get(d, 0)] for d in days],
                      chart="line", data=[(d, per_day.get(d, 0)) for d in days])

        self.stats["corpus"] = {
            "lines": len(all_runs) + bad + blank, "unparseable": bad + blank,
            "runs_read": len(all_runs), "runs_analysed": len(kept),
            "dropped_consent_declined": dropped_consent,
            "dropped_consent_unrecorded": dropped_unrecorded,
            "dropped_excluded_by_name": dropped_named,
            "consent_rate": (consented / float(recorded)) if recorded else None,
            "named_runs": named,
            "first": min(times).isoformat() if times else None,
            "last": max(times).isoformat() if times else None,
        }

    def respondents(self, groups, selected, linked, excluded_runs):
        self.h(2, "Respondents")
        if excluded_runs:
            self.p("Excluded by name (%s): %d run%s, dropped before any of "
                   "the counts below. `--keep-excluded` keeps them."
                   % (", ".join(self.args.exclude_name), excluded_runs,
                      "" if excluded_runs == 1 else "s"))
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
            self.p("Only the people who gave a name. The rest are known to "
                   "the log by an address and a browser string, which would "
                   "make this a list of IP addresses without telling you "
                   "anything the counts above have not already said.")
            rows = []
            for key, runs in groups.items():
                # Names are matched case- and space-insensitively but shown as
                # last typed, which is what the person would recognise.
                typed = [r.name for r in runs if r.name]
                if not typed:
                    # skip anyone without a name
                    continue
                who = typed[-1]
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
            self.rows(["Answer", "Value", "Respondents"], rows,
                      chart="bar_h", total=n,
                      data=[(strip_tags(dict(opts).get(v, v)), counts.get(v, 0))
                            for v in values])
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
        # A generic card is one whose blamed answers match no story in the
        # quiz, so several routes to the same contradiction share the row.
        # Which routes those were is worth its own table below.
        untold = collections.Counter()
        for r in runs:
            keys = set()
            for c in r.scored["conflicts"]:
                key = ("+".join(c["ids"]), card_key(c["title"] or NO_STORY))
                keys.add(key)
                titles[key] = card_key(c["title"] or NO_STORY)
                idsets[key] = "+".join(c["ids"])
                if not c["title"]:
                    untold[("+".join(c["ids"]),
                            ", ".join("%s=%s" % (q, r.scored["answers"].get(q))
                                      for q in c["ids"]))] += 1
            for x in r.scored["extras"]:
                key = ("extra:" + x["id"], card_key(x["title"]))
                keys.add(key)
                titles[key] = card_key(x["title"])
                idsets[key] = x["id"]
            seen.update(keys)

        universe_keys = {}
        if universe:
            for c in universe["conflicts"]:
                key = ("+".join(c["ids"]), card_key(c["title"] or NO_STORY))
                universe_keys[key] = ("+".join(c["ids"]),
                                      card_key(c["title"] or NO_STORY))
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
            rows.append([title, "`%s`" % ids, pct(c, n), c])
        rows.sort(key=lambda r: (-r[3], r[0], r[1]))
        self.rows(["Conflict card", "Answers blamed", "Respondents"],
                  [r[:3] for r in rows], chart="bar_h", total=n,
                  data=[(r[0], r[3]) for r in rows if r[3]])
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

        if untold:
            self.h(3, "Conflicts the quiz has no story for")
            self.p("A conflict card carries prose only when the answers "
                   "behind it match one of the quiz's stories, and a story "
                   "names both a set of blamed answers *and* the shape of "
                   "the answers it describes. The same set reached by a "
                   "different route falls through to `%s`, which says only "
                   "what holds of every route - so one blamed set can appear "
                   "twice in the table above, once told and once not. These "
                   "are the routes people here actually took." % NO_STORY)
            urows = [[ids, shape, pct(c, n)]
                     for (ids, shape), c in
                     sorted(untold.items(), key=lambda kv: (-kv[1], kv[0]))
                     if not (self.args.mode == "public"
                             and c < self.args.min_cell)]
            self.rows(["Answers blamed", "The route they took", "Respondents"],
                      urows)
            self.stats["conflicts_without_a_story"] = {
                "%s | %s" % k: v for k, v in untold.items()}

        counts = [len(r.scored["conflicts"]) + len(r.scored["extras"]) for r in runs]
        dist = collections.Counter(counts)
        self.h(3, "How many conflicts each person had")
        span = range(0, max(dist) + 1) if dist else []
        self.rows(["Conflicts", "Respondents"],
                  [[k, pct(dist.get(k, 0), n)] for k in span],
                  chart="columns", total=n,
                  data=[(str(k), dist.get(k, 0)) for k in span])
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
            rows.append([b, pct(c, n), c])
        rows.sort(key=lambda r: (-r[2], r[0]))
        self.rows(["Bullet", "Respondents"], [r[:2] for r in rows],
                  chart="bar_h", total=n,
                  data=[(r[0], r[2]) for r in rows if r[2]])
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
        bspan = range(0, max(bdist) + 1) if bdist else []
        self.rows(["Bullets", "Respondents"],
                  [[k, pct(bdist.get(k, 0), n)] for k in bspan],
                  chart="columns", total=n,
                  data=[(str(k), bdist.get(k, 0)) for k in bspan])
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

    # -- the modal answer --------------------------------------------------

    def modal(self, runs, views):
        """Take the most popular answer to every question, and see what the
        quiz makes of the run they add up to.

        It is a construction, not a person: the composite is nobody's answers
        unless somebody happens to have given exactly them, and a majority on
        each question separately can still be jointly inconsistent - which is
        the interesting case, and why it is run through the engine rather
        than just tabulated.
        """
        self.h(2, "The modal answer")
        qs = (self.engine.meta["questions"] if self.engine
              else self.fallback_questions(runs))
        n = len(runs)
        modal, rows, data = {}, [], []
        for q in qs:
            asked = [self.effective(r)[q["id"]] for r in runs
                     if q["id"] in self.effective(r)]
            if not asked:
                continue
            counts = collections.Counter(asked)
            # Ties go to the answer the quiz offers first, so the composite is
            # reproducible rather than dependent on iteration order.
            order = {v: i for i, (v, _) in enumerate(q.get("opts") or [])}
            top = min(counts, key=lambda v: (-counts[v], order.get(v, 99), v))
            modal[q["id"]] = top
            rows.append([q["label"], self.vlabel(q["id"], top, 60),
                         "`%s`" % top, pct(counts[top], len(asked))])
            data.append((q["label"], counts[top]))
        if not modal:
            self.p("(no answers to take a mode of)")
            return

        self.p("The most popular answer to each question, over the people who "
               "were asked it. Where a question was only put to some of them, "
               "its mode is that subgroup's, which is why the composite can "
               "include an answer most respondents never gave.")

        scored = self.engine.score(modal) if self.engine else None
        if scored:
            # Pruning can retire a question whose mode was taken over the
            # people who did see it, so report the composite the engine
            # actually scored rather than the one assembled above.
            kept = scored["answers"]
            dropped = [q["label"] for q in qs
                       if q["id"] in modal and q["id"] not in kept]
            rows = [r for r, q in zip(rows, [q for q in qs if q["id"] in modal])
                    if q["id"] in kept]
            data = [d for d, q in zip(data, [q for q in qs if q["id"] in modal])
                    if q["id"] in kept]
        self.rows(["Question", "Modal answer", "Value", "Of those asked"],
                  rows, chart="bar_h", total=n, data=data)

        if not scored:
            self.p("*The verdict on this composite needs the quiz's engine; "
                   "see the note under Conflicts.*")
            self.stats["modal_answers"] = modal
            return

        if dropped:
            self.p("Dropped from the composite, because the other modal "
                   "answers never raise %s: %s."
                   % ("it" if len(dropped) == 1 else "them",
                      ", ".join(dropped)))
        self.p("Open it: append `#a=%s` to the quiz URL." % scored["code"])

        exact = self.modal_reach(runs, kept, n)

        cards = [c["title"] or NO_STORY for c in scored["conflicts"]]
        cards += [x["title"] for x in scored["extras"]]
        self.h(3, "What the quiz says back to it")
        if cards:
            self.p("The composite is **not internally consistent**: a "
                   "majority on each question separately still adds up to a "
                   "set of claims that cannot all hold.")
            self.rows(["Conflict"], [[card_key(c)] for c in cards])
        else:
            self.p("The composite is **internally consistent** - no conflict "
                   "card. Every majority answer can be held alongside the "
                   "others.")
        if scored["bullets"]:
            self.rows(["Bullet bitten"],
                      [[card_key(b)] for b in scored["bullets"]])
        else:
            self.p("It bites no bullets.")

        if views:
            best = nearest_view(views, kept)
            if best:
                score, names, _ = best
                self.p("Nearest catalogued view: %s, agreeing on %.0f%% of "
                       "the answers."
                       % (", ".join(name for _, name in names), 100.0 * score))

        self.stats["modal"] = {
            "answers": kept, "code": scored["code"], "exact_matches": exact,
            "conflicts": [card_key(c) for c in cards],
            "bullets": [card_key(b) for b in scored["bullets"]],
        }

    def modal_reach(self, runs, kept, n):
        """How near anybody actually got to the composite, and who is nearest.

        Nobody matching it exactly is the normal case rather than a finding:
        agreeing with a dozen separate majorities at once is a product of a
        dozen fractions. What is worth knowing is whether the misses are
        scattered - lots of people one or two answers off in different places,
        so the composite really is the centre - or concentrated, with a large
        block missing it on the same few questions, which means the mode has
        blended two camps into a position neither holds.
        """
        qs = sorted(kept)
        profiles = collections.Counter(
            tuple(self.effective(r).get(q) for q in qs) for r in runs)
        target = tuple(kept[q] for q in qs)
        exact = profiles.get(target, 0)
        dist = collections.Counter()
        for profile, c in profiles.items():
            dist[sum(1 for a, b in zip(profile, target) if a != b)] += c

        # What agreeing with every majority at once would come to if the
        # questions were answered independently. They are not - that is rather
        # the point - but it says whether nobody matching is even surprising.
        expected = float(n)
        for q in qs:
            asked = [r for r in runs if q in self.effective(r)]
            if asked:
                expected *= (sum(1 for r in asked
                                 if self.effective(r)[q] == kept[q])
                             / float(len(asked)))

        self.p("%s gave exactly this set of answers. Agreeing with all %d "
               "majorities at once would be expected of about %.1f "
               "%s even if the questions were answered independently, so "
               "nobody landing on it is not by itself a surprise."
               % (pct(exact, n), len(qs), expected,
                  "person" if 0.5 <= expected < 1.5 else "people"))
        misses = sorted(d for d in dist if d)
        if misses:
            closest = misses[0]
            self.p("The nearest anybody came was %d answer%s away, and %s "
                   "got that close."
                   % (closest, "" if closest == 1 else "s",
                      pct(dist[closest], n)))
        self.h(3, "Where people part company with it")
        span = range(0, max(dist) + 1) if dist else []
        self.rows(["Answers differing", "Respondents"],
                  [[d, pct(dist.get(d, 0), n)] for d in span],
                  chart="columns", total=n,
                  data=[(str(d), dist.get(d, 0)) for d in span])

        # The largest block of people who answered these questions alike. If
        # it is not the composite, it is the more informative number: a real
        # position that real people hold, against a construction nobody does.
        top, tc = profiles.most_common(1)[0]
        if top != target and not (self.args.mode == "public"
                                  and tc < self.args.min_cell):
            differs = [q for q, a in zip(qs, top) if a != kept[q]]
            self.p("The largest block who answered these questions alike is "
                   "%s - bigger than any group the composite has - and it is "
                   "not the composite. They part from it on %d of the %d: %s."
                   % (pct(tc, n), len(differs), len(qs),
                      ", ".join(self.qlabel(q) for q in differs)))
            self.p("Where a block that size misses on the same handful of "
                   "questions, the per-question majorities are coming from "
                   "camps that disagree with each other, and the composite "
                   "takes one camp's answer here and the other's there. That "
                   "is worth checking against the verdict below: a "
                   "composite can be inconsistent because the population is "
                   "split, rather than because anybody holds an inconsistent "
                   "view.")
        self.stats["modal_distance"] = dict(dist)
        self.stats["modal_largest_block"] = tc
        return exact

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
        ranked = [(k, v) for k, v in
                  sorted(hits.items(), key=lambda kv: (-kv[1], kv[0][0]))
                  if not (self.args.mode == "public" and v < self.args.min_cell)]
        rows = [[name, "`%s`" % key, "%.1f" % v,
                 "%.0f%%" % (100.0 * v / len(runs)) if runs else "-"]
                for (key, name), v in ranked]
        self.rows(["View", "Key", "Respondents (ties split)", "Share"], rows,
                  chart="bar_h", total=len(runs),
                  data=[(name, v) for (key, name), v in ranked[:15] if v])
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
        """Markdown, which is also the plain-text form printed to stdout."""
        lines = []
        for block in self.blocks:
            kind = block[0]
            if kind == "h":
                lines += ["", "#" * block[1] + " " + block[2], ""]
            elif kind == "p":
                lines += [block[1], ""]
            elif kind == "quote":
                lines += ["> " + block[1], ""]
            elif kind == "table":
                lines += table(block[1], block[2]) + [""]
            # Charts are an HTML-only block; the table beside each one carries
            # the same numbers, so nothing is lost here.
        return "\n".join(lines).strip() + "\n"

    def render_html(self, title):
        out = [HTML_HEAD % {"title": esc(title)}]
        for block in self.blocks:
            kind = block[0]
            if kind == "h":
                out.append("<h%d>%s</h%d>"
                           % (block[1], inline_html(block[2]), block[1]))
            elif kind == "p":
                out.append("<p>%s</p>" % inline_html(block[1]))
            elif kind == "quote":
                out.append("<blockquote><p>%s</p></blockquote>"
                           % inline_html(block[1]))
            elif kind == "table":
                out.append(html_table(block[1], block[2]))
            elif kind == "chart":
                svg = CHARTS[block[1]](block[2], total=block[3]) \
                    if block[1] != "line" else CHARTS[block[1]](block[2])
                if svg:
                    out.append("<figure>%s</figure>" % svg)
        out.append("</main>")
        return "\n".join(out) + "\n"


def inline_html(text):
    """The little markdown the report actually uses, as HTML."""
    text = str(text)                        # table cells are often plain ints
    out, i = [], 0
    for m in re.finditer(r"`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*", text):
        out.append(esc(text[i:m.start()]))
        if m.group(1) is not None:
            out.append("<code>%s</code>" % esc(m.group(1)))
        elif m.group(2) is not None:
            out.append("<strong>%s</strong>" % esc(m.group(2)))
        else:
            out.append("<em>%s</em>" % esc(m.group(3)))
        i = m.end()
    out.append(esc(text[i:]))
    return "".join(out)


def html_table(headers, rows):
    out = ['<div class="tablewrap"><table><thead><tr>']
    out += ["<th>%s</th>" % inline_html(h) for h in headers]
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>"
                   + "".join("<td>%s</td>" % inline_html(c) for c in row)
                   + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


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
    ap.add_argument("--exclude-name", action="append", metavar="NAME",
                    help="drop every run by this name, and by anything "
                         "--link-anon folds into it. Repeatable; giving it at "
                         "all replaces the default list (%s)"
                         % ", ".join(DEFAULT_EXCLUDED_NAMES))
    ap.add_argument("--keep-excluded", action="store_true",
                    help="keep the runs --exclude-name would drop")
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
    ap.add_argument("--html", metavar="PATH",
                    help="write the report to this file as a self-contained "
                         "HTML page, with the tables drawn as charts")
    ap.add_argument("--json", help="write the numbers to this file as JSON")
    args = ap.parse_args()

    if args.min_cell is None:
        args.min_cell = 2 if args.mode == "public" else 1
    if args.exclude_name is None:
        args.exclude_name = list(DEFAULT_EXCLUDED_NAMES)
    if args.keep_excluded:
        args.exclude_name = []

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
    groups, excluded_runs = drop_excluded(groups, args.exclude_name)
    if not groups:
        sys.exit("every respondent was excluded by name; --keep-excluded "
                 "keeps them")
    if excluded_runs:
        # Out of the corpus entirely, not just out of the tables: they are the
        # author testing the quiz, not responses.
        survivors = {id(r) for runs in groups.values() for r in runs}
        kept = [r for r in kept if id(r) in survivors]
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

    title = "Population ethics quiz - response log"
    views = load_views()
    rep = Report(args, engine)
    rep.h(1, title)
    if args.mode == "private":
        rep.quote(BANNER)
    rep.p("Generated %s from `%s` in **%s** mode, `--dedupe %s`."
          % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), args.log,
             args.mode, args.dedupe))
    if args.mode == "public":
        rep.p("Only runs whose taker consented to public aggregate analysis "
              "are included, and nothing below identifies anybody.")

    rep.corpus(all_runs, kept, len(declined), len(unrecorded), bad, blank,
               excluded_runs)
    rep.respondents(groups, selected, linked, excluded_runs)
    rep.answers(selected)
    rep.modal(selected, views)
    rep.cards(selected, universe)
    rep.views(selected, views)
    rep.associations(selected)
    rep.profiles(selected)

    if args.mode == "private":
        rep.quote(BANNER)

    text = rep.render()
    sys.stdout.write(text)
    if args.out:
        pathlib.Path(args.out).write_text(text, encoding="utf-8")
        print("wrote %s" % args.out, file=sys.stderr)
    if args.html:
        pathlib.Path(args.html).write_text(rep.render_html(title),
                                           encoding="utf-8")
        print("wrote %s" % args.html, file=sys.stderr)
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
