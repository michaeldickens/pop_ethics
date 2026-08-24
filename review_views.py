#!/usr/bin/env python3
"""Render the named views in population_ethics_views.py as a review document.

Originally written by Claude Opus 5.

    python3 review_views.py --file population-ethics-quiz.html -o views-review.md

Each view is shown as its prose description, the answers it gives rendered in
the quiz's own words, and what the quiz then says back. The three are meant to
be read against each other.

--expect prints the same results as a Python literal, to paste into the
expectations table once they have been checked by eye.

--diff instead reports only what changed against the EXPECT already in
population_ethics_views.py -- the fast path for "did my edit change anything,
and if so what" -- and exits 1 if there is a difference to review.
"""

import argparse
import json
import pathlib
import re
import sys
import textwrap

from playwright.sync_api import sync_playwright

from population_ethics_views import VIEWS, EXPECT

PROBE = """(a) => {
  const keep = ANS;
  // Mirror showResults: answers to questions the person was never shown are
  // dropped before anything is scored. Without this a catalogue entry can
  // bullet on a question its own answers rule out.
  ANS = Object.assign({}, a);
  pruneInactive();
  const eff = ANS;
  const asked = QUESTIONS.filter(q => isActive(q)).map(q => q.id);
  const r = analyse(eff);
  const out = {
    asked: asked,
    claims: asked.map(id => [id, QUESTIONS.find(q => q.id === id).label,
      id === 'menu'
        ? (eff.menu === 'none' ? 'None of A, B and Z is best.'
                               : eff.menu + ' is the best of A, B and Z.')
        : claimText(id)]),
    conflicts: r.sets.map(S => {
      const ids = [...S].sort();
      const story = storyFor(S);
      return {ids: ids, title: story ? story.title : null};
    }).sort((x, y) => x.ids.join().localeCompare(y.ids.join())),
    alpha: r.alpha ? {picked: r.alpha.picked, over: r.alpha.pairWinner} : null,
    collapse: r.collapse
      ? {vague: r.collapse.vague.id, anchor: r.collapse.anchor.id, dir: r.collapse.dir}
      : null,
    greedy: r.greedy,
    bullets: bullets().map(b => b.t)
  };
  ANS = keep;
  return out;
}"""


def strip_tags(s):
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in [("&alpha;", "alpha"), ("&beta;", "beta"), ("&middot;", "-"),
                 ("&amp;", "&"), ("&rarr;", "->"), ("&larr;", "<-"),
                 ("\u2014", "--"), ("\u2019", "'"), ("\u201c", '"'),
                 ("\u201d", '"'), ("\u2212", "-")]:
        s = s.replace(a, b)
    return " ".join(s.split())


def collect(path):
    url = "file://" + str(pathlib.Path(path).resolve())
    out = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url)
        page.wait_for_timeout(700)
        for view in VIEWS:
            out.append((view, page.evaluate(PROBE, view["answers"])))
        browser.close()
    if errors:
        sys.exit("page errors: " + "; ".join(errors))
    return out


def expect_body(r):
    return {"conflicts": [c["ids"] for c in r["conflicts"]],
            "alpha": bool(r["alpha"]),
            "collapse": bool(r["collapse"]),
            "greedy": bool(r["greedy"]),
            "bullets": [strip_tags(b) for b in r["bullets"]],
            "asked": r["asked"]}


def as_expect(results):
    lines = ["EXPECT = {"]
    for view, r in results:
        lines.append("    %r: %r," % (view["key"], expect_body(r)))
    lines.append("}")
    return "\n".join(lines)


def as_diff(results):
    """Compare freshly computed results against EXPECT in population_ethics_views.py.

    Unlike --expect, which reprints every view's literal for a full manual
    paste, this only surfaces what actually moved -- the thing you need to
    re-review -- and catches EXPECT entries left behind by a renamed or
    deleted view.
    """
    lines, seen = [], set()
    for view, r in results:
        key = view["key"]
        seen.add(key)
        got = expect_body(r)
        want = EXPECT.get(key)
        if want is None:
            lines.append("%s: no EXPECT entry (new view)" % key)
            continue
        changed = [f for f in got if got[f] != want.get(f)]
        if changed:
            lines.append("%s:" % key)
            for f in changed:
                lines.append("  - %s: %r" % (f, want.get(f)))
                lines.append("  + %s: %r" % (f, got[f]))
    for key in EXPECT:
        if key not in seen:
            lines.append("%s: EXPECT entry has no matching view (stale)" % key)
    return "\n".join(lines) if lines else None


def as_markdown(results):
    doc = ["# Named views, and what the quiz says about them", "",
           "Read each view's description against the answers below it, then "
           "against the verdict. A description that does not match its answers "
           "is a bug in the catalogue; answers that do not match the verdict "
           "are a bug in the quiz.", ""]

    doc += ["## Contents", ""]
    for view, r in results:
        n = (len(r["conflicts"]) + bool(r["alpha"]) + bool(r["collapse"])
             + bool(r["greedy"]))
        summary = "clean" if n == 0 else ("%d conflict%s" % (n, "" if n == 1 else "s"))
        nb = len(r["bullets"])
        if nb:
            summary += ", %d bullet%s" % (nb, "" if nb == 1 else "s")
        doc.append("- [%s](#%s) - %s" % (view["name"], view["key"], summary))
    doc.append("")

    for view, r in results:
        doc += ['<a id="%s"></a>' % view["key"], "", "## %s" % view["name"], "",
                textwrap.fill(" ".join(view["blurb"].split()), 88), "",
                "### Answers", "",
                "| Question | What this view says |", "| --- | --- |"]
        for qid, label, claim in r["claims"]:
            doc.append("| %s | %s |" % (label, strip_tags(claim)))
        skipped = [q["id"] for q in [] ] or [
            k for k in ("collapse", "menu_eq") if k not in r["asked"]]
        if skipped:
            doc += ["", "Not asked: %s. These questions only appear when earlier "
                    "answers give them something to bite on." % ", ".join(skipped)]

        doc += ["", "### Verdict", ""]
        if not any((r["conflicts"], r["alpha"], r["collapse"], r["greedy"])):
            doc.append("No conflicts.")
        for c in r["conflicts"]:
            doc.append("- **%s** " % (c["title"] or "(no story: generic card)")
                       + "`%s`" % "+".join(c["ids"]))
        if r["alpha"]:
            doc.append("- **Contraction consistency (Sen's alpha)** - picked %s "
                       "over %s, having ranked %s higher in the pair."
                       % (r["alpha"]["picked"], r["alpha"]["over"], r["alpha"]["over"]))
        if r["collapse"]:
            doc.append("- **Collapsing principle** - %s unrankable, %s determinate, "
                       "running %swards."
                       % (r["collapse"]["vague"], r["collapse"]["anchor"],
                          r["collapse"]["dir"]))
        if r["greedy"]:
            doc.append("- **Greediness of neutrality** - the addition at %d is "
                       "unrankable against leaving it out, and K is ranked above "
                       "K+- all the same."
                       % r["greedy"]["level"])
        if r["bullets"]:
            doc += ["", "Bullets bitten:", ""]
            doc += ["- %s" % strip_tags(b) for b in r["bullets"]]
        doc.append("")
    return "\n".join(doc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="population-ethics-quiz.html")
    ap.add_argument("-o", "--out", default="views-review.md")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--expect", action="store_true",
                       help="print the expectations literal instead of the document")
    args = ap.parse_args()

    results = collect(args.file)
    if args.expect:
        print(as_expect(results))

    diff = as_diff(results)
    if diff is None:
        print("Expected views match actual views according to the quiz.")
    else:
        print("WARNING: Expected views do not match actual views according to the quiz.")
        print(diff)

    pathlib.Path(args.out).write_text(as_markdown(results))
    print("wrote %s (%d views)" % (args.out, len(results)))


if __name__ == "__main__":
    main()
